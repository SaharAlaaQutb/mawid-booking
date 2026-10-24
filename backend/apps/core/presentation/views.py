from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.container import build_health_service


class HealthView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes: tuple[()] = ()

    @extend_schema(
        responses={
            200: OpenApiResponse(description="All dependencies are healthy."),
            503: OpenApiResponse(description="One or more dependencies are unavailable."),
        },
        tags=["system"],
    )
    def get(self, request: Request) -> Response:
        report = build_health_service().check()
        http_status = (
            status.HTTP_200_OK if report.status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(report.as_dict(), status=http_status)
