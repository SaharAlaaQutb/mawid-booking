from datetime import UTC, date, datetime, time, timedelta

import pytest
from apps.scheduling.domain.slot_generator import (
    BusyInterval,
    ServiceTiming,
    SlotGenerator,
    SlotPolicy,
    WorkingShift,
)

GENERATOR = SlotGenerator()


def _policy(
    *,
    interval: int = 15,
    lead: int = 0,
    max_advance_days: int = 60,
) -> SlotPolicy:
    return SlotPolicy(
        slot_interval_minutes=interval,
        min_lead_time_minutes=lead,
        max_advance_days=max_advance_days,
    )


def _service(duration: int = 30, before: int = 0, after: int = 0) -> ServiceTiming:
    return ServiceTiming(
        duration_minutes=duration,
        buffer_before_minutes=before,
        buffer_after_minutes=after,
    )


def test_generates_slots_within_shift() -> None:
    slots = GENERATOR.generate(
        on_date=date(2026, 10, 26),
        timezone="UTC",
        shifts=[WorkingShift(time(9), time(10))],
        busy=[],
        service=_service(),
        policy=_policy(),
        now=datetime(2026, 10, 24, 8, tzinfo=UTC),
    )

    assert [slot.starts_at.strftime("%H:%M") for slot in slots] == [
        "09:00",
        "09:15",
        "09:30",
    ]
    assert slots[0].ends_at.strftime("%H:%M") == "09:30"


def test_applies_lead_time() -> None:
    slots = GENERATOR.generate(
        on_date=date(2026, 10, 26),
        timezone="UTC",
        shifts=[WorkingShift(time(9), time(10, 30))],
        busy=[],
        service=_service(),
        policy=_policy(lead=30),
        now=datetime(2026, 10, 26, 9, 15, tzinfo=UTC),
    )

    assert [slot.starts_at.strftime("%H:%M") for slot in slots] == ["09:45", "10:00"]


def test_applies_buffers_to_both_edges() -> None:
    slots = GENERATOR.generate(
        on_date=date(2026, 10, 26),
        timezone="UTC",
        shifts=[WorkingShift(time(9), time(10, 30))],
        busy=[],
        service=_service(before=15, after=15),
        policy=_policy(),
        now=datetime(2026, 10, 24, 8, tzinfo=UTC),
    )

    assert [slot.starts_at.strftime("%H:%M") for slot in slots] == [
        "09:15",
        "09:30",
        "09:45",
    ]


def test_subtracts_busy_intervals() -> None:
    slots = GENERATOR.generate(
        on_date=date(2026, 10, 26),
        timezone="UTC",
        shifts=[WorkingShift(time(9), time(10))],
        busy=[
            BusyInterval(
                starts_at=datetime(2026, 10, 26, 9, 20, tzinfo=UTC),
                ends_at=datetime(2026, 10, 26, 9, 40, tzinfo=UTC),
            )
        ],
        service=_service(15),
        policy=_policy(),
        now=datetime(2026, 10, 24, 8, tzinfo=UTC),
    )

    assert [slot.starts_at.strftime("%H:%M") for slot in slots] == ["09:00", "09:45"]


def test_merges_adjacent_shifts() -> None:
    slots = GENERATOR.generate(
        on_date=date(2026, 10, 26),
        timezone="UTC",
        shifts=[
            WorkingShift(time(9), time(10)),
            WorkingShift(time(10), time(11)),
        ],
        busy=[],
        service=_service(),
        policy=_policy(),
        now=datetime(2026, 10, 24, 8, tzinfo=UTC),
    )

    assert [slot.starts_at.strftime("%H:%M") for slot in slots] == [
        "09:00",
        "09:15",
        "09:30",
        "09:45",
        "10:00",
        "10:15",
        "10:30",
    ]


def test_midnight_end_time() -> None:
    slots = GENERATOR.generate(
        on_date=date(2026, 10, 26),
        timezone="UTC",
        shifts=[WorkingShift(time(22), time(0))],
        busy=[],
        service=_service(),
        policy=_policy(interval=30),
        now=datetime(2026, 10, 24, 8, tzinfo=UTC),
    )

    assert [slot.starts_at.strftime("%H:%M") for slot in slots] == [
        "22:00",
        "22:30",
        "23:00",
        "23:30",
    ]


