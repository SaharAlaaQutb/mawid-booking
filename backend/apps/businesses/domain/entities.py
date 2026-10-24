from dataclasses import dataclass
from uuid import UUID

from apps.core.domain.localized_text import LocalizedText


@dataclass(frozen=True, slots=True)
class Business:
    id: UUID
    slug: str
    name: LocalizedText
    timezone: str
    default_locale: str
    currency: str
    slot_interval_minutes: int
    min_lead_time_minutes: int
    max_advance_days: int
    cancellation_window_hours: int
    is_active: bool
