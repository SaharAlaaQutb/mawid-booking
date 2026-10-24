from django.urls import path

from apps.bookings.presentation.staff_views import StaffAppointmentStatusView
from apps.bookings.presentation.views import (
    AppointmentCancelView,
    AppointmentCreateView,
    AppointmentManageView,
    AppointmentRescheduleView,
)

urlpatterns = [
    path("", AppointmentCreateView.as_view(), name="appointment-create"),
    path("manage/<str:token>/", AppointmentManageView.as_view(), name="appointment-manage"),
    path(
        "manage/<str:token>/cancel",
        AppointmentCancelView.as_view(),
        name="appointment-cancel",
    ),
    path(
        "manage/<str:token>/reschedule",
        AppointmentRescheduleView.as_view(),
        name="appointment-reschedule",
    ),
    path(
        "<uuid:appointment_id>/status/",
        StaffAppointmentStatusView.as_view(),
        name="appointment-status",
    ),
]
