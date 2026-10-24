from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.domain.locale import SUPPORTED_LOCALES
from apps.scheduling.application.availability import Availability
from apps.scheduling.container import build_availability_service
from apps.scheduling.domain.errors import (
    BusinessNotConfiguredError,
    DateOutsideHorizonError,
    ServiceNotAvailableError,
    StaffNotAvailableError,
)
from apps.scheduling.presentation.serializers import (
    AvailabilityQueryParamsSerializer,
    AvailabilityQuerySerializer,
    AvailabilityResponseSerializer,
)


class BusinessNotConfigured(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _("No active business is configured.")
    default_code = "business_not_configured"


class ServiceNotAvailable(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _("The requested service is not available.")
    default_code = "service_not_available"


class DateOutsideHorizon(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The requested date is outside the booking horizon.")
    default_code = "date_outside_horizon"


def _response_locale(request: Request) -> str:
    explicit = request.query_params.get("lang")
    if explicit in SUPPORTED_LOCALES:
        return explicit
    language = get_language() or "en"
    return language.split("-", maxsplit=1)[0]


class AvailabilityView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes: tuple[()] = ()

    @extend_schema(
        parameters=[AvailabilityQueryParamsSerializer],
        responses={200: AvailabilityResponseSerializer},
        tags=["availability"],
    )
    def get(self, request: Request) -> Response:
        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data

        try:
            availability: Availability = build_availability_service().find(
                service_id=params["service"],
                on_date=params["date"],
                staff_id=params["staff"],
            )
        except BusinessNotConfiguredError as exc:
            raise BusinessNotConfigured from exc
        except ServiceNotAvailableError as exc:
            raise ServiceNotAvailable from exc
        except StaffNotAvailableError as exc:
            raise ValidationError({"staff": [str(_("Staff member is not available."))]}) from exc
        except DateOutsideHorizonError as exc:
            raise DateOutsideHorizon from exc

        response = Response(
            AvailabilityResponseSerializer(
                availability,
                context={"locale": _response_locale(request)},
            ).data
        )
        response["Cache-Control"] = "no-store"
        return response
