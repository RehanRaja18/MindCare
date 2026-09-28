"""DRF views for the patients API.

Views stay thin: parse the request, delegate to services.py (writes) or
selectors.py (reads), then serialize the result. No business logic here.
"""

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.patients import selectors, services
from apps.patients.api.serializers import (
    PatientProfileOwnerSerializer,
    PatientProfileUpdateSerializer,
)
from core.exceptions import DomainValidationError
from core.permissions import IsPatient


class MyPatientProfileView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def _profile(self, request):
        profile = selectors.get_patient_profile_for_user(user=request.user)
        if profile is None:
            raise NotFound("Profile not found.")
        return profile

    def get(self, request):
        return Response(PatientProfileOwnerSerializer(self._profile(request)).data)

    def patch(self, request):
        profile = self._profile(request)
        serializer = PatientProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            profile = services.update_patient_profile(
                profile=profile, **serializer.validated_data
            )
        except DomainValidationError as exc:
            raise ValidationError(exc.errors, code=exc.code) from exc
        return Response(PatientProfileOwnerSerializer(profile).data)
