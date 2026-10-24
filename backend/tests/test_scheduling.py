from datetime import UTC, date, datetime, time, timedelta

import pytest
from apps.catalog.infrastructure.models import Staff
from apps.scheduling.container import (
    build_time_off_repository,
    build_working_hours_repository,
)
from apps.scheduling.infrastructure.models import TimeOff, WorkingHours
from django.core.exceptions import ValidationError


def test_working_hours_reject_overlap(staff: Staff) -> None:
    WorkingHours.objects.create(
        staff=staff,
        weekday=0,
        start_time=time(9),
        end_time=time(12),
    )

    with pytest.raises(ValidationError, match="overlaps"):
        WorkingHours(
            staff=staff,
            weekday=0,
            start_time=time(11),
            end_time=time(13),
        ).full_clean()


def test_adjacent_working_hours_are_allowed(staff: Staff) -> None:
    WorkingHours.objects.create(
        staff=staff,
        weekday=0,
        start_time=time(9),
        end_time=time(12),
    )

    shift = WorkingHours(
        staff=staff,
        weekday=0,
        start_time=time(12),
        end_time=time(17),
    )
    shift.full_clean()


def test_midnight_end_is_treated_as_end_of_day(staff: Staff) -> None:
    shift = WorkingHours(
        staff=staff,
        weekday=0,
        start_time=time(22),
        end_time=time(0),
    )
    shift.full_clean()


def test_working_hours_repository_returns_day(staff: Staff) -> None:
    shift = WorkingHours.objects.create(
        staff=staff,
        weekday=1,
        start_time=time(9),
        end_time=time(17),
    )
    WorkingHours.objects.create(
        staff=staff,
        weekday=2,
        start_time=time(9),
        end_time=time(17),
    )

    assert build_working_hours_repository().list_for_staff_day(staff.id, 1)[0].id == shift.id


def test_working_hours_repository_returns_range(staff: Staff) -> None:
    monday = WorkingHours.objects.create(
        staff=staff,
        weekday=0,
        start_time=time(9),
        end_time=time(17),
    )
    wednesday = WorkingHours.objects.create(
        staff=staff,
        weekday=2,
        start_time=time(9),
        end_time=time(17),
    )

    shifts = build_working_hours_repository().list_for_staff_range(
        staff.id,
        date(2026, 11, 4),
        date(2026, 11, 5),
    )

    assert {shift.id for shift in shifts} == {wednesday.id}
    assert monday.id not in {shift.id for shift in shifts}


def test_time_off_repository_finds_overlaps(staff: Staff) -> None:
    start = datetime(2026, 11, 2, 9, tzinfo=UTC)
    time_off = TimeOff.objects.create(
        staff=staff,
        starts_at=start,
        ends_at=start + timedelta(hours=2),
        reason="Training",
    )

    repository = build_time_off_repository()

    assert repository.list_overlapping(
        staff.id,
        start + timedelta(minutes=30),
        start + timedelta(hours=1),
    ) == [repository.list_for_staff(staff.id)[0]]
    assert (
        repository.list_overlapping(
            staff.id,
            start + timedelta(hours=2),
            start + timedelta(hours=3),
        )
        == []
    )
    assert repository.list_for_staff(staff.id)[0].id == time_off.id


def test_time_off_rejects_naive_datetimes(staff: Staff) -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        TimeOff(
            staff=staff,
            starts_at=datetime(2026, 11, 2, 9),
            ends_at=datetime(2026, 11, 2, 10),
        ).full_clean()
