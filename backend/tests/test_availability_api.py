from datetime import time
from uuid import uuid4

import pytest
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Service, Staff, StaffService
from apps.scheduling.infrastructure.models import WorkingHours
from freezegun import freeze_time
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def availability_setup(business: Business, service: Service, staff: Staff) -> None:
    StaffService.objects.create(staff=staff, service=service)
    WorkingHours.objects.create(
        staff=staff,
        weekday=0,
        start_time=time(9),
        end_time=time(17),
    )


@freeze_time("2026-10-24T08:00:00Z")
def test_availability_endpoint_returns_slots(
    api_client: APIClient,
    service: Service,
    availability_setup: None,
) -> None:
    response = api_client.get(
        "/api/availability/",
        {"service": str(service.id), "staff": "any", "date": "2026-11-02"},
    )

    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    assert response.data["date"] == "2026-11-02"
    assert response.data["timezone"] == "Asia/Riyadh"
    assert response.data["service"]["name"] == "Consultation"
    assert len(response.data["slots"]) == 29
    assert response.data["slots"][0]["starts_at"].startswith("2026-11-02T09:15:00+03:00")
    assert response.data["slots"][0]["staff_options"][0]["name"] == "Sarah"
    assert response.data["next_available_date"] is None


@freeze_time("2026-10-24T08:00:00Z")
def test_availability_endpoint_localizes_names(
    api_client: APIClient,
    service: Service,
    availability_setup: None,
) -> None:
    response = api_client.get(
        "/api/availability/",
        {"service": str(service.id), "date": "2026-11-02", "lang": "ar"},
    )

    assert response.status_code == 200
    assert response.data["service"]["name"] == "استشارة"
    assert response.data["slots"][0]["staff_options"][0]["name"] == "سارة"


@freeze_time("2026-10-24T08:00:00Z")
def test_availability_endpoint_accepts_specific_staff(
    api_client: APIClient,
    staff: Staff,
    service: Service,
    availability_setup: None,
) -> None:
    response = api_client.get(
        "/api/availability/",
        {"service": str(service.id), "staff": str(staff.id), "date": "2026-11-02"},
    )

    assert response.status_code == 200
    assert all(len(slot["staff_options"]) == 1 for slot in response.data["slots"])


@freeze_time("2026-10-24T08:00:00Z")
def test_availability_endpoint_rejects_unknown_service(
    api_client: APIClient,
    availability_setup: None,
) -> None:
    response = api_client.get(
        "/api/availability/",
        {"service": str(uuid4()), "date": "2026-11-02"},
    )

    assert response.status_code == 404
    assert response.data["code"] == "service_not_available"


@freeze_time("2026-10-24T08:00:00Z")
def test_availability_endpoint_rejects_ineligible_staff(
    api_client: APIClient,
    service: Service,
    availability_setup: None,
) -> None:
    response = api_client.get(
        "/api/availability/",
        {"service": str(service.id), "staff": str(uuid4()), "date": "2026-11-02"},
    )

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert "staff" in response.data["fields"]


@freeze_time("2026-10-24T08:00:00Z")
def test_availability_endpoint_rejects_date_outside_horizon(
    api_client: APIClient,
    service: Service,
    availability_setup: None,
) -> None:
    response = api_client.get(
        "/api/availability/",
        {"service": str(service.id), "date": "2026-12-25"},
    )

    assert response.status_code == 400
    assert response.data["code"] == "date_outside_horizon"


@freeze_time("2026-10-24T08:00:00Z")
def test_availability_endpoint_validates_query(
    api_client: APIClient,
) -> None:
    response = api_client.get("/api/availability/", {"date": "not-a-date"})

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert "service" in response.data["fields"]
    assert "date" in response.data["fields"]


@freeze_time("2026-10-24T08:00:00Z")
def test_availability_endpoint_rejects_malformed_staff_id(
    api_client: APIClient,
    service: Service,
    availability_setup: None,
) -> None:
    response = api_client.get(
        "/api/availability/",
        {"service": str(service.id), "staff": "not-a-uuid", "date": "2026-11-02"},
    )

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert "staff" in response.data["fields"]


@freeze_time("2026-10-24T08:00:00Z")
def test_availability_endpoint_reports_missing_business(api_client: APIClient) -> None:
    Business.objects.all().delete()

    response = api_client.get(
        "/api/availability/",
        {"service": str(uuid4()), "date": "2026-11-02"},
    )

    assert response.status_code == 503
    assert response.data["code"] == "business_not_configured"
