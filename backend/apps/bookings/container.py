from apps.bookings.application.availability import AvailabilityGateway
from apps.bookings.application.booking import BookingService
from apps.bookings.application.calendar import CalendarService
from apps.bookings.application.management import BookingManagementService
from apps.bookings.application.staff_actions import StaffAppointmentService
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
from apps.businesses.container import build_business_repository
from apps.catalog.container import build_service_repository, build_staff_repository
from apps.core.domain.clock import SystemClock
from apps.core.infrastructure.unit_of_work import build_unit_of_work


def build_customer_repository() -> CustomerRepository:
    return DjangoCustomerRepository()


def build_appointment_repository() -> AppointmentRepository:
    return DjangoAppointmentRepository()


def build_reminder_repository() -> ReminderRepository:
    return DjangoReminderRepository()


def build_booking_service() -> BookingService:
    from apps.scheduling.container import build_availability_service

    return BookingService(
        business_repository=build_business_repository(),
        service_repository=build_service_repository(),
        staff_repository=build_staff_repository(),
        customer_repository=build_customer_repository(),
        appointment_repository=build_appointment_repository(),
        reminder_repository=build_reminder_repository(),
        availability=AvailabilityGateway(build_availability_service()),
        unit_of_work=build_unit_of_work(),
    )


def build_management_service() -> BookingManagementService:
    from apps.scheduling.container import build_availability_service

    return BookingManagementService(
        business_repository=build_business_repository(),
        service_repository=build_service_repository(),
        staff_repository=build_staff_repository(),
        customer_repository=build_customer_repository(),
        appointment_repository=build_appointment_repository(),
        reminder_repository=build_reminder_repository(),
        availability=AvailabilityGateway(build_availability_service()),
        unit_of_work=build_unit_of_work(),
        clock=SystemClock(),
    )


def build_staff_appointment_service() -> StaffAppointmentService:
    return StaffAppointmentService(
        business_repository=build_business_repository(),
        service_repository=build_service_repository(),
        staff_repository=build_staff_repository(),
        customer_repository=build_customer_repository(),
        appointment_repository=build_appointment_repository(),
        reminder_repository=build_reminder_repository(),
        unit_of_work=build_unit_of_work(),
        clock=SystemClock(),
    )


def build_calendar_service() -> CalendarService:
    return CalendarService(
        business_repository=build_business_repository(),
        service_repository=build_service_repository(),
        staff_repository=build_staff_repository(),
        customer_repository=build_customer_repository(),
        appointment_repository=build_appointment_repository(),
    )
