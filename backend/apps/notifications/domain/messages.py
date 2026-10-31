from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from apps.bookings.domain.entities import Appointment, Customer
from apps.businesses.domain.entities import Business
from apps.catalog.domain.entities import Service, Staff


class NotificationKind(StrEnum):
    CONFIRMATION = "confirmation"
    REMINDER = "reminder"
    CANCELLATION = "cancellation"
    RESCHEDULE = "reschedule"


@dataclass(frozen=True, slots=True)
class MessageContext:
    appointment: Appointment
    customer: Customer
    service: Service
    staff: Staff
    business: Business
    management_url: str
    language: str


@dataclass(frozen=True, slots=True)
class RenderedMessage:
    subject: str
    text_body: str
    html_body: str


class MessageRenderer(Protocol):
    def render(self, kind: NotificationKind, context: MessageContext) -> RenderedMessage: ...
