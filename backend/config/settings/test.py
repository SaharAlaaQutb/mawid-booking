from config.settings.base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
AUTH_REFRESH_COOKIE_SECURE = False
REDIS_URL = ""
CELERY_TASK_ALWAYS_EAGER = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///:memory:"),  # noqa: F405
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
