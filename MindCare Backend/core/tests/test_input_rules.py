"""The rules in docs/validation-rules.md: one valid case and several invalid ones
for every rule type, asserting the exact message text."""

from datetime import date

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from core.validators import (
    FreeTextValidator,
    HttpsUrlValidator,
    IdentifierValidator,
    OrganisationNameValidator,
    PersonNameValidator,
    normalize_email_address,
    normalize_identifier,
    normalize_multiline_text,
    normalize_phone,
    normalize_single_line,
    validate_adult_date_of_birth,
    validate_phone,
)


class RuleTestCase(SimpleTestCase):
    def assertValid(self, validator, value):
        validator(value)  # raises on failure

    def assertMessage(self, validator, value, message):
        with self.assertRaises(ValidationError) as ctx:
            validator(value)
        self.assertEqual(ctx.exception.messages, [message])


class PersonNameTests(RuleTestCase):
    v = PersonNameValidator("Full name")
    CHARS = (
        "Full name can only contain letters, spaces, hyphens (-), "
        "apostrophes (') and dots (.)."
    )

    def test_valid_names(self):
        for name in [
            "Sara Ahmed",
            "Dr. Sara Ahmed",
            "Mary-Jane O'Neil",
            "D’Souza",
            "محمد بلال",  # Urdu
            "عَلی",  # Arabic script with a combining mark (zabar)
            "José Núñez",
            "Li",
        ]:
            with self.subTest(name=name):
                self.assertValid(self.v, name)

    def test_digits_rejected(self):
        self.assertMessage(self.v, "Sara Ahmed 2", self.CHARS)
        self.assertMessage(self.v, "Dr. Sara Ahmed (Demo)", self.CHARS)

    def test_symbols_and_script_rejected(self):
        for bad in ["Sara@Ahmed", "<script>alert(1)</script>", "Sara_Ahmed", "😀 Sara"]:
            with self.subTest(bad=bad):
                self.assertMessage(self.v, bad, self.CHARS)

    def test_too_short_or_long(self):
        msg = "Full name must be between 2 and 100 characters."
        self.assertMessage(self.v, "A", msg)
        self.assertMessage(self.v, "A" * 101, msg)
        self.assertValid(self.v, "A" * 100)

    def test_needs_two_letters(self):
        self.assertMessage(self.v, "-.", "Full name must contain at least 2 letters.")
        self.assertMessage(self.v, "A.", "Full name must contain at least 2 letters.")

    def test_only_spaces_is_too_short(self):
        self.assertMessage(
            self.v, "   ", "Full name must be between 2 and 100 characters."
        )


class OrganisationNameTests(RuleTestCase):
    v = OrganisationNameValidator("Organisation name")

    def test_valid(self):
        for name in [
            "Rescue 1122",
            "Pakistan Medical & Dental Council",
            "SOS Children's Villages (Pakistan)",
            "Edhi Foundation",
            "Korea, Republic of",
            "Trauma / PTSD",
            "ایدھی فاؤنڈیشن",
        ]:
            with self.subTest(name=name):
                self.assertValid(self.v, name)

    def test_symbols_rejected(self):
        msg = (
            "Organisation name can only contain letters, numbers, spaces and "
            "& , . ' - ( ) /"
        )
        for bad in ["Edhi <b>Foundation</b>", "Help!", "NGO #1", "a@b"]:
            with self.subTest(bad=bad):
                self.assertMessage(self.v, bad, msg)

    def test_needs_letters(self):
        self.assertMessage(
            self.v, "1122", "Organisation name must contain at least 2 letters."
        )

    def test_length(self):
        msg = "Organisation name must be between 2 and 150 characters."
        self.assertMessage(self.v, "A", msg)
        self.assertMessage(self.v, "A" * 151, msg)

    def test_custom_max(self):
        v = OrganisationNameValidator("Name", max_length=100)
        self.assertMessage(v, "A" * 101, "Name must be between 2 and 100 characters.")


class FreeTextTests(RuleTestCase):
    v = FreeTextValidator("Bio", 30, 2000)

    def test_valid(self):
        self.assertValid(self.v, "CBT for anxiety and work stress, 8 years.")
        self.assertValid(self.v, "Helps when symptoms last < 6 months or > 1 year.")

    def test_length(self):
        msg = "Bio must be between 30 and 2000 characters."
        self.assertMessage(self.v, "Too short.", msg)
        self.assertMessage(self.v, "a" * 2001, msg)

    def test_html_rejected(self):
        msg = "Bio can't contain HTML tags."
        for bad in [
            "<script>alert('x')</script> and more text here",
            "Hello there <b>bold</b> friend of mine, nice",
            "A long enough comment <!-- hidden --> here",
            "Closing tag only </div> in a long enough text",
        ]:
            with self.subTest(bad=bad):
                self.assertMessage(self.v, bad, msg)

    def test_needs_letters(self):
        self.assertMessage(self.v, "." * 40, "Bio must contain at least 3 letters.")
        self.assertMessage(
            self.v, "1234567890 " * 4, "Bio must contain at least 3 letters."
        )


