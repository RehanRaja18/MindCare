"""DRF views for the accounts API.

Views stay thin: parse the request, delegate to services.py (writes) or
selectors.py (reads), then serialize the result. No business logic here.
"""

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.throttling import AnonRateThrottle, BaseThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts import selectors, services
from apps.accounts.api.serializers import (
    MindCareTokenObtainPairSerializer,
    RegisterRequestDoc,
    RegisterResponseDoc,
    RegisterSerializer,
    registration_response_data,
)
from apps.accounts.models import ApprovalStatus
from core.exceptions import DomainValidationError
from core.permissions import IsAdmin


class RegisterRateThrottle(AnonRateThrottle):
    scope = "register"


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [RegisterRateThrottle]

    @extend_schema(request=RegisterRequestDoc, responses={201: RegisterResponseDoc})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = services.register_user(
                email=data["email"],
                password=data["password"],
                full_name=data["full_name"],
                role=data["role"],
                is_adult_confirmed=data["is_adult_confirmed"],
                profile_data=data["profile"],
            )
        except services.DuplicateEmailError as exc:
            raise ValidationError({"email": str(exc)}) from exc
        except DomainValidationError as exc:
            errors = (
                exc.errors
                if "is_adult_confirmed" in exc.errors
                else {"profile": exc.errors}
            )
            raise ValidationError(errors, code=exc.code) from exc
        return Response(
            registration_response_data(user), status=status.HTTP_201_CREATED
        )


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class LoginView(TokenObtainPairView):
    serializer_class = MindCareTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]
    permission_classes = [AllowAny]
    authentication_classes = []


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")
        user = (
            selectors.get_user_from_refresh_token(refresh_token)
            if refresh_token
            else None
        )

        if user is not None and (
            not user.is_active or user.approval_status != ApprovalStatus.APPROVED
        ):
            return Response(
                {"detail": "This account is no longer authorized to refresh tokens."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK and user is not None:
            services.record_token_refresh(user=user, ip=request.META.get("REMOTE_ADDR"))
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=inline_serializer(
            "LogoutRequest", {"refresh": serializers.CharField()}
        ),
        responses={205: None},
    )
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            raise ParseError("refresh token is required")
        try:
            token = RefreshToken(refresh_token)
        except TokenError as exc:
            raise ParseError("invalid or already-blacklisted token") from exc

        try:
            token_user_id = int(token["user_id"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ParseError("invalid token format") from exc

        if token_user_id != request.user.id:
            raise ParseError("refresh token does not belong to the authenticated user")

        token.blacklist()
        services.record_logout(user=request.user, ip=request.META.get("REMOTE_ADDR"))
        return Response(status=status.HTTP_205_RESET_CONTENT)


class ClientIpDebugView(APIView):
    """TEMPORARY, admin-only: shows the proxy headers Render passes through, so the
    right NUM_PROXIES can be measured instead of guessed. Remove in the very next
    PR (docs/decisions.md, 2026-10-10). Nothing is logged or stored."""

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(exclude=True)
    def get(self, request):
        meta = request.META
        xff = meta.get("HTTP_X_FORWARDED_FOR")
        return Response(
            {
                "remote_addr": meta.get("REMOTE_ADDR"),
                "x_forwarded_for": xff,
                "x_forwarded_for_count": len(xff.split(",")) if xff else 0,
                "cf_connecting_ip": meta.get("HTTP_CF_CONNECTING_IP"),
                "true_client_ip": meta.get("HTTP_TRUE_CLIENT_IP"),
                "x_real_ip": meta.get("HTTP_X_REAL_IP"),
                "num_proxies": api_settings.NUM_PROXIES,
                "throttle_ident": BaseThrottle().get_ident(request),
            }
        )
