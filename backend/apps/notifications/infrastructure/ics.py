from datetime import datetime
from zoneinfo import ZoneInfo

from django.utils import translation
from django.utils.formats import date_format, number_format, time_format
from django.utils.timezone import localtime
from django.utils.translation import gettext

from apps.bookings.application.management import ManagedBooking
from apps.notifications.domain.ics import IcsEvent, build_ics


class DjangoIcsService:
    def build(self, booking: ManagedBooking, *, management_url: str) -> str:
        language = booking.appointment.customer_language
        with translation.override(language):
            event = IcsEvent(
                uid=f"appointment-{booking.appointment.id}@mawid",
                summary=gettext("Appointment: %(service)s at %(business)s")
                % {
                    "service": booking.service.name.for_locale(language),
                    "business": booking.business.name.for_locale(language),
                },
                description=self._description(booking, language, management_url),
                starts_at=booking.appointment.starts_at,
                ends_at=booking.appointment.ends_at,
                location=booking.business.address.for_locale(language),
                url=management_url,
            )
        return build_ics(event)

    def _description(
        self,
        booking: ManagedBooking,
        language: str,
        management_url: str,
    ) -> str:
        starts_at = localtime(
            booking.appointment.starts_at,
            ZoneInfo(booking.business.timezone),
        )
        ends_at = localtime(
            booking.appointment.ends_at,
            ZoneInfo(booking.business.timezone),
        )
        lines = [
            gettext("Staff: %(staff_name)s")
            % {"staff_name": booking.staff.name.for_locale(language)},
            gettext("Date: %(date)s") % {"date": self._date(starts_at)},
            gettext("Time: %(start_time)s - %(end_time)s (%(timezone)s)")
            % {
                "start_time": time_format(starts_at, "H:i"),
                "end_time": time_format(ends_at, "H:i"),
                "timezone": booking.business.timezone,
            },
            gettext("Price: %(price)s %(currency)s")
            % {
                "price": number_format(
                    booking.service.price_minor / 100,
                    decimal_pos=2,
                    force_grouping=True,
                ),
                "currency": booking.service.currency,
            },
            gettext("Manage your booking: %(management_url)s") % {"management_url": management_url},
        ]
        return "\n".join(lines)

    def _date(self, value: datetime) -> str:
        return date_format(value, "l, j F Y")
