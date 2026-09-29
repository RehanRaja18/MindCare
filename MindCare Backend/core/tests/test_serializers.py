"""Tests for core/serializers.py."""

from django.test import SimpleTestCase
from rest_framework import serializers

from core.serializers import RejectUnknownFieldsMixin, StrictTrueField


class _Sample(RejectUnknownFieldsMixin, serializers.Serializer):
    name = serializers.CharField(required=False)


class RejectUnknownFieldsTests(SimpleTestCase):
    def test_known_fields_pass(self):
        s = _Sample(data={"name": "x"})
        self.assertTrue(s.is_valid(), s.errors)

    def test_unknown_field_is_rejected_by_name(self):
        s = _Sample(data={"name": "x", "pseudonym": "Patient-000000"})
        self.assertFalse(s.is_valid())
        self.assertIn("pseudonym", s.errors)


class _Child(RejectUnknownFieldsMixin, serializers.Serializer):
    country = serializers.CharField()
    city = serializers.CharField(required=False)


class _Parent(RejectUnknownFieldsMixin, serializers.Serializer):
    items = _Child(many=True)


class RejectUnknownNestedFieldsTests(SimpleTestCase):
    def test_unknown_key_in_nested_many_child_is_rejected(self):
        s = _Parent(data={"items": [{"country": "PK"}, {"country": "PK", "cty": "x"}]})
        self.assertFalse(s.is_valid())
        self.assertNotIn(0, s.errors["items"])
        self.assertIn("cty", s.errors["items"][1])

    def test_valid_nested_items_pass(self):
        s = _Parent(data={"items": [{"country": "PK", "city": "Lahore"}]})
        self.assertTrue(s.is_valid(), s.errors)


class _StrictTrueSample(serializers.Serializer):
    flag = StrictTrueField()


class StrictTrueFieldTests(SimpleTestCase):
    def test_json_boolean_true_is_accepted(self):
        s = _StrictTrueSample(data={"flag": True})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["flag"], True)

    def test_null_is_rejected(self):
        s = _StrictTrueSample(data={"flag": None})
        self.assertFalse(s.is_valid())
        self.assertIn("flag", s.errors)

    def test_missing_field_is_rejected(self):
        s = _StrictTrueSample(data={})
        self.assertFalse(s.is_valid())
        self.assertIn("flag", s.errors)

    def test_truthy_string_values_are_rejected(self):
        for value in ("true", "True", "yes", "on"):
            with self.subTest(value=value):
                s = _StrictTrueSample(data={"flag": value})
                self.assertFalse(s.is_valid(), f"{value} should be rejected")
                self.assertIn("flag", s.errors)

    def test_numeric_truthy_values_are_rejected(self):
        for value in (1, "1"):
            with self.subTest(value=value):
                s = _StrictTrueSample(data={"flag": value})
                self.assertFalse(s.is_valid(), f"{value} should be rejected")
                self.assertIn("flag", s.errors)

    def test_json_boolean_false_is_rejected(self):
        s = _StrictTrueSample(data={"flag": False})
        self.assertFalse(s.is_valid())
        self.assertIn("flag", s.errors)
