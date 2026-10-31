from apps.bookings.domain.entities import Appointment, Customer
from apps.businesses.domain.entities import Business
from apps.catalog.domain.entities import Service, Staff
from apps.core.domain.locale import DEFAULT_LOCALE, SUPPORTED_LOCALES
from apps.notifications.domain.messages import MessageContext


class MessageContextBuilder:
    def build(
        self,
        *,
        appointment: Appointment,
        customer: Customer,
        service: Service,
        staff: Staff,
        business: Business,
        management_url: str,
        language: str | None = None,
    ) -> MessageContext:
        return MessageContext(
            appointment=appointment,
            customer=customer,
            service=service,
            staff=staff,
            business=business,
            management_url=management_url,
            language=self._resolve_language(appointment, customer, business, language),
        )

    def _resolve_language(
        self,
        appointment: Appointment,
        customer: Customer,
        business: Business,
        override: str | None,
    ) -> str:
        if override in SUPPORTED_LOCALES:
            return override
        for candidate in (
            appointment.customer_language,
            customer.language,
            business.default_locale,
        ):
            if candidate in SUPPORTED_LOCALES:
                return candidate
        return DEFAULT_LOCALE
