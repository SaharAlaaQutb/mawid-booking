from apps.businesses.domain.repository import BusinessRepository
from apps.businesses.infrastructure.repositories import DjangoBusinessRepository


def build_business_repository() -> BusinessRepository:
    return DjangoBusinessRepository()
