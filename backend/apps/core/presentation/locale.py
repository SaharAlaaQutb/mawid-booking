from django.http import HttpRequest
from django.utils.translation import get_language
from rest_framework.request import Request

from apps.core.domain.locale import DEFAULT_LOCALE, SUPPORTED_LOCALES


def _normalize(language: str | None) -> str | None:
    if not language:
        return None
    resolved = language.split("-", maxsplit=1)[0]
    return resolved if resolved in SUPPORTED_LOCALES else None


def resolve_request_locale(request: HttpRequest) -> str:
    explicit = request.GET.get("lang")
    if explicit in SUPPORTED_LOCALES:
        return explicit

    if request.META.get("HTTP_ACCEPT_LANGUAGE"):
        return _normalize(get_language()) or DEFAULT_LOCALE

    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        preferred = getattr(user, "preferred_language", None)
        if preferred in SUPPORTED_LOCALES:
            return preferred

    return _normalize(get_language()) or DEFAULT_LOCALE


def response_locale(request: Request) -> str:
    explicit = request.query_params.get("lang")
    if explicit in SUPPORTED_LOCALES:
        return explicit
    return _normalize(get_language()) or DEFAULT_LOCALE
