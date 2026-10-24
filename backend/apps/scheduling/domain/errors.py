class AvailabilityError(Exception):
    code = "availability_error"


class BusinessNotConfiguredError(AvailabilityError):
    code = "business_not_configured"


class ServiceNotAvailableError(AvailabilityError):
    code = "service_not_available"


class StaffNotAvailableError(AvailabilityError):
    code = "staff_not_available"


class DateOutsideHorizonError(AvailabilityError):
    code = "date_outside_horizon"
