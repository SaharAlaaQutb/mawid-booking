from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:5173"]),
    AUTH_REFRESH_COOKIE_SECURE=(bool, True),
    EMAIL_USE_TLS=(bool, False),
    EMAIL_PORT=(int, 1025),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-change-me-in-production",
)
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.businesses",
    "apps.catalog",
    "apps.scheduling",
    "apps.bookings",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.presentation.middleware.RequestIDMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "apps.core.presentation.middleware.LocaleResolutionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://mawid:mawid@localhost:5432/mawid",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("ar", "Arabic"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
USE_TZ = True
TIME_ZONE = "UTC"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.core.presentation.authentication.LocaleAwareJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.presentation.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.presentation.errors.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("DRF_ANON_THROTTLE", default="60/min"),
        "user": env("DRF_USER_THROTTLE", default="120/min"),
        "booking": env("DRF_BOOKING_THROTTLE", default="20/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

AUTH_REFRESH_COOKIE_NAME = env("AUTH_REFRESH_COOKIE_NAME", default="mawid_refresh")
AUTH_REFRESH_COOKIE_PATH = env("AUTH_REFRESH_COOKIE_PATH", default="/api/auth/")
AUTH_REFRESH_COOKIE_SECURE = env("AUTH_REFRESH_COOKIE_SECURE")
AUTH_REFRESH_COOKIE_SAMESITE = env("AUTH_REFRESH_COOKIE_SAMESITE", default="Lax")

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS")

FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", default="http://localhost:5173")

SPECTACULAR_SETTINGS = {
    "TITLE": "Mawid API",
    "DESCRIPTION": "Appointment booking API for clinics, salons, and small businesses.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "EXTENSIONS": ["apps.core.presentation.openapi.LocaleAwareJWTAuthExtension"],
}

REDIS_URL = env("REDIS_URL", default="")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL or "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND", default=REDIS_URL or "redis://localhost:6379/1"
)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=300)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BEAT_SCHEDULE: dict[str, dict[str, object]] = {
    "process-due-reminders": {
        "task": "notifications.process_due_reminders",
        "schedule": 300.0,
    },
}
CELERY_TIMEZONE = TIME_ZONE

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env("EMAIL_USE_TLS")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Mawid <no-reply@mawid.local>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", default="INFO"),
    },
}

from apps.core.presentation import request_logging  # noqa: E402

request_logging.configure_celery_logging()
