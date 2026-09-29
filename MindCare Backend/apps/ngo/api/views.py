"""DRF views for the ngo API.

Views stay thin: parse the request, delegate to services.py (writes) or
selectors.py (reads), then serialize the result. No business logic here.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ngo import selectors, services
from apps.ngo.api.serializers import (
    NGOProfileOwnerSerializer,
    NGORegistrationProfileSerializer,
)
from core.exceptions import DomainValidationError
from core.permissions import IsNGO


class MyNGOProfileView(APIView):
    permission_classes = [IsAuthenticated, IsNGO]

    def _profile(self, request):
        profile = selectors.get_ngo_profile_for_user(user=request.user)
        if profile is None:
            raise NotFound("Profile not found.")
        return profile

    @extend_schema(responses=NGOProfileOwnerSerializer)
    def get(self, request):
        return Response(NGOProfileOwnerSerializer(self._profile(request)).data)

    @extend_schema(
        request=NGORegistrationProfileSerializer,
        responses=NGOProfileOwnerSerializer,
    )
    def patch(self, request):
        profile = self._profile(request)
        serializer = NGORegistrationProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            services.update_ngo_profile(profile=profile, **serializer.validated_data)
        except DomainValidationError as exc:
            raise ValidationError(exc.errors, code=exc.code) from exc
        profile = selectors.get_ngo_profile_for_user(user=request.user)
        return Response(NGOProfileOwnerSerializer(profile).data)
