import uuid
from datetime import time

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def _start_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _end_minutes(value: time) -> int:
    return 24 * 60 if value == time(0, 0) else _start_minutes(value)


class Weekday(models.IntegerChoices):
    MONDAY = 0, _("Monday")
    TUESDAY = 1, _("Tuesday")
    WEDNESDAY = 2, _("Wednesday")
    THURSDAY = 3, _("Thursday")
    FRIDAY = 4, _("Friday")
    SATURDAY = 5, _("Saturday")
    SUNDAY = 6, _("Sunday")


class WorkingHours(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey(
        "catalog.Staff",
        on_delete=models.CASCADE,
        related_name="working_hours",
        verbose_name=_("staff member"),
    )
    weekday = models.PositiveSmallIntegerField(_("weekday"), choices=Weekday.choices)
    start_time = models.TimeField(_("start time"))
    end_time = models.TimeField(_("end time"))
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ("staff", "weekday", "start_time")
        verbose_name = _("working hours")
        verbose_name_plural = _("working hours")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(weekday__gte=0, weekday__lte=6),
                name="working_hours_weekday_range",
            ),
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time"))
                | models.Q(end_time=time(0, 0)),
                name="working_hours_valid_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.staff} {self.get_weekday_display()} {self.start_time}-{self.end_time}"

    def clean(self) -> None:
        super().clean()
        start = _start_minutes(self.start_time)
        end = _end_minutes(self.end_time)
        if end <= start:
            raise ValidationError({"end_time": _("End time must be after start time.")})

        if not self.staff_id:
            return

        siblings = WorkingHours.objects.filter(
            staff_id=self.staff_id,
            weekday=self.weekday,
        )
        if self.pk:
            siblings = siblings.exclude(pk=self.pk)

        for other in siblings:
            other_start = _start_minutes(other.start_time)
            other_end = _end_minutes(other.end_time)
            if start < other_end and end > other_start:
                raise ValidationError(_("This shift overlaps an existing shift for the same day."))


class TimeOff(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey(
        "catalog.Staff",
        on_delete=models.CASCADE,
        related_name="time_off",
        verbose_name=_("staff member"),
    )
    starts_at = models.DateTimeField(_("starts at"))
    ends_at = models.DateTimeField(_("ends at"))
    reason = models.CharField(_("reason"), max_length=255, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_time_off",
        verbose_name=_("created by"),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ("-starts_at",)
        verbose_name = _("time off")
        verbose_name_plural = _("time off")
        indexes = [
            models.Index(fields=["staff", "starts_at", "ends_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="time_off_valid_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.staff} {self.starts_at:%Y-%m-%d %H:%M} - {self.ends_at:%H:%M}"

    def clean(self) -> None:
        super().clean()
        if self.starts_at and self.ends_at:
            if timezone.is_naive(self.starts_at) or timezone.is_naive(self.ends_at):
                raise ValidationError(_("Time off must use timezone-aware datetimes."))
            if self.ends_at <= self.starts_at:
                raise ValidationError({"ends_at": _("End must be after start.")})
