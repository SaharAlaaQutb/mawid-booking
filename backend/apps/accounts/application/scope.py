from dataclasses import dataclass
from typing import Any
from uuid import UUID

from apps.accounts.application.errors import ActorNotLinkedError
from apps.catalog.container import build_staff_repository
from apps.catalog.domain.entities import Staff
from apps.catalog.domain.repository import StaffRepository

OWNER_ROLE = "owner"


@dataclass(frozen=True, slots=True)
class ActorScope:
    user_id: UUID
    role: str
    staff: Staff

    @property
    def business_id(self) -> UUID:
        return self.staff.business_id

    @property
    def is_owner(self) -> bool:
        return self.role == OWNER_ROLE


def resolve_actor(user: Any, *, staff_repository: StaffRepository | None = None) -> ActorScope:
    repository = staff_repository or build_staff_repository()
    staff = repository.get_by_user(user.id)
    if staff is None or not staff.is_active:
        raise ActorNotLinkedError("This account is not linked to an active staff member.")
    return ActorScope(user_id=user.id, role=str(user.role), staff=staff)
