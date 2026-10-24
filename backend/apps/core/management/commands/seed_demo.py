import argparse
import hashlib
import os
from datetime import date, datetime, time, timedelta
from typing import Any, TypedDict
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.infrastructure.models import Role, User
from apps.bookings.domain.status import (
    AppointmentStatus,
    ReminderKind,
    ReminderStatus,
)
from apps.bookings.infrastructure.models import Appointment, Customer, Reminder
from apps.businesses.infrastructure.models import Business
from apps.catalog.infrastructure.models import Service, Staff, StaffService
from apps.scheduling.infrastructure.models import TimeOff, WorkingHours

DEMO_SLUG = "mawid-demo"
DEMO_EMAIL = "owner@mawid.local"
DEMO_PASSWORD_ENV = "MAWID_DEMO_PASSWORD"
DEFAULT_DEMO_PASSWORD = "mawid-demo-123"


class CustomerSeed(TypedDict):
    email: str
    name: str
    phone: str
    language: str


class BookingSeed(TypedDict):
    key: str
    service: str
    staff: str
    customer: str
    starts_at: time
    status: AppointmentStatus


SERVICES: tuple[dict[str, Any], ...] = (
    {
        "name_en": "Consultation",
        "name_ar": "استشارة",
        "description_en": "A 30 minute consultation with a specialist.",
        "description_ar": "استشارة لمدة ٣٠ دقيقة مع أخصائي.",
        "duration_minutes": 30,
        "price_minor": 20000,
        "sort_order": 1,
    },
    {
        "name_en": "Follow-up",
        "name_ar": "متابعة",
        "description_en": "A short follow-up visit.",
        "description_ar": "زيارة متابعة قصيرة.",
        "duration_minutes": 20,
        "price_minor": 12000,
        "sort_order": 2,
    },
    {
        "name_en": "Deep cleaning",
        "name_ar": "تنظيف عميق",
        "description_en": "A thorough 60 minute cleaning session.",
        "description_ar": "جلسة تنظيف شاملة لمدة ٦٠ دقيقة.",
        "duration_minutes": 60,
        "price_minor": 35000,
        "buffer_after_minutes": 10,
        "sort_order": 3,
    },
    {
        "name_en": "Whitening",
        "name_ar": "تبييض الأسنان",
        "description_en": "A 45 minute whitening treatment.",
        "description_ar": "جلسة تبييض لمدة ٤٥ دقيقة.",
        "duration_minutes": 45,
        "price_minor": 45000,
        "sort_order": 4,
    },
    {
        "name_en": "Skin check",
        "name_ar": "فحص البشرة",
        "description_en": "A focused skin assessment.",
        "description_ar": "فحص مركّز للبشرة.",
        "duration_minutes": 30,
        "price_minor": 25000,
        "sort_order": 5,
    },
    {
        "name_en": "Laser session",
        "name_ar": "جلسة ليزر",
        "description_en": "A 45 minute laser treatment.",
        "description_ar": "جلسة ليزر لمدة ٤٥ دقيقة.",
        "duration_minutes": 45,
        "price_minor": 60000,
        "buffer_before_minutes": 10,
        "sort_order": 6,
    },
)

STAFF: tuple[dict[str, Any], ...] = (
    {
        "name_en": "Sarah Alotaibi",
        "name_ar": "سارة العتيبي",
        "title_en": "General dentist",
        "title_ar": "طبيبة أسنان عامة",
        "preferred_language": "ar",
        "color": "#0F766E",
    },
    {
        "name_en": "Omar Hassan",
        "name_ar": "عمر حسن",
        "title_en": "Dental hygienist",
        "title_ar": "أخصائي صحة الفم",
        "preferred_language": "en",
        "color": "#B45309",
    },
    {
        "name_en": "Noura Alzahrani",
        "name_ar": "نورة الزهراني",
        "title_en": "Dermatologist",
        "title_ar": "أخصائية جلدية",
        "preferred_language": "ar",
        "color": "#7C3AED",
    },
)

