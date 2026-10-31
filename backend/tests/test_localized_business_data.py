import pytest
from apps.accounts.infrastructure.models import Role, User
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Service, Staff
from apps.core.domain.localized_text import LocalizedText
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_client(api_client: APIClient, staff: Staff) -> APIClient:
    user = User.objects.create_user(
        email="owner@example.com",
        password="test-password",
        role=Role.OWNER,
    )
    staff.user = user
    staff.save(update_fields=["user"])
    api_client.force_authenticate(user)
    return api_client


def test_public_business_returns_requested_language(
    api_client: APIClient, business: Business
) -> None:
    arabic = api_client.get("/api/business/", {"lang": "ar"})
    english = api_client.get("/api/business/", {"lang": "en"})

    assert arabic.status_code == 200
    assert arabic.data["name"] == "عيادة الاختبار"
    assert arabic.data["address"] == business.address_ar

    assert english.status_code == 200
    assert english.data["name"] == "Test Clinic"
    assert english.data["address"] == business.address_en


def test_public_services_return_requested_language(
    api_client: APIClient, business: Business, service: Service
) -> None:
    arabic = api_client.get("/api/services/", {"lang": "ar"})
    english = api_client.get("/api/services/", {"lang": "en"})

    assert arabic.status_code == 200
    assert arabic.data[0]["name"] == "استشارة"
    assert arabic.data[0]["description"] == service.description_ar

    assert english.status_code == 200
    assert english.data[0]["name"] == "Consultation"
    assert english.data[0]["description"] == service.description_en


def test_public_staff_return_requested_language(
    api_client: APIClient, business: Business, service: Service, staff: Staff
) -> None:
    arabic = api_client.get("/api/staff/", {"lang": "ar"})
    english = api_client.get("/api/staff/", {"lang": "en"})

    assert arabic.status_code == 200
    assert any(member["name"] == "سارة" for member in arabic.data)

    assert english.status_code == 200
    assert any(member["name"] == "Sarah" for member in english.data)


def test_staff_settings_return_raw_localized_columns(
    owner_client: APIClient, business: Business
) -> None:
    response = owner_client.get("/api/settings/")

    assert response.status_code == 200
    assert response.data["name_ar"] == "عيادة الاختبار"
    assert response.data["name_en"] == "Test Clinic"
    assert response.data["address_ar"] == business.address_ar
    assert response.data["address_en"] == business.address_en

    updated = owner_client.patch(
        "/api/settings/",
        {"name_ar": "عيادة جديدة", "name_en": "New Clinic"},
        format="json",
    )

    assert updated.status_code == 200
    assert updated.data["name_ar"] == "عيادة جديدة"
    assert updated.data["name_en"] == "New Clinic"


def test_localized_text_fallbacks_to_the_other_language() -> None:
    text = LocalizedText(ar="", en="English only")
    assert text.for_locale("ar") == "English only"

    text = LocalizedText(ar="عربي فقط", en="")
    assert text.for_locale("en") == "عربي فقط"
