import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from apps.bookings.application.availability import AvailabilityGateway
from apps.bookings.application.booking import REMINDER_LEAD, BookingResult
from apps.bookings.application.errors import (
    CancellationNotAllowedError,
    ManagementTokenInvalidError,
    ServiceNotAvailableError,
    SlotTakenError,
    StaffNotAvailableError,
)
from apps.bookings.domain.entities import Appointment, Customer, Reminder
from apps.bookings.domain.errors import AppointmentConflictError
from apps.bookings.domain.policies import WindowedCancellationPolicy
from apps.bookings.domain.repository import (
    AppointmentRepository,
    CustomerRepository,
    ReminderRepository,
)
from apps.bookings.domain.status import (
    AppointmentStatus,
    CancelledBy,
    ReminderKind,
    ReminderStatus,
)
from apps.bookings.domain.tokens import hash_management_token, issue_management_token
from apps.bookings.domain.transitions import ensure_transition
from apps.businesses.domain.entities import Business
from apps.businesses.domain.repository import BusinessRepository
from apps.catalog.domain.entities import Service, Staff
from apps.catalog.domain.repository import ServiceRepository, StaffRepository
from apps.core.domain.clock import Clock
from apps.core.domain.unit_of_work import UnitOfWork
from apps.notifications.application.notification import NotificationService
from apps.notifications.domain.messages import NotificationKind
from apps.notifications.domain.senders import NotificationError

ACTIVE_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)
MAX_REASON_LENGTH = 255

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ManagedBooking:
    appointment: Appointment
    customer: Customer
    service: Service
    staff: Staff
    business: Business


