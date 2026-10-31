import logging
from dataclasses import dataclass

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.notifications.domain.messages import RenderedMessage
from apps.notifications.domain.senders import NotificationError, NotificationSender

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SentNotification:
    recipient: str
    message: RenderedMessage


class EmailNotificationSender(NotificationSender):
    def __init__(self, from_email: str | None = None) -> None:
        self._from_email = from_email or settings.DEFAULT_FROM_EMAIL

    def send(self, *, recipient: str, message: RenderedMessage) -> None:
        email = EmailMultiAlternatives(
            subject=message.subject,
            body=message.text_body,
            from_email=self._from_email,
            to=[recipient],
        )
        email.attach_alternative(message.html_body, "text/html")
        try:
            sent = email.send()
        except Exception as exc:
            raise NotificationError("Email delivery failed.") from exc
        if sent != 1:
            raise NotificationError("Email delivery failed.")


class ConsoleNotificationSender(NotificationSender):
    def send(self, *, recipient: str, message: RenderedMessage) -> None:
        logger.info(
            "notification recipient=%s subject=%s body=%s",
            recipient,
            message.subject,
            message.text_body,
        )


class FakeNotificationSender(NotificationSender):
    def __init__(self) -> None:
        self.sent: list[SentNotification] = []

    def send(self, *, recipient: str, message: RenderedMessage) -> None:
        self.sent.append(SentNotification(recipient=recipient, message=message))
