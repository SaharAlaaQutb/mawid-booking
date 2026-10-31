from uuid import UUID

from apps.businesses.domain.entities import Business
from apps.businesses.infrastructure.models import Business as BusinessModel
from apps.core.domain.localized_text import LocalizedText


def _to_entity(model: BusinessModel) -> Business:
    return Business(
        id=model.id,
        slug=model.slug,
        name=LocalizedText(ar=model.name_ar, en=model.name_en),
        timezone=model.timezone,
        default_locale=model.default_locale,
        currency=model.currency,
        slot_interval_minutes=model.slot_interval_minutes,
        min_lead_time_minutes=model.min_lead_time_minutes,
        max_advance_days=model.max_advance_days,
        cancellation_window_hours=model.cancellation_window_hours,
        phone=model.phone,
        address=LocalizedText(ar=model.address_ar, en=model.address_en),
        is_active=model.is_active,
    )


class DjangoBusinessRepository:
    def get(self, business_id: UUID) -> Business | None:
        model = BusinessModel.objects.filter(pk=business_id).first()
        return _to_entity(model) if model else None

    def get_active(self) -> Business | None:
        model = BusinessModel.objects.filter(is_active=True).order_by("created_at").first()
        return _to_entity(model) if model else None

    def get_by_slug(self, slug: str) -> Business | None:
        model = BusinessModel.objects.filter(slug=slug).first()
        return _to_entity(model) if model else None
