"""URL routes for the psychologists API, included under /api/v1/psychologists/."""

from django.urls import path

from apps.psychologists.api.views import (
    AvailabilityView,
    DirectoryDetailView,
    DirectoryListView,
    MyPsychologistProfileView,
)

app_name = "psychologists"

urlpatterns = [
    path("me/", MyPsychologistProfileView.as_view(), name="me"),
    path("me/availability/", AvailabilityView.as_view(), name="availability"),
    path("directory/", DirectoryListView.as_view(), name="directory"),
    path("directory/<int:pk>/", DirectoryDetailView.as_view(), name="directory-detail"),
]
