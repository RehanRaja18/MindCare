"""URL routes for the psychologists API, included under /api/v1/psychologists/."""

from django.urls import path

from apps.psychologists.api.views import (
    DirectoryDetailView,
    DirectoryListView,
    MyPsychologistProfileView,
)

app_name = "psychologists"

urlpatterns = [
    path("me/", MyPsychologistProfileView.as_view(), name="me"),
    path("directory/", DirectoryListView.as_view(), name="directory"),
    path("directory/<int:pk>/", DirectoryDetailView.as_view(), name="directory-detail"),
]
