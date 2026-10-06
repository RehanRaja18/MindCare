"""DRF views for the psychologists API.

Views stay thin: parse the request, delegate to services.py (writes) or
selectors.py (reads), then serialize the result. No business logic here.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.psychologists import selectors, services
from apps.psychologists.api.serializers import (
    DirectoryCardSerializer,
    DirectoryQuerySerializer,
    PsychologistProfileOwnerSerializer,
    PsychologistRegistrationProfileSerializer,
)
from core.exceptions import DomainValidationError
from core.pagination import StandardPagination
from core.permissions import IsPatient, IsPsychologist


class MyPsychologistProfileView(APIView):
    permission_classes = [IsAuthenticated, IsPsychologist]

    def _profile(self, request):
        profile = selectors.get_psychologist_profile_for_user(user=request.user)
        if profile is None:
            raise NotFound("Profile not found.")
        return profile

    @extend_schema(responses=PsychologistProfileOwnerSerializer)
    def get(self, request):
        return Response(PsychologistProfileOwnerSerializer(self._profile(request)).data)

    @extend_schema(
        request=PsychologistRegistrationProfileSerializer,
        responses=PsychologistProfileOwnerSerializer,
    )
    def patch(self, request):
        profile = self._profile(request)
        serializer = PsychologistRegistrationProfileSerializer(
            data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        try:
            profile = services.update_psychologist_profile(
                profile=profile, **serializer.validated_data
            )
        except DomainValidationError as exc:
            raise ValidationError(exc.errors, code=exc.code) from exc
        profile = selectors.get_psychologist_profile_for_user(user=request.user)
        return Response(PsychologistProfileOwnerSerializer(profile).data)


class DirectoryRateThrottle(UserRateThrottle):
    scope = "directory"


class DirectoryListView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]
    throttle_classes = [DirectoryRateThrottle]

    @extend_schema(
        parameters=[DirectoryQuerySerializer],
        responses=DirectoryCardSerializer(many=True),
    )
    def get(self, request):
        query = DirectoryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        qs = selectors.list_directory(**query.validated_data)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            DirectoryCardSerializer(page, many=True).data
        )


class DirectoryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]
    throttle_classes = [DirectoryRateThrottle]

    @extend_schema(responses=DirectoryCardSerializer)
    def get(self, request, pk):
        profile = selectors.get_directory_entry(profile_id=pk)
        if profile is None:
            raise NotFound()
        return Response(DirectoryCardSerializer(profile).data)
