from typing import Any
from uuid import UUID

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.domain.locale import SUPPORTED_LOCALES
from apps.scheduling.application.availability import Availability


class BusinessDateTimeField(serializers.DateTimeField):
    def to_representation(self, value: Any) -> str:
        return value.isoformat()


class AvailabilityQuerySerializer(serializers.Serializer):
    service = serializers.UUIDField()
    staff = serializers.CharField(required=False, allow_blank=True, default="any")
    date = serializers.DateField()
    lang = serializers.ChoiceField(choices=SUPPORTED_LOCALES, required=False)

    def validate_staff(self, value: str) -> UUID | None:
        if not value or value == "any":
            return None
        try:
            return UUID(value)
        except ValueError as exc:
            raise serializers.ValidationError(_("Use 'any' or a valid staff id.")) from exc


class AvailabilityServiceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    duration_minutes = serializers.IntegerField()
    price_minor = serializers.IntegerField()
    currency = serializers.CharField()


class StaffOptionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    color = serializers.CharField()
    booked_count = serializers.IntegerField()


class AvailabilitySlotSerializer(serializers.Serializer):
    starts_at = BusinessDateTimeField()
    ends_at = BusinessDateTimeField()
    recommended_staff_id = serializers.UUIDField()
    staff_options = StaffOptionSerializer(many=True)


class AvailabilityResponseSerializer(serializers.Serializer):
    date = serializers.DateField(source="on_date")
    timezone = serializers.CharField()
    service = serializers.SerializerMethodField()
    slots = serializers.SerializerMethodField()
    next_available_date = serializers.DateField(allow_null=True)

    @extend_schema_field(AvailabilityServiceSerializer)
    def get_service(self, availability: Availability) -> dict[str, Any]:
        locale: str = self.context.get("locale", "en")
        return AvailabilityServiceSerializer(
            {
                "id": availability.service.id,
                "name": availability.service.name.for_locale(locale),
                "duration_minutes": availability.service.duration_minutes,
                "price_minor": availability.service.price_minor,
                "currency": availability.service.currency,
            }
        ).data

    @extend_schema_field(AvailabilitySlotSerializer(many=True))
    def get_slots(self, availability: Availability) -> list[dict[str, Any]]:
        locale: str = self.context.get("locale", "en")
        return [
            AvailabilitySlotSerializer(
                {
                    "starts_at": slot.starts_at,
                    "ends_at": slot.ends_at,
                    "recommended_staff_id": slot.recommended_staff_id,
                    "staff_options": [
                        {
                            "id": option.staff.id,
                            "name": option.staff.name.for_locale(locale),
                            "color": option.staff.color,
                            "booked_count": option.booked_count,
                        }
                        for option in slot.options
                    ],
                }
            ).data
            for slot in availability.slots
        ]


class AvailabilityQueryParamsSerializer(serializers.Serializer):
    service = serializers.UUIDField(help_text="Service id.")
    staff = serializers.CharField(
        required=False,
        help_text="Staff id or 'any'.",
    )
    date = serializers.DateField(help_text="Business-local date in YYYY-MM-DD format.")
    lang = serializers.ChoiceField(
        choices=("en", "ar"),
        required=False,
        help_text="Optional response language.",
    )
