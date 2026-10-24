from uuid import UUID

from apps.accounts.application.scope import ActorScope
from apps.accounts.presentation.scope import actor_from_request, require_owner
from apps.businesses.container import build_business_repository
from apps.businesses.domain.entities import Business
from apps.catalog.infrastructure.models import Service, Staff
from apps.catalog.presentation.serializers import (
    PublicServiceSerializer,
    PublicStaffSerializer,
    ServiceSerializer,
    StaffSerializer,
)
from apps.core.presentation.locale import response_locale
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, NotAuthenticated, NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class BusinessNotConfigured(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _("No active business is configured.")
    default_code = "business_not_configured"


def _active_business() -> Business:
    business = build_business_repository().get_active()
    if business is None:
        raise BusinessNotConfigured
    return business


def _actor(request: Request) -> ActorScope:
    if not request.user.is_authenticated:
        raise NotAuthenticated
    return actor_from_request(request)


def _service(service_id: UUID, actor: ActorScope) -> Service:
    service = Service.objects.filter(pk=service_id, business_id=actor.business_id).first()
    if service is None:
        raise NotFound(str(_("The service was not found.")))
    return service


def _staff(staff_id: UUID, actor: ActorScope) -> Staff:
    staff = Staff.objects.filter(pk=staff_id, business_id=actor.business_id).first()
    if staff is None:
        raise NotFound(str(_("The staff member was not found.")))
    return staff


def _public_services(business: Business, locale: str) -> list[dict[str, object]]:
    services = Service.objects.filter(business_id=business.id, is_active=True)
    return [
        {
            "id": service.id,
            "name": service.name.for_locale(locale),
            "description": service.description.for_locale(locale),
            "duration_minutes": service.duration_minutes,
            "price_minor": service.price_minor,
            "currency": service.currency,
        }
        for service in services
    ]


class ServiceListView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(responses=PublicServiceSerializer(many=True), tags=["catalog"])
    def get(self, request: Request) -> Response:
        locale = response_locale(request)
        if request.user.is_authenticated:
            actor = actor_from_request(request)
            services = Service.objects.filter(business_id=actor.business_id)
            if not actor.is_owner:
                services = services.filter(is_active=True)
            return Response(ServiceSerializer(services, many=True).data)

        business = _active_business()
        return Response(
            PublicServiceSerializer(
                _public_services(business, locale),
                many=True,
            ).data
        )

    @extend_schema(
        request=ServiceSerializer,
        responses={201: ServiceSerializer},
        tags=["services"],
    )
    def post(self, request: Request) -> Response:
        actor = _actor(request)
        require_owner(actor)
        serializer = ServiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = serializer.save(business_id=actor.business_id)
        return Response(ServiceSerializer(service).data, status=status.HTTP_201_CREATED)


class ServiceDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses=ServiceSerializer, tags=["services"])
    def get(self, request: Request, service_id: UUID) -> Response:
        actor = _actor(request)
        return Response(ServiceSerializer(_service(service_id, actor)).data)

    @extend_schema(
        request=ServiceSerializer,
        responses=ServiceSerializer,
        tags=["services"],
    )
    def patch(self, request: Request, service_id: UUID) -> Response:
        actor = _actor(request)
        require_owner(actor)
        serializer = ServiceSerializer(_service(service_id, actor), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        service = serializer.save()
        return Response(ServiceSerializer(service).data)

    @extend_schema(responses={204: None}, tags=["services"])
    def delete(self, request: Request, service_id: UUID) -> Response:
        actor = _actor(request)
        require_owner(actor)
        service = _service(service_id, actor)
        if service.is_active:
            service.is_active = False
            service.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


def _public_staff(
    business: Business,
    locale: str,
    service_id: UUID | None,
) -> list[dict[str, object]]:
    members = Staff.objects.filter(business_id=business.id, is_active=True)
    if service_id is not None:
        members = members.filter(service_links__service_id=service_id)
    return [
        {
            "id": member.id,
            "name": member.name.for_locale(locale),
            "title": member.title.for_locale(locale),
            "bio": member.bio.for_locale(locale),
            "color": member.color,
        }
        for member in members.distinct()
    ]


class StaffListView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(responses=PublicStaffSerializer(many=True), tags=["catalog"])
    def get(self, request: Request) -> Response:
        locale = response_locale(request)
        service_id = _parse_optional_uuid(request.query_params.get("service"), "service")
        if request.user.is_authenticated:
            actor = actor_from_request(request)
            members = Staff.objects.filter(business_id=actor.business_id)
            if not actor.is_owner:
                members = members.filter(is_active=True)
            if service_id is not None:
                members = members.filter(service_links__service_id=service_id)
            return Response(
                StaffSerializer(
                    members.distinct().prefetch_related("service_links__service"),
                    many=True,
                    context={"business_id": actor.business_id},
                ).data
            )

        business = _active_business()
        return Response(
            PublicStaffSerializer(
                _public_staff(business, locale, service_id),
                many=True,
            ).data
        )

    @extend_schema(
        request=StaffSerializer,
        responses={201: StaffSerializer},
        tags=["staff"],
    )
    def post(self, request: Request) -> Response:
        actor = _actor(request)
        require_owner(actor)
        serializer = StaffSerializer(
            data=request.data,
            context={"business_id": actor.business_id},
        )
        serializer.is_valid(raise_exception=True)
        member = serializer.save(business_id=actor.business_id)
        return Response(
            StaffSerializer(member, context={"business_id": actor.business_id}).data,
            status=status.HTTP_201_CREATED,
        )


class StaffDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses=StaffSerializer, tags=["staff"])
    def get(self, request: Request, staff_id: UUID) -> Response:
        actor = _actor(request)
        member = _staff(staff_id, actor)
        return Response(StaffSerializer(member, context={"business_id": actor.business_id}).data)

    @extend_schema(
        request=StaffSerializer,
        responses=StaffSerializer,
        tags=["staff"],
    )
    def patch(self, request: Request, staff_id: UUID) -> Response:
        actor = _actor(request)
        require_owner(actor)
        serializer = StaffSerializer(
            _staff(staff_id, actor),
            data=request.data,
            partial=True,
            context={"business_id": actor.business_id},
        )
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        return Response(StaffSerializer(member, context={"business_id": actor.business_id}).data)

    @extend_schema(responses={204: None}, tags=["staff"])
    def delete(self, request: Request, staff_id: UUID) -> Response:
        actor = _actor(request)
        require_owner(actor)
        member = _staff(staff_id, actor)
        if member.is_active:
            member.is_active = False
            member.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


def _parse_optional_uuid(value: str | None, field: str) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValidationError({field: [str(_("Use a valid UUID."))]}) from exc
