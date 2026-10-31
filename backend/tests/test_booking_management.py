from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

import pytest
from apps.bookings.application import errors as booking_errors
from apps.bookings.application.availability import AvailabilityGateway
from apps.bookings.application.booking import BookingResult, BookingService
from apps.bookings.application.management import BookingManagementService
from apps.bookings.container import (
    build_appointment_repository,
    build_customer_repository,
    build_management_service,
    build_reminder_repository,
)
from apps.bookings.domain.status import AppointmentStatus, CancelledBy, ReminderStatus
from apps.bookings.infrastructure.models import Appointment, Reminder
from apps.businesses.infrastructure.models import Business
from apps.businesses.infrastructure.repositories import DjangoBusinessRepository
from apps.catalog.infrastructure.models import Service, Staff, StaffService
from apps.catalog.infrastructure.repositories import (
    DjangoServiceRepository,
    DjangoStaffRepository,
)
from apps.core.infrastructure.unit_of_work import DjangoUnitOfWork
from apps.notifications.container import build_notification_service
from apps.notifications.infrastructure.senders import FakeNotificationSender
from apps.scheduling.application.availability import AvailabilityService
from apps.scheduling.infrastructure.models import WorkingHours
from apps.scheduling.infrastructure.repositories import (
    DjangoTimeOffRepository,
    DjangoWorkingHoursRepository,
)

STARTS_AT = datetime(2026, 11, 2, 6, 15, tzinfo=UTC)


@dataclass
class MutableClock:
    value: datetime

    def now(self) -> datetime:
        return self.value


def _availability(now: datetime) -> AvailabilityService:
    return AvailabilityService(
        business_repository=DjangoBusinessRepository(),
        service_repository=DjangoServiceRepository(),
        staff_repository=DjangoStaffRepository(),
        working_hours_repository=DjangoWorkingHoursRepository(),
        time_off_repository=DjangoTimeOffRepository(),
        appointment_repository=build_appointment_repository(),
        clock=MutableClock(now),
    )


def _booking_service(now: datetime) -> BookingService:
    return BookingService(
        business_repository=DjangoBusinessRepository(),
        service_repository=DjangoServiceRepository(),
        staff_repository=DjangoStaffRepository(),
        customer_repository=build_customer_repository(),
        appointment_repository=build_appointment_repository(),
        reminder_repository=build_reminder_repository(),
        availability=AvailabilityGateway(_availability(now)),
        unit_of_work=DjangoUnitOfWork(),
        notifier=build_notification_service(
            sender=FakeNotificationSender(), base_url="https://mawid.test"
        ),
    )


def _management_service(
    clock: MutableClock,
    sender: FakeNotificationSender | None = None,
) -> BookingManagementService:
    return BookingManagementService(
        business_repository=DjangoBusinessRepository(),
        service_repository=DjangoServiceRepository(),
        staff_repository=DjangoStaffRepository(),
        customer_repository=build_customer_repository(),
        appointment_repository=build_appointment_repository(),
        reminder_repository=build_reminder_repository(),
        availability=AvailabilityGateway(_availability(clock.value)),
        unit_of_work=DjangoUnitOfWork(),
        clock=clock,
        notifier=build_notification_service(
            sender=sender or FakeNotificationSender(),
            base_url="https://mawid.test",
        ),
    )


def _setup(business: Business, service: Service, staff: Staff) -> BookingResult:
    WorkingHours.objects.create(staff=staff, weekday=0, start_time=time(9), end_time=time(17))
    StaffService.objects.create(staff=staff, service=service)
    return _booking_service(datetime(2026, 10, 24, 8, tzinfo=UTC)).create(
        service_id=service.id,
        staff_id=staff.id,
        starts_at=STARTS_AT,
        customer_name="Layla",
        customer_email="layla@example.com",
        customer_language="ar",
    )


