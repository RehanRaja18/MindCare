"""DRF views for the AI gateway. Thin: parse -> service -> respond."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.ai import services
from apps.ai.api.serializers import (
    AnxietyPredictionRequestSerializer,
    AnxietyPredictionResponseSerializer,
    DetailSerializer,
)
from core.permissions import IsApprovedPsychologist, IsPsychologist

WAKING_UP = "The AI service is waking up. Please try again in a minute."


class AIPredictionRateThrottle(UserRateThrottle):
    scope = "ai_prediction"


class AnxietyPredictionView(APIView):
    """Decision support for an approved psychologist: forwards the entered
    features to the AI service and returns its anxiety-risk prediction. Never
    patient-facing; nothing is stored."""

    permission_classes = [IsAuthenticated, IsPsychologist, IsApprovedPsychologist]
    throttle_classes = [AIPredictionRateThrottle]

    @extend_schema(
        request=AnxietyPredictionRequestSerializer,
        responses={
            200: AnxietyPredictionResponseSerializer,
            400: OpenApiResponse(
                description="Invalid input, or the AI service rejected it "
                "(e.g. age outside 18-49): {detail}."
            ),
            403: OpenApiResponse(description="Not an approved, active psychologist."),
            503: OpenApiResponse(
                DetailSerializer,
                description="The AI service is asleep or unreachable; retry shortly.",
            ),
        },
    )
    def post(self, request):
        body = AnxietyPredictionRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            result = services.predict_anxiety_risk(features=body.validated_data)
        except services.AIPredictionRejected as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        except services.AIServiceUnavailable:
            return Response(
                {"detail": WAKING_UP}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        return Response(result)
