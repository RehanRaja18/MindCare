"""DRF views for reference data.

Public (registration forms need them before the user has an account), so
authentication is disabled: an expired token must not turn a dropdown into a
401. Rate-limited per IP.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.reference import selectors
from apps.reference.api.serializers import (
    CityQuerySerializer,
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
    @extend_schema(responses=CountrySerializer(many=True))
    def get(self, request):
        return Response(CountrySerializer(selectors.list_countries(), many=True).data)


class CityListView(_PublicReferenceView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "country",
                OpenApiTypes.STR,
                required=True,
                description="ISO 3166-1 alpha-2 country code, e.g. PK.",
            ),
            OpenApiParameter(
                "search",
                OpenApiTypes.STR,
                required=False,
                description="Case-insensitive name filter.",
            ),
        ],
        responses=CitySerializer(many=True),
    )
    def get(self, request):
        query = CityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        cities = selectors.search_cities(
            country_code=query.validated_data["country"],
            search=query.validated_data.get("search"),
        )
        return Response(CitySerializer(cities, many=True).data)


class LanguageListView(_PublicReferenceView):
    @extend_schema(responses=LanguageSerializer(many=True))
    def get(self, request):
        return Response(LanguageSerializer(selectors.list_languages(), many=True).data)


class SpecializationListView(_PublicReferenceView):
    @extend_schema(responses=SpecializationSerializer(many=True))
    def get(self, request):
        return Response(
            SpecializationSerializer(selectors.list_specializations(), many=True).data
        )
