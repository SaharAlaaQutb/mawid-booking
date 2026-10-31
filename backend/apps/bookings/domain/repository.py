from datetime import datetime
from typing import Protocol
from uuid import UUID

from apps.bookings.domain.entities import Appointment, Customer, Reminder


class CustomerRepository(Protocol):
    def get(self, customer_id: UUID) -> Customer | None: ...

    def get_by_email(self, business_id: UUID, email: str) -> Customer | None: ...

    def add(self, customer: Customer) -> Customer: ...

    def update(self, customer: Customer) -> Customer: ...


class AppointmentRepository(Protocol):
    def get(self, appointment_id: UUID) -> Appointment | None: ...

    def get_by_idempotency_key(
        self,
        business_id: UUID,
        idempotency_key: str,
    ) -> Appointment | None: ...

    def get_by_management_token_hash(self, token_hash: str) -> Appointment | None: ...

    def get_for_update(self, appointment_id: UUID) -> Appointment | None: ...

    def get_by_management_token_hash_for_update(
        self,
        token_hash: str,
    ) -> Appointment | None: ...

    def add(self, appointment: Appointment) -> Appointment: ...

    def update(self, appointment: Appointment) -> Appointment: ...

    def list_for_staff(
        self,
        staff_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
    ) -> list[Appointment]: ...

    def list_for_business(
        self,
        business_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        staff_id: UUID | None = None,
    ) -> list[Appointment]: ...

    def has_overlap(
        self,
        staff_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        exclude_id: UUID | None = None,
    ) -> bool: ...


class ReminderRepository(Protocol):
    def list_due(self, before: datetime) -> list[Reminder]: ...

    def add(self, reminder: Reminder) -> Reminder: ...

    def update(self, reminder: Reminder) -> Reminder: ...

    def cancel_pending_for_appointment(self, appointment_id: UUID) -> None: ...