CUSTOMERS: tuple[CustomerSeed, ...] = (
    {
        "email": "layla@example.com",
        "name": "Layla Ahmed",
        "phone": "+966555555555",
        "language": "ar",
    },
    {
        "email": "ahmed@example.com",
        "name": "Ahmed Saleh",
        "phone": "+966544444444",
        "language": "en",
    },
    {
        "email": "mona@example.com",
        "name": "Mona Khalid",
        "phone": "+966533333333",
        "language": "ar",
    },
)

BOOKINGS: tuple[BookingSeed, ...] = (
    {
        "key": "demo-appointment-1",
        "service": "Consultation",
        "staff": "Sarah Alotaibi",
        "customer": "layla@example.com",
        "starts_at": time(10),
        "status": AppointmentStatus.CONFIRMED,
    },
    {
        "key": "demo-appointment-2",
        "service": "Whitening",
        "staff": "Sarah Alotaibi",
        "customer": "ahmed@example.com",
        "starts_at": time(11),
        "status": AppointmentStatus.PENDING,
    },
    {
        "key": "demo-appointment-3",
        "service": "Follow-up",
        "staff": "Omar Hassan",
        "customer": "mona@example.com",
        "starts_at": time(10, 30),
        "status": AppointmentStatus.CONFIRMED,
    },
)


def _next_weekday(start: date, weekday: int) -> date:
    days_ahead = (weekday - start.weekday()) % 7
    return start + timedelta(days=days_ahead)


