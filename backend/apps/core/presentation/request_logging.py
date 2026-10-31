import contextvars
import json
import logging
import time
from datetime import UTC, datetime

REQUEST_ID_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
_TASK_START_CONTEXT: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "task_start", default=None
)

logger = logging.getLogger(__name__)


class RequestIDLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID_CONTEXT.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_celery_logging() -> None:
    from celery.signals import task_failure, task_postrun, task_prerun

    @task_prerun.connect
    def _task_prerun(sender=None, task_id=None, task=None, **kwargs: object) -> None:
        _TASK_START_CONTEXT.set(time.monotonic())
        logger.info(
            "celery task started",
            extra={
                "task_id": task_id,
                "task_name": getattr(task, "name", None),
                "event": "task_started",
            },
        )

    @task_postrun.connect
    def _task_postrun(
        sender=None,
        task_id=None,
        task=None,
        retval=None,
        state=None,
        **kwargs: object,
    ) -> None:
        start = _TASK_START_CONTEXT.get(None)
        duration_ms = None
        if start is not None:
            duration_ms = round((time.monotonic() - start) * 1000, 2)
        logger.info(
            "celery task completed",
            extra={
                "task_id": task_id,
                "task_name": getattr(task, "name", None),
                "state": state,
                "duration_ms": duration_ms,
                "event": "task_completed",
            },
        )

    @task_failure.connect
    def _task_failure(
        sender=None, task_id=None, task=None, exception=None, **kwargs: object
    ) -> None:
        logger.error(
            "celery task failed",
            extra={
                "task_id": task_id,
                "task_name": getattr(task, "name", None),
                "exception": str(exception) if exception is not None else None,
                "event": "task_failed",
            },
        )
