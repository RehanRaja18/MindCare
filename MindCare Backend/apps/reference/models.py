"""Shared, admin-editable reference data used by every profile app.

Seeded once by data migrations, then maintained in Django admin — corrections
never need a code change or a new migration. Language/Specialization are
retired with is_active=False, never deleted (profiles reference them with
on_delete=PROTECT).
"""

from django.db import models
from django.db.models.functions import Lower

from core.fields import OrganisationNameField, PersonNameField
from core.models import ValidatedModelMixin
from core.validators import COUNTRY_CODE_VALIDATOR, LANGUAGE_CODE_VALIDATOR


class Country(ValidatedModelMixin, models.Model):
    code = models.CharField(
        max_length=2, unique=True, validators=[COUNTRY_CODE_VALIDATOR]
    )  # ISO 3166-1 alpha-2
    name = OrganisationNameField(max_length=100, label="Name", rule_max_length=100)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "countries"

    def __str__(self):
        return self.name


class City(ValidatedModelMixin, models.Model):
    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, related_name="cities"
    )
    # Column stays 120; the name rule caps new values at 100.
    name = PersonNameField(max_length=120, label="City")
    # Seeded cities are verified. Cities typed at registration stay unverified:
    # usable on the profile that created them, hidden from the public dropdown
    # until an admin verifies them.
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "cities"
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "country",
                name="reference_city_unique_name_per_country_ci",
            )
        ]

    def __str__(self):
        return f"{self.name}, {self.country.code}"


class Language(ValidatedModelMixin, models.Model):
    code = models.CharField(
        max_length=2, unique=True, validators=[LANGUAGE_CODE_VALIDATOR]
    )  # ISO 639-1
    name = OrganisationNameField(max_length=100, label="Name", rule_max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Specialization(ValidatedModelMixin, models.Model):
    """PLACEHOLDER taxonomy — must be reviewed by a clinical advisor before
    real launch (docs/decisions.md, 2026-09-26)."""

    slug = models.SlugField(max_length=50, unique=True)
    name = OrganisationNameField(max_length=100, label="Name", rule_max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "specialization (placeholder list)"

    def __str__(self):
        return self.name