def test_resolves_a_valid_management_link(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    booking = _setup(business, service, staff)
    managed = _management_service(MutableClock(datetime(2026, 10, 30, 8, tzinfo=UTC))).get(
        booking.management_token
    )

    assert managed.appointment.id == booking.appointment.id
    assert managed.customer.id == booking.customer.id
    assert managed.service.id == service.id
    assert managed.staff.id == staff.id


def test_rejects_invalid_and_expired_links(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    booking = _setup(business, service, staff)
    clock = MutableClock(datetime(2026, 10, 30, 8, tzinfo=UTC))
    management = _management_service(clock)

    with pytest.raises(booking_errors.ManagementTokenInvalidError):
        management.get("not-a-token")

    clock.value = STARTS_AT + timedelta(days=8)
    with pytest.raises(booking_errors.ManagementTokenInvalidError):
        management.get(booking.management_token)


def test_customer_cancels_within_policy(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    booking = _setup(business, service, staff)
    clock = MutableClock(datetime(2026, 10, 30, 8, tzinfo=UTC))
    management = _management_service(clock)

    cancelled = management.cancel(
        booking.management_token,
        reason=" Schedule conflict ",
        actor=CancelledBy.CUSTOMER,
    )

    assert cancelled.appointment.status == AppointmentStatus.CANCELLED
    assert cancelled.appointment.cancelled_at == clock.value
    assert cancelled.appointment.cancelled_by == CancelledBy.CUSTOMER.value
    assert cancelled.appointment.cancellation_reason == "Schedule conflict"
    assert cancelled.appointment.management_token_hash is None
    assert cancelled.appointment.management_token_expires_at is None
    reminder = Reminder.objects.get(appointment_id=booking.appointment.id)
    assert reminder.status == ReminderStatus.CANCELLED.value

    with pytest.raises(booking_errors.ManagementTokenInvalidError):
        management.get(booking.management_token)


def test_customer_cannot_cancel_inside_the_window(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    booking = _setup(business, service, staff)
    clock = MutableClock(STARTS_AT - timedelta(hours=2))
    management = _management_service(clock)

    with pytest.raises(booking_errors.CancellationNotAllowedError):
        management.cancel(booking.management_token)

    assert Appointment.objects.get(pk=booking.appointment.id).status == (
        AppointmentStatus.PENDING.value
    )


def test_staff_can_cancel_inside_the_window(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    booking = _setup(business, service, staff)
    clock = MutableClock(STARTS_AT - timedelta(hours=2))
    management = _management_service(clock)

    cancelled = management.cancel(
        booking.management_token,
        actor=CancelledBy.STAFF,
        enforce_policy=False,
    )

    assert cancelled.appointment.status == AppointmentStatus.CANCELLED
    assert cancelled.appointment.cancelled_by == CancelledBy.STAFF.value


def test_reschedule_moves_the_booking_and_rotates_the_link(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    booking = _setup(business, service, staff)
    clock = MutableClock(datetime(2026, 10, 30, 8, tzinfo=UTC))
    management = _management_service(clock)
    new_start = datetime(2026, 11, 2, 7, 0, tzinfo=UTC)

    moved = management.reschedule(booking.management_token, starts_at=new_start)

    assert moved.appointment.id != booking.appointment.id
    assert moved.appointment.starts_at == new_start
    assert moved.appointment.ends_at == new_start + timedelta(minutes=30)
    assert moved.appointment.status == AppointmentStatus.PENDING
    assert moved.appointment.rescheduled_from_id == booking.appointment.id
    assert moved.appointment.idempotency_key is None

    original = Appointment.objects.get(pk=booking.appointment.id)
    assert original.status == AppointmentStatus.CANCELLED.value
    assert original.management_token_hash is None
    assert Reminder.objects.get(appointment_id=original.id).status == (
        ReminderStatus.CANCELLED.value
    )
    new_reminder = Reminder.objects.get(appointment_id=moved.appointment.id)
    assert new_reminder.status == ReminderStatus.PENDING.value
    assert new_reminder.send_at == new_start - timedelta(hours=24)

    with pytest.raises(booking_errors.ManagementTokenInvalidError):
        management.get(booking.management_token)
    assert management.get(moved.management_token).appointment.id == moved.appointment.id


def test_reschedule_rejects_a_taken_slot(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    booking = _setup(business, service, staff)
    _booking_service(datetime(2026, 10, 24, 8, tzinfo=UTC)).create(
        service_id=service.id,
        staff_id=staff.id,
        starts_at=datetime(2026, 11, 2, 7, 0, tzinfo=UTC),
        customer_name="Other",
        customer_email="other@example.com",
    )
    management = _management_service(MutableClock(datetime(2026, 10, 30, 8, tzinfo=UTC)))

    with pytest.raises(booking_errors.SlotUnavailableError):
        management.reschedule(
            booking.management_token,
            starts_at=datetime(2026, 11, 2, 7, 0, tzinfo=UTC),
        )

    original = Appointment.objects.get(pk=booking.appointment.id)
    assert original.status == AppointmentStatus.PENDING.value


def test_reschedule_respects_the_cancellation_window(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    booking = _setup(business, service, staff)
    management = _management_service(MutableClock(STARTS_AT - timedelta(hours=2)))

    with pytest.raises(booking_errors.CancellationNotAllowedError):
        management.reschedule(
            booking.management_token,
            starts_at=datetime(2026, 11, 2, 7, 0, tzinfo=UTC),
        )


def test_container_builds_management_service() -> None:
    assert isinstance(build_management_service(), BookingManagementService)


def test_downloads_a_calendar_invite(
    api_client,
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    booking = _setup(business, service, staff)

    response = api_client.get(f"/api/appointments/manage/{booking.management_token}/ics")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/calendar")
    assert "attachment" in response["Content-Disposition"]
    body = response.content.decode()
    assert "BEGIN:VCALENDAR" in body
    assert f"UID:appointment-{booking.appointment.id}@mawid" in body


def test_calendar_invite_rejects_an_invalid_token(api_client, db: None) -> None:
    response = api_client.get("/api/appointments/manage/invalid/ics")

    assert response.status_code == 404


def test_cancel_sends_a_localized_cancellation_email(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    booking = _setup(business, service, staff)
    sender = FakeNotificationSender()

    _management_service(MutableClock(datetime(2026, 10, 30, 8, tzinfo=UTC)), sender).cancel(
        booking.management_token
    )

    assert len(sender.sent) == 1
    assert "تم إلغاء حجزك" in sender.sent[0].message.subject


def test_reschedule_sends_a_localized_reschedule_email(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    booking = _setup(business, service, staff)
    sender = FakeNotificationSender()
    management = _management_service(
        MutableClock(datetime(2026, 10, 30, 8, tzinfo=UTC)),
        sender,
    )

    management.reschedule(
        booking.management_token,
        starts_at=datetime(2026, 11, 2, 7, 0, tzinfo=UTC),
    )

    assert len(sender.sent) == 1
    assert "تم تغيير موعد حجزك" in sender.sent[0].message.subject
    assert "https://mawid.test/manage/" in sender.sent[0].message.text_body
