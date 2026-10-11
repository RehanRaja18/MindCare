"""Write-path business logic for psychologists.

Views call into these functions instead of touching the ORM or enforcing
business rules themselves. Anything that mutates state belongs here.
"""

from django.db import IntegrityError, transaction

from apps.accounts.models import Role
from apps.psychologists.models import (
    CREDENTIAL_FIELDS,
    MAX_YEARS_OF_EXPERIENCE,
    MIN_YEARS_OF_EXPERIENCE,
    YEARS_OF_EXPERIENCE_MESSAGE,
    PsychologistProfile,
)
from apps.reference.services import (
    ensure_active_choices,
    resolve_city,
    resolve_location_fields,
)
from core.choices import Gender
from core.exceptions import DomainValidationError
from core.validators import (
    normalize_display_text,
    normalize_identifier,
    run_validator,
    validate_iana_timezone,
)

EDITABLE_FIELDS = {
    "specializations",
    "years_of_experience",
    "languages",
    "country",
    "city",
    "timezone",
    "gender",
    "bio",
}


class DuplicateLicenseError(DomainValidationError):
    def __init__(self):
        # Deliberately generic: never confirm who holds the license.
        super().__init__({"license_number": ["This license is already registered."]})


class CredentialFieldLockedError(DomainValidationError):
    default_code = "credential_field_locked"

    def __init__(self, fields):
        super().__init__(
            {
                field: [
                    "This credential can't be changed after registration. Contact support to correct it."
                ]
                for field in fields
            }
        )


def _normalize_credential(field, value):
    if field == "license_number":
        return normalize_identifier(value)
    if field == "license_issuing_authority":
        return normalize_display_text(value)
    if field == "qualifications":
        return value.strip()
    return value  # license_issuing_country: a Country instance


def _validate_gender(gender):
    if gender is not None and gender not in Gender.values:
        raise DomainValidationError({"gender": ["Choose a valid option."]})


def _validate_years_of_experience(years_of_experience):
    if (
        isinstance(years_of_experience, bool)
        or not isinstance(years_of_experience, int)
        or not (
            MIN_YEARS_OF_EXPERIENCE <= years_of_experience <= MAX_YEARS_OF_EXPERIENCE
        )
    ):
        raise DomainValidationError(
            {"years_of_experience": [YEARS_OF_EXPERIENCE_MESSAGE]}
        )


def create_psychologist_profile(
    *,
    user,
    license_number,
    license_issuing_country,
    license_issuing_authority,
    qualifications,
    specializations,
    years_of_experience,
    languages,
    country,
    city,
    timezone,
    gender=None,
    bio="",
):
    if user.role != Role.PSYCHOLOGIST:
        raise ValueError(
            "Psychologist profiles can only be created for psychologist users."
        )
    ensure_active_choices(items=specializations, field="specializations")
    ensure_active_choices(items=languages, field="languages")
    run_validator(validate_iana_timezone, timezone, field="timezone")
    _validate_gender(gender)
    _validate_years_of_experience(years_of_experience)

    normalized_license = _normalize_credential("license_number", license_number)
    if PsychologistProfile.objects.filter(
        license_issuing_country=license_issuing_country,
        license_number=normalized_license,
    ).exists():
        raise DuplicateLicenseError()

    try:
        with transaction.atomic():
            profile = PsychologistProfile.objects.create(
                user=user,
                license_number=normalized_license,
                license_issuing_country=license_issuing_country,
                license_issuing_authority=_normalize_credential(
                    "license_issuing_authority", license_issuing_authority
                ),
                qualifications=_normalize_credential("qualifications", qualifications),
                years_of_experience=years_of_experience,
                country=country,
                city=resolve_city(country=country, name=city),
                timezone=timezone,
                gender=gender,
                bio=bio or "",
            )
            profile.specializations.set(specializations)
            profile.languages.set(languages)
    except IntegrityError as exc:
        if PsychologistProfile.objects.filter(
            license_issuing_country=license_issuing_country,
            license_number=normalized_license,
        ).exists():
            raise DuplicateLicenseError() from exc
        raise
    return profile


def update_psychologist_profile(*, profile, **fields):
    changed = [
        field
        for field in CREDENTIAL_FIELDS
        if field in fields
        and _normalize_credential(field, fields[field]) != getattr(profile, field)
    ]
    if changed:
        raise CredentialFieldLockedError(changed)
    for field in CREDENTIAL_FIELDS:
        fields.pop(field, None)

    unknown = sorted(set(fields) - EDITABLE_FIELDS)
    if unknown:
        raise DomainValidationError(
            {name: ["This field can't be updated."] for name in unknown}
        )

    if "gender" in fields:
        _validate_gender(fields["gender"])
    if "years_of_experience" in fields:
        _validate_years_of_experience(fields["years_of_experience"])

    specializations = fields.pop("specializations", None)
    languages = fields.pop("languages", None)
    if specializations is not None:
        ensure_active_choices(items=specializations, field="specializations")
    if languages is not None:
        ensure_active_choices(items=languages, field="languages")
    if fields.get("timezone") is not None:
        run_validator(validate_iana_timezone, fields["timezone"], field="timezone")
    if "bio" in fields and fields["bio"] is None:
        fields["bio"] = ""

    resolve_location_fields(
        current_country=profile.country,
        current_city=profile.city,
        fields=fields,
        city_required=True,
    )

    with transaction.atomic():
        for name, value in fields.items():
            setattr(profile, name, value)
        profile.save()
        if specializations is not None:
            profile.specializations.set(specializations)
        if languages is not None:
            profile.languages.set(languages)
    return profile
