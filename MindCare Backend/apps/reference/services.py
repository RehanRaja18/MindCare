"""Write-path business logic for reference data.

Cities are created only as a side effect of a profile write — there is no
public city-create endpoint (spec §3.4).
"""

from django.db import IntegrityError, transaction

from apps.reference.models import City
from core.exceptions import DomainValidationError
from core.validators import normalize_display_text

CITY_NAME_MAX_LENGTH = 120


def resolve_city(*, country, name):
    cleaned = normalize_display_text(name or "")
    if not cleaned:
        raise DomainValidationError({"city": ["City name can't be empty."]})
    if len(cleaned) > CITY_NAME_MAX_LENGTH:
        raise DomainValidationError({"city": ["City name is too long."]})

    existing = City.objects.filter(country=country, name__iexact=cleaned).first()
    if existing is not None:
        return existing
    try:
        with transaction.atomic():
            return City.objects.create(country=country, name=cleaned)
    except IntegrityError:
        # Another request created the same city between our lookup and insert.
        return City.objects.get(country=country, name__iexact=cleaned)


def resolve_location_fields(*, current_country, current_city, fields, city_required):
    """Validate/resolve `country` + `city` in a profile write. `fields["city"]`
    comes in as a name (str) and leaves as a City or None. Mutates `fields`."""
    if (
        "country" in fields
        and fields["country"] is None
        and current_country is not None
    ):
        raise DomainValidationError({"country": ["Country can't be removed once set."]})
    country = fields.get("country", current_country)

    if "city" in fields:
        name = fields["city"]
        if not name:
            if city_required:
                raise DomainValidationError({"city": ["City is required."]})
            fields["city"] = None
        else:
            if country is None:
                raise DomainValidationError(
                    {"city": ["Choose a country before a city."]}
                )
            fields["city"] = resolve_city(country=country, name=name)
    elif (
        "country" in fields
        and current_city is not None
        and current_city.country_id != country.pk
    ):
        if city_required:
            raise DomainValidationError(
                {"city": ["Changing country needs a city in the new country."]}
            )
        fields["city"] = None
    return fields


def ensure_active_choices(*, items, field):
    if not items:
        raise DomainValidationError({field: ["Choose at least one."]})
    inactive = [str(item) for item in items if not item.is_active]
    if inactive:
        raise DomainValidationError(
            {field: [f"No longer available: {', '.join(inactive)}."]}
        )
