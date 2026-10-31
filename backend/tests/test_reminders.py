from datetime import UTC, datetime, timedelta

from apps.bookings.domain.status import AppointmentStatus, ReminderKind, ReminderStatus
from apps.bookings.infrastructure.models import Appointment, Reminder
from apps.bookings.infrastructure.repositories import DjangoReminderRepository
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Service, Staff
from apps.notifications.application.reminders import MAX_ATTEMPTS
from apps.notifications.container import build_reminder_service
from apps.notifications.domain.messages import RenderedMessage
from apps.notifications.domain.senders import NotificationError
from apps.notifications.infrastructure.senders import FakeNotificationSender

NOW = datetime(2026, 11, 2, 8, 0, tzinfo=UTC)
STARTS_AT = NOW + timedelta(hours=2)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class FailingSender:
    def send(self, *, recipient: str, message: RenderedMessage) -> None:
        raise NotificationError("smtp down")


def _appointment(
    business: Business,
    service: Service,
    staff: Staff,
    customer: object,
    *,
    status: str = AppointmentStatus.PENDING.value,
    starts_at: datetime = STARTS_AT,
) -> Appointment:
    return Appointment.objects.create(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        status=status,
        price_minor=service.price_minor,
        currency=service.currency,
        customer_language="ar",
    )


def _reminder(appointment: Appointment, *, language: str = "ar") -> Reminder:
    return Reminder.objects.create(
        appointment=appointment,
        kind=ReminderKind.REMINDER.value,
        send_at=NOW - timedelta(minutes=1),
        status=ReminderStatus.PENDING.value,
        attempts=0,
        language=language,
    )


def test_due_reminder_is_sent_once(
    business: Business,
    service: Service,
    staff: Staff,
    customer: object,
) -> None:
    appointment = _appointment(business, service, staff, customer)
    reminder = _reminder(appointment)
    sender = FakeNotificationSender()
    service_layer = build_reminder_service(
        sender=sender,
        base_url="https://mawid.test",
        clock=FixedClock(NOW),
    )

    assert service_layer.process_due() == 1
    assert service_layer.process_due() == 0

    reminder.refresh_from_db()
    assert reminder.status == ReminderStatus.SENT.value
    assert reminder.sent_at == NOW
    assert reminder.attempts == 1
    assert len(sender.sent) == 1


def test_reminder_uses_the_stored_language(
    business: Business,
    service: Service,
    staff: Staff,
    customer: object,
) -> None:
    appointment = _appointment(business, service, staff, customer)
    _reminder(appointment, language="ar")
    sender = FakeNotificationSender()
    service_layer = build_reminder_service(
        sender=sender,
        base_url="https://mawid.test",
        clock=FixedClock(NOW),
    )

    service_layer.process_due()

    message = sender.sent[0].message
    assert "عيادة الاختبار" in message.subject
    assert "استشارة" in message.text_body
    assert 'dir="rtl"' in message.html_body


def test_cancelled_appointment_cancels_the_reminder(
    business: Business,
    service: Service,
    staff: Staff,
    customer: object,
) -> None:
    appointment = _appointment(
        business,
        service,
        staff,
        customer,
        status=AppointmentStatus.CANCELLED.value,
    )
    reminder = _reminder(appointment)
    sender = FakeNotificationSender()
    service_layer = build_reminder_service(
        sender=sender,
        base_url="https://mawid.test",
        clock=FixedClock(NOW),
    )

    service_layer.process_due()

    reminder.refresh_from_db()
    assert reminder.status == ReminderStatus.CANCELLED.value
    assert sender.sent == []


def test_failed_reminder_is_retried_then_marked_failed(
    business: Business,
    service: Service,
    staff: Staff,
    customer: object,
) -> None:
    appointment = _appointment(business, service, staff, customer)
    reminder = _reminder(appointment)
    clock = FixedClock(NOW)
    service_layer = build_reminder_service(
        sender=FailingSender(),
        base_url="https://mawid.test",
        clock=clock,
    )

    for attempt in range(1, MAX_ATTEMPTS + 1):
        service_layer.process_due()
        reminder.refresh_from_db()
        assert reminder.attempts == attempt
        if attempt < MAX_ATTEMPTS:
            assert reminder.status == ReminderStatus.PENDING.value
            clock.value = reminder.send_at
        else:
            assert reminder.status == ReminderStatus.FAILED.value


def test_reminder_rotates_the_management_token(
    business: Business,
    service: Service,
    staff: Staff,
    customer: object,
) -> None:
    appointment = _appointment(business, service, staff, customer)
    appointment.management_token_hash = "a" * 64
    appointment.save(update_fields=["management_token_hash"])
    _reminder(appointment)
    sender = FakeNotificationSender()
    service_layer = build_reminder_service(
        sender=sender,
        base_url="https://mawid.test",
        clock=FixedClock(NOW),
    )

    service_layer.process_due()

    appointment.refresh_from_db()
    assert appointment.management_token_hash != "a" * 64
    assert appointment.management_token_expires_at is not None
    assert "https://mawid.test/manage/" in sender.sent[0].message.text_body


def test_claim_due_only_returns_pending_reminders(
    business: Business,
    service: Service,
    staff: Staff,
    customer: object,
) -> None:
    appointment = _appointment(business, service, staff, customer)
    _reminder(appointment)
    sent_appointment = _appointment(
        business, service, staff, customer, starts_at=STARTS_AT + timedelta(hours=1)
    )
    sent = _reminder(sent_appointment)
    sent.status = ReminderStatus.SENT.value
    sent.save(update_fields=["status"])

    claimed = DjangoReminderRepository().claim_due(NOW, limit=10)

    assert len(claimed) == 1
    assert claimed[0].status == ReminderStatus.PENDING
