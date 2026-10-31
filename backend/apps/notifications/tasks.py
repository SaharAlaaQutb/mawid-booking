from uuid import UUID

from apps.bookings.container import (
    build_appointment_repository,
    build_customer_repository,
)
from apps.businesses.container import build_business_repository
from apps.catalog.container import build_service_repository, build_staff_repository
from apps.notifications.container import build_notification_service, build_reminder_service
from apps.notifications.domain.messages import NotificationKind
from apps.notifications.domain.senders import NotificationError
from celery import shared_task


@shared_task(name="notifications.ping")
def ping(language: str = "en") -> str:
    return language


@shared_task(
    bind=True,
    autoretry_for=(NotificationError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
    name="notifications.send_notification",
)
def send_notification(
    self: object,
    *,
    appointment_id: str,
    kind: str,
    management_token: str,
    language: str,
) -> None:
    appointment = build_appointment_repository().get(UUID(appointment_id))
    if appointment is None:
        raise NotificationError("Appointment not found.")
    customer = build_customer_repository().get(appointment.customer_id)
    service = build_service_repository().get(appointment.service_id)
    staff = build_staff_repository().get(appointment.staff_id)
    business = build_business_repository().get(appointment.business_id)
    if customer is None or service is None or staff is None or business is None:
        raise NotificationError("Appointment details not found.")

    build_notification_service().send(
        NotificationKind(kind),
        appointment=appointment,
        customer=customer,
        service=service,
        staff=staff,
        business=business,
        management_token=management_token,
        language=language,
    )


@shared_task(name="notifications.process_due_reminders")
def process_due_reminders(limit: int = 100) -> int:
    return build_reminder_service().process_due(limit=limit)
