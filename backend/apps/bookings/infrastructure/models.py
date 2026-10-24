import uuid
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.bookings.domain.status import (
    ACTIVE_APPOINTMENT_STATUSES,
    APPOINTMENT_STATUS_CHOICES,
    CANCELLED_BY_CHOICES,
    REMINDER_KIND_CHOICES,
    REMINDER_STATUS_CHOICES,
    AppointmentStatus,
    ReminderKind,
    ReminderStatus,
)
from apps.core.domain.locale import DEFAULT_LOCALE, LOCALE_CHOICES


class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="customers",
        verbose_name=_("business"),
    )
    name = models.CharField(_("name"), max_length=120)
    email = models.EmailField(_("email"))
    phone = models.CharField(_("phone"), max_length=32, blank=True)
    language = models.CharField(
        _("language"),
        max_length=5,
        choices=LOCALE_CHOICES,
        default=DEFAULT_LOCALE,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ("name", "email")
        verbose_name = _("customer")
        verbose_name_plural = _("customers")
        constraints = [
            models.UniqueConstraint(
                fields=["business", "email"],
                name="unique_customer_email_per_business",
            ),
        ]
        indexes = [
            models.Index(fields=["business", "email"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if not self.name.strip():
            raise ValidationError({"name": _("Name is required.")})
        validate_email(self.email)


class Appointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="appointments",
        verbose_name=_("business"),
    )
    service = models.ForeignKey(
        "catalog.Service",
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name=_("service"),
    )
    staff = models.ForeignKey(
        "catalog.Staff",
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name=_("staff member"),
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name=_("customer"),
    )
    starts_at = models.DateTimeField(_("starts at"))
    ends_at = models.DateTimeField(_("ends at"))
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=APPOINTMENT_STATUS_CHOICES,
        default=AppointmentStatus.PENDING.value,
    )
    price_minor = models.PositiveIntegerField(_("price in minor units"), default=0)
    currency = models.CharField(_("currency"), max_length=3, default="SAR")
    customer_language = models.CharField(
        _("customer language"),
        max_length=5,
        choices=LOCALE_CHOICES,
        default=DEFAULT_LOCALE,
    )
    notes = models.TextField(_("notes"), blank=True)
    management_token_hash = models.CharField(
        _("management token hash"),
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    management_token_expires_at = models.DateTimeField(
        _("management token expires at"),
        null=True,
        blank=True,
    )
    idempotency_key = models.CharField(
        _("idempotency key"),
        max_length=64,
        default="",
        blank=True,
    )
    rescheduled_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rescheduled_children",
        verbose_name=_("rescheduled from"),
    )
    cancelled_at = models.DateTimeField(_("cancelled at"), null=True, blank=True)
    cancelled_by = models.CharField(
        _("cancelled by"),
        max_length=8,
        choices=CANCELLED_BY_CHOICES,
        blank=True,
        default="",
    )
    cancellation_reason = models.CharField(
        _("cancellation reason"),
        max_length=255,
        blank=True,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ("starts_at",)
        verbose_name = _("appointment")
        verbose_name_plural = _("appointments")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="appointment_valid_range",
            ),
            models.UniqueConstraint(
                fields=["business", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="unique_appointment_idempotency_key",
            ),
        ]
        indexes = [
            models.Index(fields=["business", "starts_at", "ends_at"]),
            models.Index(fields=["staff", "starts_at", "ends_at"]),
            models.Index(fields=["status", "starts_at"]),
            models.Index(fields=["customer", "starts_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.customer} - {self.service} @ {self.starts_at:%Y-%m-%d %H:%M}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.currency = self.currency.strip().upper()
        self.customer_language = self.customer_language.strip().lower()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if not self.starts_at or not self.ends_at:
            return
        if timezone.is_naive(self.starts_at) or timezone.is_naive(self.ends_at):
            raise ValidationError(_("Appointments must use timezone-aware datetimes."))
        if self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": _("End must be after start.")})

        if self.service_id and self.service.business_id != self.business_id:
            raise ValidationError({"service": _("Service belongs to another business.")})
        if self.staff_id and self.staff.business_id != self.business_id:
            raise ValidationError({"staff": _("Staff member belongs to another business.")})
        if self.customer_id and self.customer.business_id != self.business_id:
            raise ValidationError({"customer": _("Customer belongs to another business.")})

        if not self.staff_id:
            return

        conflicts = Appointment.objects.filter(
            staff_id=self.staff_id,
            status__in=ACTIVE_APPOINTMENT_STATUSES,
            starts_at__lt=self.ends_at,
            ends_at__gt=self.starts_at,
        )
        if self.pk:
            conflicts = conflicts.exclude(pk=self.pk)
        if conflicts.exists():
            raise ValidationError(_("This staff member already has an appointment in that slot."))


class Reminder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="reminders",
        verbose_name=_("appointment"),
    )
    kind = models.CharField(
        _("kind"),
        max_length=16,
        choices=REMINDER_KIND_CHOICES,
        default=ReminderKind.REMINDER.value,
    )
    send_at = models.DateTimeField(_("send at"))
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=REMINDER_STATUS_CHOICES,
        default=ReminderStatus.PENDING.value,
    )
    attempts = models.PositiveSmallIntegerField(_("attempts"), default=0)
    last_error = models.TextField(_("last error"), blank=True)
    language = models.CharField(
        _("language"),
        max_length=5,
        choices=LOCALE_CHOICES,
        default=DEFAULT_LOCALE,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ("send_at",)
        verbose_name = _("reminder")
        verbose_name_plural = _("reminders")
        constraints = [
            models.UniqueConstraint(
                fields=["appointment", "kind"],
                name="unique_reminder_kind_per_appointment",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "send_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_kind_display()} for {self.appointment_id} at {self.send_at:%Y-%m-%d %H:%M}"
        )

    def clean(self) -> None:
        super().clean()
        if self.send_at and timezone.is_naive(self.send_at):
            raise ValidationError({"send_at": _("Send time must be timezone-aware.")})
