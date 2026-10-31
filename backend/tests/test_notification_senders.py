import logging

import pytest
from apps.notifications.domain.messages import RenderedMessage
from apps.notifications.domain.senders import NotificationError
from apps.notifications.infrastructure.senders import (
    ConsoleNotificationSender,
    EmailNotificationSender,
    FakeNotificationSender,
)
from django.core import mail

MESSAGE = RenderedMessage(
    subject="Your booking is confirmed",
    text_body="Hello Layla,\n\nSee you soon.",
    html_body="<p>Hello Layla,</p>",
)


def test_email_sender_sends_text_and_html(mailoutbox: list[mail.EmailMessage]) -> None:
    EmailNotificationSender(from_email="Mawid <no-reply@mawid.test>").send(
        recipient="layla@example.com",
        message=MESSAGE,
    )

    assert len(mailoutbox) == 1
    email = mailoutbox[0]
    assert email.to == ["layla@example.com"]
    assert email.subject == MESSAGE.subject
    assert email.body == MESSAGE.text_body
    assert email.alternatives == [(MESSAGE.html_body, "text/html")]


def test_email_sender_raises_when_delivery_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(self: mail.EmailMessage) -> int:
        raise OSError("smtp down")

    monkeypatch.setattr(mail.EmailMessage, "send", _fail)

    with pytest.raises(NotificationError):
        EmailNotificationSender().send(recipient="layla@example.com", message=MESSAGE)


def test_fake_sender_records_notifications() -> None:
    sender = FakeNotificationSender()

    sender.send(recipient="layla@example.com", message=MESSAGE)

    assert len(sender.sent) == 1
    assert sender.sent[0].recipient == "layla@example.com"
    assert sender.sent[0].message == MESSAGE


def test_console_sender_logs_notification(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="apps.notifications.infrastructure.senders")

    ConsoleNotificationSender().send(recipient="layla@example.com", message=MESSAGE)

    assert "layla@example.com" in caplog.text
    assert MESSAGE.subject in caplog.text
