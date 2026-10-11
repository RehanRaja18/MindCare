"""
Shared field validators and text normalizers used by more than one app.

The rules and their exact messages are specified in docs/validation-rules.md; the
Web (src/utils/validation.ts) and the App (lib/core/utils/validators.dart) mirror
them. Change all three together.

Validators raise django.core.exceptions.ValidationError so they work on model
fields and DRF serializer fields alike. Services that need the same check
wrap them with run_validator(), which re-raises as DomainValidationError.
Class-based validators are @deconstructible so they can sit on model fields.
"""

import re
import unicodedata
from functools import cache
from urllib.parse import urlsplit
from zoneinfo import available_timezones

from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator
from django.utils import timezone as dj_timezone
from django.utils.deconstruct import deconstructible

from core.exceptions import DomainValidationError

MINIMUM_AGE = 18
MAXIMUM_AGE = 120

PHONE_MESSAGE = (
    "Enter a phone number in international format (e.g. +923001234567), "
    "or a Pakistani number starting with 0 (e.g. 03001234567)."
)
E164_VALIDATOR = RegexValidator(regex=r"^\+[1-9]\d{6,14}$", message=PHONE_MESSAGE)


# --- Normalisers -------------------------------------------------------------


def _is_control(ch):
    return unicodedata.category(ch) == "Cc"


def normalize_single_line(value):
    """Control characters removed (tabs and newlines become spaces), spaces
    collapsed, trimmed."""
    if value is None:
        return value
    cleaned = "".join(
        " " if ch in "\t\n\r" else ("" if _is_control(ch) else ch) for ch in str(value)
    )
    return " ".join(cleaned.split())


def normalize_multiline_text(value):
    """Keeps line breaks; everything else as normalize_single_line, per line.
    Format characters (e.g. the zero-width non-joiner Urdu needs) are kept."""
    if value is None:
        return value
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(
        " " if ch == "\t" else ch for ch in text if not _is_control(ch) or ch in "\n\t"
    )
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return "\n".join(lines).strip()


# Kept for existing callers: identical to normalize_single_line.
normalize_display_text = normalize_single_line


def normalize_identifier(value):
    return normalize_single_line(value).upper()


def normalize_email_address(value):
    # Same normalization as User.email (accounts.models.UserManager._create_user):
    # strip, normalize_email(), then lower-case the whole address.
    return BaseUserManager.normalize_email(normalize_single_line(value or "")).lower()


_PHONE_SEPARATORS = re.compile(r"[\s\-.()]")


def normalize_phone(value):
    """Separators removed; 00 -> +; a Pakistani local number (single leading 0,
    then 9-10 digits) -> +92 without the 0. Anything else is left for the E.164
    validator to judge."""
    if value is None:
        return value
    phone = _PHONE_SEPARATORS.sub("", normalize_single_line(value))
    if phone.startswith("00"):
        return "+" + phone[2:]
    if re.fullmatch(r"0[1-9]\d{8,9}", phone):
        return "+92" + phone[1:]
    return phone


def validate_phone(value):
    E164_VALIDATOR(value)


# --- Character classes -------------------------------------------------------


def _is_letter(ch):
    return unicodedata.category(ch)[0] == "L"


def _is_mark(ch):
    return unicodedata.category(ch)[0] == "M"


def _count_letters(value):
    return sum(1 for ch in value if _is_letter(ch))


def _length_message(label, min_length, max_length):
    return f"{label} must be between {min_length} and {max_length} characters."


# --- Rule validators ---------------------------------------------------------


@deconstructible
class PersonNameValidator:
    """Letters (any script, with combining marks), spaces, - ' ’ . only;
    2-100 characters; at least 2 letters."""

    EXTRA = frozenset(" -'’.")

    def __init__(self, label, min_length=2, max_length=100):
        self.label = label
        self.min_length = min_length
        self.max_length = max_length

    def __call__(self, value):
        value = value or ""
        if any(
            not (_is_letter(ch) or _is_mark(ch) or ch in self.EXTRA) for ch in value
        ):
            raise ValidationError(
                f"{self.label} can only contain letters, spaces, hyphens (-), "
                "apostrophes (') and dots (.).",
                code="invalid_characters",
            )
        if not self.min_length <= len(value.strip()) <= self.max_length:
            raise ValidationError(
                _length_message(self.label, self.min_length, self.max_length),
                code="length",
            )
        if _count_letters(value) < 2:
            raise ValidationError(
                f"{self.label} must contain at least 2 letters.", code="letters"
            )

    def __eq__(self, other):
        return isinstance(other, PersonNameValidator) and (
            self.label,
            self.min_length,
            self.max_length,
        ) == (other.label, other.min_length, other.max_length)


