from dataclasses import replace
from uuid import UUID

from apps.accounts.application.scope import ActorScope
from apps.bookings.application.errors import (
    AppointmentAccessDeniedError,
    AppointmentNotFoundError,
)
from apps.bookings.application.management import MAX_REASON_LENGTH, ManagedBooking
from apps.bookings.domain.entities import Appointment
from apps.bookings.domain.repository import (
    AppointmentRepository,
    CustomerRepository,
    ReminderRepository,
)
from apps.bookings.domain.status import AppointmentStatus, CancelledBy
from apps.bookings.domain.transitions import ensure_transition
from apps.businesses.domain.repository import BusinessRepository
from apps.catalog.domain.repository import ServiceRepository, StaffRepository
from apps.core.domain.clock import Clock
from apps.core.domain.unit_of_work import UnitOfWork

TERMINAL_STATUSES = frozenset(
    {
        AppointmentStatus.CANCELLED,
        AppointmentStatus.COMPLETED,
        AppointmentStatus.NO_SHOW,
    }
)


class StaffAppointmentService:
    def __init__(
        self,
        *,
        business_repository: BusinessRepository,
        service_repository: ServiceRepository,
        staff_repository: StaffRepository,
        customer_repository: CustomerRepository,
        appointment_repository: AppointmentRepository,
        reminder_repository: ReminderRepository,
        unit_of_work: UnitOfWork,
        clock: Clock,
    ) -> None:
        self._businesses = business_repository
        self._services = service_repository
        self._staff = staff_repository
        self._customers = customer_repository
        self._appointments = appointment_repository
        self._reminders = reminder_repository
        self._uow = unit_of_work
        self._clock = clock

    def update_status(
        self,
        appointment_id: UUID,
        *,
        actor: ActorScope,
        target: AppointmentStatus,
        reason: str = "",
    ) -> ManagedBooking:
        now = self._clock.now()
        with self._uow:
            appointment = self._appointments.get_for_update(appointment_id)
            if appointment is None or appointment.business_id != actor.business_id:
                raise AppointmentNotFoundError("The appointment was not found.")
            if not actor.is_owner and appointment.staff_id != actor.staff.id:
                raise AppointmentAccessDeniedError(
                    "This appointment belongs to another staff member."
                )

            ensure_transition(appointment.status, target)
            if target is AppointmentStatus.CANCELLED:
                updated = replace(
                    appointment,
                    status=target,
                    cancelled_at=now,
                    cancelled_by=CancelledBy.STAFF.value,
                    cancellation_reason=reason.strip()[:MAX_REASON_LENGTH],
                    management_token_hash=None,
                    management_token_expires_at=None,
                )
            elif target in TERMINAL_STATUSES:
                updated = replace(
                    appointment,
                    status=target,
                    management_token_hash=None,
                    management_token_expires_at=None,
                )
            else:
                updated = replace(appointment, status=target)

            updated = self._appointments.update(updated)
            if target in TERMINAL_STATUSES:
                self._reminders.cancel_pending_for_appointment(updated.id)
            return self._details(updated)

    def _details(self, appointment: Appointment) -> ManagedBooking:
        customer = self._customers.get(appointment.customer_id)
        service = self._services.get(appointment.service_id)
        staff = self._staff.get(appointment.staff_id)
        business = self._businesses.get(appointment.business_id)
        if customer is None or service is None or staff is None or business is None:
            raise AppointmentNotFoundError("The appointment was not found.")
        return ManagedBooking(
            appointment=appointment,
            customer=customer,
            service=service,
            staff=staff,
            business=business,
        )
