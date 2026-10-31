from django.conf import settings

from apps.bookings.infrastructure.repositories import (
    DjangoAppointmentRepository,
    DjangoCustomerRepository,
    DjangoReminderRepository,
)
from apps.businesses.infrastructure.repositories import DjangoBusinessRepository
from apps.catalog.infrastructure.repositories import (
    DjangoServiceRepository,
    DjangoStaffRepository,
)
from apps.core.domain.clock import Clock, SystemClock
from apps.core.infrastructure.unit_of_work import build_unit_of_work
from apps.notifications.application.notification import NotificationService
from apps.notifications.application.reminders import ReminderService
from apps.notifications.domain.messages import MessageRenderer
from apps.notifications.domain.senders import NotificationSender
from apps.notifications.infrastructure.renderers import DjangoTemplateMessageRenderer
from apps.notifications.infrastructure.senders import (
    ConsoleNotificationSender,
    EmailNotificationSender,
    FakeNotificationSender,
)


def build_message_renderer() -> MessageRenderer:
    return DjangoTemplateMessageRenderer()


def build_email_sender() -> NotificationSender:
    return EmailNotificationSender()


def build_console_sender() -> NotificationSender:
    return ConsoleNotificationSender()


def build_fake_sender() -> FakeNotificationSender:
    return FakeNotificationSender()


def build_notification_service(
    *,
    sender: NotificationSender | None = None,
    base_url: str | None = None,
) -> NotificationService:
    return NotificationService(
        renderer=build_message_renderer(),
        sender=sender or build_email_sender(),
        base_url=base_url or settings.FRONTEND_BASE_URL,
    )


def build_reminder_service(
    *,
    sender: NotificationSender | None = None,
    base_url: str | None = None,
    clock: Clock | None = None,
) -> ReminderService:
    return ReminderService(
        reminder_repository=DjangoReminderRepository(),
        appointment_repository=DjangoAppointmentRepository(),
        customer_repository=DjangoCustomerRepository(),
        service_repository=DjangoServiceRepository(),
        staff_repository=DjangoStaffRepository(),
        business_repository=DjangoBusinessRepository(),
        notifier=build_notification_service(sender=sender, base_url=base_url),
        clock=clock or SystemClock(),
        unit_of_work=build_unit_of_work(),
    )
