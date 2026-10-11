"""Model fields that normalise and validate user-entered text the same way
everywhere (docs/validation-rules.md).

Normalisation runs in to_python(), which Model.full_clean() calls and writes
back to the instance, so Django admin forms and ValidatedModelMixin.save() both
store the cleaned value. Validators are added by each field; DB columns keep
their existing max_length (the validator enforces the stricter limit).
"""

from django.db import models

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
)


class _NormalisingMixin:
    normaliser = staticmethod(normalize_single_line)

    def to_python(self, value):
        value = super().to_python(value)
        if isinstance(value, str):
            value = self.normaliser(value)
        return value


class PersonNameField(_NormalisingMixin, models.CharField):
    def __init__(self, *args, label="Name", **kwargs):
        self.label = label
        kwargs.setdefault("max_length", 100)
        super().__init__(*args, **kwargs)
        self.validators.append(PersonNameValidator(label))

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["label"] = self.label
        return name, path, args, kwargs


class OrganisationNameField(_NormalisingMixin, models.CharField):
    def __init__(self, *args, label="Name", rule_max_length=150, **kwargs):
        self.label = label
        self.rule_max_length = rule_max_length
        kwargs.setdefault("max_length", 200)
        super().__init__(*args, **kwargs)
        self.validators.append(
            OrganisationNameValidator(label, max_length=rule_max_length)
        )

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["label"] = self.label
        kwargs["rule_max_length"] = self.rule_max_length
        return name, path, args, kwargs


class FreeTextField(models.TextField):
    def __init__(
        self, *args, label="Text", min_length=1, rule_max_length=1000, **kwargs
    ):
        self.label = label
        self.min_length = min_length
        self.rule_max_length = rule_max_length
        super().__init__(*args, **kwargs)
        self.validators.append(FreeTextValidator(label, min_length, rule_max_length))

    def to_python(self, value):
        value = super().to_python(value)
        if isinstance(value, str):
            value = normalize_multiline_text(value)
        return value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.update(
            label=self.label,
            min_length=self.min_length,
            rule_max_length=self.rule_max_length,
        )
        return name, path, args, kwargs


class IdentifierField(_NormalisingMixin, models.CharField):
    normaliser = staticmethod(normalize_identifier)

    def __init__(self, *args, label="Identifier", **kwargs):
        self.label = label
        kwargs.setdefault("max_length", 64)
        super().__init__(*args, **kwargs)
        self.validators.append(IdentifierValidator(label))

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["label"] = self.label
        return name, path, args, kwargs


class PhoneField(_NormalisingMixin, models.CharField):
    normaliser = staticmethod(normalize_phone)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 20)
        super().__init__(*args, **kwargs)
        if E164_VALIDATOR not in self.validators:
            self.validators.append(E164_VALIDATOR)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop("validators", None)
        return name, path, args, kwargs


class HttpsUrlField(_NormalisingMixin, models.CharField):
    def __init__(self, *args, label="Link", allowed_domains=None, **kwargs):
        self.label = label
        self.allowed_domains = allowed_domains
        kwargs.setdefault("max_length", 200)
        super().__init__(*args, **kwargs)
        self.validators.append(HttpsUrlValidator(label, allowed_domains))

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["label"] = self.label
        if self.allowed_domains:
            kwargs["allowed_domains"] = self.allowed_domains
        return name, path, args, kwargs
