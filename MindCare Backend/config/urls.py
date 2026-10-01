"""
URL configuration for the config project.

Each app's api/urls.py is mounted under /api/v1/<app-name>/.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

API_V1_APPS = [
    "accounts",
    "reference",
    "stats",
    "patients",
    "psychologists",
    "appointments",
    "clinical_notes",
    "journals",
    "recommendations",
    "wearables",
    "reports",
    "payments",
    "notifications",
    "communities",
    "moderation",
    "ngo",
    "rewards",
    "emergency",
]

api_v1_patterns = [
    path(f"{app.replace('_', '-')}/", include(f"apps.{app}.api.urls"))
    for app in API_V1_APPS
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1_patterns)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"
    ),
]
