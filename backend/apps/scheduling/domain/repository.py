from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from apps.scheduling.domain.entities import TimeOff, WorkingHours


class WorkingHoursRepository(Protocol):
    def list_for_staff_day(self, staff_id: UUID, weekday: int) -> list[WorkingHours]: ...

    def list_for_staff_range(
        self,
        staff_id: UUID,
        starts_on: date,
        ends_on: date,
    ) -> list[WorkingHours]: ...

    def list_for_staff(self, staff_id: UUID) -> list[WorkingHours]: ...


class TimeOffRepository(Protocol):
    def list_overlapping(
        self,
        staff_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
    ) -> list[TimeOff]: ...

    def list_for_staff(self, staff_id: UUID) -> list[TimeOff]: ...
