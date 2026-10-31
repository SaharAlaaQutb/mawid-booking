import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from apps.bookings.application.availability import AvailabilityGateway
from apps.bookings.application.errors import (
    BusinessNotConfiguredError,
    IdempotencyConflictError,
    ServiceNotAvailableError,
    SlotTakenError,
    StaffNotAvailableError,
)
from apps.bookings.domain.entities import Appointment, Customer, Reminder
from apps.bookings.domain.errors import AppointmentConflictError
from apps.bookings.domain.repository import (
    AppointmentRepository,
    CustomerRepository,
    ReminderRepository,
)
from apps.bookings.domain.status import AppointmentStatus, ReminderKind, ReminderStatus
from apps.bookings.domain.tokens import IssuedManagementToken, issue_management_token
from apps.businesses.domain.entities import Business
from apps.businesses.domain.repository import BusinessRepository
from apps.catalog.domain.entities import Service, Staff
from apps.catalog.domain.repository import ServiceRepository, StaffRepository
from apps.core.domain.locale import SUPPORTED_LOCALES
from apps.core.domain.unit_of_work import UnitOfWork
from apps.notifications.application.notification import NotificationService
from apps.notifications.domain.messages import NotificationKind
from apps.notifications.domain.senders import NotificationError

REMINDER_LEAD = timedelta(hours=24)
MAX_IDEMPOTENCY_KEY_LENGTH = 64

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BookingResult:
    appointment: Appointment
    customer: Customer
    service: Service
    staff: Staff
    business: Business
    management_token: str


