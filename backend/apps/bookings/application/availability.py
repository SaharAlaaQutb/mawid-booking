from datetime import UTC, date, datetime
from uuid import UUID

from apps.bookings.application.errors import (
    BusinessNotConfiguredError,
    ServiceNotAvailableError,
    SlotUnavailableError,
    StaffNotAvailableError,
)
from apps.scheduling.application.availability import (
    Availability,
    AvailabilityService,
    AvailabilitySlot,
)
from apps.scheduling.domain.errors import (
    BusinessNotConfiguredError as SchedulingBusinessNotConfiguredError,
)
from apps.scheduling.domain.errors import (
    DateOutsideHorizonError,
)
from apps.scheduling.domain.errors import (
    ServiceNotAvailableError as SchedulingServiceNotAvailableError,
)
from apps.scheduling.domain.errors import (
    StaffNotAvailableError as SchedulingStaffNotAvailableError,
)


class AvailabilityGateway:
    def __init__(self, service: AvailabilityService) -> None:
        self._service = service

    def choose_staff(
        self,
        *,
        service_id: UUID,
        on_date: date,
        starts_at: datetime,
    ) -> UUID:
        slot = self._matching_slot(
            self._find(service_id=service_id, staff_id=None, on_date=on_date),
            starts_at,
        )
        if slot is None:
            raise SlotUnavailableError("The requested start time is not available.")
        return slot.recommended_staff_id

    def find_slot(
        self,
        *,
        service_id: UUID,
        staff_id: UUID,
        on_date: date,
        starts_at: datetime,
    ) -> AvailabilitySlot:
        slot = self._matching_slot(
            self._find(service_id=service_id, staff_id=staff_id, on_date=on_date),
            starts_at,
        )
        if slot is None:
            raise SlotUnavailableError("The requested start time is not available.")
        return slot

    def _find(
        self,
        *,
        service_id: UUID,
        staff_id: UUID | None,
        on_date: date,
    ) -> Availability:
        try:
            return self._service.find(
                service_id=service_id,
                on_date=on_date,
                staff_id=staff_id,
            )
        except SchedulingBusinessNotConfiguredError as exc:
            raise BusinessNotConfiguredError("No active business is configured.") from exc
        except SchedulingServiceNotAvailableError as exc:
            raise ServiceNotAvailableError("The requested service is not available.") from exc
        except SchedulingStaffNotAvailableError as exc:
            raise StaffNotAvailableError("The requested staff member is not available.") from exc
        except DateOutsideHorizonError as exc:
            raise SlotUnavailableError("The requested start time is not available.") from exc

    def _matching_slot(
        self,
        availability: Availability,
        starts_at: datetime,
    ) -> AvailabilitySlot | None:
        instant = starts_at.astimezone(UTC)
        return next(
            (
                candidate
                for candidate in availability.slots
                if candidate.starts_at.astimezone(UTC) == instant
            ),
            None,
        )
