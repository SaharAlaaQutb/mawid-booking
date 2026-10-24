from enum import StrEnum


class AppointmentStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


ACTIVE_APPOINTMENT_STATUSES = (
    AppointmentStatus.PENDING.value,
    AppointmentStatus.CONFIRMED.value,
)

APPOINTMENT_STATUS_CHOICES = [
    (status.value, status.value.replace("_", " ").title()) for status in AppointmentStatus
]


class CancelledBy(StrEnum):
    CUSTOMER = "customer"
    STAFF = "staff"


CANCELLED_BY_CHOICES = [(actor.value, actor.value.title()) for actor in CancelledBy]


class ReminderKind(StrEnum):
    CONFIRMATION = "confirmation"
    REMINDER = "reminder"


REMINDER_KIND_CHOICES = [(kind.value, kind.value.title()) for kind in ReminderKind]


class ReminderStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


REMINDER_STATUS_CHOICES = [(status.value, status.value.title()) for status in ReminderStatus]
