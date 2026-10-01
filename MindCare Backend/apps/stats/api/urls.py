"""URL routes for the stats API, included under /api/v1/stats/."""

from django.urls import path

from apps.stats.api.views import PublicStatsView

app_name = "stats"

urlpatterns = [
    path("public/", PublicStatsView.as_view(), name="public"),
]
