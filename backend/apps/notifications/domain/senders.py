from typing import Protocol

from apps.notifications.domain.messages import RenderedMessage


class NotificationError(Exception):
    """Raised when a notification cannot be delivered."""


class NotificationSender(Protocol):
    def send(self, *, recipient: str, message: RenderedMessage) -> None: ...
