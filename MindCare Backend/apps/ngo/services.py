"""Write-path business logic for ngo.

Views call into these functions instead of touching the ORM or enforcing
business rules themselves. Anything that mutates state belongs here.
"""

from django.core.validators import URLValidator, validate_email
from django.db import IntegrityError, transaction

from apps.accounts.models import Role
from apps.ngo.models import CREDENTIAL_FIELDS, NGOProfile, NGOServiceArea
from apps.reference.services import resolve_city, resolve_location_fields
from core.exceptions import DomainValidationError
from core.validators import (
    E164_VALIDATOR,
    normalize_display_text,
    normalize_identifier,
    run_validator,
    validate_iana_timezone,
)

EDITABLE_FIELDS = {
    "country",
    "city",
    "timezone",
    "official_phone",
    "official_email",
    "website",
    "description",
    "service_areas",
}

# Model max_length values; validated here because save() doesn't run full_clean().
MAX_LENGTHS = {
    "organization_name": 200,
    "registering_authority": 200,
    "registration_number": 64,
    "description": 2000,
}


class DuplicateNGORegistrationError(DomainValidationError):
    def __init__(self):
        # Deliberately generic: never confirm who holds the registration.
        super().__init__(
            {
                "registration_number": [
                    "This organisation registration is already on file."
                ]
            }
        )


class CredentialFieldLockedError(DomainValidationError):
    default_code = "credential_field_locked"

    def __init__(self, fields):
        super().__init__(
            {
                field: [
                    "This credential can't be changed after registration. "
                    "Contact support to correct it."
                ]
                for field in fields
            }
        )


def _normalize_credential(field, value):
    if field == "registration_number":
        return normalize_identifier(value)
    if field in ("organization_name", "registering_authority"):
        return normalize_display_text(value)
    return value  # registration_country: a Country instance


def _validate_max_length(field, value):
    limit = MAX_LENGTHS[field]
    if value is not None and len(value) > limit:
        raise DomainValidationError(
            {field: [f"Ensure this field has no more than {limit} characters."]}
        )


def _validate_email(value):
    if not value:
        raise DomainValidationError(
            {"official_email": ["This field may not be blank."]}
        )
    run_validator(validate_email, value, field="official_email")


def _clean_website(value):
    if not value:
        return ""
    run_validator(URLValidator(), value, field="website")
    return value


def _resolve_service_areas(service_areas):
    if not service_areas:
        raise DomainValidationError(
            {"service_areas": ["Add at least one service area."]}
        )
    resolved, seen = [], set()
    for area in service_areas:
        country = area["country"]
        city = (
            resolve_city(country=country, name=area["city"])
            if area.get("city")
            else None
        )
        key = (country.pk, city.pk if city else None)
        if key in seen:
            raise DomainValidationError(
                {"service_areas": ["Each service area can only be listed once."]}
            )
        seen.add(key)
        resolved.append((country, city))
    return resolved


def _replace_service_areas(profile, resolved):
    profile.service_areas.all().delete()
    NGOServiceArea.objects.bulk_create(
        NGOServiceArea(ngo=profile, country=country, city=city)
        for country, city in resolved
    )


def create_ngo_profile(
    *,
    user,
    organization_name,
    registration_number,
    registration_country,
    registering_authority,
    country,
    city,
    timezone,
    official_phone,
    official_email,
    service_areas,
    website="",
    description="",
):
    if user.role != Role.NGO:
        raise ValueError("NGO profiles can only be created for NGO users.")
    run_validator(validate_iana_timezone, timezone, field="timezone")
    run_validator(E164_VALIDATOR, official_phone, field="official_phone")
    _validate_email(official_email)
    website = _clean_website(website)
    description = description or ""

    organization_name = _normalize_credential("organization_name", organization_name)
    registering_authority = _normalize_credential(
        "registering_authority", registering_authority
    )
    normalized_number = _normalize_credential(
        "registration_number", registration_number
    )
    _validate_max_length("organization_name", organization_name)
    _validate_max_length("registering_authority", registering_authority)
    _validate_max_length("registration_number", normalized_number)
    _validate_max_length("description", description)

    duplicate = NGOProfile.objects.filter(
        registration_country=registration_country, registration_number=normalized_number
    )
    if duplicate.exists():
        raise DuplicateNGORegistrationError()

    resolved_areas = _resolve_service_areas(service_areas)
    try:
        # Savepoint, so an IntegrityError doesn't poison an outer transaction.
        with transaction.atomic():
            profile = NGOProfile.objects.create(
                user=user,
                organization_name=organization_name,
                registration_number=normalized_number,
                registration_country=registration_country,
                registering_authority=registering_authority,
                country=country,
                city=resolve_city(country=country, name=city),
                timezone=timezone,
                official_phone=official_phone,
                official_email=official_email,
                website=website,
                description=description,
            )
            _replace_service_areas(profile, resolved_areas)
    except IntegrityError as exc:
        if duplicate.exists():
            raise DuplicateNGORegistrationError() from exc
        raise
    return profile


def update_ngo_profile(*, profile, **fields):
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

    service_areas = fields.pop("service_areas", None)
    resolved_areas = (
        _resolve_service_areas(service_areas) if service_areas is not None else None
    )
    if fields.get("timezone") is not None:
        run_validator(validate_iana_timezone, fields["timezone"], field="timezone")
    if "official_phone" in fields:
        run_validator(
            E164_VALIDATOR, fields["official_phone"] or "", field="official_phone"
        )
    if "official_email" in fields:
        _validate_email(fields["official_email"])
    if "website" in fields:
        fields["website"] = _clean_website(fields["website"])
    if "description" in fields:
        fields["description"] = fields["description"] or ""
        _validate_max_length("description", fields["description"])

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
        if resolved_areas is not None:
            _replace_service_areas(profile, resolved_areas)
    return profile
