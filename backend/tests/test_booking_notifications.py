import logging
from datetime import UTC, datetime, time

import pytest
from apps.bookings.application.availability import AvailabilityGateway
from apps.bookings.application.booking import BookingResult, BookingService
from apps.bookings.container import (
    build_appointment_repository,
    build_customer_repository,
    build_reminder_repository,
)
from apps.businesses.infrastructure.models import Business
from apps.businesses.infrastructure.repositories import DjangoBusinessRepository
from apps.catalog.infrastructure.models import Service, Staff, StaffService
from apps.catalog.infrastructure.repositories import (
    DjangoServiceRepository,
    DjangoStaffRepository,
)
from apps.core.infrastructure.unit_of_work import DjangoUnitOfWork
from apps.notifications.container import build_notification_service
from apps.notifications.domain.messages import RenderedMessage
from apps.notifications.domain.senders import NotificationError
from apps.notifications.infrastructure.senders import FakeNotificationSender
from apps.scheduling.application.availability import AvailabilityService
from apps.scheduling.infrastructure.models import WorkingHours
from apps.scheduling.infrastructure.repositories import (
    DjangoTimeOffRepository,
    DjangoWorkingHoursRepository,
)

STARTS_AT = datetime(2026, 11, 2, 6, 15, tzinfo=UTC)


class FailingSender:
    def send(self, *, recipient: str, message: RenderedMessage) -> None:
        raise NotificationError("smtp down")


def _availability() -> AvailabilityService:
    return AvailabilityService(
        business_repository=DjangoBusinessRepository(),
        service_repository=DjangoServiceRepository(),
        staff_repository=DjangoStaffRepository(),
        working_hours_repository=DjangoWorkingHoursRepository(),
        time_off_repository=DjangoTimeOffRepository(),
        appointment_repository=build_appointment_repository(),
        clock=_FixedClock(datetime(2026, 10, 24, 8, tzinfo=UTC)),
    )


class _FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


def _booking_service(sender: FakeNotificationSender | FailingSender) -> BookingService:
    return BookingService(
        business_repository=DjangoBusinessRepository(),
        service_repository=DjangoServiceRepository(),
        staff_repository=DjangoStaffRepository(),
        customer_repository=build_customer_repository(),
        appointment_repository=build_appointment_repository(),
        reminder_repository=build_reminder_repository(),
        availability=AvailabilityGateway(_availability()),
        unit_of_work=DjangoUnitOfWork(),
        notifier=build_notification_service(sender=sender, base_url="https://mawid.test"),
    )


def _setup(business: Business, service: Service, staff: Staff) -> None:
    WorkingHours.objects.create(staff=staff, weekday=0, start_time=time(9), end_time=time(17))
    StaffService.objects.create(staff=staff, service=service)


def _book(
    service: Service, staff: Staff, sender: FakeNotificationSender | FailingSender
) -> BookingResult:
    return _booking_service(sender).create(
        service_id=service.id,
        staff_id=staff.id,
        starts_at=STARTS_AT,
        customer_name="Layla",
        customer_email="layla@example.com",
        customer_language="ar",
    )


def test_booking_sends_one_confirmation_in_customer_language(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _setup(business, service, staff)
    sender = FakeNotificationSender()

    _book(service, staff, sender)

    assert len(sender.sent) == 1
    sent = sender.sent[0]
    assert sent.recipient == "layla@example.com"
    assert "عيادة الاختبار" in sent.message.subject
    assert "استشارة" in sent.message.text_body
    assert "https://mawid.test/manage/" in sent.message.text_body


def test_notification_failure_does_not_fail_booking(
    business: Business,
    service: Service,
    staff: Staff,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _setup(business, service, staff)
    caplog.set_level(logging.ERROR, logger="apps.bookings.application.booking")

    result = _book(service, staff, FailingSender())

    assert result.appointment.id is not None
    assert "Failed to send booking confirmation" in caplog.text
