from datetime import datetime
from uuid import UUID

from django.db import IntegrityError

from apps.bookings.domain.entities import Appointment, Customer, Reminder
from apps.bookings.domain.errors import AppointmentConflictError
from apps.bookings.domain.status import (
    ACTIVE_APPOINTMENT_STATUSES,
    AppointmentStatus,
    ReminderKind,
    ReminderStatus,
)
from apps.bookings.infrastructure.models import Appointment as AppointmentModel
from apps.bookings.infrastructure.models import Customer as CustomerModel
from apps.bookings.infrastructure.models import Reminder as ReminderModel


def _customer_to_entity(model: CustomerModel) -> Customer:
    return Customer(
        id=model.id,
        business_id=model.business_id,
        name=model.name,
        email=model.email,
        phone=model.phone,
        language=model.language,
    )


def _appointment_to_entity(model: AppointmentModel) -> Appointment:
    return Appointment(
        id=model.id,
        business_id=model.business_id,
        service_id=model.service_id,
        staff_id=model.staff_id,
        customer_id=model.customer_id,
        starts_at=model.starts_at,
        ends_at=model.ends_at,
        status=AppointmentStatus(model.status),
        price_minor=model.price_minor,
        currency=model.currency,
        customer_language=model.customer_language,
        notes=model.notes,
        management_token_hash=model.management_token_hash,
        management_token_expires_at=model.management_token_expires_at,
        idempotency_key=model.idempotency_key or None,
        rescheduled_from_id=model.rescheduled_from_id,
        cancelled_at=model.cancelled_at,
        cancelled_by=model.cancelled_by,
        cancellation_reason=model.cancellation_reason,
    )


def _reminder_to_entity(model: ReminderModel) -> Reminder:
    return Reminder(
        id=model.id,
        appointment_id=model.appointment_id,
        kind=ReminderKind(model.kind),
        send_at=model.send_at,
        sent_at=model.sent_at,
        status=ReminderStatus(model.status),
        attempts=model.attempts,
        language=model.language,
    )


class DjangoCustomerRepository:
    def get(self, customer_id: UUID) -> Customer | None:
        model = CustomerModel.objects.filter(pk=customer_id).first()
        return _customer_to_entity(model) if model else None

    def get_by_email(self, business_id: UUID, email: str) -> Customer | None:
        model = CustomerModel.objects.filter(
            business_id=business_id,
            email=email.strip().lower(),
        ).first()
        return _customer_to_entity(model) if model else None

    def add(self, customer: Customer) -> Customer:
        model = CustomerModel.objects.create(
            id=customer.id,
            business_id=customer.business_id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            language=customer.language,
        )
        return _customer_to_entity(model)

    def update(self, customer: Customer) -> Customer:
        model = CustomerModel.objects.get(pk=customer.id)
        model.business_id = customer.business_id
        model.name = customer.name
        model.email = customer.email
        model.phone = customer.phone
        model.language = customer.language
        model.save()
        return _customer_to_entity(model)


