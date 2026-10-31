from django.conf import settings

from apps.notifications.application.notification import NotificationService
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
