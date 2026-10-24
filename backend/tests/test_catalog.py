import pytest
from apps.businesses.infrastructure.models import Business
from apps.catalog.container import build_service_repository, build_staff_repository
from apps.catalog.infrastructure.models import Service, Staff, StaffService
from django.core.exceptions import ValidationError


def test_service_total_duration_includes_buffers(service: Service) -> None:
    entity = build_service_repository().get(service.id)

    assert entity is not None
    assert entity.total_duration_minutes == 45
    assert entity.name.for_locale("ar") == "استشارة"


def test_repositories_filter_by_staff_and_service(
    service: Service,
    staff: Staff,
) -> None:
    StaffService.objects.create(staff=staff, service=service)

    assert build_service_repository().list_for_staff(staff.id) == [
        build_service_repository().get(service.id)
    ]
    assert build_staff_repository().list_for_service(service.id) == [
        build_staff_repository().get(staff.id)
    ]
    assert build_staff_repository().list_service_ids(staff.id) == {service.id}


def test_inactive_services_are_hidden(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    service.is_active = False
    service.save(update_fields=["is_active"])
    StaffService.objects.create(staff=staff, service=service)

    assert build_service_repository().list_active(business.id) == []
    assert build_service_repository().list_for_staff(staff.id) == []


def test_staff_service_requires_same_business(service: Service) -> None:
    other_business = Business.objects.create(
        slug="other",
        name_en="Other",
        name_ar="آخر",
    )
    other_staff = Staff.objects.create(
        business=other_business,
        name_en="Other Staff",
        name_ar="موظف آخر",
    )

    with pytest.raises(ValidationError, match="same business"):
        StaffService(staff=other_staff, service=service).full_clean()
