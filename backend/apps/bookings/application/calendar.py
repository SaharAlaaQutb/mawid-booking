from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from apps.accounts.application.scope import ActorScope
from apps.bookings.application.errors import (
    AppointmentAccessDeniedError,
    CalendarRangeError,
    StaffNotAvailableError,
)
from apps.bookings.domain.entities import Appointment, Customer
from apps.bookings.domain.repository import AppointmentRepository, CustomerRepository
from apps.businesses.domain.repository import BusinessRepository
from apps.catalog.domain.entities import Service, Staff
from apps.catalog.domain.repository import ServiceRepository, StaffRepository

MAX_CALENDAR_DAYS = 62


@dataclass(frozen=True, slots=True)
class CalendarAppointment:
    appointment: Appointment
    service: Service
    customer: Customer


@dataclass(frozen=True, slots=True)
class StaffCalendar:
    staff: Staff
    appointments: tuple[CalendarAppointment, ...]


@dataclass(frozen=True, slots=True)
class CalendarResult:
    starts_on: date
    ends_on: date
    timezone: str
    staff: tuple[StaffCalendar, ...]


class CalendarService:
    def __init__(
        self,
        *,
        business_repository: BusinessRepository,
        service_repository: ServiceRepository,
        staff_repository: StaffRepository,
        customer_repository: CustomerRepository,
        appointment_repository: AppointmentRepository,
    ) -> None:
        self._businesses = business_repository
        self._services = service_repository
        self._staff = staff_repository
        self._customers = customer_repository
        self._appointments = appointment_repository

    def for_actor(
        self,
        *,
        actor: ActorScope,
        starts_on: date,
        ends_on: date,
        staff_id: UUID | None = None,
    ) -> CalendarResult:
        self._validate_range(starts_on, ends_on)
        business = self._businesses.get(actor.business_id)
        if business is None:
            raise CalendarRangeError("The business was not found.")
        if not actor.is_owner and staff_id is not None and staff_id != actor.staff.id:
            raise AppointmentAccessDeniedError("Calendar access is limited to your own schedule.")

        active_staff = self._staff.list_active(actor.business_id)
        selected_staff = self._select_staff(
            active_staff,
            actor=actor,
            staff_id=staff_id,
        )
        local_timezone = ZoneInfo(business.timezone)
        range_start = datetime.combine(starts_on, time.min, tzinfo=local_timezone)
        range_end = datetime.combine(ends_on + timedelta(days=1), time.min, tzinfo=local_timezone)
        appointments = self._appointments.list_for_business(
            actor.business_id,
            range_start,
            range_end,
            staff_id=staff_id if actor.is_owner else actor.staff.id,
        )
        by_staff: dict[UUID, list[CalendarAppointment]] = {
            member.id: [] for member in selected_staff
        }
        services: dict[UUID, Service] = {}
        customers: dict[UUID, Customer] = {}
        for appointment in appointments:
            appointment_details = self._enrich(
                appointment,
                services=services,
                customers=customers,
            )
            if appointment_details is None:
                continue
            by_staff.setdefault(appointment.staff_id, []).append(appointment_details)

        return CalendarResult(
            starts_on=starts_on,
            ends_on=ends_on,
            timezone=business.timezone,
            staff=tuple(
                StaffCalendar(staff=member, appointments=tuple(by_staff[member.id]))
                for member in selected_staff
            ),
        )

    def _validate_range(self, starts_on: date, ends_on: date) -> None:
        if ends_on < starts_on:
            raise CalendarRangeError("The end date must be on or after the start date.")
        if (ends_on - starts_on).days + 1 > MAX_CALENDAR_DAYS:
            raise CalendarRangeError(f"Calendar ranges are limited to {MAX_CALENDAR_DAYS} days.")

    def _select_staff(
        self,
        active_staff: list[Staff],
        *,
        actor: ActorScope,
        staff_id: UUID | None,
    ) -> list[Staff]:
        if staff_id is not None:
            selected = next((member for member in active_staff if member.id == staff_id), None)
            if selected is None:
                raise StaffNotAvailableError("The requested staff member is not available.")
            return [selected]
        if actor.is_owner:
            return active_staff
        return [member for member in active_staff if member.id == actor.staff.id]

    def _enrich(
        self,
        appointment: Appointment,
        *,
        services: dict[UUID, Service],
        customers: dict[UUID, Customer],
    ) -> CalendarAppointment | None:
        service = services.get(appointment.service_id)
        if service is None:
            service = self._services.get(appointment.service_id)
            if service is None:
                return None
            services[service.id] = service
        customer = customers.get(appointment.customer_id)
        if customer is None:
            customer = self._customers.get(appointment.customer_id)
            if customer is None:
                return None
            customers[customer.id] = customer
        return CalendarAppointment(appointment=appointment, service=service, customer=customer)
