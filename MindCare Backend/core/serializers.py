"""Shared DRF serializer helpers."""

from collections.abc import Mapping

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


@extend_schema_field(OpenApiTypes.BOOL)
class StrictTrueField(serializers.Field):
    """Accepts only the JSON boolean `true` — no coercion of "true", 1, "yes", etc.
    For legal declarations (e.g. the 18+ confirmation) that must be explicit."""

    default_error_messages = {
        "invalid": "Must be the JSON boolean true.",
    }

    def to_internal_value(self, data):
        if data is not True:
            self.fail("invalid")
        return True

    def to_representation(self, value):
        return bool(value)


class RejectUnknownFieldsMixin:
    """Reject request keys the serializer doesn't declare, instead of silently
    ignoring them. Used where a client sending e.g. `pseudonym` must get a 400,
    not a 200 that quietly did nothing."""

    def to_internal_value(self, data):
        # Checked here, not in validate(): `initial_data` only exists on the root
        # serializer, so nested / many=True children would silently accept typos.
        if isinstance(data, Mapping):
            unknown = sorted(set(data) - set(self.fields))
            if unknown:
                raise serializers.ValidationError(
                    {key: ["This field can't be set."] for key in unknown}
                )
        return super().to_internal_value(data)
