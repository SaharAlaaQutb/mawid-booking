from dataclasses import dataclass
from datetime import datetime, time
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WorkingHours:
    id: UUID
    staff_id: UUID
    weekday: int
    start_time: time
    end_time: time


@dataclass(frozen=True, slots=True)
class TimeOff:
    id: UUID
    staff_id: UUID
    starts_at: datetime
    ends_at: datetime
    reason: str
