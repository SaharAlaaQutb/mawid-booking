from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.bookings.application.management import ManagedBooking
from apps.bookings.domain.entities import Appointment, Customer
from apps.bookings.domain.status import AppointmentStatus
from apps.businesses.domain.entities import Business
from apps.catalog.domain.entities import Service, Staff
from apps.core.domain.localized_text import LocalizedText
from apps.notifications.domain.ics import IcsEvent, build_ics
from apps.notifications.infrastructure.ics import DjangoIcsService

MANAGEMENT_URL = "https://mawid.test/manage/token-value"
STARTS_AT = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


def _booking(language: str = "en") -> ManagedBooking:
    business = Business(
        id=uuid4(),
        slug="test-clinic",
        name=LocalizedText(ar="عيادة الاختبار", en="Test Clinic"),
        timezone="Asia/Riyadh",
        default_locale="en",
        currency="SAR",
        slot_interval_minutes=15,
        min_lead_time_minutes=120,
        max_advance_days=60,
        cancellation_window_hours=24,
        phone="+966500000000",
        address=LocalizedText(ar="الرياض", en="Riyadh"),
        is_active=True,
    )
    service = Service(
        id=uuid4(),
        business_id=business.id,
        name=LocalizedText(ar="استشارة", en="Consultation"),
        description=LocalizedText(ar="فحص عام", en="General checkup"),
        duration_minutes=30,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
        price_minor=20000,
        currency="SAR",
        is_active=True,
        sort_order=0,
    )
    staff = Staff(
        id=uuid4(),
        business_id=business.id,
        user_id=None,
        name=LocalizedText(ar="سارة", en="Sarah"),
        title=LocalizedText(ar="طبيبة", en="Doctor"),
        bio=LocalizedText(),
        preferred_language="en",
        color="#0F766E",
        is_active=True,
    )
    customer = Customer(
        id=uuid4(),
        business_id=business.id,
        name="Layla",
        email="layla@example.com",
        phone="+966500000000",
        language=language,
    )
    appointment = Appointment(
        id=uuid4(),
        business_id=business.id,
        service_id=service.id,
        staff_id=staff.id,
        customer_id=customer.id,
        starts_at=STARTS_AT,
        ends_at=STARTS_AT + timedelta(minutes=30),
        status=AppointmentStatus.PENDING,
        price_minor=20000,
        currency="SAR",
        customer_language=language,
        notes="",
        management_token_hash=None,
        management_token_expires_at=None,
        idempotency_key=None,
        rescheduled_from_id=None,
    )
    return ManagedBooking(
        appointment=appointment,
        customer=customer,
        service=service,
        staff=staff,
        business=business,
    )


def test_builds_calendar_with_stable_uid_and_utc_timestamps() -> None:
    booking = _booking()
    service = DjangoIcsService()

    first = service.build(booking, management_url=MANAGEMENT_URL)
    second = service.build(booking, management_url=MANAGEMENT_URL)

    assert first == second
    assert "BEGIN:VCALENDAR" in first
    assert f"UID:appointment-{booking.appointment.id}@mawid" in first
    assert "DTSTART:20261102T090000Z" in first
    assert "DTEND:20261102T093000Z" in first
    assert f"URL:{MANAGEMENT_URL}" in first


def test_arabic_calendar_invite_is_localized() -> None:
    content = DjangoIcsService().build(_booking(language="ar"), management_url=MANAGEMENT_URL)

    assert "موعد: استشارة في عيادة الاختبار" in content
    assert "الموظف: سارة" in content
    assert "الرياض" in content


def test_escapes_commas_semicolons_and_newlines() -> None:
    content = build_ics(
        IcsEvent(
            uid="event-1@mawid",
            summary="Checkup, follow-up; bring\nnotes",
            description="Line one\nLine two",
            starts_at=STARTS_AT,
            ends_at=STARTS_AT + timedelta(minutes=30),
        )
    )

    assert "SUMMARY:Checkup\\, follow-up\\; bring\\nnotes" in content
    assert "DESCRIPTION:Line one\\nLine two" in content


def test_folds_long_lines_at_75_octets() -> None:
    content = build_ics(
        IcsEvent(
            uid="event-1@mawid",
            summary="Summary",
            description="x" * 200,
            starts_at=STARTS_AT,
            ends_at=STARTS_AT + timedelta(minutes=30),
        )
    )

    for line in content.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75
