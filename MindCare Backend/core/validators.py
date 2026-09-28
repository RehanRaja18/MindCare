"""
Shared field validators and text normalizers used by more than one app.

Validators raise django.core.exceptions.ValidationError so they work on model
fields and DRF serializer fields alike. Services that need the same check
wrap them with run_validator(), which re-raises as DomainValidationError.
"""

from functools import cache
from zoneinfo import available_timezones

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone as dj_timezone

from core.exceptions import DomainValidationError

MINIMUM_AGE = 18

E164_VALIDATOR = RegexValidator(
    regex=r"^\+[1-9]\d{6,14}$",
    message="Enter a phone number in international format, e.g. +923001234567.",
)


@cache
def _iana_timezones():
    return frozenset(available_timezones())


def validate_iana_timezone(value):
    if value not in _iana_timezones():
        raise ValidationError(f"{value!r} is not a recognised IANA timezone.")


def age_on(dob, today):
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def validate_adult_date_of_birth(value, *, today=None):
    today = today or dj_timezone.localdate()
    if value > today:
        raise ValidationError("Date of birth can't be in the future.")
    if age_on(value, today) < MINIMUM_AGE:
        raise ValidationError("You must be 18 or older to use MindCare.")


def normalize_display_text(value):
    return " ".join(value.split())


def normalize_identifier(value):
    return value.strip().upper()


def run_validator(validator, value, *, field):
    try:
        validator(value)
    except ValidationError as exc:
        raise DomainValidationError({field: list(exc.messages)}) from exc
