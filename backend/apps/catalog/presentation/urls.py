from apps.catalog.presentation.views import (
    ServiceDetailView,
    ServiceListView,
    StaffDetailView,
    StaffListView,
)
from django.urls import path

urlpatterns = [
    path("services/", ServiceListView.as_view(), name="service-list"),
    path("services/<uuid:service_id>/", ServiceDetailView.as_view(), name="service-detail"),
    path("staff/", StaffListView.as_view(), name="staff-list"),
    path("staff/<uuid:staff_id>/", StaffDetailView.as_view(), name="staff-detail"),
]
