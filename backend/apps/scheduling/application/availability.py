from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from apps.bookings.domain.repository import AppointmentRepository
from apps.bookings.domain.status import ACTIVE_APPOINTMENT_STATUSES
from apps.businesses.domain.repository import BusinessRepository
from apps.catalog.domain.entities import Service, Staff
from apps.catalog.domain.repository import ServiceRepository, StaffRepository
from apps.core.domain.clock import Clock
from apps.scheduling.domain.errors import (
    BusinessNotConfiguredError,
    DateOutsideHorizonError,
    ServiceNotAvailableError,
    StaffNotAvailableError,
)
from apps.scheduling.domain.repository import TimeOffRepository, WorkingHoursRepository
from apps.scheduling.domain.slot_generator import (
    BusyInterval,
    ServiceTiming,
    SlotGenerator,
    SlotPolicy,
    TimeSlot,
    WorkingShift,
    local_day_bounds,
)

NEXT_AVAILABLE_LOOKAHEAD_DAYS = 14


@dataclass(frozen=True, slots=True)
class StaffSlotOption:
    staff: Staff
    starts_at: datetime
    ends_at: datetime
    booked_count: int


@dataclass(frozen=True, slots=True)
class AvailabilitySlot:
    starts_at: datetime
    ends_at: datetime
    options: tuple[StaffSlotOption, ...]
    recommended_staff_id: UUID


@dataclass(frozen=True, slots=True)
class Availability:
    on_date: date
    timezone: str
    service: Service
    slots: tuple[AvailabilitySlot, ...]
    next_available_date: date | None


@dataclass(frozen=True, slots=True)
class _StaffSlots:
    slots: list[TimeSlot]
    booked_count: int


