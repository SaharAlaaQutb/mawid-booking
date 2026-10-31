from typing import Any

from django.utils import translation
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.domain.locale import SUPPORTED_LOCALES


class LocaleAwareJWTAuthentication(JWTAuthentication):
    def authenticate(self, request: Request) -> tuple[Any, Any] | None:
        result = super().authenticate(request)
        if result is None:
            return None
        user, _ = result
        if request.GET.get("lang") in SUPPORTED_LOCALES:
            return result
        if request.META.get("HTTP_ACCEPT_LANGUAGE"):
            return result
        preferred = getattr(user, "preferred_language", None)
        if preferred in SUPPORTED_LOCALES:
            translation.activate(preferred)
        return result
