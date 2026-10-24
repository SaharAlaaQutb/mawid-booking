import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.domain.locale import DEFAULT_LOCALE, LOCALE_CHOICES
from apps.core.domain.localized_text import LocalizedText

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message=_("Use a hex color such as #0F766E."),
)


class Service(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="services",
        verbose_name=_("business"),
    )
    name_ar = models.CharField(_("Arabic name"), max_length=120)
    name_en = models.CharField(_("English name"), max_length=120)
    description_ar = models.TextField(_("Arabic description"), blank=True)
    description_en = models.TextField(_("English description"), blank=True)
    duration_minutes = models.PositiveSmallIntegerField(
        _("duration in minutes"),
        validators=[MinValueValidator(5)],
    )
    buffer_before_minutes = models.PositiveSmallIntegerField(
        _("buffer before in minutes"),
        default=0,
    )
    buffer_after_minutes = models.PositiveSmallIntegerField(
        _("buffer after in minutes"),
        default=0,
    )
    price_minor = models.PositiveIntegerField(_("price in minor units"), default=0)
    currency = models.CharField(_("currency"), max_length=3, default="SAR")
    is_active = models.BooleanField(_("active"), default=True)
    sort_order = models.PositiveSmallIntegerField(_("sort order"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ("sort_order", "name_en")
        verbose_name = _("service")
        verbose_name_plural = _("services")
        indexes = [
            models.Index(fields=["business", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name_en or self.name_ar

    @property
    def name(self) -> LocalizedText:
        return LocalizedText(ar=self.name_ar, en=self.name_en)

    @property
    def description(self) -> LocalizedText:
        return LocalizedText(ar=self.description_ar, en=self.description_en)

    def clean(self) -> None:
        super().clean()
        if not self.name_ar.strip() or not self.name_en.strip():
            raise ValidationError(_("Both service names are required."))
        if not self.currency.strip():
            raise ValidationError({"currency": _("Currency is required.")})


class Staff(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="staff",
        verbose_name=_("business"),
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_profile",
        verbose_name=_("user"),
    )
    name_ar = models.CharField(_("Arabic name"), max_length=120)
    name_en = models.CharField(_("English name"), max_length=120)
    title_ar = models.CharField(_("Arabic title"), max_length=120, blank=True)
    title_en = models.CharField(_("English title"), max_length=120, blank=True)
    bio_ar = models.TextField(_("Arabic bio"), blank=True)
    bio_en = models.TextField(_("English bio"), blank=True)
    preferred_language = models.CharField(
        _("preferred language"),
        max_length=5,
        choices=LOCALE_CHOICES,
        default=DEFAULT_LOCALE,
    )
    color = models.CharField(
        _("calendar color"),
        max_length=7,
        default="#0F766E",
        validators=[HEX_COLOR_VALIDATOR],
    )
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ("name_en",)
        verbose_name = _("staff member")
        verbose_name_plural = _("staff members")
        indexes = [
            models.Index(fields=["business", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name_en or self.name_ar

    @property
    def name(self) -> LocalizedText:
        return LocalizedText(ar=self.name_ar, en=self.name_en)

    @property
    def title(self) -> LocalizedText:
        return LocalizedText(ar=self.title_ar, en=self.title_en)

    @property
    def bio(self) -> LocalizedText:
        return LocalizedText(ar=self.bio_ar, en=self.bio_en)

    def clean(self) -> None:
        super().clean()
        if not self.name_ar.strip() or not self.name_en.strip():
            raise ValidationError(_("Both staff names are required."))


class StaffService(models.Model):
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name="service_links",
        verbose_name=_("staff member"),
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="staff_links",
        verbose_name=_("service"),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ("staff", "service")
        verbose_name = _("staff service")
        verbose_name_plural = _("staff services")
        constraints = [
            models.UniqueConstraint(
                fields=["staff", "service"],
                name="unique_staff_service",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.staff} - {self.service}"

    def clean(self) -> None:
        super().clean()
        if self.staff.business_id != self.service.business_id:
            raise ValidationError(_("Staff and service must belong to the same business."))
