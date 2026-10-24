import pytest
from apps.businesses.container import build_business_repository
from apps.businesses.infrastructure.models import Business
from django.core.exceptions import ValidationError


def test_repository_returns_active_business(business: Business) -> None:
    repository = build_business_repository()

    assert repository.get_active() == repository.get(business.id)
    assert repository.get_by_slug("test-clinic") == repository.get(business.id)


def test_repository_ignores_inactive_business(business: Business) -> None:
    business.is_active = False
    business.save(update_fields=["is_active"])

    assert build_business_repository().get_active() is None


def test_invalid_timezone_is_rejected(business: Business) -> None:
    business.timezone = "Mars/Olympus"

    with pytest.raises(ValidationError, match="valid IANA timezone"):
        business.full_clean()


def test_both_names_are_required(business: Business) -> None:
    business.name_ar = " "

    with pytest.raises(ValidationError, match="Both business names"):
        business.full_clean()
