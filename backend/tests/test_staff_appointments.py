from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from apps.accounts.infrastructure.models import Role, User
from apps.bookings.domain.status import AppointmentStatus, ReminderKind, ReminderStatus
from apps.bookings.infrastructure.models import Appointment, Customer, Reminder
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Service, Staff
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

STARTS_AT = datetime(2026, 11, 2, 6, 15, tzinfo=UTC)


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
def colleague(business: Business) -> Staff:
    return Staff.objects.create(
        business=business,
        name_ar="نورة",
        name_en="Noura",
        preferred_language="ar",
    )


@pytest.fixture
def colleague_client(
    api_client: APIClient,
    colleague: Staff,
) -> APIClient:
    user = User.objects.create_user(email="noura@example.com", password="test-password")
    colleague.user = user
    colleague.save(update_fields=["user"])
    api_client.force_authenticate(user)
    return api_client


def _appointment(
    *,
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
    starts_at: datetime = STARTS_AT,
    status: AppointmentStatus = AppointmentStatus.PENDING,
) -> Appointment:
    return Appointment.objects.create(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=service.duration_minutes),
        status=status,
        price_minor=service.price_minor,
        currency=service.currency,
        customer_language="en",
    )


def test_staff_confirms_and_completes_appointment(
    owner_client: APIClient,
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
) -> None:
    appointment = _appointment(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
    )

    confirmed = owner_client.patch(
        f"/api/appointments/{appointment.id}/status/",
        {"status": "confirmed"},
        format="json",
    )
    assert confirmed.status_code == 200
    assert confirmed.data["status"] == "confirmed"

    completed = owner_client.patch(
        f"/api/appointments/{appointment.id}/status/",
        {"status": "completed"},
        format="json",
    )
    assert completed.status_code == 200
    assert completed.data["status"] == "completed"
    assert completed.data["management_url"] is None


def test_staff_cannot_skip_to_completed(
    owner_client: APIClient,
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
) -> None:
    appointment = _appointment(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
    )

    response = owner_client.patch(
        f"/api/appointments/{appointment.id}/status/",
        {"status": "completed"},
        format="json",
    )

    assert response.status_code == 409
    assert response.data["code"] == "invalid_transition"


