import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.domain.locale import DEFAULT_LOCALE, LOCALE_CHOICES
from apps.core.domain.localized_text import LocalizedText
from apps.core.validators import validate_timezone


class Business(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(_("slug"), max_length=80, unique=True)
    name_ar = models.CharField(_("Arabic name"), max_length=120)
    name_en = models.CharField(_("English name"), max_length=120)
    timezone = models.CharField(
        _("timezone"),
        max_length=64,
        default="UTC",
        validators=[validate_timezone],
    )
    default_locale = models.CharField(
        _("default locale"),
        max_length=5,
        choices=LOCALE_CHOICES,
        default=DEFAULT_LOCALE,
    )
    currency = models.CharField(_("currency"), max_length=3, default="SAR")
    slot_interval_minutes = models.PositiveSmallIntegerField(
        _("slot interval in minutes"),
        default=15,
        validators=[MinValueValidator(5)],
    )
    min_lead_time_minutes = models.PositiveIntegerField(
        _("minimum lead time in minutes"),
        default=120,
    )
    max_advance_days = models.PositiveSmallIntegerField(
        _("maximum advance booking days"),
        default=60,
        validators=[MinValueValidator(1)],
    )
    cancellation_window_hours = models.PositiveSmallIntegerField(
        _("cancellation window in hours"),
        default=24,
    )
    phone = models.CharField(_("phone"), max_length=32, blank=True)
    address_ar = models.CharField(_("Arabic address"), max_length=255, blank=True)
    address_en = models.CharField(_("English address"), max_length=255, blank=True)
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ("name_en",)
        verbose_name = _("business")
        verbose_name_plural = _("businesses")
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self) -> str:
        return self.name_en or self.name_ar or self.slug

    @property
    def name(self) -> LocalizedText:
        return LocalizedText(ar=self.name_ar, en=self.name_en)

    @property
    def address(self) -> LocalizedText:
        return LocalizedText(ar=self.address_ar, en=self.address_en)

    def clean(self) -> None:
        super().clean()
        if not self.name_ar.strip() or not self.name_en.strip():
            raise ValidationError(_("Both business names are required."))
        if not self.currency.strip():
            raise ValidationError({"currency": _("Currency is required.")})
