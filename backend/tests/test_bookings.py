from dataclasses import replace
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from apps.bookings.container import (
    build_appointment_repository,
    build_customer_repository,
    build_reminder_repository,
)
from apps.bookings.domain.entities import Appointment, Reminder
from apps.bookings.domain.status import (
    AppointmentStatus,
    ReminderKind,
    ReminderStatus,
)
from apps.bookings.domain.transitions import (
    InvalidStatusTransitionError,
    can_transition,
    ensure_transition,
)
from apps.bookings.infrastructure.models import Appointment as AppointmentModel
from apps.bookings.infrastructure.models import Customer
from apps.bookings.infrastructure.models import Reminder as ReminderModel
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Service, Staff
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone


def _appointment(
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
    starts_at: datetime,
    ends_at: datetime,
    status: AppointmentStatus = AppointmentStatus.CONFIRMED,
) -> AppointmentModel:
    return AppointmentModel.objects.create(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
        starts_at=starts_at,
        ends_at=ends_at,
        status=status.value,
        price_minor=service.price_minor,
        currency=business.currency,
        customer_language=customer.language,
    )


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED),
        (AppointmentStatus.PENDING, AppointmentStatus.CANCELLED),
        (AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED),
        (AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED),
        (AppointmentStatus.CONFIRMED, AppointmentStatus.NO_SHOW),
    ],
)
def test_allowed_status_transitions(
    current: AppointmentStatus,
    target: AppointmentStatus,
) -> None:
    assert can_transition(current, target)
    ensure_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (AppointmentStatus.COMPLETED, AppointmentStatus.CONFIRMED),
        (AppointmentStatus.CANCELLED, AppointmentStatus.PENDING),
        (AppointmentStatus.NO_SHOW, AppointmentStatus.CONFIRMED),
    ],
)
def test_forbidden_status_transitions(
    current: AppointmentStatus,
    target: AppointmentStatus,
) -> None:
    assert not can_transition(current, target)
    with pytest.raises(InvalidStatusTransitionError):
        ensure_transition(current, target)


def test_customer_email_is_normalized(customer: Customer) -> None:
    assert customer.email == "layla@example.com"


def test_customer_repository_is_scoped_by_business(business: Business, customer: Customer) -> None:
    repository = build_customer_repository()
    other_business = Business.objects.create(
        slug="other",
        name_en="Other",
        name_ar="آخر",
    )

    assert repository.get_by_email(business.id, "LAYLA@EXAMPLE.COM") == repository.get(customer.id)
    assert repository.get_by_email(other_business.id, customer.email) is None


