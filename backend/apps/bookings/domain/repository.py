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

    def add(self, appointment: Appointment) -> Appointment: ...

    def update(self, appointment: Appointment) -> Appointment: ...

    def list_for_staff(
        self,
        staff_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
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
