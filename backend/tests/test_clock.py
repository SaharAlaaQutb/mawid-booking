from datetime import UTC

from apps.core.domain.clock import SystemClock


def test_system_clock_returns_timezone_aware_utc_time() -> None:
    now = SystemClock().now()

    assert now.tzinfo is not None
    assert now.utcoffset() == UTC.utcoffset(now)
