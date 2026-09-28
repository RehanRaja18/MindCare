"""Tests for core/serializers.py."""

from django.test import SimpleTestCase
from rest_framework import serializers

from core.serializers import RejectUnknownFieldsMixin


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
