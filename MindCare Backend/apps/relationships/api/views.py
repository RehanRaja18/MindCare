"""DRF views for the relationships API. Thin: parse -> service/selector -> serialize."""

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.psychologists.api.serializers import DirectoryCardSerializer
from apps.relationships import selectors, services
from apps.relationships.api.serializers import (
    PatientEndSerializer,
    RelationshipPatientViewSerializer,
    RequestCreateSerializer,
)
from core.exceptions import DomainValidationError
from core.pagination import StandardPagination
from core.permissions import IsPatient


def _domain(callable_, **kwargs):
    try:
        return callable_(**kwargs)
    except DomainValidationError as exc:
        raise ValidationError(exc.errors, code=exc.code) from exc


class RelationshipRequestRateThrottle(UserRateThrottle):
    scope = "relationship_requests"


class RequestListCreateView(APIView):
    """GET: the patient's request history (the App's history screen).
    POST: send a request. Only POST is throttled."""

    permission_classes = [IsAuthenticated, IsPatient]

    def get_throttles(self):
        if self.request.method == "POST":
            return [RelationshipRequestRateThrottle()]
        return []

    @extend_schema(responses=RelationshipPatientViewSerializer(many=True))
    def get(self, request):
        paginator = StandardPagination()
        page = paginator.paginate_queryset(
            selectors.patient_requests(patient_user=request.user), request, view=self
        )
        return paginator.get_paginated_response(
            RelationshipPatientViewSerializer(page, many=True).data
        )

    @extend_schema(
        request=RequestCreateSerializer,
        responses={201: RelationshipPatientViewSerializer},
    )
    def post(self, request):
        body = RequestCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        rel = _domain(
            services.request_psychologist,
            patient_user=request.user,
            psychologist_id=body.validated_data["psychologist"],
        )
        return Response(
            RelationshipPatientViewSerializer(rel).data, status=status.HTTP_201_CREATED
        )


class CancelRequestView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @extend_schema(request=None, responses=RelationshipPatientViewSerializer)
    def post(self, request, pk):
        rel = _domain(
            services.cancel_request, patient_user=request.user, relationship_id=pk
        )
        return Response(RelationshipPatientViewSerializer(rel).data)


class CurrentRelationshipView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @extend_schema(
        responses=inline_serializer(
            "CurrentRelationship",
            {"relationship": RelationshipPatientViewSerializer(allow_null=True)},
        )
    )
    def get(self, request):
        rel = selectors.patient_current(patient_user=request.user)
        data = RelationshipPatientViewSerializer(rel).data if rel else None
        return Response({"relationship": data})


class EndCurrentRelationshipView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @extend_schema(
        request=PatientEndSerializer, responses=RelationshipPatientViewSerializer
    )
    def post(self, request):
        body = PatientEndSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        rel = _domain(
            services.patient_end_relationship, patient_user=request.user, confirm=True
        )
        return Response(RelationshipPatientViewSerializer(rel).data)


class RecentPsychologistsView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @extend_schema(responses=DirectoryCardSerializer(many=True))
    def get(self, request):
        cards = selectors.recent_psychologists(patient_user=request.user)
        return Response(DirectoryCardSerializer(cards, many=True).data)
