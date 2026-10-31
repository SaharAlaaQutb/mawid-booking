import pytest
from apps.accounts.infrastructure.models import Role, User
from apps.bookings.domain.status import AppointmentStatus
from apps.bookings.infrastructure.models import Appointment, Customer
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Service, Staff
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_user(db: None) -> User:
    return User.objects.create_user(
        email="owner@example.com",
        password="test-password",
        role=Role.OWNER,
    )


@pytest.fixture
def owner_client(api_client: APIClient, owner_user: User, staff: Staff) -> APIClient:
    staff.user = owner_user
    staff.save(update_fields=["user"])
    api_client.force_authenticate(owner_user)
    return api_client


@pytest.fixture
def colleague(db: None, business: Business) -> Staff:
    colleague = Staff.objects.create(
        business=business,
        name_ar="نورة",
        name_en="Noura",
        preferred_language="ar",
    )
    user = User.objects.create_user(email="noura@example.com", password="test-password")
    colleague.user = user
    colleague.save(update_fields=["user"])
    return colleague


@pytest.fixture
def colleague_client(api_client: APIClient, colleague: Staff) -> APIClient:
    api_client.force_authenticate(colleague.user)
    return api_client


def _starts_at() -> str:
    from datetime import UTC, datetime, timedelta

    return (datetime(2026, 11, 2, 9, 0, tzinfo=UTC) + timedelta(days=1)).isoformat()


def test_validation_error_is_localized(
    api_client: APIClient,
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    arabic = api_client.post(
        "/api/appointments/",
        {},
        format="json",
        HTTP_ACCEPT_LANGUAGE="ar",
    )
    english = api_client.post(
        "/api/appointments/",
        {},
        format="json",
        HTTP_ACCEPT_LANGUAGE="en",
    )

    assert arabic.status_code == 400
    assert arabic.data["code"] == "validation_error"
    assert arabic.data["detail"] == "فشل التحقق."
    assert arabic.data["fields"]

    assert english.status_code == 400
    assert english.data["code"] == "validation_error"
    assert english.data["detail"] == "Validation failed."
    assert english.data["fields"]


def test_permission_error_is_localized(
    colleague_client: APIClient,
    colleague: Staff,
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
) -> None:
    appointment = Appointment.objects.create(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
        starts_at="2026-11-03T09:00:00Z",
        ends_at="2026-11-03T09:30:00Z",
        status=AppointmentStatus.PENDING.value,
        price_minor=service.price_minor,
        currency=service.currency,
        customer_language="en",
    )

    response = colleague_client.patch(
        f"/api/appointments/{appointment.id}/status/",
        {"status": "cancelled"},
        format="json",
        HTTP_ACCEPT_LANGUAGE="ar",
    )

    assert response.status_code == 403
    assert response.data["code"] == "permission_denied"
    assert response.data["detail"] == "لا يمكنك تغيير هذا الموعد."
