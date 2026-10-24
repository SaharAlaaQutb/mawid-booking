from apps.core.presentation.views import HealthView
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", HealthView.as_view(), name="health"),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[AllowAny]),
        name="openapi-schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="openapi-schema", permission_classes=[AllowAny]),
        name="swagger-ui",
    ),
    path("api/auth/", include("apps.accounts.presentation.urls")),
    path("api/", include("apps.scheduling.presentation.urls")),
]