def test_dst_spring_forward_uses_real_time() -> None:
    slots = GENERATOR.generate(
        on_date=date(2026, 3, 29),
        timezone="Europe/London",
        shifts=[WorkingShift(time(0), time(4))],
        busy=[],
        service=_service(15),
        policy=_policy(),
        now=datetime(2026, 3, 28, 0, tzinfo=UTC),
    )

    local_times = [slot.starts_at.strftime("%H:%M") for slot in slots]

    assert len(slots) == 12
    assert "00:45" in local_times
    assert "01:00" not in local_times
    assert "02:00" in local_times


def test_dst_fall_back_keeps_both_repeated_hours() -> None:
    slots = GENERATOR.generate(
        on_date=date(2026, 10, 25),
        timezone="Europe/London",
        shifts=[WorkingShift(time(0), time(4))],
        busy=[],
        service=_service(15),
        policy=_policy(),
        now=datetime(2026, 10, 24, 0, tzinfo=UTC),
    )

    local_times = [slot.starts_at.strftime("%H:%M") for slot in slots]

    assert len(slots) == 20
    assert local_times.count("01:00") == 2
    assert len({slot.starts_at.astimezone(UTC) for slot in slots}) == 20


def test_closed_day_returns_no_slots() -> None:
    slots = GENERATOR.generate(
        on_date=date(2026, 10, 26),
        timezone="UTC",
        shifts=[],
        busy=[],
        service=_service(),
        policy=_policy(),
        now=datetime(2026, 10, 24, 8, tzinfo=UTC),
    )

    assert slots == []


def test_past_date_returns_no_slots() -> None:
    slots = GENERATOR.generate(
        on_date=date(2026, 10, 25),
        timezone="UTC",
        shifts=[WorkingShift(time(9), time(17))],
        busy=[],
        service=_service(),
        policy=_policy(),
        now=datetime(2026, 10, 26, 8, tzinfo=UTC),
    )

    assert slots == []


def test_outside_horizon_returns_no_slots() -> None:
    now = datetime(2026, 10, 24, 8, tzinfo=UTC)
    slots = GENERATOR.generate(
        on_date=now.date() + timedelta(days=61),
        timezone="UTC",
        shifts=[WorkingShift(time(9), time(17))],
        busy=[],
        service=_service(),
        policy=_policy(max_advance_days=60),
        now=now,
    )

    assert slots == []


def test_non_adjacent_shifts_keep_the_gap() -> None:
    slots = GENERATOR.generate(
        on_date=date(2026, 10, 26),
        timezone="UTC",
        shifts=[
            WorkingShift(time(9), time(10)),
            WorkingShift(time(11), time(12)),
        ],
        busy=[],
        service=_service(30),
        policy=_policy(interval=30),
        now=datetime(2026, 10, 24, 8, tzinfo=UTC),
    )

    assert [slot.starts_at.strftime("%H:%M") for slot in slots] == [
        "09:00",
        "09:30",
        "11:00",
        "11:30",
    ]


@pytest.mark.parametrize(
    ("service_timing", "policy", "message"),
    [
        (ServiceTiming(duration_minutes=0), _policy(), "duration_minutes"),
        (ServiceTiming(duration_minutes=15, buffer_before_minutes=-1), _policy(), "buffers"),
        (ServiceTiming(duration_minutes=15, buffer_after_minutes=-1), _policy(), "buffers"),
        (_service(15), _policy(interval=0), "slot_interval_minutes"),
    ],
)
def test_rejects_invalid_configuration(
    service_timing: ServiceTiming,
    policy: SlotPolicy,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        GENERATOR.generate(
            on_date=date(2026, 10, 26),
            timezone="UTC",
            shifts=[WorkingShift(time(9), time(17))],
            busy=[],
            service=service_timing,
            policy=policy,
            now=datetime(2026, 10, 24, 8, tzinfo=UTC),
        )


def test_service_total_duration_includes_buffers() -> None:
    assert _service(30, before=5, after=10).total_duration_minutes == 45


def test_naive_now_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        GENERATOR.generate(
            on_date=date(2026, 10, 26),
            timezone="UTC",
            shifts=[WorkingShift(time(9), time(17))],
            busy=[],
            service=_service(),
            policy=_policy(),
            now=datetime(2026, 10, 24, 8),
        )
