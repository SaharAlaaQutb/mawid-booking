class BookingError(ValueError):
    pass


class BusinessNotConfiguredError(BookingError):
    pass


class ServiceNotAvailableError(BookingError):
    pass


class StaffNotAvailableError(BookingError):
    pass


class SlotUnavailableError(BookingError):
    pass


class SlotTakenError(BookingError):
    pass


class CancellationNotAllowedError(BookingError):
    pass


class ManagementTokenInvalidError(BookingError):
    pass


class IdempotencyConflictError(BookingError):
    pass


class AppointmentNotFoundError(BookingError):
    pass


class AppointmentAccessDeniedError(BookingError):
    pass


class CalendarRangeError(BookingError):
    pass
