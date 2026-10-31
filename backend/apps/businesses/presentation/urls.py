from apps.businesses.presentation.views import PublicBusinessView, SettingsView
from django.urls import path

urlpatterns = [
    path("business/", PublicBusinessView.as_view(), name="business-profile"),
    path("settings/", SettingsView.as_view(), name="business-settings"),
]
