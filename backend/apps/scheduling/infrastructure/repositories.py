from datetime import date, datetime, timedelta
from uuid import UUID

from apps.scheduling.domain.entities import TimeOff, WorkingHours
from apps.scheduling.infrastructure.models import TimeOff as TimeOffModel
from apps.scheduling.infrastructure.models import WorkingHours as WorkingHoursModel


def _working_hours_to_entity(model: WorkingHoursModel) -> WorkingHours:
    return WorkingHours(
        id=model.id,
        staff_id=model.staff_id,
        weekday=model.weekday,
        start_time=model.start_time,
        end_time=model.end_time,
    )


def _time_off_to_entity(model: TimeOffModel) -> TimeOff:
    return TimeOff(
        id=model.id,
        staff_id=model.staff_id,
        starts_at=model.starts_at,
        ends_at=model.ends_at,
        reason=model.reason,
    )


class DjangoWorkingHoursRepository:
    def list_for_staff_day(self, staff_id: UUID, weekday: int) -> list[WorkingHours]:
        models = WorkingHoursModel.objects.filter(staff_id=staff_id, weekday=weekday)
        return [_working_hours_to_entity(model) for model in models]

    def list_for_staff_range(
        self,
        staff_id: UUID,
        starts_on: date,
        ends_on: date,
    ) -> list[WorkingHours]:
        span = (ends_on - starts_on).days
        weekdays = {(starts_on + timedelta(days=offset)).weekday() for offset in range(span + 1)}
        models = WorkingHoursModel.objects.filter(staff_id=staff_id, weekday__in=weekdays)
        return [_working_hours_to_entity(model) for model in models]

    def list_for_staff(self, staff_id: UUID) -> list[WorkingHours]:
        models = WorkingHoursModel.objects.filter(staff_id=staff_id)
        return [_working_hours_to_entity(model) for model in models]


class DjangoTimeOffRepository:
    def list_overlapping(
        self,
        staff_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
    ) -> list[TimeOff]:
        models = TimeOffModel.objects.filter(
            staff_id=staff_id,
            starts_at__lt=ends_at,
            ends_at__gt=starts_at,
        )
        return [_time_off_to_entity(model) for model in models]

    def list_for_staff(self, staff_id: UUID) -> list[TimeOff]:
        models = TimeOffModel.objects.filter(staff_id=staff_id)
        return [_time_off_to_entity(model) for model in models]
