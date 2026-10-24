from config.settings.base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
AUTH_REFRESH_COOKIE_SECURE = False
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")  # noqa: F405
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = env(  # noqa: F405
    "CELERY_RESULT_BACKEND",
    default="redis://localhost:6379/1",
)
