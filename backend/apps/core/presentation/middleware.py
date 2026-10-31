import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.utils import translation

from apps.core.presentation.locale import resolve_request_locale
from apps.core.presentation.request_logging import REQUEST_ID_CONTEXT


class RequestIDMiddleware:
    header_name = "HTTP_X_REQUEST_ID"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.META.get(self.header_name) or str(uuid.uuid4())
        request.request_id = request_id  # type: ignore[attr-defined]
        token = REQUEST_ID_CONTEXT.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            REQUEST_ID_CONTEXT.reset(token)
        response["X-Request-ID"] = request_id
        return response


class LocaleResolutionMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        locale = resolve_request_locale(request)
        request.LANGUAGE_CODE = locale
        with translation.override(locale):
            response = self.get_response(request)
            response["Content-Language"] = translation.get_language() or locale
        return response
