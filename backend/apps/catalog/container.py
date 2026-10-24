from apps.catalog.domain.repository import ServiceRepository, StaffRepository
from apps.catalog.infrastructure.repositories import (
    DjangoServiceRepository,
    DjangoStaffRepository,
)


def build_service_repository() -> ServiceRepository:
    return DjangoServiceRepository()


def build_staff_repository() -> StaffRepository:
    return DjangoStaffRepository()
