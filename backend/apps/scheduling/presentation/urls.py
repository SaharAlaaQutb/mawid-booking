from django.urls import path

from apps.scheduling.presentation.staff_views import (
    TimeOffDetailView,
    TimeOffListView,
    WorkingHoursDetailView,
    WorkingHoursListView,
)
from apps.scheduling.presentation.views import AvailabilityView

urlpatterns = [
    path("availability/", AvailabilityView.as_view(), name="availability"),
    path("working-hours/", WorkingHoursListView.as_view(), name="working-hours-list"),
    path(
        "working-hours/<uuid:hours_id>/",
        WorkingHoursDetailView.as_view(),
        name="working-hours-detail",
    ),
    path("time-off/", TimeOffListView.as_view(), name="time-off-list"),
    path("time-off/<uuid:time_off_id>/", TimeOffDetailView.as_view(), name="time-off-detail"),
]