def test_staff_cancel_revokes_link_and_reminder(
    owner_client: APIClient,
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
) -> None:
    appointment = _appointment(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
    )
    appointment.management_token_hash = "hash"
    appointment.save(update_fields=["management_token_hash"])
    Reminder.objects.create(
        appointment=appointment,
        kind=ReminderKind.REMINDER,
        send_at=STARTS_AT - timedelta(hours=24),
        status=ReminderStatus.PENDING,
        language="en",
    )

    response = owner_client.patch(
        f"/api/appointments/{appointment.id}/status/",
        {"status": "cancelled", "reason": "Staff unavailable"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["status"] == "cancelled"
    assert response.data["cancelled_by"] == "staff"
    assert response.data["cancellation_reason"] == "Staff unavailable"
    appointment.refresh_from_db()
    assert appointment.management_token_hash is None
    assert appointment.reminders.get().status == ReminderStatus.CANCELLED


def test_staff_no_show_is_terminal(
    owner_client: APIClient,
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
) -> None:
    appointment = _appointment(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
    )

    first = owner_client.patch(
        f"/api/appointments/{appointment.id}/status/",
        {"status": "no_show"},
        format="json",
    )
    second = owner_client.patch(
        f"/api/appointments/{appointment.id}/status/",
        {"status": "confirmed"},
        format="json",
    )

    assert first.status_code == 200
    assert first.data["status"] == "no_show"
    assert second.status_code == 409


def test_staff_cannot_update_colleague_appointment(
    colleague_client: APIClient,
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
) -> None:
    appointment = _appointment(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
    )

    response = colleague_client.patch(
        f"/api/appointments/{appointment.id}/status/",
        {"status": "confirmed"},
        format="json",
    )

    assert response.status_code == 403


def test_owner_can_update_colleague_appointment(
    owner_client: APIClient,
    business: Business,
    service: Service,
    colleague: Staff,
    customer: Customer,
) -> None:
    appointment = _appointment(
        business=business,
        service=service,
        staff=colleague,
        customer=customer,
    )

    response = owner_client.patch(
        f"/api/appointments/{appointment.id}/status/",
        {"status": "confirmed"},
        format="json",
    )

    assert response.status_code == 200


def test_staff_cannot_update_another_business_appointment(
    owner_client: APIClient,
    service: Service,
    customer: Customer,
) -> None:
    other_business = Business.objects.create(
        slug="other",
        name_ar="أخرى",
        name_en="Other",
        timezone="Asia/Riyadh",
    )
    other_service = Service.objects.create(
        business=other_business,
        name_ar="خدمة",
        name_en="Other service",
        duration_minutes=30,
    )
    other_staff = Staff.objects.create(
        business=other_business,
        name_ar="شخص",
        name_en="Other staff",
    )
    other_customer = Customer.objects.create(
        business=other_business,
        name="Other",
        email="other@example.com",
    )
    appointment = _appointment(
        business=other_business,
        service=other_service,
        staff=other_staff,
        customer=other_customer,
    )

    response = owner_client.patch(
        f"/api/appointments/{appointment.id}/status/",
        {"status": "confirmed"},
        format="json",
    )

    assert response.status_code == 404


def test_status_endpoint_requires_authentication(
    api_client: APIClient,
    service: Service,
) -> None:
    response = api_client.patch(
        f"/api/appointments/{uuid4()}/status/",
        {"status": "confirmed"},
        format="json",
    )

    assert response.status_code == 401


def test_calendar_groups_appointments_by_staff(
    owner_client: APIClient,
    business: Business,
    service: Service,
    staff: Staff,
    colleague: Staff,
    customer: Customer,
) -> None:
    _appointment(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
    )
    _appointment(
        business=business,
        service=service,
        staff=colleague,
        customer=customer,
        starts_at=STARTS_AT + timedelta(hours=1),
    )

    response = owner_client.get(
        "/api/calendar/",
        {"from": "2026-11-02", "to": "2026-11-02", "lang": "ar"},
    )

    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    assert response.data["from"] == "2026-11-02"
    assert response.data["to"] == "2026-11-02"
    assert len(response.data["staff"]) == 2
    by_name = {member["name"]: member for member in response.data["staff"]}
    assert by_name["سارة"]["appointments"][0]["starts_at"] == "2026-11-02T09:15:00+03:00"
    assert by_name["سارة"]["appointments"][0]["service"]["name"] == "استشارة"
    assert by_name["نورة"]["appointments"][0]["starts_at"] == "2026-11-02T10:15:00+03:00"


def test_calendar_limits_staff_to_own_schedule(
    colleague_client: APIClient,
    business: Business,
    service: Service,
    staff: Staff,
    colleague: Staff,
    customer: Customer,
) -> None:
    _appointment(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
    )
    _appointment(
        business=business,
        service=service,
        staff=colleague,
        customer=customer,
        starts_at=STARTS_AT + timedelta(hours=1),
    )

    response = colleague_client.get(
        "/api/calendar/",
        {"from": "2026-11-02", "to": "2026-11-02"},
    )

    assert response.status_code == 200
    assert [member["id"] for member in response.data["staff"]] == [str(colleague.id)]


def test_calendar_rejects_colleague_filter_for_staff(
    colleague_client: APIClient,
    staff: Staff,
) -> None:
    response = colleague_client.get(
        "/api/calendar/",
        {"from": "2026-11-02", "to": "2026-11-02", "staff": str(staff.id)},
    )

    assert response.status_code == 403


def test_owner_can_filter_calendar_by_staff(
    owner_client: APIClient,
    staff: Staff,
    colleague: Staff,
) -> None:
    response = owner_client.get(
        "/api/calendar/",
        {"from": "2026-11-02", "to": "2026-11-02", "staff": str(staff.id)},
    )

    assert response.status_code == 200
    assert [member["id"] for member in response.data["staff"]] == [str(staff.id)]


def test_calendar_rejects_invalid_range(owner_client: APIClient) -> None:
    response = owner_client.get(
        "/api/calendar/",
        {"from": "2026-11-03", "to": "2026-11-02"},
    )

    assert response.status_code == 400
    assert response.data["code"] == "invalid_range"


def test_calendar_rejects_oversized_range(owner_client: APIClient) -> None:
    response = owner_client.get(
        "/api/calendar/",
        {"from": "2026-01-01", "to": "2026-12-31"},
    )

    assert response.status_code == 400
    assert response.data["code"] == "invalid_range"


def test_staff_cancel_sends_a_localized_cancellation_email(
    owner_client: APIClient,
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
    mailoutbox: list,
) -> None:
    appointment = _appointment(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
    )
    appointment.customer_language = "ar"
    appointment.save(update_fields=["customer_language"])

    response = owner_client.patch(
        f"/api/appointments/{appointment.id}/status/",
        {"status": "cancelled"},
        format="json",
    )

    assert response.status_code == 200
    assert len(mailoutbox) == 1
    assert "تم إلغاء حجزك" in mailoutbox[0].subject
