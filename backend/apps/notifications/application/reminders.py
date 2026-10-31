from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from apps.bookings.domain.entities import Appointment, Customer, Reminder
from apps.bookings.domain.repository import (
    AppointmentRepository,
    CustomerRepository,
    ReminderRepository,
)
from apps.bookings.domain.status import AppointmentStatus, ReminderStatus
from apps.bookings.domain.tokens import issue_management_token
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
MAX_ATTEMPTS = 3
RETRY_DELAY = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class ReminderDetails:
    customer: Customer
    service: Service
    staff: Staff
    business: Business


class ReminderService:
    def __init__(
        self,
        *,
        reminder_repository: ReminderRepository,
        appointment_repository: AppointmentRepository,
        customer_repository: CustomerRepository,
        service_repository: ServiceRepository,
        staff_repository: StaffRepository,
        business_repository: BusinessRepository,
        notifier: NotificationService,
        clock: Clock,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._reminders = reminder_repository
        self._appointments = appointment_repository
        self._customers = customer_repository
        self._services = service_repository
        self._staff = staff_repository
        self._businesses = business_repository
        self._notifier = notifier
        self._clock = clock
        self._uow = unit_of_work

    def process_due(self, limit: int = 100) -> int:
        now = self._clock.now()
        processed = 0
        with self._uow:
            for reminder in self._reminders.claim_due(now, limit):
                self._process(reminder, now)
                processed += 1
        return processed

    def _process(self, reminder: Reminder, now: datetime) -> None:
        appointment = self._appointments.get_for_update(reminder.appointment_id)
        if appointment is None or appointment.status not in ACTIVE_STATUSES:
            self._reminders.update(replace(reminder, status=ReminderStatus.CANCELLED))
            return

        details = self._details(appointment)
        if details is None:
            self._reminders.update(replace(reminder, status=ReminderStatus.FAILED))
            return

        token = issue_management_token(appointment.starts_at)
        self._appointments.update(
            replace(
                appointment,
                management_token_hash=token.token_hash,
                management_token_expires_at=token.expires_at,
            )
        )
        try:
            self._notifier.send(
                NotificationKind.REMINDER,
                appointment=appointment,
                customer=details.customer,
                service=details.service,
                staff=details.staff,
                business=details.business,
                management_token=token.value,
                language=reminder.language,
            )
        except NotificationError:
            self._reminders.update(self._failed_reminder(reminder, now))
            return
        self._reminders.update(
            replace(
                reminder,
                status=ReminderStatus.SENT,
                sent_at=now,
                attempts=reminder.attempts + 1,
            )
        )

    def _failed_reminder(self, reminder: Reminder, now: datetime) -> Reminder:
        attempts = reminder.attempts + 1
        if attempts >= MAX_ATTEMPTS:
            return replace(reminder, status=ReminderStatus.FAILED, attempts=attempts)
        return replace(
            reminder,
            status=ReminderStatus.PENDING,
            attempts=attempts,
            send_at=now + RETRY_DELAY * attempts,
        )

    def _details(self, appointment: Appointment) -> ReminderDetails | None:
        customer = self._customers.get(appointment.customer_id)
        service = self._services.get(appointment.service_id)
        staff = self._staff.get(appointment.staff_id)
        business = self._businesses.get(appointment.business_id)
        if customer is None or service is None or staff is None or business is None:
            return None
        return ReminderDetails(
            customer=customer,
            service=service,
            staff=staff,
            business=business,
        )