class Command(BaseCommand):
    help = "Create or update an idempotent demo business, catalog, schedule, and booking."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--owner-email",
            default=DEMO_EMAIL,
            help=f"Owner email address (default: {DEMO_EMAIL}).",
        )

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        owner_email = str(options["owner_email"]).strip().lower()
        password = os.environ.get(DEMO_PASSWORD_ENV, DEFAULT_DEMO_PASSWORD)

        owner, _ = User.objects.get_or_create(
            email=owner_email,
            defaults={"full_name": "Demo Owner"},
        )
        owner.full_name = owner.full_name or "Demo Owner"
        owner.role = Role.OWNER
        owner.is_staff = True
        owner.is_superuser = True
        owner.set_password(password)
        owner.save()

        business, _ = Business.objects.update_or_create(
            slug=DEMO_SLUG,
            defaults={
                "name_en": "Mawid Demo Clinic",
                "name_ar": "عيادة مود التجريبية",
                "timezone": "Asia/Riyadh",
                "default_locale": "ar",
                "currency": "SAR",
                "slot_interval_minutes": 15,
                "min_lead_time_minutes": 120,
                "max_advance_days": 60,
                "cancellation_window_hours": 24,
                "phone": "+966500000000",
                "address_en": "King Fahd Road, Riyadh",
                "address_ar": "طريق الملك فهد، الرياض",
                "is_active": True,
            },
        )

        services: dict[str, Service] = {}
        for service_data in SERVICES:
            service, _ = Service.objects.update_or_create(
                business=business,
                name_en=service_data["name_en"],
                defaults={
                    "name_ar": service_data["name_ar"],
                    "description_en": service_data["description_en"],
                    "description_ar": service_data["description_ar"],
                    "duration_minutes": service_data["duration_minutes"],
                    "buffer_before_minutes": service_data.get("buffer_before_minutes", 0),
                    "buffer_after_minutes": service_data.get("buffer_after_minutes", 0),
                    "price_minor": service_data["price_minor"],
                    "currency": business.currency,
                    "sort_order": service_data["sort_order"],
                    "is_active": True,
                },
            )
            services[service_data["name_en"]] = service

        staff_members: dict[str, Staff] = {}
        for index, staff_data in enumerate(STAFF):
            staff, _ = Staff.objects.update_or_create(
                business=business,
                name_en=staff_data["name_en"],
                defaults={
                    "name_ar": staff_data["name_ar"],
                    "title_en": staff_data["title_en"],
                    "title_ar": staff_data["title_ar"],
                    "preferred_language": staff_data["preferred_language"],
                    "color": staff_data["color"],
                    "is_active": True,
                    "user": owner if index == 0 else None,
                },
            )
            staff_members[staff_data["name_en"]] = staff

            WorkingHours.objects.filter(staff=staff).delete()
            WorkingHours.objects.bulk_create(
                [
                    WorkingHours(
                        staff=staff,
                        weekday=weekday,
                        start_time=time(9),
                        end_time=time(17),
                    )
                    for weekday in range(0, 5)
                ]
                + [
                    WorkingHours(staff=staff, weekday=5, start_time=time(10), end_time=time(14)),
                ]
            )

        assignments = {
            "Sarah Alotaibi": ("Consultation", "Follow-up", "Deep cleaning", "Whitening"),
            "Omar Hassan": ("Consultation", "Follow-up"),
            "Noura Alzahrani": ("Consultation", "Skin check", "Laser session"),
        }
        for staff_name, service_names in assignments.items():
            for service_name in service_names:
                StaffService.objects.get_or_create(
                    staff=staff_members[staff_name],
                    service=services[service_name],
                )

        local_zone = ZoneInfo(business.timezone)
        local_today = timezone.now().astimezone(local_zone).date()
        booking_day = _next_weekday(local_today, 0)

        next_week_start = _next_weekday(local_today + timedelta(days=1), 2)
        TimeOff.objects.filter(
            staff=staff_members["Omar Hassan"], reason="Training session"
        ).delete()
        TimeOff.objects.create(
            staff=staff_members["Omar Hassan"],
            starts_at=datetime.combine(next_week_start, time(14), tzinfo=local_zone),
            ends_at=datetime.combine(next_week_start, time(15), tzinfo=local_zone),
            reason="Training session",
            created_by=owner,
        )

        customers: dict[str, Customer] = {}
        for customer_data in CUSTOMERS:
            customer, _ = Customer.objects.update_or_create(
                business=business,
                email=customer_data["email"],
                defaults={
                    "name": customer_data["name"],
                    "phone": customer_data["phone"],
                    "language": customer_data["language"],
                },
            )
            customers[customer_data["email"]] = customer

        appointments: list[Appointment] = []
        for booking_data in BOOKINGS:
            service = services[booking_data["service"]]
            customer = customers[booking_data["customer"]]
            starts_at = datetime.combine(booking_day, booking_data["starts_at"], tzinfo=local_zone)
            ends_at = starts_at + timedelta(minutes=service.duration_minutes)
            appointment, _ = Appointment.objects.update_or_create(
                business=business,
                idempotency_key=booking_data["key"],
                defaults={
                    "service": service,
                    "staff": staff_members[booking_data["staff"]],
                    "customer": customer,
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "status": booking_data["status"].value,
                    "price_minor": service.price_minor,
                    "currency": business.currency,
                    "customer_language": customer.language,
                    "notes": "Demo appointment created by seed_demo.",
                    "management_token_hash": hashlib.sha256(
                        f"demo-management-token-{booking_data['key']}".encode()
                    ).hexdigest(),
                    "management_token_expires_at": starts_at + timedelta(days=7),
                },
            )
            Reminder.objects.update_or_create(
                appointment=appointment,
                kind=ReminderKind.REMINDER.value,
                defaults={
                    "send_at": starts_at - timedelta(hours=24),
                    "status": ReminderStatus.PENDING.value,
                    "language": customer.language,
                },
            )
            appointments.append(appointment)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo ready: business={business.slug}, owner={owner.email}, "
                f"staff={len(staff_members)}, services={len(services)}, "
                f"appointments={len(appointments)} on {booking_day.isoformat()}"
            )
        )