class BookingService:
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
        self._notifier = notifier

    def create(
        self,
        *,
        service_id: UUID,
        staff_id: UUID | None,
        starts_at: datetime,
        customer_name: str,
        customer_email: str,
        customer_phone: str = "",
        customer_language: str = "en",
        notes: str = "",
        idempotency_key: str | None = None,
    ) -> BookingResult:
        if starts_at.tzinfo is None:
            raise ValueError("starts_at must be timezone-aware")
        if not customer_name.strip():
            raise ValueError("customer_name is required")

        business = self._businesses.get_active()
        if business is None:
            raise BusinessNotConfiguredError("No active business is configured.")
        service = self._services.get(service_id)
        if service is None or not service.is_active or service.business_id != business.id:
            raise ServiceNotAvailableError("The requested service is not available.")

        key = (idempotency_key or "").strip() or None
        if key and len(key) > MAX_IDEMPOTENCY_KEY_LENGTH:
            raise ValueError("idempotency_key is too long")
        if key:
            existing = self._appointments.get_by_idempotency_key(business.id, key)
            if existing is not None:
                return self._replay(
                    existing, service=service, staff_id=staff_id, starts_at=starts_at
                )

        local_date = starts_at.astimezone(ZoneInfo(business.timezone)).date()
        if staff_id is None:
            staff_id = self._availability.choose_staff(
                service_id=service.id,
                on_date=local_date,
                starts_at=starts_at,
            )

        try:
            with self._uow:
                staff = self._staff.get_for_update(staff_id)
                if staff is None or not staff.is_active or staff.business_id != business.id:
                    raise StaffNotAvailableError("The requested staff member is not available.")
                self._availability.find_slot(
                    service_id=service.id,
                    staff_id=staff.id,
                    on_date=local_date,
                    starts_at=starts_at,
                )
                customer = self._upsert_customer(
                    business_id=business.id,
                    name=customer_name,
                    email=customer_email,
                    phone=customer_phone,
                    language=customer_language,
                    fallback_language=business.default_locale,
                )
                token = issue_management_token(starts_at)
                appointment = self._new_appointment(
                    business_id=business.id,
                    service=service,
                    staff_id=staff.id,
                    customer=customer,
                    starts_at=starts_at,
                    notes=notes,
                    idempotency_key=key,
                    token=token,
                )
                saved = self._appointments.add(appointment)
                self._reminders.add(
                    Reminder(
                        id=uuid4(),
                        appointment_id=saved.id,
                        kind=ReminderKind.REMINDER,
                        send_at=starts_at - REMINDER_LEAD,
                        sent_at=None,
                        status=ReminderStatus.PENDING,
                        attempts=0,
                        language=customer.language,
                    )
                )
        except AppointmentConflictError as exc:
            if key:
                existing = self._appointments.get_by_idempotency_key(business.id, key)
                if existing is not None:
                    return self._replay(
                        existing,
                        service=service,
                        staff_id=staff_id,
                        starts_at=starts_at,
                    )
            raise SlotTakenError("This slot is no longer available.") from exc

        self._send_confirmation(
            appointment=saved,
            customer=customer,
            service=service,
            staff=staff,
            business=business,
            management_token=token.value,
        )
        return BookingResult(
            appointment=saved,
            customer=customer,
            service=service,
            staff=staff,
            business=business,
            management_token=token.value,
        )

    def _send_confirmation(
        self,
        *,
        appointment: Appointment,
        customer: Customer,
        service: Service,
        staff: Staff,
        business: Business,
        management_token: str,
    ) -> None:
        try:
            self._notifier.send(
                NotificationKind.CONFIRMATION,
                appointment=appointment,
                customer=customer,
                service=service,
                staff=staff,
                business=business,
                management_token=management_token,
            )
        except NotificationError:
            logger.exception(
                "Failed to send booking confirmation",
                extra={"appointment_id": str(appointment.id)},
            )

    def _replay(
        self,
        appointment: Appointment,
        *,
        service: Service,
        staff_id: UUID | None,
        starts_at: datetime,
    ) -> BookingResult:
        if (
            appointment.service_id != service.id
            or appointment.starts_at.astimezone(UTC) != starts_at.astimezone(UTC)
            or (staff_id is not None and appointment.staff_id != staff_id)
        ):
            raise IdempotencyConflictError(
                "The idempotency key was already used for a different booking."
            )
        if appointment.status not in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED):
            raise IdempotencyConflictError("The original booking is no longer active.")
        customer = self._customers.get(appointment.customer_id)
        staff = self._staff.get(appointment.staff_id)
        business = self._businesses.get(appointment.business_id)
        if customer is None or staff is None or business is None:
            raise IdempotencyConflictError("The original booking is no longer available.")
        token = issue_management_token(appointment.starts_at)
        updated = self._appointments.update(
            replace(
                appointment,
                management_token_hash=token.token_hash,
                management_token_expires_at=token.expires_at,
            )
        )
        return BookingResult(
            appointment=updated,
            customer=customer,
            service=service,
            staff=staff,
            business=business,
            management_token=token.value,
        )

    def _upsert_customer(
        self,
        *,
        business_id: UUID,
        name: str,
        email: str,
        phone: str,
        language: str,
        fallback_language: str,
    ) -> Customer:
        normalized_email = email.strip().lower()
        requested_language = language if language in SUPPORTED_LOCALES else fallback_language
        existing = self._customers.get_by_email(business_id, normalized_email)
        if existing is not None:
            return self._customers.update(
                replace(
                    existing,
                    name=name.strip(),
                    phone=phone.strip() or existing.phone,
                    language=requested_language,
                )
            )
        return self._customers.add(
            Customer(
                id=uuid4(),
                business_id=business_id,
                name=name.strip(),
                email=normalized_email,
                phone=phone.strip(),
                language=requested_language,
            )
        )

    def _new_appointment(
        self,
        *,
        business_id: UUID,
        service: Service,
        staff_id: UUID,
        customer: Customer,
        starts_at: datetime,
        notes: str,
        idempotency_key: str | None,
        token: IssuedManagementToken,
    ) -> Appointment:
        return Appointment(
            id=uuid4(),
            business_id=business_id,
            service_id=service.id,
            staff_id=staff_id,
            customer_id=customer.id,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=service.duration_minutes),
            status=AppointmentStatus.PENDING,
            price_minor=service.price_minor,
            currency=service.currency,
            customer_language=customer.language,
            notes=notes.strip(),
            management_token_hash=token.token_hash,
            management_token_expires_at=token.expires_at,
            idempotency_key=idempotency_key,
            rescheduled_from_id=None,
        )
