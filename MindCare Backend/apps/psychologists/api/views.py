"""DRF views for the psychologists API.

Views stay thin: parse the request, delegate to services.py (writes) or
selectors.py (reads), then serialize the result. No business logic here.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.psychologists import selectors, services
from apps.psychologists.api.serializers import (
    PsychologistProfileOwnerSerializer,
    PsychologistRegistrationProfileSerializer,
)
from core.exceptions import DomainValidationError
from core.permissions import IsPsychologist


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
