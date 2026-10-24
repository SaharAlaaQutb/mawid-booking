import pytest
from apps.accounts.infrastructure.models import Role, User
from django.conf import settings
from rest_framework.test import APIClient


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        email="owner@example.com",
        password="strong-password-123",
        full_name="Mawid Owner",
        role=Role.OWNER,
    )


@pytest.mark.django_db
def test_login_returns_access_token_and_sets_refresh_cookie(
    api_client: APIClient,
    user: User,
) -> None:
    response = api_client.post(
        "/api/auth/token/",
        {"email": user.email, "password": "strong-password-123"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["access"]
    assert "refresh" not in response.data
    assert settings.AUTH_REFRESH_COOKIE_NAME in response.cookies


@pytest.mark.django_db
def test_me_requires_authentication(api_client: APIClient) -> None:
    response = api_client.get("/api/auth/me/")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


@pytest.mark.django_db
def test_me_returns_current_user(api_client: APIClient, user: User) -> None:
    login = api_client.post(
        "/api/auth/token/",
        {"email": user.email, "password": "strong-password-123"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    response = api_client.get("/api/auth/me/")

    assert response.status_code == 200
    assert response.json()["email"] == user.email
    assert response.json()["role"] == Role.OWNER


@pytest.mark.django_db
def test_refresh_reads_cookie_and_rotates_it(api_client: APIClient, user: User) -> None:
    api_client.post(
        "/api/auth/token/",
        {"email": user.email, "password": "strong-password-123"},
        format="json",
    )
    original_cookie = api_client.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value

    response = api_client.post("/api/auth/refresh/", {}, format="json")

    assert response.status_code == 200
    assert response.data["access"]
    assert api_client.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value != original_cookie


@pytest.mark.django_db
def test_logout_clears_refresh_cookie(api_client: APIClient, user: User) -> None:
    api_client.post(
        "/api/auth/token/",
        {"email": user.email, "password": "strong-password-123"},
        format="json",
    )

    response = api_client.post("/api/auth/logout/")

    assert response.status_code == 204
    assert response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value == ""


@pytest.mark.django_db
def test_login_validation_errors_use_error_envelope(api_client: APIClient) -> None:
    response = api_client.post("/api/auth/token/", {"email": "missing@example.com"}, format="json")

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert "password" in response.json()["fields"]
    assert response.json()["request_id"]


@pytest.mark.django_db
def test_invalid_login_is_rejected(api_client: APIClient, user: User) -> None:
    response = api_client.post(
        "/api/auth/token/",
        {"email": user.email, "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"
