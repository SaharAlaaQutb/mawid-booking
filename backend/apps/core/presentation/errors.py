import logging
from typing import Any

from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

_CODE_MAP = {
    "invalid": "validation_error",
    "not_authenticated": "authentication_required",
    "not_found": "not_found",
    "permission_denied": "permission_denied",
    "method_not_allowed": "method_not_allowed",
    "throttled": "throttled",
}


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("The request conflicts with the current state.")
    default_code = "conflict"


def _request_id(context: dict[str, Any]) -> str | None:
    request: HttpRequest | None = context.get("request")
    return getattr(request, "request_id", None) if request else None


def _fields_from_validation_error(exc: ValidationError, data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return dict(data)
    if isinstance(data, list):
        return {"non_field_errors": data}
    return {"non_field_errors": [str(exc.detail)]}


def api_exception_handler(
    exc: Exception,
    context: dict[str, Any],
) -> Response | None:
    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled API exception", exc_info=exc)
        return Response(
            {
                "code": "server_error",
                "detail": str(_("An unexpected error occurred.")),
                "fields": {},
                "request_id": _request_id(context),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = _CODE_MAP.get(getattr(exc, "default_code", ""), getattr(exc, "default_code", "error"))
    fields: dict[str, Any] = {}

    if isinstance(exc, ValidationError):
        fields = _fields_from_validation_error(exc, response.data)
        detail = str(_("Validation failed."))
    elif isinstance(response.data, dict) and "detail" in response.data:
        detail = str(response.data["detail"])
    else:
        detail = str(_("Request failed."))

    response.data = {
        "code": code,
        "detail": detail,
        "fields": fields,
        "request_id": _request_id(context),
    }
    return response
