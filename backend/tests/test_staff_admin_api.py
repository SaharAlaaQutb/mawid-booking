from datetime import time

import pytest
from apps.accounts.infrastructure.models import Role, User
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Service, Staff, StaffService
from apps.scheduling.infrastructure.models import TimeOff, WorkingHours
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_user(db: None) -> User:
    return User.objects.create_user(
        email="admin-owner@example.com",
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
def staff_client(api_client: APIClient, colleague: Staff) -> APIClient:
    user = User.objects.create_user(email="staff-user@example.com", password="test-password")
    colleague.user = user
    colleague.save(update_fields=["user"])
    api_client.force_authenticate(user)
    return api_client


@pytest.fixture
def colleague(business: Business) -> Staff:
    return Staff.objects.create(
        business=business,
        name_ar="نورة",
        name_en="Noura",
    )


@pytest.fixture
def other_business(db: None) -> Business:
    return Business.objects.create(
        slug="other-clinic",
        name_ar="عيادة أخرى",
        name_en="Other Clinic",
        timezone="Asia/Riyadh",
    )


def test_public_service_list_is_localized_and_hides_inactive(
    api_client: APIClient,
    service: Service,
) -> None:
    Service.objects.create(
        business=service.business,
        name_ar="مخفية",
        name_en="Hidden",
        duration_minutes=30,
        is_active=False,
    )

    response = api_client.get("/api/services/", {"lang": "ar"})

    assert response.status_code == 200
    assert response.data == [
        {
            "id": str(service.id),
            "name": "استشارة",
            "description": "",
            "duration_minutes": 30,
            "price_minor": 20000,
            "currency": "SAR",
        }
    ]


def test_public_staff_list_filters_by_service(
    api_client: APIClient,
    service: Service,
    staff: Staff,
    colleague: Staff,
) -> None:
    StaffService.objects.create(staff=staff, service=service)

    response = api_client.get("/api/staff/", {"service": str(service.id), "lang": "ar"})

    assert response.status_code == 200
    assert [member["id"] for member in response.data] == [str(staff.id)]
    assert response.data[0]["name"] == "سارة"


def test_owner_creates_service_in_own_business(
    owner_client: APIClient,
    business: Business,
    other_business: Business,
) -> None:
    response = owner_client.post(
        "/api/services/",
        {
            "business_id": str(other_business.id),
            "name_ar": "جلسة",
            "name_en": "Session",
            "duration_minutes": 45,
            "price_minor": 30000,
            "currency": "sar",
        },
        format="json",
    )

    assert response.status_code == 201
    created = Service.objects.get(pk=response.data["id"])
    assert created.business_id == business.id
    assert created.currency == "SAR"


def test_staff_member_cannot_create_service(
    staff_client: APIClient,
) -> None:
    response = staff_client.post(
        "/api/services/",
        {
            "name_ar": "جلسة",
            "name_en": "Session",
            "duration_minutes": 45,
        },
        format="json",
    )

    assert response.status_code == 403


def test_service_detail_is_scoped_to_business(
    owner_client: APIClient,
    other_business: Business,
) -> None:
    other_service = Service.objects.create(
        business=other_business,
        name_ar="خدمة",
        name_en="Other service",
        duration_minutes=30,
    )

    response = owner_client.get(f"/api/services/{other_service.id}/")

    assert response.status_code == 404


def test_owner_soft_deletes_service(
    owner_client: APIClient,
    service: Service,
) -> None:
    response = owner_client.delete(f"/api/services/{service.id}/")

    assert response.status_code == 204
    service.refresh_from_db()
    assert service.is_active is False


def test_owner_creates_staff_with_services(
    owner_client: APIClient,
    business: Business,
    service: Service,
) -> None:
    response = owner_client.post(
        "/api/staff/",
        {
            "name_ar": "ليان",
            "name_en": "Layan",
            "preferred_language": "ar",
            "color": "#112233",
            "service_ids": [str(service.id)],
        },
        format="json",
    )

    assert response.status_code == 201
    assert [
        {
            "id": str(item["id"]),
            "name_en": item["name_en"],
            "name_ar": item["name_ar"],
        }
        for item in response.data["services"]
    ] == [{"id": str(service.id), "name_en": "Consultation", "name_ar": "استشارة"}]
    member = Staff.objects.get(pk=response.data["id"])
    assert member.business_id == business.id


def test_staff_service_ids_must_match_business(
    owner_client: APIClient,
    other_business: Business,
) -> None:
    other_service = Service.objects.create(
        business=other_business,
        name_ar="خدمة",
        name_en="Other service",
        duration_minutes=30,
    )

    response = owner_client.post(
        "/api/staff/",
        {
            "name_ar": "ليان",
            "name_en": "Layan",
            "service_ids": [str(other_service.id)],
        },
        format="json",
    )

    assert response.status_code == 400
    assert "service_ids" in response.data["fields"]


def test_owner_updates_staff_service_assignments(
    owner_client: APIClient,
    staff: Staff,
    service: Service,
) -> None:
    response = owner_client.patch(
        f"/api/staff/{staff.id}/",
        {"service_ids": [str(service.id)]},
        format="json",
    )

    assert response.status_code == 200
    assert StaffService.objects.filter(staff=staff, service=service).exists()


def test_staff_member_cannot_create_staff(
    staff_client: APIClient,
) -> None:
    response = staff_client.post(
        "/api/staff/",
        {"name_ar": "شخص", "name_en": "Person"},
        format="json",
    )

    assert response.status_code == 403


def test_owner_creates_working_hours(
    owner_client: APIClient,
    staff: Staff,
) -> None:
    response = owner_client.post(
        "/api/working-hours/",
        {
            "staff": str(staff.id),
            "weekday": 0,
            "start_time": "09:00",
            "end_time": "17:00",
        },
        format="json",
    )

    assert response.status_code == 201
    assert WorkingHours.objects.filter(staff=staff).count() == 1


def test_overlapping_working_hours_are_rejected(
    owner_client: APIClient,
    staff: Staff,
) -> None:
    WorkingHours.objects.create(
        staff=staff,
        weekday=0,
        start_time=time(9),
        end_time=time(17),
    )

    response = owner_client.post(
        "/api/working-hours/",
        {
            "staff": str(staff.id),
            "weekday": 0,
            "start_time": "10:00",
            "end_time": "12:00",
        },
        format="json",
    )

    assert response.status_code == 400


def test_working_hours_are_scoped_for_staff(
    staff_client: APIClient,
    staff: Staff,
    colleague: Staff,
) -> None:
    WorkingHours.objects.create(
        staff=staff,
        weekday=0,
        start_time=time(9),
        end_time=time(17),
    )
    WorkingHours.objects.create(
        staff=colleague,
        weekday=1,
        start_time=time(9),
        end_time=time(17),
    )

    own = staff_client.get("/api/working-hours/")
    forbidden = staff_client.get("/api/working-hours/", {"staff": str(staff.id)})

    assert own.status_code == 200
    assert [str(entry["staff"]) for entry in own.data] == [str(colleague.id)]
    assert forbidden.status_code == 403


def test_owner_creates_time_off(
    owner_client: APIClient,
    owner_user: User,
    staff: Staff,
) -> None:
    response = owner_client.post(
        "/api/time-off/",
        {
            "staff": str(staff.id),
            "starts_at": "2026-11-05T09:00:00+03:00",
            "ends_at": "2026-11-05T12:00:00+03:00",
            "reason": "Training",
        },
        format="json",
    )

    assert response.status_code == 201
    entry = TimeOff.objects.get(pk=response.data["id"])
    assert entry.created_by == owner_user


def test_time_off_rejects_naive_datetime(
    owner_client: APIClient,
    staff: Staff,
) -> None:
    response = owner_client.post(
        "/api/time-off/",
        {
            "staff": str(staff.id),
            "starts_at": "2026-11-05T09:00:00",
            "ends_at": "2026-11-05T12:00:00",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "starts_at" in response.data["fields"]


def test_time_off_rejects_staff_from_another_business(
    owner_client: APIClient,
    other_business: Business,
) -> None:
    other_staff = Staff.objects.create(
        business=other_business,
        name_ar="شخص",
        name_en="Other staff",
    )

    response = owner_client.post(
        "/api/time-off/",
        {
            "staff": str(other_staff.id),
            "starts_at": "2026-11-05T09:00:00+03:00",
            "ends_at": "2026-11-05T12:00:00+03:00",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "staff" in response.data["fields"]


def test_owner_reads_and_updates_settings(
    owner_client: APIClient,
    business: Business,
) -> None:
    read = owner_client.get("/api/settings/")
    updated = owner_client.patch(
        "/api/settings/",
        {"timezone": "Africa/Cairo", "currency": "egp"},
        format="json",
    )

    assert read.status_code == 200
    assert updated.status_code == 200
    assert updated.data["timezone"] == "Africa/Cairo"
    assert updated.data["currency"] == "EGP"
    business.refresh_from_db()
    assert business.timezone == "Africa/Cairo"


def test_settings_reject_invalid_timezone(
    owner_client: APIClient,
) -> None:
    response = owner_client.patch(
        "/api/settings/",
        {"timezone": "Not/AZone"},
        format="json",
    )

    assert response.status_code == 400
    assert "timezone" in response.data["fields"]


def test_staff_member_cannot_update_settings(
    staff_client: APIClient,
) -> None:
    response = staff_client.patch(
        "/api/settings/",
        {"timezone": "Africa/Cairo"},
        format="json",
    )

    assert response.status_code == 403


def test_public_cannot_list_appointments(
    api_client: APIClient,
) -> None:
    response = api_client.get("/api/appointments/")

    assert response.status_code == 405


def test_public_business_profile_is_localized(
    api_client: APIClient,
    business: Business,
) -> None:
    business.address_ar = "الرياض"
    business.address_en = "Riyadh"
    business.phone = "+966500000000"
    business.save(update_fields=["address_ar", "address_en", "phone"])

    response = api_client.get("/api/business/", {"lang": "ar"})

    assert response.status_code == 200
    assert response.data["name"] == "عيادة الاختبار"
    assert response.data["address"] == "الرياض"
    assert response.data["timezone"] == "Asia/Riyadh"
