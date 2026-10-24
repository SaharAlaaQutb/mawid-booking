from django.urls import path

from apps.accounts.presentation.views import LoginView, LogoutView, MeView, RefreshView

urlpatterns = [
    path("token/", LoginView.as_view(), name="token-obtain-pair"),
    path("refresh/", RefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
]
