from apps.bookings.container import build_appointment_repository
from apps.businesses.container import build_business_repository
from apps.catalog.container import build_service_repository, build_staff_repository
from apps.core.domain.clock import SystemClock
from apps.scheduling.application.availability import AvailabilityService
from apps.scheduling.domain.repository import TimeOffRepository, WorkingHoursRepository
from apps.scheduling.infrastructure.repositories import (
    DjangoTimeOffRepository,
    DjangoWorkingHoursRepository,
)


def build_working_hours_repository() -> WorkingHoursRepository:
    return DjangoWorkingHoursRepository()


def build_time_off_repository() -> TimeOffRepository:
    return DjangoTimeOffRepository()


def build_availability_service() -> AvailabilityService:
    return AvailabilityService(
        business_repository=build_business_repository(),
        service_repository=build_service_repository(),
        staff_repository=build_staff_repository(),
        working_hours_repository=build_working_hours_repository(),
        time_off_repository=build_time_off_repository(),
        appointment_repository=build_appointment_repository(),
        clock=SystemClock(),
    )
