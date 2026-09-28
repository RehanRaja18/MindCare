"""Write-path business logic for patients.

Views call into these functions instead of touching the ORM or enforcing
business rules themselves. Anything that mutates state belongs here.
"""

from django.db import IntegrityError, transaction

from apps.accounts.models import Role
from apps.patients.models import PatientProfile, generate_pseudonym
from apps.reference.services import resolve_location_fields
from core.choices import Gender
from core.exceptions import DomainValidationError
from core.validators import (
    E164_VALIDATOR,
    run_validator,
    validate_adult_date_of_birth,
    validate_iana_timezone,
)

MAX_PSEUDONYM_ATTEMPTS = 5

UPDATABLE_FIELDS = {
    "is_profile_public",
    "country",
    "city",
    "timezone",
    "date_of_birth",
    "gender",
    "phone_number",
    "preferred_language",
}


class PseudonymGenerationError(Exception):
    """Could not generate a unique pseudonym after MAX_PSEUDONYM_ATTEMPTS."""


def create_patient_profile(*, user, timezone):
    if user.role != Role.PATIENT:
        raise ValueError("Patient profiles can only be created for patient users.")
    run_validator(validate_iana_timezone, timezone, field="timezone")

    for _ in range(MAX_PSEUDONYM_ATTEMPTS):
        try:
            with transaction.atomic():
                return PatientProfile.objects.create(
                    user=user, pseudonym=generate_pseudonym(), timezone=timezone
                )
        except IntegrityError:
            if PatientProfile.objects.filter(user=user).exists():
                raise
            # Otherwise it was a pseudonym collision: try a fresh one.
    raise PseudonymGenerationError("Could not generate a unique pseudonym.")


def update_patient_profile(*, profile, **fields):
    unknown = sorted(set(fields) - UPDATABLE_FIELDS)
    if unknown:
        raise DomainValidationError(
            {name: ["This field can't be updated."] for name in unknown}
        )

    if fields.get("timezone") is not None:
        run_validator(validate_iana_timezone, fields["timezone"], field="timezone")
    if fields.get("phone_number"):
        run_validator(E164_VALIDATOR, fields["phone_number"], field="phone_number")
    elif "phone_number" in fields:
        fields["phone_number"] = None
    if fields.get("date_of_birth") is not None:
        run_validator(
            validate_adult_date_of_birth, fields["date_of_birth"], field="date_of_birth"
        )
    if fields.get("gender") is not None and fields["gender"] not in Gender.values:
        raise DomainValidationError({"gender": ["Choose a valid option."]})

    resolve_location_fields(
        current_country=profile.country,
        current_city=profile.city,
        fields=fields,
        city_required=False,
    )

    for name, value in fields.items():
        setattr(profile, name, value)
    profile.save()
    return profile