class IdentifierTests(RuleTestCase):
    v = IdentifierValidator("License number")

    def test_valid(self):
        for value in ["PMDC-12345", "PMC/2021/123", "12345-P", "DEMO-0001", "A1B"]:
            with self.subTest(value=value):
                self.assertValid(self.v, value)

    def test_symbols_rejected(self):
        msg = (
            "License number can only contain letters, numbers, spaces, dots (.), "
            "slashes (/) and hyphens (-)."
        )
        for bad in ["PMDC#123", "<b>123</b>", "12_34"]:
            with self.subTest(bad=bad):
                self.assertMessage(self.v, bad, msg)

    def test_needs_digit(self):
        self.assertMessage(
            self.v, "PMDC", "License number must contain at least one number."
        )

    def test_length(self):
        msg = "License number must be between 3 and 64 characters."
        self.assertMessage(self.v, "A1", msg)
        self.assertMessage(self.v, "1" * 65, msg)


class PhoneTests(RuleTestCase):
    MSG = (
        "Enter a phone number in international format (e.g. +923001234567), "
        "or a Pakistani number starting with 0 (e.g. 03001234567)."
    )

    def test_normalisation(self):
        cases = {
            "03001234567": "+923001234567",
            "0300-1234567": "+923001234567",
            "0300 123 4567": "+923001234567",
            "042 1234567": "+92421234567",
            "(042) 3578-1234": "+924235781234",
            "+92 300 1234567": "+923001234567",
            "00923001234567": "+923001234567",
            "+44 20 7946 0958": "+442079460958",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_phone(raw), expected)

    def test_valid(self):
        self.assertValid(validate_phone, "+923001234567")

    def test_invalid(self):
        for bad in ["12345", "3001234567", "+0123456789", "phone", "+92abc", "0300"]:
            with self.subTest(bad=bad):
                self.assertMessage(validate_phone, normalize_phone(bad), self.MSG)


class HttpsUrlTests(RuleTestCase):
    def test_https_required(self):
        v = HttpsUrlValidator("Website")
        self.assertValid(v, "https://edhi.org")
        msg = "Website must be a full https:// address (e.g. https://example.org)."
        for bad in [
            "http://edhi.org",
            "edhi.org",
            "javascript:alert(1)",
            "ftp://x.org",
        ]:
            with self.subTest(bad=bad):
                self.assertMessage(v, bad, msg)

    def test_max_length(self):
        v = HttpsUrlValidator("Website")
        self.assertMessage(
            v,
            "https://example.org/" + "a" * 200,
            "Website must be at most 200 characters.",
        )

    def test_allowed_domains(self):
        v = HttpsUrlValidator(
            "Video link", allowed_domains=["zoom.us", "meet.google.com"]
        )
        self.assertValid(v, "https://us02web.zoom.us/j/123")
        self.assertValid(v, "https://meet.google.com/abc-defg-hij")
        msg = "Video link must be a link on one of: zoom.us, meet.google.com."
        self.assertMessage(v, "https://zoom.us.evil.com/j/1", msg)
        self.assertMessage(v, "https://notzoom.us/j/1", msg)


class DateOfBirthTests(RuleTestCase):
    today = date(2026, 10, 10)

    def check(self, value):
        validate_adult_date_of_birth(value, today=self.today)

    def test_valid(self):
        self.check(date(1990, 1, 1))
        self.check(date(1906, 10, 10))  # exactly 120

    def test_too_old(self):
        self.check(date(1906, 10, 9))  # 120, a day past the birthday: still fine
        with self.assertRaises(ValidationError) as ctx:
            self.check(date(1905, 10, 10))  # 121 today
        self.assertEqual(
            ctx.exception.messages, ["Enter a real date of birth (age 120 or under)."]
        )

    def test_future_and_minor(self):
        with self.assertRaises(ValidationError):
            self.check(date(2027, 1, 1))
        with self.assertRaises(ValidationError):
            self.check(date(2010, 1, 1))


class NormaliserTests(SimpleTestCase):
    def test_single_line_strips_controls_and_collapses(self):
        self.assertEqual(normalize_single_line("  Sara\t\x00 Ahmed\n "), "Sara Ahmed")

    def test_multiline_keeps_newlines(self):
        self.assertEqual(
            normalize_multiline_text("  Line one  \r\nLine\x07   two\t\tend  "),
            "Line one\nLine two end",
        )

    def test_multiline_keeps_urdu_zero_width_non_joiner(self):
        self.assertEqual(normalize_multiline_text("ab‌cd"), "ab‌cd")

    def test_identifier(self):
        self.assertEqual(normalize_identifier("  pmdc-  123 "), "PMDC- 123")

    def test_email(self):
        self.assertEqual(
            normalize_email_address("  Sara@Example.COM "), "sara@example.com"
        )
