from datetime import UTC, datetime, timedelta

from apps.bookings.domain.status import AppointmentStatus, ReminderKind, ReminderStatus
from apps.bookings.infrastructure.models import Appointment, Reminder
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Service, Staff
from apps.notifications.tasks import process_due_reminders, send_notification
from django.core.mail import EmailMultiAlternatives
from freezegun import freeze_time

NOW = datetime(2026, 11, 2, 8, 0, tzinfo=UTC)
STARTS_AT = NOW + timedelta(hours=2)


def _appointment(
    business: Business,
    service: Service,
    staff: Staff,
    customer: object,
    *,
    starts_at: datetime = STARTS_AT,
    customer_language: str = "ar",
) -> Appointment:
    return Appointment.objects.create(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        status=AppointmentStatus.PENDING.value,
        price_minor=service.price_minor,
        currency=service.currency,
        customer_language=customer_language,
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


@freeze_time(NOW)
def test_task_sends_due_reminder_once(
    business: Business,
    service: Service,
    staff: Staff,
    customer: object,
    mailoutbox: list,
) -> None:
    appointment = _appointment(business, service, staff, customer)
    _reminder(appointment)

    assert process_due_reminders.delay().get() == 1
    assert process_due_reminders.delay().get() == 0
    assert len(mailoutbox) == 1


@freeze_time(NOW)
def test_task_sends_reminder_in_the_stored_language(
    business: Business,
    service: Service,
    staff: Staff,
    customer: object,
    mailoutbox: list,
) -> None:
    appointment = _appointment(business, service, staff, customer)
    _reminder(appointment, language="ar")

    process_due_reminders.delay()

    assert "عيادة الاختبار" in mailoutbox[0].subject
    assert "استشارة" in mailoutbox[0].body


def test_task_marks_reminder_failed_after_retries(
    monkeypatch,
    business: Business,
    service: Service,
    staff: Staff,
    customer: object,
) -> None:
    appointment = _appointment(business, service, staff, customer)
    reminder = _reminder(appointment)

    def _fail(self: EmailMultiAlternatives) -> int:
        raise OSError("smtp down")

    monkeypatch.setattr(EmailMultiAlternatives, "send", _fail)

    with freeze_time(NOW) as frozen:
        for attempt in range(3):
            process_due_reminders.delay()
            reminder.refresh_from_db()
            if attempt < 2:
                frozen.move_to(reminder.send_at)

    assert reminder.attempts == 3
    assert reminder.status == ReminderStatus.FAILED.value


@freeze_time(NOW)
def test_send_notification_task_uses_the_explicit_language(
    business: Business,
    service: Service,
    staff: Staff,
    customer: object,
    mailoutbox: list,
) -> None:
    appointment = _appointment(business, service, staff, customer, customer_language="en")

    send_notification.delay(
        appointment_id=str(appointment.id),
        kind="confirmation",
        management_token="token-value",
        language="ar",
    )

    assert len(mailoutbox) == 1
    assert "تم تأكيد حجزك" in mailoutbox[0].subject
