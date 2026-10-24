from datetime import datetime, timedelta
from typing import Protocol


class CancellationPolicy(Protocol):
    def can_cancel(self, *, starts_at: datetime, now: datetime) -> bool: ...


class AlwaysAllowPolicy:
    def can_cancel(self, *, starts_at: datetime, now: datetime) -> bool:
        return True


class NoCancelPolicy:
    def can_cancel(self, *, starts_at: datetime, now: datetime) -> bool:
        return False


class WindowedCancellationPolicy:
    def __init__(self, window_hours: int) -> None:
        if window_hours < 0:
            raise ValueError("window_hours cannot be negative")
        self._window = timedelta(hours=window_hours)

    def can_cancel(self, *, starts_at: datetime, now: datetime) -> bool:
        return now <= starts_at - self._window