@deconstructible
class OrganisationNameValidator:
    """Letters, digits, spaces and & , . ' ’ - ( ) / ; 2-150 characters (or a
    custom max); at least 2 letters."""

    EXTRA = frozenset(" &,.'’-()/")

    def __init__(self, label, min_length=2, max_length=150):
        self.label = label
        self.min_length = min_length
        self.max_length = max_length

    def __call__(self, value):
        value = value or ""
        if any(
            not (_is_letter(ch) or _is_mark(ch) or ch.isdigit() or ch in self.EXTRA)
            for ch in value
        ):
            raise ValidationError(
                f"{self.label} can only contain letters, numbers, spaces and "
                "& , . ' - ( ) /",
                code="invalid_characters",
            )
        if not self.min_length <= len(value.strip()) <= self.max_length:
            raise ValidationError(
                _length_message(self.label, self.min_length, self.max_length),
                code="length",
            )
        if _count_letters(value) < 2:
            raise ValidationError(
                f"{self.label} must contain at least 2 letters.", code="letters"
            )

    def __eq__(self, other):
        return isinstance(other, OrganisationNameValidator) and (
            self.label,
            self.min_length,
            self.max_length,
        ) == (other.label, other.min_length, other.max_length)


HTML_TAG = re.compile(r"<\s*[A-Za-z/!?]")


@deconstructible
class FreeTextValidator:
    """Length min-max, no HTML tags, at least 3 letters."""

    def __init__(self, label, min_length, max_length):
        self.label = label
        self.min_length = min_length
        self.max_length = max_length

    def __call__(self, value):
        value = value or ""
        if not self.min_length <= len(value.strip()) <= self.max_length:
            raise ValidationError(
                _length_message(self.label, self.min_length, self.max_length),
                code="length",
            )
        if HTML_TAG.search(value):
            raise ValidationError(f"{self.label} can't contain HTML tags.", code="html")
        if _count_letters(value) < 3:
            raise ValidationError(
                f"{self.label} must contain at least 3 letters.", code="letters"
            )

    def __eq__(self, other):
        return isinstance(other, FreeTextValidator) and (
            self.label,
            self.min_length,
            self.max_length,
        ) == (other.label, other.min_length, other.max_length)


@deconstructible
class IdentifierValidator:
    """License / registration numbers: A-Z 0-9 space . / - ; 3-64; a digit."""

    PATTERN = re.compile(r"[A-Za-z0-9 ./\-]*")

    def __init__(self, label, min_length=3, max_length=64):
        self.label = label
        self.min_length = min_length
        self.max_length = max_length

    def __call__(self, value):
        value = value or ""
        if not self.PATTERN.fullmatch(value):
            raise ValidationError(
                f"{self.label} can only contain letters, numbers, spaces, dots (.), "
                "slashes (/) and hyphens (-).",
                code="invalid_characters",
            )
        if not self.min_length <= len(value.strip()) <= self.max_length:
            raise ValidationError(
                _length_message(self.label, self.min_length, self.max_length),
                code="length",
            )
        if not any(ch.isdigit() for ch in value):
            raise ValidationError(
                f"{self.label} must contain at least one number.", code="digit"
            )

    def __eq__(self, other):
        return isinstance(other, IdentifierValidator) and (
            self.label,
            self.min_length,
            self.max_length,
        ) == (other.label, other.min_length, other.max_length)


@deconstructible
class HttpsUrlValidator:
    """A valid https:// URL, at most 200 characters, optionally restricted to
    some domains (and their subdomains)."""

    MAX_LENGTH = 200

    def __init__(self, label, allowed_domains=None):
        self.label = label
        self.allowed_domains = list(allowed_domains) if allowed_domains else None

    def __call__(self, value):
        value = value or ""
        try:
            URLValidator(schemes=["https"])(value)
            ok = value.lower().startswith("https://")
        except ValidationError:
            ok = False
        if not ok:
            raise ValidationError(
                f"{self.label} must be a full https:// address "
                "(e.g. https://example.org).",
                code="https",
            )
        if len(value) > self.MAX_LENGTH:
            raise ValidationError(
                f"{self.label} must be at most {self.MAX_LENGTH} characters.",
                code="length",
            )
        if self.allowed_domains:
            host = (urlsplit(value).hostname or "").lower()
            if not any(
                host == domain or host.endswith("." + domain)
                for domain in self.allowed_domains
            ):
                raise ValidationError(
                    f"{self.label} must be a link on one of: "
                    f"{', '.join(self.allowed_domains)}.",
                    code="domain",
                )

    def __eq__(self, other):
        return isinstance(other, HttpsUrlValidator) and (
            self.label,
            self.allowed_domains,
        ) == (other.label, other.allowed_domains)


COUNTRY_CODE_VALIDATOR = RegexValidator(
    regex=r"^[A-Z]{2}$", message="Enter a two-letter ISO country code, e.g. PK."
)
LANGUAGE_CODE_VALIDATOR = RegexValidator(
    regex=r"^[a-z]{2}$", message="Enter a two-letter ISO 639-1 code, e.g. ur."
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
    age = age_on(value, today)
    if age < MINIMUM_AGE:
        raise ValidationError("You must be 18 or older to use MindCare.")
    if age > MAXIMUM_AGE:
        raise ValidationError("Enter a real date of birth (age 120 or under).")


def whole_number_message(label, minimum, maximum):
    return f"{label} must be a whole number between {minimum} and {maximum}."


def number_message(label, minimum, maximum):
    return f"{label} must be a number between {minimum} and {maximum}."


def run_validator(validator, value, *, field):
    try:
        validator(value)
    except ValidationError as exc:
        raise DomainValidationError({field: list(exc.messages)}) from exc
