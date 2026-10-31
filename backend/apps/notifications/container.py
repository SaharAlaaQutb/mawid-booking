from apps.notifications.domain.messages import MessageRenderer
from apps.notifications.infrastructure.renderers import DjangoTemplateMessageRenderer


def build_message_renderer() -> MessageRenderer:
    return DjangoTemplateMessageRenderer()
