from typing import Any

from rest_framework import serializers

from apps.bookings.domain.status import AppointmentStatus
from apps.bookings.presentation.serializers import (
    AppointmentCustomerSerializer,
    AppointmentServiceSerializer,
    IsoDateTimeField,
)

STAFF_TARGET_STATUSES = (
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.COMPLETED,
    AppointmentStatus.CANCELLED,
    AppointmentStatus.NO_SHOW,
)


class AppointmentStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=STAFF_TARGET_STATUSES)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class CalendarQuerySerializer(serializers.Serializer):
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    staff = serializers.UUIDField(required=False)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        mapped = data.copy()
        if "from" in mapped:
            mapped["starts_on"] = mapped["from"]
        if "to" in mapped:
            mapped["ends_on"] = mapped["to"]
        return super().to_internal_value(mapped)


class CalendarAppointmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    starts_at = IsoDateTimeField()
    ends_at = IsoDateTimeField()
    status = serializers.CharField()
    service = AppointmentServiceSerializer()
    customer = AppointmentCustomerSerializer()
    notes = serializers.CharField(allow_blank=True)


class CalendarStaffSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    color = serializers.CharField()
    appointments = CalendarAppointmentSerializer(many=True)


class CalendarResponseSerializer(serializers.Serializer):
    from_date = serializers.DateField(source="from")
    to_date = serializers.DateField(source="to")
    timezone = serializers.CharField()
    staff = CalendarStaffSerializer(many=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        data = super().to_representation(instance)
        data["from"] = data.pop("from_date")
        data["to"] = data.pop("to_date")
        return data