class DjangoAppointmentRepository:
    def get(self, appointment_id: UUID) -> Appointment | None:
        model = AppointmentModel.objects.filter(pk=appointment_id).first()
        return _appointment_to_entity(model) if model else None

    def get_by_idempotency_key(
        self,
        business_id: UUID,
        idempotency_key: str,
    ) -> Appointment | None:
        model = AppointmentModel.objects.filter(
            business_id=business_id,
            idempotency_key=idempotency_key,
        ).first()
        return _appointment_to_entity(model) if model else None

    def get_by_management_token_hash(self, token_hash: str) -> Appointment | None:
        model = AppointmentModel.objects.filter(management_token_hash=token_hash).first()
        return _appointment_to_entity(model) if model else None

    def get_for_update(self, appointment_id: UUID) -> Appointment | None:
        model = AppointmentModel.objects.select_for_update().filter(pk=appointment_id).first()
        return _appointment_to_entity(model) if model else None

    def get_by_management_token_hash_for_update(
        self,
        token_hash: str,
    ) -> Appointment | None:
        model = (
            AppointmentModel.objects.select_for_update()
            .filter(management_token_hash=token_hash)
            .first()
        )
        return _appointment_to_entity(model) if model else None

    def add(self, appointment: Appointment) -> Appointment:
        try:
            model = AppointmentModel.objects.create(
                id=appointment.id,
                business_id=appointment.business_id,
                service_id=appointment.service_id,
                staff_id=appointment.staff_id,
                customer_id=appointment.customer_id,
                starts_at=appointment.starts_at,
                ends_at=appointment.ends_at,
                status=appointment.status.value,
                price_minor=appointment.price_minor,
                currency=appointment.currency,
                customer_language=appointment.customer_language,
                notes=appointment.notes,
                management_token_hash=appointment.management_token_hash,
                management_token_expires_at=appointment.management_token_expires_at,
                idempotency_key=appointment.idempotency_key or "",
                rescheduled_from_id=appointment.rescheduled_from_id,
                cancelled_at=appointment.cancelled_at,
                cancelled_by=appointment.cancelled_by,
                cancellation_reason=appointment.cancellation_reason,
            )
        except IntegrityError as exc:
            raise AppointmentConflictError from exc
        return _appointment_to_entity(model)

    def update(self, appointment: Appointment) -> Appointment:
        model = AppointmentModel.objects.get(pk=appointment.id)
        model.business_id = appointment.business_id
        model.service_id = appointment.service_id
        model.staff_id = appointment.staff_id
        model.customer_id = appointment.customer_id
        model.starts_at = appointment.starts_at
        model.ends_at = appointment.ends_at
        model.status = appointment.status.value
        model.price_minor = appointment.price_minor
        model.currency = appointment.currency
        model.customer_language = appointment.customer_language
        model.notes = appointment.notes
        model.management_token_hash = appointment.management_token_hash
        model.management_token_expires_at = appointment.management_token_expires_at
        model.idempotency_key = appointment.idempotency_key or ""
        model.rescheduled_from_id = appointment.rescheduled_from_id
        model.cancelled_at = appointment.cancelled_at
        model.cancelled_by = appointment.cancelled_by
        model.cancellation_reason = appointment.cancellation_reason
        model.save()
        return _appointment_to_entity(model)

    def list_for_staff(
        self,
        staff_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
    ) -> list[Appointment]:
        models = AppointmentModel.objects.filter(
            staff_id=staff_id,
            starts_at__lt=ends_at,
            ends_at__gt=starts_at,
        )
        return [_appointment_to_entity(model) for model in models]

    def list_for_business(
        self,
        business_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        staff_id: UUID | None = None,
    ) -> list[Appointment]:
        models = AppointmentModel.objects.filter(
            business_id=business_id,
            starts_at__lt=ends_at,
            ends_at__gt=starts_at,
        )
        if staff_id is not None:
            models = models.filter(staff_id=staff_id)
        return [_appointment_to_entity(model) for model in models]

    def has_overlap(
        self,
        staff_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        exclude_id: UUID | None = None,
    ) -> bool:
        models = AppointmentModel.objects.filter(
            staff_id=staff_id,
            status__in=ACTIVE_APPOINTMENT_STATUSES,
            starts_at__lt=ends_at,
            ends_at__gt=starts_at,
        )
        if exclude_id:
            models = models.exclude(pk=exclude_id)
        return models.exists()


class DjangoReminderRepository:
    def list_due(self, before: datetime) -> list[Reminder]:
        models = ReminderModel.objects.filter(
            status=ReminderStatus.PENDING.value,
            send_at__lte=before,
        )
        return [_reminder_to_entity(model) for model in models]

    def add(self, reminder: Reminder) -> Reminder:
        model = ReminderModel.objects.create(
            id=reminder.id,
            appointment_id=reminder.appointment_id,
            kind=reminder.kind.value,
            send_at=reminder.send_at,
            sent_at=reminder.sent_at,
            status=reminder.status.value,
            attempts=reminder.attempts,
            language=reminder.language,
        )
        return _reminder_to_entity(model)

    def update(self, reminder: Reminder) -> Reminder:
        model = ReminderModel.objects.get(pk=reminder.id)
        model.appointment_id = reminder.appointment_id
        model.kind = reminder.kind.value
        model.send_at = reminder.send_at
        model.sent_at = reminder.sent_at
        model.status = reminder.status.value
        model.attempts = reminder.attempts
        model.language = reminder.language
        model.save()
        return _reminder_to_entity(model)

    def cancel_pending_for_appointment(self, appointment_id: UUID) -> None:
        ReminderModel.objects.filter(
            appointment_id=appointment_id,
            status=ReminderStatus.PENDING.value,
        ).update(status=ReminderStatus.CANCELLED.value)
