from pathlib import Path

from apps.notifications.domain.senders import NotificationError
from apps.notifications.tasks import ping
from config.celery import app
from django.conf import settings

COMPOSE_FILE = Path(__file__).resolve().parents[2] / "docker-compose.yml"


def test_ping_task_is_registered() -> None:
    assert "notifications.ping" in app.tasks


def test_ping_task_runs_in_eager_mode() -> None:
    assert settings.CELERY_TASK_ALWAYS_EAGER is True
    assert ping.delay("ar").get() == "ar"


def test_send_notification_task_uses_retry_policy() -> None:
    task = app.tasks["notifications.send_notification"]

    assert task.autoretry_for == (NotificationError,)
    assert task.retry_backoff is True
    assert task.retry_jitter is True
    assert task.max_retries == 3


def test_celery_reliability_settings_are_enabled() -> None:
    assert settings.CELERY_TASK_ACKS_LATE is True
    assert settings.CELERY_TASK_REJECT_ON_WORKER_LOST is True
    assert settings.CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP is True
    assert settings.CELERY_TASK_TIME_LIMIT == 300


def test_worker_and_beat_services_exist_in_dev_compose() -> None:
    compose = COMPOSE_FILE.read_text()

    assert "worker:" in compose
    assert "beat:" in compose
    assert "celery -A config worker" in compose
    assert "celery -A config beat" in compose
