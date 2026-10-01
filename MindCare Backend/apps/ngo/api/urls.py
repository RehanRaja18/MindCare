"""URL routes for the ngo API, included under /api/v1/ngo/."""

from django.urls import path

from apps.ngo.api.views import MyNGOProfileView

app_name = "ngo"

urlpatterns = [
    path("me/", MyNGOProfileView.as_view(), name="me"),
]
