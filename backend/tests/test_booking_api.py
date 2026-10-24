from collections.abc import Iterator
from datetime import time
from typing import Any
from urllib.parse import urlparse

import pytest
from apps.bookings.domain.status import AppointmentStatus, ReminderStatus
from apps.bookings.infrastructure.models import Appointment, Reminder
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Service, Staff, StaffService
from apps.scheduling.infrastructure.models import WorkingHours
from django.core.cache import cache
from freezegun import freeze_time
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_throttle_cache() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def bookable(business: Business, service: Service, staff: Staff) -> None:
    StaffService.objects.create(staff=staff, service=service)
    WorkingHours.objects.create(
        staff=staff,
        weekday=0,
        start_time=time(9),
        end_time=time(17),
    )


def _payload(service: Service, **overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "service": str(service.id),
        "starts_at": "2026-11-02T09:15:00+03:00",
        "customer_name": "Layla",
        "customer_email": "Layla@Example.com",
        "customer_phone": "+966500000001",
        "notes": "First visit",
    }
    data.update(overrides)
    return data


def _create(
    api_client: APIClient,
    service: Service,
    **overrides: object,
) -> dict[str, Any]:
    response = api_client.post(
        "/api/appointments/",
        _payload(service, **overrides),
        format="json",
        HTTP_IDEMPOTENCY_KEY="booking-key-1",
    )
    assert response.status_code == 201, response.data
    return response.data


def _path(management_url: Any) -> str:
    assert isinstance(management_url, str)
    return urlparse(management_url).path


@freeze_time("2026-10-24T08:00:00Z")
def test_create_appointment(
    api_client: APIClient,
    service: Service,
    staff: Staff,
    bookable: None,
) -> None:
    response = api_client.post(
        "/api/appointments/",
        _payload(service),
        format="json",
        HTTP_IDEMPOTENCY_KEY="booking-key-1",
    )

    assert response.status_code == 201
    assert response["Cache-Control"] == "no-store"
    assert response.data["status"] == "pending"
    assert response.data["starts_at"] == "2026-11-02T09:15:00+03:00"
    assert response.data["ends_at"] == "2026-11-02T09:45:00+03:00"
    assert response.data["staff"]["id"] == str(staff.id)
    assert response.data["service"]["name"] == "Consultation"
    assert response.data["customer"]["email"] == "layla@example.com"
    assert str(response.data["management_url"]).startswith(
        "http://testserver/api/appointments/manage/"
    )
    assert Appointment.objects.count() == 1
    assert Reminder.objects.filter(status=ReminderStatus.PENDING).count() == 1


@freeze_time("2026-10-24T08:00:00Z")
def test_create_assigns_any_eligible_staff(
    api_client: APIClient,
    service: Service,
    staff: Staff,
    bookable: None,
) -> None:
    created = _create(api_client, service, staff="any")

    assert created["staff"]["id"] == str(staff.id)


@freeze_time("2026-10-24T08:00:00Z")
def test_create_replays_idempotent_request(
    api_client: APIClient,
    service: Service,
    bookable: None,
) -> None:
    first = _create(api_client, service)
    second = _create(api_client, service)

    assert first["id"] == second["id"]
    assert Appointment.objects.count() == 1


@freeze_time("2026-10-24T08:00:00Z")
def test_create_rejects_reused_key_for_different_slot(
    api_client: APIClient,
    service: Service,
    bookable: None,
) -> None:
    _create(api_client, service)

    response = api_client.post(
        "/api/appointments/",
        _payload(service, starts_at="2026-11-02T10:15:00+03:00"),
        format="json",
        HTTP_IDEMPOTENCY_KEY="booking-key-1",
    )

    assert response.status_code == 409
    assert response.data["code"] == "idempotency_conflict"


@freeze_time("2026-10-24T08:00:00Z")
def test_create_rejects_unknown_service(
    api_client: APIClient,
    service: Service,
) -> None:
    response = api_client.post(
        "/api/appointments/",
        {**_payload(service), "service": "00000000-0000-0000-0000-000000000000"},
        format="json",
    )

    assert response.status_code == 404
    assert response.data["code"] == "service_not_available"


