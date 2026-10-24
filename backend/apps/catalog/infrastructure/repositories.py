from uuid import UUID

from apps.catalog.domain.entities import Service, Staff
from apps.catalog.infrastructure.models import Service as ServiceModel
from apps.catalog.infrastructure.models import Staff as StaffModel
from apps.catalog.infrastructure.models import StaffService
from apps.core.domain.localized_text import LocalizedText


def _service_to_entity(model: ServiceModel) -> Service:
    return Service(
        id=model.id,
        business_id=model.business_id,
        name=LocalizedText(ar=model.name_ar, en=model.name_en),
        description=LocalizedText(ar=model.description_ar, en=model.description_en),
        duration_minutes=model.duration_minutes,
        buffer_before_minutes=model.buffer_before_minutes,
        buffer_after_minutes=model.buffer_after_minutes,
        price_minor=model.price_minor,
        currency=model.currency,
        is_active=model.is_active,
        sort_order=model.sort_order,
    )


def _staff_to_entity(model: StaffModel) -> Staff:
    return Staff(
        id=model.id,
        business_id=model.business_id,
        user_id=model.user_id,
        name=LocalizedText(ar=model.name_ar, en=model.name_en),
        title=LocalizedText(ar=model.title_ar, en=model.title_en),
        bio=LocalizedText(ar=model.bio_ar, en=model.bio_en),
        preferred_language=model.preferred_language,
        color=model.color,
        is_active=model.is_active,
    )


class DjangoServiceRepository:
    def get(self, service_id: UUID) -> Service | None:
        model = ServiceModel.objects.filter(pk=service_id).first()
        return _service_to_entity(model) if model else None

    def list_active(self, business_id: UUID) -> list[Service]:
        models = ServiceModel.objects.filter(business_id=business_id, is_active=True)
        return [_service_to_entity(model) for model in models]

    def list_for_staff(self, staff_id: UUID) -> list[Service]:
        models = ServiceModel.objects.filter(
            staff_links__staff_id=staff_id,
            is_active=True,
        ).order_by("sort_order", "name_en")
        return [_service_to_entity(model) for model in models]


class DjangoStaffRepository:
    def get(self, staff_id: UUID) -> Staff | None:
        model = StaffModel.objects.filter(pk=staff_id).first()
        return _staff_to_entity(model) if model else None

    def list_active(self, business_id: UUID) -> list[Staff]:
        models = StaffModel.objects.filter(business_id=business_id, is_active=True)
        return [_staff_to_entity(model) for model in models]

    def list_for_service(self, service_id: UUID) -> list[Staff]:
        models = StaffModel.objects.filter(
            service_links__service_id=service_id,
            is_active=True,
        ).order_by("name_en")
        return [_staff_to_entity(model) for model in models]

    def list_service_ids(self, staff_id: UUID) -> set[UUID]:
        return set(
            StaffService.objects.filter(staff_id=staff_id).values_list("service_id", flat=True)
        )
