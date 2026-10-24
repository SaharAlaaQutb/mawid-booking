from django.urls import path

from apps.scheduling.presentation.views import AvailabilityView

urlpatterns = [
    path("availability/", AvailabilityView.as_view(), name="availability"),
]
