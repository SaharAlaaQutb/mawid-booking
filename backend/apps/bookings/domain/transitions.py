from apps.bookings.domain.status import AppointmentStatus


class InvalidStatusTransitionError(ValueError):
    def __init__(self, current: AppointmentStatus, target: AppointmentStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition appointment from {current.value} to {target.value}.")


ALLOWED_TRANSITIONS: dict[AppointmentStatus, frozenset[AppointmentStatus]] = {
    AppointmentStatus.PENDING: frozenset(
        {
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.CANCELLED,
            AppointmentStatus.NO_SHOW,
        }
    ),
    AppointmentStatus.CONFIRMED: frozenset(
        {
            AppointmentStatus.COMPLETED,
            AppointmentStatus.CANCELLED,
            AppointmentStatus.NO_SHOW,
        }
    ),
    AppointmentStatus.COMPLETED: frozenset(),
    AppointmentStatus.CANCELLED: frozenset(),
    AppointmentStatus.NO_SHOW: frozenset(),
}


def can_transition(current: AppointmentStatus, target: AppointmentStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def ensure_transition(current: AppointmentStatus, target: AppointmentStatus) -> None:
    if not can_transition(current, target):
        raise InvalidStatusTransitionError(current, target)
