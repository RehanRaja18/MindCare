"""OpenAPI description of MindCare's JWT authentication (drf-spectacular)."""

from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme


class ActivityTrackingJWTScheme(SimpleJWTScheme):
    """Same bearer-JWT scheme as simplejwt's; ActivityTrackingJWTAuthentication only
    adds psychologist activity tracking."""

    target_class = "apps.accounts.authentication.ActivityTrackingJWTAuthentication"
