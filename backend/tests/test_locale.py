import pytest
from apps.accounts.infrastructure.models import Role, User
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Staff
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


def test_query_language_overrides_accept_language(
    api_client: APIClient,
    business: Business,
) -> None:
    response = api_client.get(
        "/api/business/",
        {"lang": "ar"},
        HTTP_ACCEPT_LANGUAGE="en",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "عيادة الاختبار"
    assert response["Content-Language"] == "ar"


def test_accept_language_localizes_public_business_data(
    api_client: APIClient,
    business: Business,
) -> None:
    response = api_client.get("/api/business/", HTTP_ACCEPT_LANGUAGE="ar")

    assert response.status_code == 200
    assert response.json()["name"] == "عيادة الاختبار"
    assert response["Content-Language"] == "ar"


def test_staff_preferred_language_is_used_without_a_header(
    api_client: APIClient,
    business: Business,
    staff: Staff,
) -> None:
    user = User.objects.create_user(
        email="owner@example.com",
        password="test-password",
        role=Role.OWNER,
        preferred_language="ar",
    )
    staff.user = user
    staff.save(update_fields=["user"])
    access = RefreshToken.for_user(user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = api_client.get("/api/business/")

    assert response.status_code == 200
    assert response.json()["name"] == "عيادة الاختبار"
    assert response["Content-Language"] == "ar"


def test_unsupported_query_language_falls_back_to_the_header(
    api_client: APIClient,
    business: Business,
) -> None:
    response = api_client.get(
        "/api/business/",
        {"lang": "fr"},
        HTTP_ACCEPT_LANGUAGE="en",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Test Clinic"
    assert response["Content-Language"] == "en"


def test_content_language_defaults_to_english(
    api_client: APIClient,
    business: Business,
) -> None:
    response = api_client.get("/api/business/")

    assert response.status_code == 200
    assert response["Content-Language"] == "en"
