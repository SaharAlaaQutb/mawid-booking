from apps.bookings.domain.repository import (
    AppointmentRepository,
    CustomerRepository,
    ReminderRepository,
)
from apps.bookings.infrastructure.repositories import (
    DjangoAppointmentRepository,
    DjangoCustomerRepository,
    DjangoReminderRepository,
)


def build_customer_repository() -> CustomerRepository:
    return DjangoCustomerRepository()


def build_appointment_repository() -> AppointmentRepository:
    return DjangoAppointmentRepository()


def build_reminder_repository() -> ReminderRepository:
    return DjangoReminderRepository()
