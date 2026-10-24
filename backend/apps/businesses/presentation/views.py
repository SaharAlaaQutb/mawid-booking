from apps.accounts.presentation.scope import actor_from_request, require_owner
from apps.businesses.container import build_business_repository
from apps.businesses.infrastructure.models import Business
from apps.businesses.presentation.serializers import (
    BusinessSettingsSerializer,
    PublicBusinessSerializer,
)
from apps.core.presentation.locale import response_locale
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


def _business_for_request(request: Request) -> Business:
    actor = actor_from_request(request)
    business = Business.objects.filter(pk=actor.business_id).first()
    if business is None:
        raise NotFound(str(_("The business was not found.")))
    return business


class PublicBusinessView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(responses=PublicBusinessSerializer, tags=["business"])
    def get(self, request: Request) -> Response:
        business = build_business_repository().get_active()
        if business is None:
            raise NotFound(str(_("No active business is configured.")))
        locale = response_locale(request)
        return Response(
            PublicBusinessSerializer(
                {
                    "id": business.id,
                    "slug": business.slug,
                    "name": business.name.for_locale(locale),
                    "address": business.address.for_locale(locale),
                    "timezone": business.timezone,
                    "default_locale": business.default_locale,
                    "currency": business.currency,
                    "phone": business.phone,
                }
            ).data
        )


class SettingsView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses=BusinessSettingsSerializer, tags=["settings"])
    def get(self, request: Request) -> Response:
        business = _business_for_request(request)
        return Response(BusinessSettingsSerializer(business).data)

    @extend_schema(
        request=BusinessSettingsSerializer,
        responses=BusinessSettingsSerializer,
        tags=["settings"],
    )
    def patch(self, request: Request) -> Response:
        actor = actor_from_request(request)
        require_owner(actor)
        business = Business.objects.filter(pk=actor.business_id).first()
        if business is None:
            raise NotFound(str(_("The business was not found.")))
        serializer = BusinessSettingsSerializer(business, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