def test_appointment_clean_rejects_staff_overlap(
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    _appointment(business, service, staff, customer, starts_at, ends_at)

    overlap = AppointmentModel(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
        starts_at=starts_at + timedelta(minutes=15),
        ends_at=ends_at + timedelta(minutes=15),
        status=AppointmentStatus.PENDING.value,
    )

    with pytest.raises(ValidationError, match="already has an appointment"):
        overlap.full_clean()


def test_cancelled_appointments_do_not_block_a_slot(
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    _appointment(
        business,
        service,
        staff,
        customer,
        starts_at,
        ends_at,
        AppointmentStatus.CANCELLED,
    )

    replacement = AppointmentModel(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
        starts_at=starts_at,
        ends_at=ends_at,
        status=AppointmentStatus.PENDING.value,
    )
    replacement.full_clean()


def test_appointment_repository_round_trip(
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    repository = build_appointment_repository()
    appointment = Appointment(
        id=uuid4(),
        business_id=business.id,
        service_id=service.id,
        staff_id=staff.id,
        customer_id=customer.id,
        starts_at=starts_at,
        ends_at=ends_at,
        status=AppointmentStatus.CONFIRMED,
        price_minor=service.price_minor,
        currency=business.currency,
        customer_language=customer.language,
        notes="First visit",
        management_token_hash=None,
        management_token_expires_at=None,
        idempotency_key="round-trip",
        rescheduled_from_id=None,
    )

    saved = repository.add(appointment)

    assert saved == appointment
    assert repository.get(appointment.id) == appointment
    assert repository.has_overlap(staff.id, starts_at, ends_at)
    assert not repository.has_overlap(
        staff.id,
        ends_at,
        ends_at + timedelta(minutes=30),
    )

    cancelled = replace(appointment, status=AppointmentStatus.CANCELLED)
    repository.update(cancelled)

    saved_cancelled = repository.get(appointment.id)
    assert saved_cancelled is not None
    assert saved_cancelled.status == AppointmentStatus.CANCELLED
    assert not repository.has_overlap(staff.id, starts_at, ends_at)


def test_appointment_list_does_not_issue_n_plus_one_queries(
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    for offset in range(3):
        start = starts_at + timedelta(hours=offset)
        _appointment(
            business,
            service,
            staff,
            customer,
            start,
            start + timedelta(minutes=30),
        )

    repository = build_appointment_repository()
    with CaptureQueriesContext(connection) as queries:
        appointments = repository.list_for_staff(
            staff.id,
            starts_at,
            starts_at + timedelta(hours=3),
        )

    assert len(appointments) == 3
    assert len(queries) == 1


def test_idempotency_key_is_unique_per_business(
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    AppointmentModel.objects.create(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
        starts_at=starts_at,
        ends_at=ends_at,
        status=AppointmentStatus.CONFIRMED.value,
        idempotency_key="duplicate",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        AppointmentModel.objects.create(
            business=business,
            service=service,
            staff=staff,
            customer=customer,
            starts_at=ends_at + timedelta(hours=1),
            ends_at=ends_at + timedelta(hours=2),
            status=AppointmentStatus.CONFIRMED.value,
            idempotency_key="duplicate",
        )


def test_reminder_repository_lists_due_reminders(
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    appointment = _appointment(business, service, staff, customer, starts_at, ends_at)
    due = ReminderModel.objects.create(
        appointment=appointment,
        kind=ReminderKind.REMINDER.value,
        send_at=timezone.now() - timedelta(minutes=1),
        language="ar",
    )
    ReminderModel.objects.create(
        appointment=appointment,
        kind=ReminderKind.CONFIRMATION.value,
        send_at=timezone.now() + timedelta(hours=1),
    )

    reminders = build_reminder_repository().list_due(timezone.now())

    assert [reminder.id for reminder in reminders] == [due.id]
    assert reminders[0].kind == ReminderKind.REMINDER
    assert reminders[0].status == ReminderStatus.PENDING


def test_reminder_repository_round_trip(
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    appointment = _appointment(business, service, staff, customer, starts_at, ends_at)
    repository = build_reminder_repository()
    reminder = Reminder(
        id=uuid4(),
        appointment_id=appointment.id,
        kind=ReminderKind.CONFIRMATION,
        send_at=starts_at - timedelta(hours=24),
        sent_at=None,
        status=ReminderStatus.PENDING,
        attempts=0,
        language="en",
    )

    saved = repository.add(reminder)

    assert saved == reminder
    updated = replace(
        reminder,
        status=ReminderStatus.SENT,
        sent_at=timezone.now(),
        attempts=1,
    )
    assert repository.update(updated).status == ReminderStatus.SENT


@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="The exclusion constraint is PostgreSQL-only.",
)
def test_database_rejects_overlapping_active_appointments(
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    _appointment(business, service, staff, customer, starts_at, ends_at)

    with pytest.raises(IntegrityError), transaction.atomic():
        _appointment(
            business,
            service,
            staff,
            customer,
            starts_at + timedelta(minutes=15),
            ends_at + timedelta(minutes=15),
        )


def test_appointment_requires_aware_datetimes(
    business: Business,
    service: Service,
    staff: Staff,
    customer: Customer,
) -> None:
    appointment = AppointmentModel(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
        starts_at=datetime(2026, 11, 2, 9),
        ends_at=datetime(2026, 11, 2, 10),
    )

    with pytest.raises(ValidationError, match="timezone-aware"):
        appointment.full_clean()