class AvailabilityService:
    def __init__(
        self,
        *,
        business_repository: BusinessRepository,
        service_repository: ServiceRepository,
        staff_repository: StaffRepository,
        working_hours_repository: WorkingHoursRepository,
        time_off_repository: TimeOffRepository,
        appointment_repository: AppointmentRepository,
        clock: Clock,
        slot_generator: SlotGenerator | None = None,
    ) -> None:
        self._businesses = business_repository
        self._services = service_repository
        self._staff = staff_repository
        self._working_hours = working_hours_repository
        self._time_off = time_off_repository
        self._appointments = appointment_repository
        self._clock = clock
        self._generator = slot_generator or SlotGenerator()

    def find(
        self,
        *,
        service_id: UUID,
        on_date: date,
        staff_id: UUID | None = None,
    ) -> Availability:
        business = self._businesses.get_active()
        if business is None:
            raise BusinessNotConfiguredError("No active business is configured.")

        service = self._services.get(service_id)
        if service is None or not service.is_active or service.business_id != business.id:
            raise ServiceNotAvailableError("The requested service is not available.")

        eligible_staff = [
            staff
            for staff in self._staff.list_for_service(service_id)
            if staff.is_active and staff.business_id == business.id
        ]
        if staff_id is not None:
            selected = next((staff for staff in eligible_staff if staff.id == staff_id), None)
            if selected is None:
                raise StaffNotAvailableError("The requested staff member is not available.")
            eligible_staff = [selected]

        now = self._clock.now()
        zone = ZoneInfo(business.timezone)
        today = now.astimezone(zone).date()
        last_bookable_day = today + timedelta(days=business.max_advance_days)
        if on_date > last_bookable_day:
            raise DateOutsideHorizonError("The requested date is outside the booking horizon.")

        slots = self._slots_for_date(
            on_date=on_date,
            service=service,
            staff_members=eligible_staff,
            timezone=business.timezone,
            policy=SlotPolicy(
                slot_interval_minutes=business.slot_interval_minutes,
                min_lead_time_minutes=business.min_lead_time_minutes,
                max_advance_days=business.max_advance_days,
            ),
            now=now,
        )

        next_available_date = None
        if not slots and eligible_staff:
            next_available_date = self._next_available_date(
                after=on_date,
                today=today,
                last_bookable_day=last_bookable_day,
                service=service,
                staff_members=eligible_staff,
                timezone=business.timezone,
                policy=SlotPolicy(
                    slot_interval_minutes=business.slot_interval_minutes,
                    min_lead_time_minutes=business.min_lead_time_minutes,
                    max_advance_days=business.max_advance_days,
                ),
                now=now,
            )

        return Availability(
            on_date=on_date,
            timezone=business.timezone,
            service=service,
            slots=slots,
            next_available_date=next_available_date,
        )

    def _slots_for_date(
        self,
        *,
        on_date: date,
        service: Service,
        staff_members: list[Staff],
        timezone: str,
        policy: SlotPolicy,
        now: datetime,
    ) -> tuple[AvailabilitySlot, ...]:
        grouped: dict[datetime, list[StaffSlotOption]] = {}
        for staff in staff_members:
            result = self._staff_slots(
                on_date=on_date,
                service=service,
                staff=staff,
                timezone=timezone,
                policy=policy,
                now=now,
            )
            for slot in result.slots:
                grouped.setdefault(slot.starts_at.astimezone(UTC), []).append(
                    StaffSlotOption(
                        staff=staff,
                        starts_at=slot.starts_at,
                        ends_at=slot.ends_at,
                        booked_count=result.booked_count,
                    )
                )

        slots: list[AvailabilitySlot] = []
        for _slot_instant in sorted(grouped):
            options = sorted(
                grouped[_slot_instant],
                key=lambda option: (
                    option.staff.name.for_locale("en").casefold(),
                    str(option.staff.id),
                ),
            )
            recommended = min(
                options,
                key=lambda option: (
                    option.booked_count,
                    option.staff.name.for_locale("en").casefold(),
                    str(option.staff.id),
                ),
            )
            slots.append(
                AvailabilitySlot(
                    starts_at=options[0].starts_at,
                    ends_at=recommended.ends_at,
                    options=tuple(options),
                    recommended_staff_id=recommended.staff.id,
                )
            )
        return tuple(slots)

    def _staff_slots(
        self,
        *,
        on_date: date,
        service: Service,
        staff: Staff,
        timezone: str,
        policy: SlotPolicy,
        now: datetime,
    ) -> _StaffSlots:
        day_start, day_end = local_day_bounds(on_date, timezone)
        shifts = [
            WorkingShift(start_time=shift.start_time, end_time=shift.end_time)
            for shift in self._working_hours.list_for_staff_day(staff.id, on_date.weekday())
        ]
        time_off = self._time_off.list_overlapping(staff.id, day_start, day_end)
        appointments = [
            appointment
            for appointment in self._appointments.list_for_staff(
                staff.id,
                day_start,
                day_end,
            )
            if appointment.status.value in ACTIVE_APPOINTMENT_STATUSES
        ]
        busy = [
            BusyInterval(starts_at=interval.starts_at, ends_at=interval.ends_at)
            for interval in time_off
        ] + [
            BusyInterval(starts_at=appointment.starts_at, ends_at=appointment.ends_at)
            for appointment in appointments
        ]
        slots = self._generator.generate(
            on_date=on_date,
            timezone=timezone,
            shifts=shifts,
            busy=busy,
            service=ServiceTiming(
                duration_minutes=service.duration_minutes,
                buffer_before_minutes=service.buffer_before_minutes,
                buffer_after_minutes=service.buffer_after_minutes,
            ),
            policy=policy,
            now=now,
            staff_id=staff.id,
        )
        return _StaffSlots(slots=slots, booked_count=len(appointments))

    def _next_available_date(
        self,
        *,
        after: date,
        today: date,
        last_bookable_day: date,
        service: Service,
        staff_members: list[Staff],
        timezone: str,
        policy: SlotPolicy,
        now: datetime,
    ) -> date | None:
        cursor = max(after + timedelta(days=1), today)
        search_limit = min(
            last_bookable_day,
            max(after, today) + timedelta(days=NEXT_AVAILABLE_LOOKAHEAD_DAYS),
        )
        while cursor <= search_limit:
            if self._slots_for_date(
                on_date=cursor,
                service=service,
                staff_members=staff_members,
                timezone=timezone,
                policy=policy,
                now=now,
            ):
                return cursor
            cursor += timedelta(days=1)
        return None
