"""URL routes for the AI gateway, included under /api/v1/ai/."""

from django.urls import path

from apps.ai.api.views import AnxietyPredictionView

app_name = "ai"

urlpatterns = [
    path(
        "anxiety-prediction/",
        AnxietyPredictionView.as_view(),
        name="anxiety-prediction",
    ),
]
