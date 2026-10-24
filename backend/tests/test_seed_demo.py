from io import StringIO

import pytest
from apps.accounts.infrastructure.models import User
from apps.bookings.infrastructure.models import Appointment, Customer, Reminder
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Service, Staff, StaffService
from apps.scheduling.infrastructure.models import TimeOff, WorkingHours
from django.core.management import call_command


@pytest.mark.django_db
def test_seed_demo_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAWID_DEMO_PASSWORD", raising=False)
    output = StringIO()

    call_command("seed_demo", stdout=output)
    call_command("seed_demo", stdout=output)

    business = Business.objects.get(slug="mawid-demo")
    owner = User.objects.get(email="owner@mawid.local")

    assert owner.check_password("mawid-demo-123")
    assert owner.is_superuser
    assert Business.objects.count() == 1
    assert Service.objects.filter(business=business).count() == 6
    assert Staff.objects.filter(business=business).count() == 3
    assert StaffService.objects.filter(staff__business=business).count() == 9
    assert WorkingHours.objects.filter(staff__business=business).count() == 18
    assert TimeOff.objects.filter(staff__business=business).count() == 1
    assert Customer.objects.filter(business=business).count() == 3
    assert Appointment.objects.filter(business=business).count() == 3
    assert Reminder.objects.filter(appointment__business=business).count() == 3
    assert "Demo ready" in output.getvalue()
