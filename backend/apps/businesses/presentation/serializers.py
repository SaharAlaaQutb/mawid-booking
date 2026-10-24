from typing import Any

from apps.businesses.infrastructure.models import Business
from rest_framework import serializers


class BusinessSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = (
            "id",
            "slug",
            "name_ar",
            "name_en",
            "timezone",
            "default_locale",
            "currency",
            "slot_interval_minutes",
            "min_lead_time_minutes",
            "max_advance_days",
            "cancellation_window_hours",
            "phone",
            "address_ar",
            "address_en",
        )
        read_only_fields = ("id", "slug")

    def validate_currency(self, value: str) -> str:
        currency = value.strip().upper()
        if len(currency) != 3:
            raise serializers.ValidationError("Use a three-letter currency code.")
        return currency

    def update(self, instance: Business, validated_data: dict[str, Any]) -> Business:
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.full_clean()
        instance.save()
        return instance


class PublicBusinessSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.SlugField()
    name = serializers.CharField()
    address = serializers.CharField()
    timezone = serializers.CharField()
    default_locale = serializers.CharField()
    currency = serializers.CharField()
    phone = serializers.CharField()
