import logging

from apps.core.presentation.middleware import RequestIDMiddleware
from apps.core.presentation.request_logging import (
    REQUEST_ID_CONTEXT,
    JsonFormatter,
    RequestIDLogFilter,
    configure_celery_logging,
)
from django.http import HttpRequest, HttpResponse

from celery.signals import task_postrun, task_prerun


def test_json_formatter_includes_request_id_and_message() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="app",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    token = REQUEST_ID_CONTEXT.set("req-123")
    try:
        RequestIDLogFilter().filter(record)
        output = formatter.format(record)
    finally:
        REQUEST_ID_CONTEXT.reset(token)
    assert '"request_id": "req-123"' in output
    assert '"message": "hello world"' in output
    assert '"level": "INFO"' in output


def test_json_formatter_defaults_request_id() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="app", level=logging.ERROR, pathname="", lineno=0, msg="boom", args=None, exc_info=None
    )
    output = formatter.format(record)
    assert '"request_id": "-"' in output


def test_request_id_filter_reads_context_var() -> None:
    record = logging.LogRecord(
        name="app", level=logging.INFO, pathname="", lineno=0, msg="x", args=None, exc_info=None
    )
    token = REQUEST_ID_CONTEXT.set("req-999")
    try:
        assert RequestIDLogFilter().filter(record) is True
        assert record.request_id == "req-999"
    finally:
        REQUEST_ID_CONTEXT.reset(token)


def test_request_id_filter_defaults_to_dash() -> None:
    record = logging.LogRecord(
        name="app", level=logging.INFO, pathname="", lineno=0, msg="x", args=None, exc_info=None
    )
    assert RequestIDLogFilter().filter(record) is True
    assert record.request_id == "-"


def test_request_id_middleware_sets_and_resets_context() -> None:
    def get_response(request: HttpRequest) -> HttpResponse:
        assert REQUEST_ID_CONTEXT.get() == "custom-id"
        return HttpResponse("ok")

    middleware = RequestIDMiddleware(get_response)
    request = HttpRequest()
    request.META = {"HTTP_X_REQUEST_ID": "custom-id"}

    response = middleware(request)

    assert response["X-Request-ID"] == "custom-id"
    assert REQUEST_ID_CONTEXT.get() is None


def test_celery_signals_are_connected() -> None:
    configure_celery_logging()
    assert task_prerun.receivers
    assert task_postrun.receivers
