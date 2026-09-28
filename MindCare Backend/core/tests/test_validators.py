"""Tests for core/validators.py."""

from datetime import date

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from core.exceptions import DomainValidationError
from core.validators import (
    E164_VALIDATOR,
    age_on,
    normalize_display_text,
    normalize_identifier,
    run_validator,
    validate_adult_date_of_birth,
    validate_iana_timezone,
)


class TimezoneValidatorTests(SimpleTestCase):
    def test_accepts_iana_names(self):
        for tz in ["Asia/Karachi", "Europe/London", "America/Toronto", "UTC"]:
            validate_iana_timezone(tz)

    def test_rejects_unknown_names(self):
        for tz in ["Asia/Lahore", "PKT", "GMT+5", ""]:
            with self.assertRaises(ValidationError):
                validate_iana_timezone(tz)


class PhoneValidatorTests(SimpleTestCase):
    def test_accepts_e164(self):
        E164_VALIDATOR("+923001234567")
        E164_VALIDATOR("+442071838750")

    def test_rejects_non_e164(self):
        for value in ["03001234567", "+0123456789", "+92 300 1234567", "+12345"]:
            with self.assertRaises(ValidationError):
                E164_VALIDATOR(value)


class AdultDateOfBirthTests(SimpleTestCase):
    today = date(2026, 9, 28)

    def test_exactly_18_today_passes(self):
        validate_adult_date_of_birth(date(2008, 9, 28), today=self.today)

    def test_one_day_short_of_18_fails(self):
        with self.assertRaises(ValidationError):
            validate_adult_date_of_birth(date(2008, 9, 29), today=self.today)

    def test_future_date_fails(self):
        with self.assertRaises(ValidationError):
            validate_adult_date_of_birth(date(2027, 1, 1), today=self.today)

    def test_leap_day_birthday(self):
        self.assertEqual(age_on(date(2008, 2, 29), date(2026, 2, 28)), 17)
        self.assertEqual(age_on(date(2008, 2, 29), date(2026, 3, 1)), 18)


class NormalizerTests(SimpleTestCase):
    def test_display_text_collapses_whitespace(self):
        self.assertEqual(
            normalize_display_text("  Rahim   Yar  Khan "), "Rahim Yar Khan"
        )

    def test_identifier_strips_and_uppercases(self):
        self.assertEqual(normalize_identifier("  pmdc-123 "), "PMDC-123")


class RunValidatorTests(SimpleTestCase):
    def test_wraps_django_error_as_domain_error(self):
        with self.assertRaises(DomainValidationError) as ctx:
            run_validator(validate_iana_timezone, "Nowhere/Land", field="timezone")
        self.assertIn("timezone", ctx.exception.errors)
        self.assertEqual(ctx.exception.code, "invalid")
