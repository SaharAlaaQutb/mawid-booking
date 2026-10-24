class AppointmentConflictError(ValueError):
    """Raised when the database rejects an overlapping or duplicate appointment."""
