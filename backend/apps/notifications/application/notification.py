from apps.bookings.domain.entities import Appointment, Customer
from apps.bookings.domain.tokens import build_management_link
from apps.businesses.domain.entities import Business
from apps.catalog.domain.entities import Service, Staff
from apps.notifications.application.context import MessageContextBuilder
from apps.notifications.domain.messages import (
    MessageRenderer,
    NotificationKind,
)
from apps.notifications.domain.senders import NotificationSender


class NotificationService:
    def __init__(
        self,
        *,
        renderer: MessageRenderer,
        sender: NotificationSender,
        base_url: str,
        context_builder: MessageContextBuilder | None = None,
    ) -> None:
        self._renderer = renderer
        self._sender = sender
        self._base_url = base_url
        self._context_builder = context_builder or MessageContextBuilder()

    def send(
        self,
        kind: NotificationKind,
        *,
        appointment: Appointment,
        customer: Customer,
        service: Service,
        staff: Staff,
        business: Business,
        management_token: str,
    ) -> None:
        context = self._context_builder.build(
            appointment=appointment,
            customer=customer,
            service=service,
            staff=staff,
            business=business,
            management_url=build_management_link(self._base_url, management_token),
        )
        message = self._renderer.render(kind, context)
        self._sender.send(recipient=customer.email, message=message)
