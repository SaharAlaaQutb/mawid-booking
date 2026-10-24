from typing import Any
from uuid import UUID

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.domain.locale import SUPPORTED_LOCALES


class AwareDateTimeField(serializers.DateTimeField):
    default_error_messages = {
        "naive": _("Include a timezone offset in the start time."),
    }

    def to_internal_value(self, data: Any) -> Any:
        if isinstance(data, str):
            value = data.strip()
            marker = value.find("T")
            has_offset = value.endswith("Z") or (
                marker >= 0 and ("+" in value[marker:] or "-" in value[marker + 1 :])
            )
            if not has_offset:
                self.fail("naive")
        parsed = super().to_internal_value(data)
        if timezone.is_naive(parsed):
            self.fail("naive")
        return parsed


class IsoDateTimeField(serializers.DateTimeField):
    def to_representation(self, value: Any) -> Any:
        return value.isoformat() if value is not None else None


class AppointmentServiceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    duration_minutes = serializers.IntegerField()
    price_minor = serializers.IntegerField()
    currency = serializers.CharField()


class AppointmentStaffSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    color = serializers.CharField()


class AppointmentCustomerSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField(allow_blank=True)


class AppointmentBusinessSerializer(serializers.Serializer):
    name = serializers.CharField()
    timezone = serializers.CharField()


class AppointmentResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    starts_at = IsoDateTimeField()
    ends_at = IsoDateTimeField()
    service = AppointmentServiceSerializer()
    staff = AppointmentStaffSerializer()
    customer = AppointmentCustomerSerializer()
    business = AppointmentBusinessSerializer()
    management_url = serializers.CharField(allow_null=True, required=False)
    rescheduled_from_id = serializers.UUIDField(allow_null=True)
    cancelled_at = IsoDateTimeField(allow_null=True)
    cancelled_by = serializers.CharField(allow_blank=True)
    cancellation_reason = serializers.CharField(allow_blank=True)


class AppointmentCreateSerializer(serializers.Serializer):
    service = serializers.UUIDField()
    staff = serializers.CharField(required=False, allow_blank=True)
    starts_at = AwareDateTimeField()
    customer_name = serializers.CharField(max_length=120)
    customer_email = serializers.EmailField()
    customer_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    language = serializers.ChoiceField(choices=SUPPORTED_LOCALES, required=False)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate_staff(self, value: str) -> UUID | None:
        if not value or value == "any":
            return None
        try:
            return UUID(value)
        except ValueError as exc:
            raise serializers.ValidationError(_("Use 'any' or a valid staff id.")) from exc


class AppointmentCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AppointmentRescheduleSerializer(serializers.Serializer):
    starts_at = AwareDateTimeField()
