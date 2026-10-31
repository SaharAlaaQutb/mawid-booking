from typing import Any
from uuid import UUID

from apps.catalog.infrastructure.models import Service, Staff, StaffService
from django.db import transaction
from rest_framework import serializers


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = (
            "id",
            "name_ar",
            "name_en",
            "description_ar",
            "description_en",
            "duration_minutes",
            "buffer_before_minutes",
            "buffer_after_minutes",
            "price_minor",
            "currency",
            "is_active",
            "sort_order",
        )
        read_only_fields = ("id",)

    def validate_currency(self, value: str) -> str:
        currency = value.strip().upper()
        if len(currency) != 3:
            raise serializers.ValidationError("Use a three-letter currency code.")
        return currency


class PublicServiceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField()
    duration_minutes = serializers.IntegerField()
    price_minor = serializers.IntegerField()
    currency = serializers.CharField()


class StaffSerializer(serializers.ModelSerializer):
    service_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
    )
    services = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = (
            "id",
            "name_ar",
            "name_en",
            "title_ar",
            "title_en",
            "bio_ar",
            "bio_en",
            "preferred_language",
            "color",
            "is_active",
            "user",
            "service_ids",
            "services",
        )
        read_only_fields = ("id", "user", "services")

    def validate_service_ids(self, value: list[UUID]) -> list[UUID]:
        business_id = self.instance.business_id if self.instance else self.context["business_id"]
        unique_ids = list(dict.fromkeys(value))
        if not unique_ids:
            return []
        count = Service.objects.filter(business_id=business_id, id__in=unique_ids).count()
        if count != len(unique_ids):
            raise serializers.ValidationError("Every service must belong to your business.")
        return unique_ids

    def get_services(self, instance: Staff) -> list[dict[str, Any]]:
        return [
            {
                "id": link.service_id,
                "name_en": link.service.name_en,
                "name_ar": link.service.name_ar,
            }
            for link in instance.service_links.select_related("service")
        ]

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> Staff:
        service_ids = validated_data.pop("service_ids", [])
        staff = Staff.objects.create(**validated_data)
        StaffService.objects.bulk_create(
            [StaffService(staff=staff, service_id=service_id) for service_id in service_ids]
        )
        return staff

    @transaction.atomic
    def update(self, instance: Staff, validated_data: dict[str, Any]) -> Staff:
        service_ids = validated_data.pop("service_ids", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.full_clean()
        instance.save()
        if service_ids is not None:
            StaffService.objects.filter(staff=instance).exclude(service_id__in=service_ids).delete()
            existing = set(
                StaffService.objects.filter(staff=instance).values_list(
                    "service_id",
                    flat=True,
                )
            )
            StaffService.objects.bulk_create(
                [
                    StaffService(staff=instance, service_id=service_id)
                    for service_id in service_ids
                    if service_id not in existing
                ]
            )
        return instance


class PublicStaffSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    title = serializers.CharField()
    bio = serializers.CharField()
    color = serializers.CharField()
