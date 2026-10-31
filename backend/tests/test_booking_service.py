from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

import pytest
from apps.bookings.application import errors as booking_errors
from apps.bookings.application.availability import AvailabilityGateway
from apps.bookings.application.booking import BookingService
from apps.bookings.container import (
    build_appointment_repository,
    build_customer_repository,
    build_reminder_repository,
)
from apps.bookings.domain.status import AppointmentStatus, ReminderKind, ReminderStatus
from apps.bookings.domain.tokens import hash_management_token
from apps.bookings.infrastructure.models import Appointment, Customer, Reminder
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
class FixedClock:
    value: datetime

    def now(self) -> datetime:
        return self.value


def _booking_service() -> BookingService:
    availability = AvailabilityService(
        business_repository=DjangoBusinessRepository(),
        service_repository=DjangoServiceRepository(),
        staff_repository=DjangoStaffRepository(),
        working_hours_repository=DjangoWorkingHoursRepository(),
        time_off_repository=DjangoTimeOffRepository(),
        appointment_repository=build_appointment_repository(),
        clock=FixedClock(datetime(2026, 10, 24, 8, tzinfo=UTC)),
    )
    return BookingService(
        business_repository=DjangoBusinessRepository(),
        service_repository=DjangoServiceRepository(),
        staff_repository=DjangoStaffRepository(),
        customer_repository=build_customer_repository(),
        appointment_repository=build_appointment_repository(),
        reminder_repository=build_reminder_repository(),
        availability=AvailabilityGateway(availability),
        unit_of_work=DjangoUnitOfWork(),
        notifier=build_notification_service(
            sender=FakeNotificationSender(), base_url="https://mawid.test"
        ),
    )


def _add_schedule(staff: Staff) -> None:
    WorkingHours.objects.create(
        staff=staff,
        weekday=0,
        start_time=time(9),
        end_time=time(17),
    )


def _add_assignment(staff: Staff, service: Service) -> None:
    StaffService.objects.create(staff=staff, service=service)


def _create(
    service: Service,
    staff: Staff | None,
    *,
    starts_at: datetime = STARTS_AT,
    email: str = "new@example.com",
    name: str = "New Customer",
    phone: str = "",
    language: str = "en",
    notes: str = "",
    idempotency_key: str | None = None,
):
    return _booking_service().create(
        service_id=service.id,
        staff_id=staff.id if staff else None,
        starts_at=starts_at,
        customer_name=name,
        customer_email=email,
        customer_phone=phone,
        customer_language=language,
        notes=notes,
        idempotency_key=idempotency_key,
    )


def test_creates_customer_appointment_reminder_and_token(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _add_schedule(staff)
    _add_assignment(staff, service)
    business.default_locale = "ar"
    business.save(update_fields=["default_locale"])

    result = _create(
        service,
        staff,
        email="New@Example.COM",
        phone=" +966500000001 ",
        language="",
        notes="  First visit  ",
    )

    assert result.appointment.status == AppointmentStatus.PENDING
    assert result.appointment.starts_at == STARTS_AT
    assert result.appointment.ends_at == STARTS_AT + timedelta(minutes=30)
    assert result.appointment.price_minor == service.price_minor
    assert result.appointment.currency == business.currency
    assert result.appointment.notes == "First visit"
    assert result.customer.email == "new@example.com"
    assert result.customer.phone == "+966500000001"
    assert result.customer.language == "ar"
    assert result.appointment.customer_language == "ar"
    assert result.appointment.management_token_hash == hash_management_token(
        result.management_token
    )
    assert result.appointment.management_token_expires_at == STARTS_AT + timedelta(days=7)

    reminder = Reminder.objects.get(appointment_id=result.appointment.id)
    assert reminder.kind == ReminderKind.REMINDER.value
    assert reminder.send_at == STARTS_AT - timedelta(hours=24)
    assert reminder.status == ReminderStatus.PENDING.value
    assert reminder.language == "ar"


def test_chooses_recommended_staff_when_staff_is_any(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    second_staff = Staff.objects.create(
        business=business,
        name_en="Ahmed",
        name_ar="أحمد",
    )
    for member in (staff, second_staff):
        _add_schedule(member)
        _add_assignment(member, service)

    result = _create(service, None)

    assert result.appointment.staff_id == second_staff.id


def test_rejects_a_start_that_is_not_an_available_slot(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _add_schedule(staff)
    _add_assignment(staff, service)

    with pytest.raises(booking_errors.SlotUnavailableError):
        _create(service, staff, starts_at=datetime(2026, 11, 2, 6, 0, tzinfo=UTC))


def test_rejects_staff_who_cannot_perform_the_service(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _add_schedule(staff)
    other_staff = Staff.objects.create(
        business=business,
        name_en="Unassigned",
        name_ar="غير معين",
    )
    _add_schedule(other_staff)

    with pytest.raises(booking_errors.StaffNotAvailableError):
        _create(service, other_staff)


def test_reuses_customer_and_updates_their_details(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _add_schedule(staff)
    _add_assignment(staff, service)
    first = _create(service, staff, email="repeat@example.com", name="Old Name")
    second = _create(
        service,
        staff,
        starts_at=datetime(2026, 11, 2, 7, 0, tzinfo=UTC),
        email="REPEAT@example.com",
        name="New Name",
        phone="+966500000002",
    )

    assert second.customer.id == first.customer.id
    assert second.customer.name == "New Name"
    assert second.customer.phone == "+966500000002"
    assert Customer.objects.count() == 1
    assert Appointment.objects.count() == 2


def test_idempotency_key_returns_the_same_appointment(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _add_schedule(staff)
    _add_assignment(staff, service)

    first = _create(service, staff, idempotency_key="request-1")
    second = _create(service, staff, idempotency_key="request-1")

    assert second.appointment.id == first.appointment.id
    assert second.appointment.management_token_hash == hash_management_token(
        second.management_token
    )
    assert first.management_token != second.management_token
    assert Appointment.objects.count() == 1
    assert Reminder.objects.count() == 1


def test_idempotency_key_rejects_a_different_booking(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _add_schedule(staff)
    _add_assignment(staff, service)
    _create(service, staff, idempotency_key="request-1")

    with pytest.raises(booking_errors.IdempotencyConflictError):
        _create(
            service,
            staff,
            starts_at=datetime(2026, 11, 2, 6, 45, tzinfo=UTC),
            idempotency_key="request-1",
        )


def test_rejects_overlong_idempotency_key(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _add_schedule(staff)
    _add_assignment(staff, service)

    with pytest.raises(ValueError, match="too long"):
        _create(service, staff, idempotency_key="x" * 65)


def test_rejects_naive_start(business: Business, service: Service) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _create(service, None, starts_at=datetime(2026, 11, 2, 9))


def test_missing_business_is_rejected(business: Business, service: Service) -> None:
    Business.objects.all().delete()

    with pytest.raises(booking_errors.BusinessNotConfiguredError):
        _create(service, None, starts_at=datetime(2026, 11, 2, 6, 15, tzinfo=UTC))
