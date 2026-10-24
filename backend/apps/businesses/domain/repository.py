from typing import Protocol
from uuid import UUID

from apps.businesses.domain.entities import Business


class BusinessRepository(Protocol):
    def get(self, business_id: UUID) -> Business | None: ...

    def get_active(self) -> Business | None: ...

    def get_by_slug(self, slug: str) -> Business | None: ...
