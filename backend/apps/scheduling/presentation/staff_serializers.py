from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.bookings.presentation.serializers import AwareDateTimeField
from apps.catalog.infrastructure.models import Staff
from apps.scheduling.infrastructure.models import TimeOff, WorkingHours


def _raise_model_errors(exc: DjangoValidationError) -> None:
    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict) from exc
    raise serializers.ValidationError(exc.messages) from exc


class _ScopedStaffSerializer(serializers.ModelSerializer):
    staff = serializers.PrimaryKeyRelatedField(queryset=Staff.objects.all())

    def validate_staff(self, value: Staff) -> Staff:
        business_id = self.context.get("business_id")
        if business_id is not None and value.business_id != business_id:
            raise serializers.ValidationError("The staff member belongs to another business.")
        return value


class WorkingHoursSerializer(_ScopedStaffSerializer):
    class Meta:
        model = WorkingHours
        fields = ("id", "staff", "weekday", "start_time", "end_time")
        read_only_fields = ("id",)

    def create(self, validated_data: dict[str, Any]) -> WorkingHours:
        instance = WorkingHours(**validated_data)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            _raise_model_errors(exc)
        instance.save()
        return instance

    def update(self, instance: WorkingHours, validated_data: dict[str, Any]) -> WorkingHours:
        for field, value in validated_data.items():
            setattr(instance, field, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            _raise_model_errors(exc)
        instance.save()
        return instance


class TimeOffSerializer(_ScopedStaffSerializer):
    starts_at = AwareDateTimeField()
    ends_at = AwareDateTimeField()

    class Meta:
        model = TimeOff
        fields = ("id", "staff", "starts_at", "ends_at", "reason", "created_by")
        read_only_fields = ("id", "created_by")

    def create(self, validated_data: dict[str, Any]) -> TimeOff:
        instance = TimeOff(**validated_data)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            _raise_model_errors(exc)
        instance.save()
        return instance

    def update(self, instance: TimeOff, validated_data: dict[str, Any]) -> TimeOff:
        for field, value in validated_data.items():
            setattr(instance, field, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            _raise_model_errors(exc)
        instance.save()
        return instance


def parse_staff_filter(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise serializers.ValidationError({"staff": ["Use a valid UUID."]}) from exc
