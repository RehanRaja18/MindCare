"""DRF authentication that records psychologist activity (Phase 3)."""

from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.relationships.services import record_activity

# Token housekeeping isn't "activity".
UNTRACKED_PATHS = frozenset({"/api/v1/accounts/refresh/", "/api/v1/accounts/logout/"})


class ActivityTrackingJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None and request.path not in UNTRACKED_PATHS:
            record_activity(user=result[0])
        return result
