"""Database models for the patients app.

Phase 2 PatientProfile holds identity, demographics and preferences only — no
health data before the Phase 5 audit trail (docs/decisions.md, 2026-09-26).
"""

import secrets

from django.conf import settings
from django.db import models

from core.choices import Gender
from core.fields import PhoneField
from core.models import ValidatedModelMixin
from core.validators import validate_iana_timezone

PSEUDONYM_PREFIX = "Patient-"


def generate_pseudonym():
    return f"{PSEUDONYM_PREFIX}{secrets.token_hex(3)}"


class PatientProfile(ValidatedModelMixin, models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile",
    )
    # Immutable, never usable for login. Shown instead of the real name unless
    # is_profile_public (see selectors.get_patient_display_identity).
    pseudonym = models.CharField(max_length=16, unique=True, editable=False)
    is_profile_public = models.BooleanField(default=False)
    country = models.ForeignKey(
        "reference.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    city = models.ForeignKey(
        "reference.City",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    timezone = models.CharField(max_length=64, validators=[validate_iana_timezone])
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=20, choices=Gender.choices, null=True, blank=True
    )
    # Contact number only — NOT a login identifier. Phone-number login, if built,
    # gets its own unique, verified field on User (docs/decisions.md, 2026-09-26).
    phone_number = PhoneField(max_length=20, null=True, blank=True)
    preferred_language = models.ForeignKey(
        "reference.Language",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.pseudonym
