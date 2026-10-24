from dataclasses import dataclass
from datetime import UTC, date, datetime, time

import pytest
from apps.bookings.domain.status import AppointmentStatus
from apps.bookings.infrastructure.models import Appointment as AppointmentModel
from apps.bookings.infrastructure.repositories import DjangoAppointmentRepository
from apps.businesses.infrastructure.models import Business
from apps.businesses.infrastructure.repositories import DjangoBusinessRepository
from apps.catalog.infrastructure.models import Service, Staff, StaffService
from apps.catalog.infrastructure.repositories import (
    DjangoServiceRepository,
    DjangoStaffRepository,
)
from apps.scheduling.application.availability import AvailabilityService
from apps.scheduling.domain.errors import (
    BusinessNotConfiguredError,
    DateOutsideHorizonError,
    ServiceNotAvailableError,
    StaffNotAvailableError,
)
from apps.scheduling.infrastructure.models import TimeOff, WorkingHours
from apps.scheduling.infrastructure.repositories import (
    DjangoTimeOffRepository,
    DjangoWorkingHoursRepository,
)
from django.db import connection
from django.test.utils import CaptureQueriesContext


@dataclass
class FixedClock:
    value: datetime

    def now(self) -> datetime:
        return self.value


def _service(business: Business, service: Service, staff: Staff) -> AvailabilityService:
    return AvailabilityService(
        business_repository=DjangoBusinessRepository(),
        service_repository=DjangoServiceRepository(),
        staff_repository=DjangoStaffRepository(),
        working_hours_repository=DjangoWorkingHoursRepository(),
        time_off_repository=DjangoTimeOffRepository(),
        appointment_repository=DjangoAppointmentRepository(),
        clock=FixedClock(datetime(2026, 10, 24, 8, tzinfo=UTC)),
    )


def _add_schedule(staff: Staff, weekday: int = 0) -> None:
    WorkingHours.objects.create(
        staff=staff,
        weekday=weekday,
        start_time=time(9),
        end_time=time(17),
    )


def _add_assignment(staff: Staff, service: Service) -> None:
    StaffService.objects.create(staff=staff, service=service)


