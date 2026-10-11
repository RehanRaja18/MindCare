"""Model mixins shared across apps. `core` is not a Django app: nothing here
defines a concrete model or a migration.

ValidatedModelMixin makes the field rules in docs/validation-rules.md apply on
every save(), not only in forms and serializers, so services and management
commands can't store a value the API would reject.
"""

from django.core.exceptions import ValidationError

from core.exceptions import DomainValidationError


class ValidatedModelMixin:
    """save() runs full_clean() on the plain fields first.

    - Relations, uniqueness and constraints are left to the database (no extra
      queries per save).
    - save(update_fields=[...]) validates only those fields, so a row stored
      before a rule existed (e.g. a name with digits) can still be saved for
      something else, like last_login. The rule applies when that field is
      written next.
    - A failure raises DomainValidationError({field: [messages]}), which views
      turn into a 400. bulk_create(), QuerySet.update() and raw SQL bypass this:
      don't use them on user-entered fields.
    """

    def _fields_to_skip(self, update_fields):
        relations = {f.name for f in self._meta.concrete_fields if f.is_relation}
        if update_fields is None:
            return relations
        wanted = set(update_fields)
        return relations | {
            f.name
            for f in self._meta.concrete_fields
            if f.name not in wanted and f.attname not in wanted
        }

    def save(self, *args, **kwargs):
        exclude = self._fields_to_skip(kwargs.get("update_fields"))
        try:
            self.clean_fields(exclude=exclude)
            if kwargs.get("update_fields") is None:
                self.clean()
        except ValidationError as exc:
            raise DomainValidationError(exc.message_dict) from exc
        super().save(*args, **kwargs)
