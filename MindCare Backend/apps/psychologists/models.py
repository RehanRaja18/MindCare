"""Database models for the psychologists app.

Credential fields are sent at registration and LOCKED afterwards: they are what
an admin reviews for approval (docs/decisions.md, 2026-09-26). Corrections go
through Django admin until Phase 2.5's re-review flow.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models

from core.choices import Gender
from core.validators import validate_iana_timezone

CREDENTIAL_FIELDS = (
    "license_number",
    "license_issuing_country",
    "license_issuing_authority",
    "qualifications",
)

MIN_YEARS_OF_EXPERIENCE = 0
MAX_YEARS_OF_EXPERIENCE = 70


class NotAcceptingReason(models.TextChoices):
    FULLY_BOOKED = "fully_booked", "Fully booked"
    AWAY = "away", "Away / on leave"
    OTHER = "other", "Other"


class PsychologistProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="psychologist_profile",
    )
    # Admin-only; stored normalized (stripped, upper-cased).
    license_number = models.CharField(max_length=64)
    license_issuing_country = models.ForeignKey(
        "reference.Country", on_delete=models.PROTECT, related_name="+"
    )
    license_issuing_authority = models.CharField(max_length=200)
    qualifications = models.TextField(max_length=1000)
    specializations = models.ManyToManyField(
        "reference.Specialization", related_name="+"
    )
    years_of_experience = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(MAX_YEARS_OF_EXPERIENCE)]
    )
    languages = models.ManyToManyField("reference.Language", related_name="+")
    country = models.ForeignKey(
        "reference.Country", on_delete=models.PROTECT, related_name="+"
    )
    city = models.ForeignKey(
        "reference.City", on_delete=models.PROTECT, related_name="+"
    )
    timezone = models.CharField(max_length=64, validators=[validate_iana_timezone])
    gender = models.CharField(
        max_length=20, choices=Gender.choices, null=True, blank=True
    )
    bio = models.TextField(max_length=2000, blank=True, default="")
    # Set by the psychologist (Phase 3); never changes on its own. Patients see
    # only on/off; the reason stays on the psychologist's availability endpoint.
    is_accepting_patients = models.BooleanField(default=True)
    not_accepting_reason = models.CharField(
        max_length=20, choices=NotAcceptingReason.choices, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["license_issuing_country", "license_number"],
                name="psychologists_unique_license_per_country",
            )
        ]

    def __str__(self):
        return f"Psychologist profile #{self.pk}"
