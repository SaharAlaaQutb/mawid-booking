from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from apps.bookings.domain.status import AppointmentStatus, ReminderKind, ReminderStatus


@dataclass(frozen=True, slots=True)
class Customer:
    id: UUID
    business_id: UUID
    name: str
    email: str
    phone: str
    language: str


@dataclass(frozen=True, slots=True)
class Appointment:
    id: UUID
    business_id: UUID
    service_id: UUID
    staff_id: UUID
    customer_id: UUID
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    price_minor: int
    currency: str
    customer_language: str
    notes: str
    management_token_hash: str | None
    management_token_expires_at: datetime | None
    idempotency_key: str | None
    rescheduled_from_id: UUID | None
    cancelled_at: datetime | None = None
    cancelled_by: str = ""
    cancellation_reason: str = ""


@dataclass(frozen=True, slots=True)
class Reminder:
    id: UUID
    appointment_id: UUID
    kind: ReminderKind
    send_at: datetime
    sent_at: datetime | None
    status: ReminderStatus
    attempts: int
    language: str
