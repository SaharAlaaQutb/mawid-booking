from dataclasses import dataclass
from uuid import UUID

from apps.core.domain.localized_text import LocalizedText


@dataclass(frozen=True, slots=True)
class Service:
    id: UUID
    business_id: UUID
    name: LocalizedText
    description: LocalizedText
    duration_minutes: int
    buffer_before_minutes: int
    buffer_after_minutes: int
    price_minor: int
    currency: str
    is_active: bool
    sort_order: int

    @property
    def total_duration_minutes(self) -> int:
        return self.buffer_before_minutes + self.duration_minutes + self.buffer_after_minutes


@dataclass(frozen=True, slots=True)
class Staff:
    id: UUID
    business_id: UUID
    user_id: UUID | None
    name: LocalizedText
    title: LocalizedText
    bio: LocalizedText
    preferred_language: str
    color: str
    is_active: bool
