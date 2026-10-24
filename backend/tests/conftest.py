from datetime import UTC, datetime, timedelta

import pytest
from apps.bookings.infrastructure.models import Customer
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Service, Staff
from apps.core.domain.localized_text import LocalizedText
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def business(db: None) -> Business:
    return Business.objects.create(
        slug="test-clinic",
        name_en="Test Clinic",
        name_ar="عيادة الاختبار",
        timezone="Asia/Riyadh",
        default_locale="en",
        currency="SAR",
    )


@pytest.fixture
def service(business: Business) -> Service:
    return Service.objects.create(
        business=business,
        name_en="Consultation",
        name_ar="استشارة",
        duration_minutes=30,
        buffer_before_minutes=5,
        buffer_after_minutes=10,
        price_minor=20000,
        currency="SAR",
    )


@pytest.fixture
def staff(business: Business) -> Staff:
    return Staff.objects.create(
        business=business,
        name_en="Sarah",
        name_ar="سارة",
        preferred_language="en",
    )


@pytest.fixture
def customer(business: Business) -> Customer:
    return Customer.objects.create(
        business=business,
        name="Layla",
        email="LAYLA@Example.com",
        phone="+966500000000",
        language="ar",
    )


@pytest.fixture
def starts_at() -> datetime:
    return datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


@pytest.fixture
def ends_at(starts_at: datetime) -> datetime:
    return starts_at + timedelta(minutes=30)


@pytest.fixture
def localized_text() -> LocalizedText:
    return LocalizedText(ar="عربي", en="English")
