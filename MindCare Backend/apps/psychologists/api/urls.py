"""URL routes for the psychologists API, included under /api/v1/psychologists/."""

from django.urls import path

from apps.psychologists.api.views import MyPsychologistProfileView

app_name = "psychologists"

urlpatterns = [
    path("me/", MyPsychologistProfileView.as_view(), name="me"),
]
