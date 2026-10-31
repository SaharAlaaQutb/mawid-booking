from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request

from apps.accounts.application.errors import ActorNotLinkedError
from apps.accounts.application.scope import ActorScope, resolve_actor


def actor_from_request(request: Request) -> ActorScope:
    try:
        return resolve_actor(request.user)
    except ActorNotLinkedError as exc:
        raise PermissionDenied(
            str(_("This account is not linked to an active staff member."))
        ) from exc


def require_owner(actor: ActorScope) -> None:
    if not actor.is_owner:
        raise PermissionDenied(str(_("Only the business owner can perform this action.")))
