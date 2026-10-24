from apps.scheduling.domain.repository import TimeOffRepository, WorkingHoursRepository
from apps.scheduling.infrastructure.repositories import (
    DjangoTimeOffRepository,
    DjangoWorkingHoursRepository,
)


def build_working_hours_repository() -> WorkingHoursRepository:
    return DjangoWorkingHoursRepository()


def build_time_off_repository() -> TimeOffRepository:
    return DjangoTimeOffRepository()