def test_returns_available_slots_for_any_staff(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _add_schedule(staff)
    _add_assignment(staff, service)

    availability = _service(business, service, staff).find(
        service_id=service.id,
        on_date=date(2026, 11, 2),
    )

    assert availability.timezone == "Asia/Riyadh"
    assert len(availability.slots) == 29
    assert availability.slots[0].starts_at.strftime("%H:%M") == "09:15"
    assert availability.slots[0].ends_at.strftime("%H:%M") == "09:45"
    assert availability.slots[0].recommended_staff_id == staff.id
    assert availability.slots[0].options[0].booked_count == 0
    assert availability.next_available_date is None


def test_time_off_removes_slots(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _add_schedule(staff)
    _add_assignment(staff, service)
    TimeOff.objects.create(
        staff=staff,
        starts_at=datetime(2026, 11, 2, 7, tzinfo=UTC),
        ends_at=datetime(2026, 11, 2, 7, 30, tzinfo=UTC),
    )

    availability = _service(business, service, staff).find(
        service_id=service.id,
        on_date=date(2026, 11, 2),
    )

    starts = {slot.starts_at.strftime("%H:%M") for slot in availability.slots}
    assert "09:15" in starts
    assert "09:45" not in starts
    assert "10:00" not in starts
    assert "10:15" not in starts
    assert "10:45" in starts


def test_recommends_least_booked_staff_deterministically(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    second_staff = Staff.objects.create(
        business=business,
        name_en="Ahmed",
        name_ar="أحمد",
    )
    for member in (staff, second_staff):
        _add_schedule(member)
        _add_assignment(member, service)
    customer = business.customers.create(name="Layla", email="layla@example.com")
    AppointmentModel.objects.create(
        business=business,
        service=service,
        staff=staff,
        customer=customer,
        starts_at=datetime(2026, 11, 2, 6, 15, tzinfo=UTC),
        ends_at=datetime(2026, 11, 2, 6, 45, tzinfo=UTC),
        status=AppointmentStatus.CONFIRMED.value,
    )

    availability = _service(business, service, staff).find(
        service_id=service.id,
        on_date=date(2026, 11, 2),
    )

    first = availability.slots[0]
    assert [option.staff.id for option in first.options] == [second_staff.id]
    later = next(slot for slot in availability.slots if slot.starts_at.strftime("%H:%M") == "10:00")
    assert {option.staff.id for option in later.options} == {staff.id, second_staff.id}
    assert later.recommended_staff_id == second_staff.id
    assert later.options[0].staff.id == second_staff.id


def test_specific_staff_returns_only_that_staff(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    second_staff = Staff.objects.create(
        business=business,
        name_en="Ahmed",
        name_ar="أحمد",
    )
    for member in (staff, second_staff):
        _add_schedule(member)
        _add_assignment(member, service)

    availability = _service(business, service, staff).find(
        service_id=service.id,
        on_date=date(2026, 11, 2),
        staff_id=staff.id,
    )

    assert all(slot.options[0].staff.id == staff.id for slot in availability.slots)
    assert all(len(slot.options) == 1 for slot in availability.slots)


def test_next_available_date_skips_closed_days(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _add_schedule(staff, weekday=0)
    _add_assignment(staff, service)

    availability = _service(business, service, staff).find(
        service_id=service.id,
        on_date=date(2026, 11, 1),
    )

    assert availability.slots == ()
    assert availability.next_available_date == date(2026, 11, 2)


def test_date_outside_horizon_raises(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _add_schedule(staff)
    _add_assignment(staff, service)

    with pytest.raises(DateOutsideHorizonError):
        _service(business, service, staff).find(
            service_id=service.id,
            on_date=date(2026, 12, 25),
        )


def test_ineligible_staff_is_rejected(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    other_staff = Staff.objects.create(
        business=business,
        name_en="Unassigned",
        name_ar="غير معين",
    )
    _add_schedule(staff)
    _add_assignment(staff, service)

    with pytest.raises(StaffNotAvailableError):
        _service(business, service, staff).find(
            service_id=service.id,
            on_date=date(2026, 11, 2),
            staff_id=other_staff.id,
        )


def test_inactive_service_is_rejected(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    service.is_active = False
    service.save(update_fields=["is_active"])

    with pytest.raises(ServiceNotAvailableError):
        _service(business, service, staff).find(
            service_id=service.id,
            on_date=date(2026, 11, 2),
        )


def test_availability_uses_a_fixed_number_of_queries(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    second_staff = Staff.objects.create(
        business=business,
        name_en="Ahmed",
        name_ar="أحمد",
    )
    for member in (staff, second_staff):
        _add_schedule(member)
        _add_assignment(member, service)

    with CaptureQueriesContext(connection) as queries:
        availability = _service(business, service, staff).find(
            service_id=service.id,
            on_date=date(2026, 11, 2),
        )

    assert len(availability.slots) == 29
    assert len(queries) == 9


def test_availability_result_is_empty_when_no_staff(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    availability = _service(business, service, staff).find(
        service_id=service.id,
        on_date=date(2026, 11, 2),
    )

    assert availability.slots == ()
    assert availability.next_available_date is None


def test_appointment_from_other_staff_does_not_block_slot(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    second_staff = Staff.objects.create(
        business=business,
        name_en="Ahmed",
        name_ar="أحمد",
    )
    for member in (staff, second_staff):
        _add_schedule(member)
        _add_assignment(member, service)
    customer = business.customers.create(name="Layla", email="layla@example.com")
    AppointmentModel.objects.create(
        business=business,
        service=service,
        staff=second_staff,
        customer=customer,
        starts_at=datetime(2026, 11, 2, 6, 15, tzinfo=UTC),
        ends_at=datetime(2026, 11, 2, 6, 45, tzinfo=UTC),
        status=AppointmentStatus.CONFIRMED.value,
    )

    availability = _service(business, service, staff).find(
        service_id=service.id,
        on_date=date(2026, 11, 2),
    )

    assert availability.slots[0].options[0].staff.id == staff.id


def test_past_date_has_no_slots_but_offers_next_available_date(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _add_schedule(staff)
    _add_assignment(staff, service)

    availability = _service(business, service, staff).find(
        service_id=service.id,
        on_date=date(2026, 10, 19),
    )

    assert availability.slots == ()
    assert availability.next_available_date == date(2026, 10, 26)


def test_dst_fall_back_keeps_slots_distinct_when_grouping(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    business.timezone = "Europe/London"
    business.save(update_fields=["timezone"])
    service.duration_minutes = 15
    service.buffer_before_minutes = 0
    service.buffer_after_minutes = 0
    service.save(
        update_fields=[
            "duration_minutes",
            "buffer_before_minutes",
            "buffer_after_minutes",
        ]
    )
    _add_assignment(staff, service)
    WorkingHours.objects.create(
        staff=staff,
        weekday=6,
        start_time=time(0),
        end_time=time(4),
    )

    availability = _service(business, service, staff).find(
        service_id=service.id,
        on_date=date(2026, 10, 25),
    )

    assert len(availability.slots) == 20
    assert len({slot.starts_at.astimezone(UTC) for slot in availability.slots}) == 20
    assert sum(slot.starts_at.strftime("%H:%M") == "01:00" for slot in availability.slots) == 2


def test_business_not_configured_raises(
    business: Business,
    staff: Staff,
    service: Service,
) -> None:
    Business.objects.all().delete()

    with pytest.raises(BusinessNotConfiguredError):
        _service(business, service, staff).find(
            service_id=service.id,
            on_date=date(2026, 11, 2),
        )


def test_next_available_date_is_none_without_upcoming_shifts(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    _add_assignment(staff, service)

    availability = _service(business, service, staff).find(
        service_id=service.id,
        on_date=date(2026, 10, 26),
    )

    assert availability.slots == ()
    assert availability.next_available_date is None
