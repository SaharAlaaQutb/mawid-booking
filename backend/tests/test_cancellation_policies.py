from datetime import UTC, datetime, timedelta

import pytest
from apps.bookings.domain.policies import (
    AlwaysAllowPolicy,
    NoCancelPolicy,
    WindowedCancellationPolicy,
)

STARTS_AT = datetime(2026, 11, 2, 9, tzinfo=UTC)


def test_always_allow_policy_allows_cancellation() -> None:
    assert AlwaysAllowPolicy().can_cancel(starts_at=STARTS_AT, now=STARTS_AT)


def test_no_cancel_policy_rejects_cancellation() -> None:
    assert not NoCancelPolicy().can_cancel(
        starts_at=STARTS_AT,
        now=STARTS_AT - timedelta(days=2),
    )


def test_windowed_policy_allows_at_the_boundary_and_earlier() -> None:
    policy = WindowedCancellationPolicy(24)

    assert policy.can_cancel(starts_at=STARTS_AT, now=STARTS_AT - timedelta(hours=24))
    assert policy.can_cancel(starts_at=STARTS_AT, now=STARTS_AT - timedelta(hours=48))


def test_windowed_policy_rejects_inside_the_window() -> None:
    policy = WindowedCancellationPolicy(24)

    assert not policy.can_cancel(
        starts_at=STARTS_AT,
        now=STARTS_AT - timedelta(hours=23, minutes=59),
    )


def test_windowed_policy_rejects_negative_window() -> None:
    with pytest.raises(ValueError, match="negative"):
        WindowedCancellationPolicy(-1)