class BookingManagementService:
    def __init__(
        self,
        *,
        business_repository: BusinessRepository,
        service_repository: ServiceRepository,
        staff_repository: StaffRepository,
        customer_repository: CustomerRepository,
        appointment_repository: AppointmentRepository,
        reminder_repository: ReminderRepository,
        availability: AvailabilityGateway,
        unit_of_work: UnitOfWork,
        clock: Clock,
        notifier: NotificationService,
    ) -> None:
        self._businesses = business_repository
        self._services = service_repository
        self._staff = staff_repository
        self._customers = customer_repository
        self._appointments = appointment_repository
        self._reminders = reminder_repository
        self._availability = availability
        self._uow = unit_of_work
        self._clock = clock
        self._notifier = notifier

    def get(self, token: str) -> ManagedBooking:
        appointment = self._find(token, self._clock.now())
        return self._details(appointment)

    def cancel(
        self,
        token: str,
        *,
        reason: str = "",
        actor: CancelledBy = CancelledBy.CUSTOMER,
        enforce_policy: bool = True,
    ) -> ManagedBooking:
        now = self._clock.now()
        with self._uow:
            appointment = self._find(token, now, for_update=True)
            details = self._details(appointment)
            self._ensure_can_cancel(details, now=now, enforce_policy=enforce_policy)
            ensure_transition(appointment.status, AppointmentStatus.CANCELLED)
            updated = replace(
                appointment,
                status=AppointmentStatus.CANCELLED,
                cancelled_at=now,
                cancelled_by=actor.value,
                cancellation_reason=reason.strip()[:MAX_REASON_LENGTH],
                management_token_hash=None,
                management_token_expires_at=None,
            )
            updated = self._appointments.update(updated)
            self._reminders.cancel_pending_for_appointment(updated.id)
        result = replace(details, appointment=updated)
        self._notify(NotificationKind.CANCELLATION, result)
        return result

    def reschedule(
        self,
        token: str,
        *,
        starts_at: datetime,
    ) -> BookingResult:
        if starts_at.tzinfo is None:
            raise ValueError("starts_at must be timezone-aware")
        now = self._clock.now()
        current = self._details(self._find(token, now))
        self._ensure_can_cancel(current, now=now, enforce_policy=True)
        local_date = starts_at.astimezone(ZoneInfo(current.business.timezone)).date()

        try:
            with self._uow:
                staff = self._staff.get_for_update(current.staff.id)
                if staff is None or not staff.is_active:
                    raise StaffNotAvailableError("The requested staff member is not available.")
                appointment = self._find(token, now, for_update=True)
                details = self._details(appointment)
                self._ensure_can_cancel(details, now=now, enforce_policy=True)
                if not details.service.is_active:
                    raise ServiceNotAvailableError("The requested service is not available.")
                self._availability.find_slot(
                    service_id=details.service.id,
                    staff_id=staff.id,
                    on_date=local_date,
                    starts_at=starts_at,
                )
                self._appointments.update(self._cancelled_for_reschedule(appointment, now))
                self._reminders.cancel_pending_for_appointment(appointment.id)
                new_token = issue_management_token(starts_at)
                saved = self._appointments.add(
                    self._rescheduled_appointment(
                        appointment,
                        details=details,
                        starts_at=starts_at,
                        token_hash=new_token.token_hash,
                        token_expires_at=new_token.expires_at,
                    )
                )
                self._reminders.add(
                    Reminder(
                        id=uuid4(),
                        appointment_id=saved.id,
                        kind=ReminderKind.REMINDER,
                        send_at=starts_at - REMINDER_LEAD,
                        sent_at=None,
                        status=ReminderStatus.PENDING,
                        attempts=0,
                        language=details.customer.language,
                    )
                )
        except AppointmentConflictError as exc:
            raise SlotTakenError("This slot is no longer available.") from exc

        result = BookingResult(
            appointment=saved,
            customer=details.customer,
            service=details.service,
            staff=details.staff,
            business=details.business,
            management_token=new_token.value,
        )
        self._notify(
            NotificationKind.RESCHEDULE,
            result,
            management_token=new_token.value,
        )
        return result

    def _notify(
        self,
        kind: NotificationKind,
        booking: ManagedBooking | BookingResult,
        *,
        management_token: str | None = None,
    ) -> None:
        try:
            self._notifier.send(
                kind,
                appointment=booking.appointment,
                customer=booking.customer,
                service=booking.service,
                staff=booking.staff,
                business=booking.business,
                management_token=management_token,
            )
        except NotificationError:
            logger.exception(
                "Failed to send %s notification",
                kind.value,
                extra={"appointment_id": str(booking.appointment.id)},
            )

    def _find(
        self,
        token: str,
        now: datetime,
        *,
        for_update: bool = False,
    ) -> Appointment:
        if not token.strip():
            raise ManagementTokenInvalidError("The management link is invalid or has expired.")
        token_hash = hash_management_token(token)
        if for_update:
            appointment = self._appointments.get_by_management_token_hash_for_update(token_hash)
        else:
            appointment = self._appointments.get_by_management_token_hash(token_hash)
        if (
            appointment is None
            or appointment.management_token_expires_at is None
            or appointment.management_token_expires_at <= now
            or appointment.status not in ACTIVE_STATUSES
        ):
            raise ManagementTokenInvalidError("The management link is invalid or has expired.")
        return appointment

    def _details(self, appointment: Appointment) -> ManagedBooking:
        customer = self._customers.get(appointment.customer_id)
        service = self._services.get(appointment.service_id)
        staff = self._staff.get(appointment.staff_id)
        business = self._businesses.get(appointment.business_id)
        if customer is None or service is None or staff is None or business is None:
            raise ManagementTokenInvalidError("The management link is invalid or has expired.")
        return ManagedBooking(
            appointment=appointment,
            customer=customer,
            service=service,
            staff=staff,
            business=business,
        )

    def _ensure_can_cancel(
        self,
        managed: ManagedBooking,
        *,
        now: datetime,
        enforce_policy: bool,
    ) -> None:
        if not enforce_policy:
            return
        policy = WindowedCancellationPolicy(managed.business.cancellation_window_hours)
        if not policy.can_cancel(starts_at=managed.appointment.starts_at, now=now):
            raise CancellationNotAllowedError("This appointment can no longer be changed online.")

    def _cancelled_for_reschedule(self, appointment: Appointment, now: datetime) -> Appointment:
        return replace(
            appointment,
            status=AppointmentStatus.CANCELLED,
            cancelled_at=now,
            cancelled_by=CancelledBy.CUSTOMER.value,
            cancellation_reason="Rescheduled",
            management_token_hash=None,
            management_token_expires_at=None,
        )

    def _rescheduled_appointment(
        self,
        appointment: Appointment,
        *,
        details: ManagedBooking,
        starts_at: datetime,
        token_hash: str,
        token_expires_at: datetime,
    ) -> Appointment:
        return Appointment(
            id=uuid4(),
            business_id=appointment.business_id,
            service_id=appointment.service_id,
            staff_id=appointment.staff_id,
            customer_id=appointment.customer_id,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=details.service.duration_minutes),
            status=AppointmentStatus.PENDING,
            price_minor=appointment.price_minor,
            currency=appointment.currency,
            customer_language=appointment.customer_language,
            notes=appointment.notes,
            management_token_hash=token_hash,
            management_token_expires_at=token_expires_at,
            idempotency_key=None,
            rescheduled_from_id=appointment.id,
        )