@freeze_time("2026-10-24T08:00:00Z")
def test_create_rejects_naive_start(
    api_client: APIClient,
    service: Service,
) -> None:
    response = api_client.post(
        "/api/appointments/",
        _payload(service, starts_at="2026-11-02T09:15:00"),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert "starts_at" in response.data["fields"]


@freeze_time("2026-10-24T08:00:00Z")
def test_create_rejects_unavailable_slot(
    api_client: APIClient,
    service: Service,
    bookable: None,
) -> None:
    response = api_client.post(
        "/api/appointments/",
        _payload(service, starts_at="2026-11-02T20:00:00+03:00"),
        format="json",
    )

    assert response.status_code == 422
    assert response.data["code"] == "slot_unavailable"
    assert Appointment.objects.count() == 0


@freeze_time("2026-10-24T08:00:00Z")
def test_manage_returns_localized_appointment(
    api_client: APIClient,
    service: Service,
    bookable: None,
) -> None:
    created = _create(api_client, service, language="ar")

    response = api_client.get(_path(created["management_url"]), {"lang": "ar"})

    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    assert response.data["id"] == created["id"]
    assert response.data["service"]["name"] == "استشارة"
    assert response.data["business"]["name"] == "عيادة الاختبار"


def test_manage_rejects_invalid_token(api_client: APIClient) -> None:
    response = api_client.get("/api/appointments/manage/not-a-real-token/")

    assert response.status_code == 404
    assert response.data["code"] == "management_link_invalid"


@freeze_time("2026-10-24T08:00:00Z")
def test_cancel_appointment_revokes_link(
    api_client: APIClient,
    service: Service,
    bookable: None,
) -> None:
    created = _create(api_client, service)
    path = _path(created["management_url"])

    with freeze_time("2026-10-30T08:00:00Z"):
        response = api_client.post(
            f"{path.rstrip('/')}/cancel",
            {"reason": "Changed plans"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "cancelled"
        assert response.data["cancelled_by"] == "customer"
        assert response.data["cancellation_reason"] == "Changed plans"
        assert response.data["management_url"] is None

        assert api_client.get(path).status_code == 404

    appointment = Appointment.objects.get(pk=created["id"])
    assert appointment.status == AppointmentStatus.CANCELLED
    assert appointment.management_token_hash is None
    assert not Reminder.objects.filter(
        appointment_id=appointment.id,
        status=ReminderStatus.PENDING,
    ).exists()


@freeze_time("2026-10-24T08:00:00Z")
def test_cancel_rejects_appointment_inside_window(
    api_client: APIClient,
    service: Service,
    bookable: None,
) -> None:
    created = _create(api_client, service)
    path = _path(created["management_url"])

    with freeze_time("2026-11-02T04:15:00Z"):
        response = api_client.post(f"{path.rstrip('/')}/cancel", {}, format="json")

    assert response.status_code == 409
    assert response.data["code"] == "cancellation_not_allowed"
    assert Appointment.objects.get(pk=created["id"]).status == AppointmentStatus.PENDING


@freeze_time("2026-10-24T08:00:00Z")
def test_reschedule_moves_appointment_and_rotates_link(
    api_client: APIClient,
    service: Service,
    bookable: None,
) -> None:
    created = _create(api_client, service)
    old_path = _path(created["management_url"])

    with freeze_time("2026-10-30T08:00:00Z"):
        response = api_client.post(
            f"{old_path.rstrip('/')}/reschedule",
            {"starts_at": "2026-11-02T10:00:00+03:00"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["starts_at"] == "2026-11-02T10:00:00+03:00"
        assert response.data["status"] == "pending"
        assert response.data["management_url"] != created["management_url"]
        assert api_client.get(old_path).status_code == 404
        assert api_client.get(_path(response.data["management_url"])).status_code == 200

    assert Appointment.objects.get(pk=created["id"]).status == AppointmentStatus.CANCELLED
    assert Appointment.objects.filter(status=AppointmentStatus.PENDING).count() == 1


@freeze_time("2026-10-24T08:00:00Z")
def test_reschedule_rejects_unavailable_slot(
    api_client: APIClient,
    service: Service,
    bookable: None,
) -> None:
    created = _create(api_client, service)
    path = _path(created["management_url"])

    with freeze_time("2026-10-30T08:00:00Z"):
        response = api_client.post(
            f"{path.rstrip('/')}/reschedule",
            {"starts_at": "2026-11-02T20:00:00+03:00"},
            format="json",
        )

    assert response.status_code == 422
    assert response.data["code"] == "slot_unavailable"
    assert Appointment.objects.get(pk=created["id"]).status == AppointmentStatus.PENDING


@freeze_time("2026-10-24T08:00:00Z")
def test_idempotency_key_does_not_revive_cancelled_booking(
    api_client: APIClient,
    service: Service,
    bookable: None,
) -> None:
    created = _create(api_client, service)
    path = _path(created["management_url"])

    with freeze_time("2026-10-30T08:00:00Z"):
        cancelled = api_client.post(f"{path.rstrip('/')}/cancel", {}, format="json")
        assert cancelled.status_code == 200

        replay = api_client.post(
            "/api/appointments/",
            _payload(service),
            format="json",
            HTTP_IDEMPOTENCY_KEY="booking-key-1",
        )

    assert replay.status_code == 409
    assert replay.data["code"] == "idempotency_conflict"
