from typing import Any
from zoneinfo import ZoneInfo

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.bookings.application.booking import BookingResult
from apps.bookings.application.errors import (
    BusinessNotConfiguredError,
    CancellationNotAllowedError,
    IdempotencyConflictError,
    ManagementTokenInvalidError,
    ServiceNotAvailableError,
    SlotTakenError,
    SlotUnavailableError,
    StaffNotAvailableError,
)
from apps.bookings.application.management import ManagedBooking
from apps.bookings.container import build_booking_service, build_management_service
from apps.bookings.presentation.serializers import (
    AppointmentCancelSerializer,
    AppointmentCreateSerializer,
    AppointmentRescheduleSerializer,
    AppointmentResponseSerializer,
)
from apps.core.presentation.locale import response_locale


class BusinessNotConfigured(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _("No active business is configured.")
    default_code = "business_not_configured"


class ServiceNotAvailable(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _("The requested service is not available.")
    default_code = "service_not_available"


class StaffNotAvailable(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = _("The requested staff member is not available.")
    default_code = "staff_not_available"


class SlotUnavailable(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = _("The requested time is not available.")
    default_code = "slot_unavailable"


class SlotTaken(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("This slot was just taken. Choose another time.")
    default_code = "slot_taken"


class IdempotencyConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("This idempotency key was already used for a different booking.")
    default_code = "idempotency_conflict"


class ManagementLinkInvalid(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _("This management link is invalid or has expired.")
    default_code = "management_link_invalid"


class CancellationNotAllowed(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("This appointment can no longer be cancelled online.")
    default_code = "cancellation_not_allowed"


def _management_url(request: Request, token: str) -> str:
    return request.build_absolute_uri(reverse("appointment-manage", kwargs={"token": token}))


def appointment_payload(
    booking: BookingResult | ManagedBooking,
    *,
    locale: str,
    management_url: str | None,
) -> dict[str, Any]:
    appointment = booking.appointment
    service = booking.service
    staff = booking.staff
    business = booking.business
    customer = booking.customer
    local_timezone = ZoneInfo(business.timezone)
    return dict(
        AppointmentResponseSerializer(
            {
                "id": appointment.id,
                "status": appointment.status.value,
                "starts_at": appointment.starts_at.astimezone(local_timezone),
                "ends_at": appointment.ends_at.astimezone(local_timezone),
                "service": {
                    "id": service.id,
                    "name": service.name.for_locale(locale),
                    "duration_minutes": service.duration_minutes,
                    "price_minor": service.price_minor,
                    "currency": service.currency,
                },
                "staff": {
                    "id": staff.id,
                    "name": staff.name,
                    "color": staff.color,
                },
                "customer": {
                    "name": customer.name,
                    "email": customer.email,
                    "phone": customer.phone,
                },
                "business": {
                    "name": business.name.for_locale(locale),
                    "timezone": business.timezone,
                },
                "management_url": management_url,
                "rescheduled_from_id": appointment.rescheduled_from_id,
                "cancelled_at": (
                    appointment.cancelled_at.astimezone(local_timezone)
                    if appointment.cancelled_at is not None
                    else None
                ),
                "cancelled_by": appointment.cancelled_by,
                "cancellation_reason": appointment.cancellation_reason,
            }
        ).data
    )


class AppointmentCreateView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes: tuple[()] = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "booking"

    @extend_schema(
        request=AppointmentCreateSerializer,
        responses={201: AppointmentResponseSerializer},
        tags=["appointments"],
    )
    def post(self, request: Request) -> Response:
        serializer = AppointmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        locale = params.get("language") or response_locale(request)

        try:
            result = build_booking_service().create(
                service_id=params["service"],
                staff_id=params.get("staff"),
                starts_at=params["starts_at"],
                customer_name=params["customer_name"],
                customer_email=params["customer_email"],
                customer_phone=params.get("customer_phone", ""),
                customer_language=locale,
                notes=params.get("notes", ""),
                idempotency_key=request.headers.get("Idempotency-Key"),
            )
        except BusinessNotConfiguredError as exc:
            raise BusinessNotConfigured from exc
        except ServiceNotAvailableError as exc:
            raise ServiceNotAvailable from exc
        except StaffNotAvailableError as exc:
            raise StaffNotAvailable from exc
        except SlotUnavailableError as exc:
            raise SlotUnavailable from exc
        except SlotTakenError as exc:
            raise SlotTaken from exc
        except IdempotencyConflictError as exc:
            raise IdempotencyConflict from exc
        except ValueError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]}) from exc

        response = Response(
            appointment_payload(
                result,
                locale=locale,
                management_url=_management_url(request, result.management_token),
            ),
            status=status.HTTP_201_CREATED,
        )
        response["Cache-Control"] = "no-store"
        return response


class AppointmentManageView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes: tuple[()] = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "booking"

    @extend_schema(responses={200: AppointmentResponseSerializer}, tags=["appointments"])
    def get(self, request: Request, token: str) -> Response:
        try:
            booking = build_management_service().get(token)
        except ManagementTokenInvalidError as exc:
            raise ManagementLinkInvalid from exc

        response = Response(
            appointment_payload(
                booking,
                locale=response_locale(request),
                management_url=_management_url(request, token),
            )
        )
        response["Cache-Control"] = "no-store"
        return response


class AppointmentCancelView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes: tuple[()] = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "booking"

    @extend_schema(
        request=AppointmentCancelSerializer,
        responses={200: AppointmentResponseSerializer},
        tags=["appointments"],
    )
    def post(self, request: Request, token: str) -> Response:
        serializer = AppointmentCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = build_management_service().cancel(
                token,
                reason=serializer.validated_data.get("reason", ""),
            )
        except ManagementTokenInvalidError as exc:
            raise ManagementLinkInvalid from exc
        except CancellationNotAllowedError as exc:
            raise CancellationNotAllowed from exc

        response = Response(
            appointment_payload(
                booking,
                locale=response_locale(request),
                management_url=None,
            )
        )
        response["Cache-Control"] = "no-store"
        return response


class AppointmentRescheduleView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes: tuple[()] = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "booking"

    @extend_schema(
        request=AppointmentRescheduleSerializer,
        responses={200: AppointmentResponseSerializer},
        tags=["appointments"],
    )
    def post(self, request: Request, token: str) -> Response:
        serializer = AppointmentRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = build_management_service().reschedule(
                token,
                starts_at=serializer.validated_data["starts_at"],
            )
        except ManagementTokenInvalidError as exc:
            raise ManagementLinkInvalid from exc
        except CancellationNotAllowedError as exc:
            raise CancellationNotAllowed from exc
        except StaffNotAvailableError as exc:
            raise StaffNotAvailable from exc
        except SlotUnavailableError as exc:
            raise SlotUnavailable from exc
        except SlotTakenError as exc:
            raise SlotTaken from exc

        response = Response(
            appointment_payload(
                result,
                locale=response_locale(request),
                management_url=_management_url(request, result.management_token),
            )
        )
        response["Cache-Control"] = "no-store"
        return response
