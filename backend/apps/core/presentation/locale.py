from django.utils.translation import get_language
from rest_framework.request import Request

from apps.core.domain.locale import DEFAULT_LOCALE, SUPPORTED_LOCALES


def response_locale(request: Request) -> str:
    explicit = request.query_params.get("lang")
    if explicit in SUPPORTED_LOCALES:
        return explicit
    language = get_language() or DEFAULT_LOCALE
    resolved = language.split("-", maxsplit=1)[0]
    return resolved if resolved in SUPPORTED_LOCALES else DEFAULT_LOCALE
