from uuid import UUID

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.application.scope import ActorScope
from apps.accounts.presentation.scope import actor_from_request, require_owner
from apps.catalog.infrastructure.models import Staff
from apps.scheduling.infrastructure.models import TimeOff, WorkingHours
from apps.scheduling.presentation.staff_serializers import (
    TimeOffSerializer,
    WorkingHoursSerializer,
    parse_staff_filter,
)


def _staff_filter(request: Request, actor: ActorScope) -> UUID | None:
    requested = parse_staff_filter(request.query_params.get("staff"))
    if requested is None:
        return None if actor.is_owner else actor.staff.id
    member = Staff.objects.filter(pk=requested, business_id=actor.business_id).first()
    if member is None:
        raise NotFound(str(_("The staff member was not found.")))
    if not actor.is_owner and member.id != actor.staff.id:
        raise PermissionDenied(str(_("You can only access your own schedule.")))
    return member.id


def _working_hours(hours_id: UUID, actor: ActorScope) -> WorkingHours:
    hours = WorkingHours.objects.filter(
        pk=hours_id,
        staff__business_id=actor.business_id,
    ).first()
    if hours is None:
        raise NotFound(str(_("The working hours entry was not found.")))
    if not actor.is_owner and hours.staff_id != actor.staff.id:
        raise PermissionDenied(str(_("You can only access your own schedule.")))
    return hours


def _time_off(time_off_id: UUID, actor: ActorScope) -> TimeOff:
    entry = TimeOff.objects.filter(
        pk=time_off_id,
        staff__business_id=actor.business_id,
    ).first()
    if entry is None:
        raise NotFound(str(_("The time off entry was not found.")))
    if not actor.is_owner and entry.staff_id != actor.staff.id:
        raise PermissionDenied(str(_("You can only access your own schedule.")))
    return entry


class WorkingHoursListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses=WorkingHoursSerializer(many=True), tags=["working hours"])
    def get(self, request: Request) -> Response:
        actor = actor_from_request(request)
        staff_id = _staff_filter(request, actor)
        hours = WorkingHours.objects.filter(staff__business_id=actor.business_id)
        if staff_id is not None:
            hours = hours.filter(staff_id=staff_id)
        elif not actor.is_owner:
            hours = hours.filter(staff_id=actor.staff.id)
        return Response(WorkingHoursSerializer(hours, many=True).data)

    @extend_schema(
        request=WorkingHoursSerializer,
        responses={201: WorkingHoursSerializer},
        tags=["working hours"],
    )
    def post(self, request: Request) -> Response:
        actor = actor_from_request(request)
        require_owner(actor)
        serializer = WorkingHoursSerializer(
            data=request.data,
            context={"business_id": actor.business_id},
        )
        serializer.is_valid(raise_exception=True)
        hours = serializer.save()
        return Response(
            WorkingHoursSerializer(hours).data,
            status=status.HTTP_201_CREATED,
        )


class WorkingHoursDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses=WorkingHoursSerializer, tags=["working hours"])
    def get(self, request: Request, hours_id: UUID) -> Response:
        actor = actor_from_request(request)
        return Response(WorkingHoursSerializer(_working_hours(hours_id, actor)).data)

    @extend_schema(
        request=WorkingHoursSerializer,
        responses=WorkingHoursSerializer,
        tags=["working hours"],
    )
    def patch(self, request: Request, hours_id: UUID) -> Response:
        actor = actor_from_request(request)
        require_owner(actor)
        serializer = WorkingHoursSerializer(
            _working_hours(hours_id, actor),
            data=request.data,
            partial=True,
            context={"business_id": actor.business_id},
        )
        serializer.is_valid(raise_exception=True)
        hours = serializer.save()
        return Response(WorkingHoursSerializer(hours).data)

    @extend_schema(responses={204: None}, tags=["working hours"])
    def delete(self, request: Request, hours_id: UUID) -> Response:
        actor = actor_from_request(request)
        require_owner(actor)
        _working_hours(hours_id, actor).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TimeOffListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses=TimeOffSerializer(many=True), tags=["time off"])
    def get(self, request: Request) -> Response:
        actor = actor_from_request(request)
        staff_id = _staff_filter(request, actor)
        entries = TimeOff.objects.filter(staff__business_id=actor.business_id)
        if staff_id is not None:
            entries = entries.filter(staff_id=staff_id)
        elif not actor.is_owner:
            entries = entries.filter(staff_id=actor.staff.id)
        return Response(TimeOffSerializer(entries, many=True).data)

    @extend_schema(
        request=TimeOffSerializer,
        responses={201: TimeOffSerializer},
        tags=["time off"],
    )
    def post(self, request: Request) -> Response:
        actor = actor_from_request(request)
        require_owner(actor)
        serializer = TimeOffSerializer(
            data=request.data,
            context={"business_id": actor.business_id},
        )
        serializer.is_valid(raise_exception=True)
        entry = serializer.save(created_by=request.user)
        return Response(TimeOffSerializer(entry).data, status=status.HTTP_201_CREATED)


class TimeOffDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses=TimeOffSerializer, tags=["time off"])
    def get(self, request: Request, time_off_id: UUID) -> Response:
        actor = actor_from_request(request)
        return Response(TimeOffSerializer(_time_off(time_off_id, actor)).data)

    @extend_schema(
        request=TimeOffSerializer,
        responses=TimeOffSerializer,
        tags=["time off"],
    )
    def patch(self, request: Request, time_off_id: UUID) -> Response:
        actor = actor_from_request(request)
        require_owner(actor)
        serializer = TimeOffSerializer(
            _time_off(time_off_id, actor),
            data=request.data,
            partial=True,
            context={"business_id": actor.business_id},
        )
        serializer.is_valid(raise_exception=True)
        entry = serializer.save()
        return Response(TimeOffSerializer(entry).data)

    @extend_schema(responses={204: None}, tags=["time off"])
    def delete(self, request: Request, time_off_id: UUID) -> Response:
        actor = actor_from_request(request)
        require_owner(actor)
        _time_off(time_off_id, actor).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
