"""Database models for the ngo app.

NGOProfile is pulled forward into Phase 2 because it's created at registration;
the rest of NGO onboarding stays in Phase 12. Credential fields are locked after
registration (docs/decisions.md, 2026-09-26). Service areas are what Phase 13
will match on; they are deliberately separate from the headquarters location.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from core.validators import E164_VALIDATOR, validate_iana_timezone

CREDENTIAL_FIELDS = (
    "organization_name",
    "registration_number",
    "registration_country",
    "registering_authority",
)


class NGOProfile(models.Model):
    # The account holder is the NGO's representative, not the organisation.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ngo_profile"
    )
    organization_name = models.CharField(max_length=200)
    # Admin-only; stored normalized (stripped, upper-cased).
    registration_number = models.CharField(max_length=64)
    registration_country = models.ForeignKey(
        "reference.Country", on_delete=models.PROTECT, related_name="+"
    )
    registering_authority = models.CharField(max_length=200)
    country = models.ForeignKey(
        "reference.Country", on_delete=models.PROTECT, related_name="+"
    )
    city = models.ForeignKey(
        "reference.City", on_delete=models.PROTECT, related_name="+"
    )
    timezone = models.CharField(max_length=64, validators=[validate_iana_timezone])
    # Admin-only for now; Phase 13 decides who else sees them.
    official_phone = models.CharField(max_length=20, validators=[E164_VALIDATOR])
    official_email = models.EmailField()
    website = models.URLField(blank=True, default="")
    description = models.TextField(max_length=2000, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "NGO profile"
        constraints = [
            models.UniqueConstraint(
                fields=["registration_country", "registration_number"],
                name="ngo_unique_registration_per_country",
            )
        ]

    def __str__(self):
        return self.organization_name


class NGOServiceArea(models.Model):
    """A country, optionally narrowed to one city. city=NULL means nationwide."""

    ngo = models.ForeignKey(
        NGOProfile, on_delete=models.CASCADE, related_name="service_areas"
    )
    country = models.ForeignKey(
        "reference.Country", on_delete=models.PROTECT, related_name="+"
    )
    city = models.ForeignKey(
        "reference.City",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ngo", "country"],
                condition=Q(city__isnull=True),
                name="ngo_service_area_unique_nationwide",
            ),
            models.UniqueConstraint(
                fields=["ngo", "country", "city"],
                condition=Q(city__isnull=False),
                name="ngo_service_area_unique_city",
            ),
        ]

    def __str__(self):
        return f"{self.city or 'All of'} {self.country}"
