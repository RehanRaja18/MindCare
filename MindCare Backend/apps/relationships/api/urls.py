"""URL routes for the relationships API, included under /api/v1/relationships/."""

from django.urls import path

from apps.relationships.api.views import (
    AcceptRequestView,
    CancelRequestView,
    CurrentRelationshipView,
    DeclineRequestView,
    EndCurrentRelationshipView,
    HistoryView,
    InboxView,
    PatientDetailView,
    PatientEndView,
    PatientListView,
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
    # Psychologist-facing
    path(
        "requests/<int:pk>/accept/", AcceptRequestView.as_view(), name="request-accept"
    ),
    path(
        "requests/<int:pk>/decline/",
        DeclineRequestView.as_view(),
        name="request-decline",
    ),
    path("inbox/", InboxView.as_view(), name="inbox"),
    path("patients/", PatientListView.as_view(), name="patients"),
    path("patients/<int:pk>/", PatientDetailView.as_view(), name="patient-detail"),
    path("patients/<int:pk>/end/", PatientEndView.as_view(), name="patient-end"),
    path("history/", HistoryView.as_view(), name="history"),
]
