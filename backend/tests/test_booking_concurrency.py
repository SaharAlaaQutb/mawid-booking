from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time, timedelta
from threading import Barrier

import pytest
from apps.bookings.application.booking import BookingResult
from apps.bookings.application.errors import BookingError
from apps.bookings.container import build_booking_service
from apps.bookings.infrastructure.models import Appointment
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Service, Staff, StaffService
from apps.scheduling.infrastructure.models import WorkingHours
from django.db import connection, connections

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        connection.vendor != "postgresql",
        reason="Concurrent booking requires PostgreSQL row locks.",
    ),
]


def test_two_simultaneous_bookings_create_exactly_one(
    business: Business,
    service: Service,
    staff: Staff,
) -> None:
    business.timezone = "UTC"
    business.save(update_fields=["timezone"])
    StaffService.objects.create(staff=staff, service=service)
    for weekday in range(7):
        WorkingHours.objects.create(
            staff=staff,
            weekday=weekday,
            start_time=time(9),
            end_time=time(17),
        )
    starts_at = datetime.combine(
        (datetime.now(UTC) + timedelta(days=3)).date(),
        time(10),
        tzinfo=UTC,
    )
    barrier = Barrier(2)

    def attempt(email: str) -> BookingResult | BookingError:
        connections.close_all()
        try:
            barrier.wait(timeout=5)
            return build_booking_service().create(
                service_id=service.id,
                staff_id=staff.id,
                starts_at=starts_at,
                customer_name=email.split("@")[0],
                customer_email=email,
            )
        except BookingError as exc:
            return exc
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, ["first@example.com", "second@example.com"]))

    assert sum(isinstance(result, BookingResult) for result in results) == 1
    assert sum(isinstance(result, BookingError) for result in results) == 1
    assert Appointment.objects.count() == 1
