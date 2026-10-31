from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from apps.bookings.domain.entities import Appointment, Customer
from apps.bookings.domain.status import AppointmentStatus
from apps.businesses.domain.entities import Business
from apps.catalog.domain.entities import Service, Staff
from apps.core.domain.localized_text import LocalizedText
from apps.notifications.application.context import MessageContextBuilder
from apps.notifications.domain.messages import MessageContext, NotificationKind
from apps.notifications.infrastructure.renderers import DjangoTemplateMessageRenderer

MANAGEMENT_URL = "https://mawid.example/manage/token-value"


def _business() -> Business:
    return Business(
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


def _service(*, name_ar: str = "استشارة") -> Service:
    return Service(
        id=uuid4(),
        business_id=uuid4(),
        name=LocalizedText(ar=name_ar, en="Consultation"),
        description=LocalizedText(ar="فحص عام", en="General checkup"),
        duration_minutes=30,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
        price_minor=20000,
        currency="SAR",
        is_active=True,
        sort_order=0,
    )


def _staff(*, name_ar: str = "سارة") -> Staff:
    return Staff(
        id=uuid4(),
        business_id=uuid4(),
        user_id=None,
        name=LocalizedText(ar=name_ar, en="Sarah"),
        title=LocalizedText(ar="طبيبة", en="Doctor"),
        bio=LocalizedText(),
        preferred_language="en",
        color="#0F766E",
        is_active=True,
    )


def _customer(language: str = "ar") -> Customer:
    return Customer(
        id=uuid4(),
        business_id=uuid4(),
        name="Layla",
        email="layla@example.com",
        phone="+966500000000",
        language=language,
    )


def _appointment(language: str = "ar", notes: str = "") -> Appointment:
    starts_at = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
    return Appointment(
        id=uuid4(),
        business_id=uuid4(),
        service_id=uuid4(),
        staff_id=uuid4(),
        customer_id=uuid4(),
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        status=AppointmentStatus.PENDING,
        price_minor=20000,
        currency="SAR",
        customer_language=language,
        notes=notes,
        management_token_hash=None,
        management_token_expires_at=None,
        idempotency_key=None,
        rescheduled_from_id=None,
    )


def _context(
    *,
    language: str = "en",
    service_ar: str = "استشارة",
    notes: str = "",
) -> MessageContext:
    return MessageContextBuilder().build(
        appointment=_appointment(language=language, notes=notes),
        customer=_customer(language=language),
        service=_service(name_ar=service_ar),
        staff=_staff(),
        business=_business(),
        management_url=MANAGEMENT_URL,
    )


@pytest.fixture
def renderer() -> DjangoTemplateMessageRenderer:
    return DjangoTemplateMessageRenderer()


def test_english_confirmation_contains_localized_booking_details(
    renderer: DjangoTemplateMessageRenderer,
) -> None:
    message = renderer.render(NotificationKind.CONFIRMATION, _context(language="en"))

    assert "Test Clinic" in message.subject
    assert "confirmed" in message.subject
    assert "Layla" in message.text_body
    assert "Consultation" in message.text_body
    assert "Sarah" in message.text_body
    assert "12:00 - 12:30" in message.text_body
    assert "200.00 SAR" in message.text_body
    assert MANAGEMENT_URL in message.text_body
    assert 'dir="ltr"' in message.html_body


def test_arabic_confirmation_uses_arabic_content_and_rtl_html(
    renderer: DjangoTemplateMessageRenderer,
) -> None:
    message = renderer.render(NotificationKind.CONFIRMATION, _context(language="ar"))

    assert "عيادة الاختبار" in message.subject
    assert "تم تأكيد حجزك" in message.subject
    assert "مرحباً" in message.text_body
    assert "استشارة" in message.text_body
    assert "سارة" in message.text_body
    assert 'dir="rtl"' in message.html_body
    assert 'lang="ar"' in message.html_body


def test_missing_arabic_value_falls_back_to_english(
    renderer: DjangoTemplateMessageRenderer,
) -> None:
    message = renderer.render(
        NotificationKind.CONFIRMATION,
        _context(language="ar", service_ar=""),
    )

    assert "Consultation" in message.text_body


def test_utc_booking_is_rendered_in_business_timezone(
    renderer: DjangoTemplateMessageRenderer,
) -> None:
    message = renderer.render(NotificationKind.CONFIRMATION, _context(language="en"))

    assert "12:00" in message.text_body
    assert "Asia/Riyadh" in message.text_body


def test_each_notification_kind_has_a_distinct_subject(
    renderer: DjangoTemplateMessageRenderer,
) -> None:
    context = _context(language="en")
    subjects = {renderer.render(kind, context).subject for kind in NotificationKind}

    assert len(subjects) == len(NotificationKind)
    assert all("Test Clinic" in subject for subject in subjects)


def test_notes_are_rendered_when_present(
    renderer: DjangoTemplateMessageRenderer,
) -> None:
    message = renderer.render(
        NotificationKind.CONFIRMATION,
        _context(language="en", notes="Bring your insurance card"),
    )

    assert "Bring your insurance card" in message.text_body


def test_unsupported_language_falls_back_to_business_default(
    renderer: DjangoTemplateMessageRenderer,
) -> None:
    message = renderer.render(NotificationKind.CONFIRMATION, _context(language="fr"))

    assert "Your booking is confirmed." in message.text_body
