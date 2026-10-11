"""Shared DRF serializer helpers."""

from collections.abc import Mapping

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.validators import (
    E164_VALIDATOR,
    FreeTextValidator,
    HttpsUrlValidator,
    IdentifierValidator,
    OrganisationNameValidator,
    PersonNameValidator,
    normalize_identifier,
    normalize_multiline_text,
    normalize_phone,
    normalize_single_line,
    number_message,
    whole_number_message,
)


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


# --- Validated input fields (docs/validation-rules.md) ------------------------
# Each helper normalises the value the same way the model field does, then runs
# the same validator, so the API answers with the field's own key and the exact
# message the frontends show.


class NormalizedCharField(serializers.CharField):
    def __init__(self, *, normaliser=normalize_single_line, **kwargs):
        self.normaliser = normaliser
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        return self.normaliser(super().to_internal_value(data))


def person_name_field(label, **kwargs):
    return NormalizedCharField(validators=[PersonNameValidator(label)], **kwargs)


def organisation_name_field(label, max_length=150, **kwargs):
    return NormalizedCharField(
        validators=[OrganisationNameValidator(label, max_length=max_length)],
        **kwargs,
    )


def free_text_field(label, min_length, max_length, **kwargs):
    return NormalizedCharField(
        normaliser=normalize_multiline_text,
        validators=[FreeTextValidator(label, min_length, max_length)],
        **kwargs,
    )


def identifier_field(label, **kwargs):
    return NormalizedCharField(
        normaliser=normalize_identifier,
        validators=[IdentifierValidator(label)],
        **kwargs,
    )


def phone_field(**kwargs):
    return NormalizedCharField(
        normaliser=normalize_phone, validators=[E164_VALIDATOR], **kwargs
    )


def https_url_field(label, allowed_domains=None, **kwargs):
    return NormalizedCharField(
        validators=[HttpsUrlValidator(label, allowed_domains)], **kwargs
    )


def search_field(**kwargs):
    return NormalizedCharField(max_length=120, **kwargs)


def whole_number_field(label, minimum, maximum, **kwargs):
    message = whole_number_message(label, minimum, maximum)
    return serializers.IntegerField(
        min_value=minimum,
        max_value=maximum,
        error_messages={"invalid": message, "min_value": message, "max_value": message},
        **kwargs,
    )


def number_field(label, minimum, maximum, **kwargs):
    message = number_message(label, minimum, maximum)
    return serializers.FloatField(
        min_value=minimum,
        max_value=maximum,
        error_messages={"invalid": message, "min_value": message, "max_value": message},
        **kwargs,
    )
