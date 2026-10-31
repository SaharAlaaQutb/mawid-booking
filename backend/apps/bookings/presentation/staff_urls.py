from django.urls import path

from apps.bookings.presentation.staff_views import CalendarView

urlpatterns = [
    path("calendar/", CalendarView.as_view(), name="staff-calendar"),
]
