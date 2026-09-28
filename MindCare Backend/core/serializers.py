"""Shared DRF serializer helpers."""

from rest_framework import serializers


class RejectUnknownFieldsMixin:
    """Reject request keys the serializer doesn't declare, instead of silently
    ignoring them. Used where a client sending e.g. `pseudonym` must get a 400,
    not a 200 that quietly did nothing."""

    def validate(self, attrs):
        initial = getattr(self, "initial_data", None) or {}
        unknown = sorted(set(initial) - set(self.fields))
        if unknown:
            raise serializers.ValidationError(
                {key: ["This field can't be set."] for key in unknown}
            )
        return super().validate(attrs)
