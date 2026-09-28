"""DRF views for reference data.

Public (registration forms need them before the user has an account), so
authentication is disabled: an expired token must not turn a dropdown into a
401. Rate-limited per IP.
"""

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.reference import selectors
from apps.reference.api.serializers import (
    CitySerializer,
    CountrySerializer,
    LanguageSerializer,
    SpecializationSerializer,
)


class ReferenceRateThrottle(AnonRateThrottle):
    scope = "reference"


class _PublicReferenceView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ReferenceRateThrottle]


class CountryListView(_PublicReferenceView):
    def get(self, request):
        return Response(CountrySerializer(selectors.list_countries(), many=True).data)


class CityListView(_PublicReferenceView):
    def get(self, request):
        country = request.query_params.get("country")
        if not country:
            raise ValidationError({"country": ["This query parameter is required."]})
        cities = selectors.search_cities(
            country_code=country, search=request.query_params.get("search")
        )
        return Response(CitySerializer(cities, many=True).data)


class LanguageListView(_PublicReferenceView):
    def get(self, request):
        return Response(LanguageSerializer(selectors.list_languages(), many=True).data)


class SpecializationListView(_PublicReferenceView):
    def get(self, request):
        return Response(
            SpecializationSerializer(selectors.list_specializations(), many=True).data
        )
