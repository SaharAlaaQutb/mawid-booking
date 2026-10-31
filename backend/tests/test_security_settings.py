import os

os.environ["DJANGO_SECRET_KEY"] = "test-secret-key-for-security-tests"
os.environ["DJANGO_ALLOWED_HOSTS"] = "example.com"
os.environ["CORS_ALLOWED_ORIGINS"] = "https://example.com"
os.environ["DJANGO_CSRF_TRUSTED_ORIGINS"] = "https://example.com"

from config.settings import prod


def test_prod_is_not_debug() -> None:
    assert prod.DEBUG is False


def test_prod_requires_explicit_origins() -> None:
    assert prod.CORS_ALLOWED_ORIGINS == ["https://example.com"]
    assert "http://localhost:5173" not in prod.CORS_ALLOWED_ORIGINS
    assert prod.CSRF_TRUSTED_ORIGINS == ["https://example.com"]


def test_prod_secure_cookies_and_headers() -> None:
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.CSRF_COOKIE_SECURE is True
    assert prod.SESSION_COOKIE_HTTPONLY is True
    assert prod.CSRF_COOKIE_HTTPONLY is True
    assert prod.SESSION_COOKIE_SAMESITE == "Lax"
    assert prod.CSRF_COOKIE_SAMESITE == "Lax"
    assert prod.SECURE_REFERRER_POLICY == "same-origin"
    assert prod.SECURE_CONTENT_TYPE_NOSNIFF is True


def test_prod_hsts_and_ssl_redirect() -> None:
    assert prod.SECURE_SSL_REDIRECT is True
    assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert prod.SECURE_HSTS_SECONDS > 0
    assert prod.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert prod.SECURE_HSTS_PRELOAD is True


def test_prod_has_rate_limits() -> None:
    rates = prod.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert rates["anon"]
    assert rates["user"]
    assert rates["booking"]
