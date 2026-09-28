"""URL routes for the patients API, included under /api/v1/patients/."""

from django.urls import path

from apps.patients.api.views import MyPatientProfileView

app_name = "patients"

urlpatterns = [
    path("me/", MyPatientProfileView.as_view(), name="me"),
]
