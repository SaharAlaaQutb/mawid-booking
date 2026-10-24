from datetime import datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.presentation.scope import actor_from_request
from apps.bookings.application.calendar import CalendarResult
from apps.bookings.application.errors import (
    AppointmentAccessDeniedError,
    AppointmentNotFoundError,
    CalendarRangeError,
    StaffNotAvailableError,
)
from apps.bookings.container import (
    build_calendar_service,
    build_staff_appointment_service,
)
from apps.bookings.domain.transitions import InvalidStatusTransitionError
from apps.bookings.presentation.serializers import AppointmentResponseSerializer
from apps.bookings.presentation.staff_serializers import (
    AppointmentStatusUpdateSerializer,
    CalendarQuerySerializer,
    CalendarResponseSerializer,
)
from apps.bookings.presentation.views import appointment_payload
from apps.core.presentation.locale import response_locale


class AppointmentNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _("The appointment was not found.")
    default_code = "appointment_not_found"


class InvalidTransition(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("This status change is not allowed.")
    default_code = "invalid_transition"


class CalendarRangeInvalid(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The requested calendar range is invalid.")
    default_code = "invalid_range"


class CalendarStaffUnavailable(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _("The requested staff member is not available.")
    default_code = "staff_not_available"


class StaffAppointmentStatusView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        request=AppointmentStatusUpdateSerializer,
        responses={200: AppointmentResponseSerializer},
        tags=["staff appointments"],
    )
    def patch(self, request: Request, appointment_id: UUID) -> Response:
        actor = actor_from_request(request)
        serializer = AppointmentStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = build_staff_appointment_service().update_status(
                appointment_id,
                actor=actor,
                target=serializer.validated_data["status"],
                reason=serializer.validated_data.get("reason", ""),
            )
        except AppointmentNotFoundError as exc:
            raise AppointmentNotFound from exc
        except AppointmentAccessDeniedError as exc:
            raise PermissionDenied(str(_("You cannot change this appointment."))) from exc
        except InvalidStatusTransitionError as exc:
            raise InvalidTransition from exc

        response = Response(
            appointment_payload(
                booking,
                locale=response_locale(request),
                management_url=None,
            )
        )
        response["Cache-Control"] = "no-store"
        return response


def _iso(value: datetime, timezone: ZoneInfo) -> str:
    return value.astimezone(timezone).isoformat()


def _calendar_payload(result: CalendarResult, *, locale: str) -> dict[str, Any]:
    local_timezone = ZoneInfo(result.timezone)
    return {
        "from": result.starts_on.isoformat(),
        "to": result.ends_on.isoformat(),
        "timezone": result.timezone,
        "staff": [
            {
                "id": str(calendar.staff.id),
                "name": calendar.staff.name.for_locale(locale),
                "color": calendar.staff.color,
                "appointments": [
                    {
                        "id": str(entry.appointment.id),
                        "starts_at": _iso(entry.appointment.starts_at, local_timezone),
                        "ends_at": _iso(entry.appointment.ends_at, local_timezone),
                        "status": entry.appointment.status.value,
                        "service": {
                            "id": str(entry.service.id),
                            "name": entry.service.name.for_locale(locale),
                            "duration_minutes": entry.service.duration_minutes,
                            "price_minor": entry.service.price_minor,
                            "currency": entry.service.currency,
                        },
                        "customer": {
                            "name": entry.customer.name,
                            "email": entry.customer.email,
                            "phone": entry.customer.phone,
                        },
                        "notes": entry.appointment.notes,
                    }
                    for entry in calendar.appointments
                ],
            }
            for calendar in result.staff
        ],
    }


class CalendarView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[CalendarQuerySerializer],
        responses={200: CalendarResponseSerializer},
        tags=["staff calendar"],
    )
    def get(self, request: Request) -> Response:
        actor = actor_from_request(request)
        serializer = CalendarQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        try:
            result = build_calendar_service().for_actor(
                actor=actor,
                starts_on=params["starts_on"],
                ends_on=params["ends_on"],
                staff_id=params.get("staff"),
            )
        except CalendarRangeError as exc:
            raise CalendarRangeInvalid from exc
        except StaffNotAvailableError as exc:
            raise CalendarStaffUnavailable from exc
        except AppointmentAccessDeniedError as exc:
            raise PermissionDenied(
                str(_("Calendar access is limited to your own schedule."))
            ) from exc

        response = Response(
            _calendar_payload(result, locale=response_locale(request)),
        )
        response["Cache-Control"] = "no-store"
        return response
