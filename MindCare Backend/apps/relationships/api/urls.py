"""URL routes for the relationships API, included under /api/v1/relationships/."""

from django.urls import path

from apps.relationships.api.views import (
    CancelRequestView,
    CurrentRelationshipView,
    EndCurrentRelationshipView,
    RecentPsychologistsView,
    RequestListCreateView,
)

app_name = "relationships"

urlpatterns = [
    path("requests/", RequestListCreateView.as_view(), name="requests"),
    path(
        "requests/<int:pk>/cancel/", CancelRequestView.as_view(), name="request-cancel"
    ),
    path("current/", CurrentRelationshipView.as_view(), name="current"),
    path("current/end/", EndCurrentRelationshipView.as_view(), name="current-end"),
    path("recent/", RecentPsychologistsView.as_view(), name="recent"),
]
