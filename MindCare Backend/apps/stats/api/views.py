"""DRF views for the stats API. Thin: selector -> serializer."""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.stats import selectors
from apps.stats.api.serializers import PublicStatsSerializer


class PublicStatsRateThrottle(AnonRateThrottle):
    scope = "public_stats"


class PublicStatsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PublicStatsRateThrottle]

    def get(self, request):
        return Response(
            PublicStatsSerializer(selectors.get_public_platform_stats()).data
        )
