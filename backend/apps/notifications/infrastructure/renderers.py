from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from django.template.loader import render_to_string
from django.utils import translation
from django.utils.formats import date_format, number_format, time_format
from django.utils.timezone import localtime

from apps.notifications.domain.messages import (
    MessageContext,
    MessageRenderer,
    NotificationKind,
    RenderedMessage,
)

TEMPLATE_DIRECTORY = "notifications/email"


class DjangoTemplateMessageRenderer(MessageRenderer):
    def render(self, kind: NotificationKind, context: MessageContext) -> RenderedMessage:
        with translation.override(context.language):
            template_context = self._template_context(context)
            subject = self._render(f"{kind.value}_subject.txt", template_context)
            text_body = self._render(f"{kind.value}_body.txt", template_context)
            html_body = self._render(f"{kind.value}_body.html", template_context)
        return RenderedMessage(
            subject=subject.strip().replace("\n", " "),
            text_body=text_body.strip(),
            html_body=html_body.strip(),
        )

    def _render(self, template_name: str, context: dict[str, Any]) -> str:
        return render_to_string(f"{TEMPLATE_DIRECTORY}/{template_name}", context)

    def _template_context(self, context: MessageContext) -> dict[str, Any]:
        starts_at = self._local_time(context, context.appointment.starts_at)
        ends_at = self._local_time(context, context.appointment.ends_at)
        language = context.language
        return {
            "language": language,
            "direction": "rtl" if language == "ar" else "ltr",
            "business_name": context.business.name.for_locale(language),
            "customer_name": context.customer.name,
            "customer_email": context.customer.email,
            "customer_phone": context.customer.phone,
            "service_name": context.service.name.for_locale(language),
            "service_description": context.service.description.for_locale(language),
            "staff_name": context.staff.name.for_locale(language),
            "staff_title": context.staff.title.for_locale(language),
            "date": date_format(starts_at, "l, j F Y"),
            "start_time": time_format(starts_at, "H:i"),
            "end_time": time_format(ends_at, "H:i"),
            "timezone": context.business.timezone,
            "duration": context.service.duration_minutes,
            "price": number_format(
                context.service.price_minor / 100,
                decimal_pos=2,
                force_grouping=True,
            ),
            "currency": context.service.currency,
            "notes": context.appointment.notes,
            "management_url": context.management_url,
        }

    def _local_time(self, context: MessageContext, value: datetime) -> datetime:
        return localtime(value, ZoneInfo(context.business.timezone))


def build_template_renderer() -> MessageRenderer:
    return DjangoTemplateMessageRenderer()
