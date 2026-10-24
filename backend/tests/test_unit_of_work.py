import pytest
from apps.businesses.infrastructure.models import Business
from apps.core.infrastructure.unit_of_work import build_unit_of_work


@pytest.mark.django_db
def test_unit_of_work_rolls_back() -> None:
    with build_unit_of_work() as unit_of_work:
        Business.objects.create(
            slug="rolled-back",
            name_en="Rolled Back",
            name_ar="ملغي",
        )
        unit_of_work.rollback()

    assert not Business.objects.filter(slug="rolled-back").exists()
