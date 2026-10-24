from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class WorkingShift:
    start_time: time
    end_time: time


@dataclass(frozen=True, slots=True)
class BusyInterval:
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True, slots=True)
class ServiceTiming:
    duration_minutes: int
    buffer_before_minutes: int = 0
    buffer_after_minutes: int = 0

    @property
    def total_duration_minutes(self) -> int:
        return self.buffer_before_minutes + self.duration_minutes + self.buffer_after_minutes


@dataclass(frozen=True, slots=True)
class SlotPolicy:
    slot_interval_minutes: int
    min_lead_time_minutes: int
    max_advance_days: int


@dataclass(frozen=True, slots=True)
class TimeSlot:
    starts_at: datetime
    ends_at: datetime
    staff_id: UUID | None = None


def _local_datetime(day: date, value: time, zone: ZoneInfo) -> datetime:
    naive = datetime.combine(day, value)
    local = naive.replace(tzinfo=zone)
    return local.astimezone(UTC).astimezone(zone)


def local_day_bounds(day: date, timezone: str) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone)
    return (
        _local_datetime(day, time.min, zone),
        _local_datetime(day + timedelta(days=1), time.min, zone),
    )


def _shift_bounds(day: date, shift: WorkingShift, zone: ZoneInfo) -> tuple[datetime, datetime]:
    starts_at = _local_datetime(day, shift.start_time, zone)
    ends_on = day + timedelta(days=1) if shift.end_time == time(0) else day
    ends_at = _local_datetime(ends_on, shift.end_time, zone)
    return starts_at, ends_at


def _merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    if not intervals:
        return []

    ordered = sorted(intervals, key=lambda interval: interval[0])
    merged = [ordered[0]]
    for starts_at, ends_at in ordered[1:]:
        previous_start, previous_end = merged[-1]
        if starts_at <= previous_end:
            merged[-1] = (previous_start, max(previous_end, ends_at))
        else:
            merged.append((starts_at, ends_at))
    return merged


def _overlaps(
    starts_at: datetime,
    ends_at: datetime,
    busy: list[BusyInterval],
) -> bool:
    return any(starts_at < interval.ends_at and ends_at > interval.starts_at for interval in busy)


class SlotGenerator:
    def generate(
        self,
        *,
        on_date: date,
        timezone: str,
        shifts: list[WorkingShift],
        busy: list[BusyInterval],
        service: ServiceTiming,
        policy: SlotPolicy,
        now: datetime,
        staff_id: UUID | None = None,
    ) -> list[TimeSlot]:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        if policy.slot_interval_minutes <= 0:
            raise ValueError("slot_interval_minutes must be positive")
        if service.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if service.buffer_before_minutes < 0 or service.buffer_after_minutes < 0:
            raise ValueError("buffers cannot be negative")

        zone = ZoneInfo(timezone)
        local_today = now.astimezone(zone).date()
        if on_date < local_today or on_date > local_today + timedelta(days=policy.max_advance_days):
            return []

        intervals = [
            (bounds[0].astimezone(UTC), bounds[1].astimezone(UTC))
            for shift in shifts
            if (bounds := _shift_bounds(on_date, shift, zone))[0] < bounds[1]
        ]
        merged_shifts = _merge_intervals(intervals)
        if not merged_shifts:
            return []

        active_busy = [
            interval
            for interval in busy
            if interval.starts_at < interval.ends_at
            and interval.starts_at.tzinfo is not None
            and interval.ends_at.tzinfo is not None
        ]
        lead_cutoff = now + timedelta(minutes=policy.min_lead_time_minutes)
        advance = timedelta(minutes=policy.slot_interval_minutes)
        occupation_after = timedelta(
            minutes=service.duration_minutes + service.buffer_after_minutes
        )
        occupation_before = timedelta(minutes=service.buffer_before_minutes)

        slots: list[TimeSlot] = []
        seen: set[datetime] = set()
        for shift_start, shift_end in merged_shifts:
            cursor = shift_start.astimezone(UTC)
            while cursor < shift_end:
                occupied_start = cursor - occupation_before
                occupied_end = cursor + occupation_after
                if (
                    cursor >= lead_cutoff
                    and occupied_start >= shift_start
                    and occupied_end <= shift_end
                    and not _overlaps(occupied_start, occupied_end, active_busy)
                    and cursor not in seen
                ):
                    slots.append(
                        TimeSlot(
                            starts_at=cursor.astimezone(zone),
                            ends_at=(
                                cursor + timedelta(minutes=service.duration_minutes)
                            ).astimezone(zone),
                            staff_id=staff_id,
                        )
                    )
                    seen.add(cursor)
                cursor += advance

        return sorted(slots, key=lambda slot: slot.starts_at.astimezone(UTC))
