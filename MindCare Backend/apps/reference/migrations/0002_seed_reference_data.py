"""Seed countries (ISO 3166-1), languages (ISO 639-1), major Pakistani cities,
and the PLACEHOLDER specialization list from apps/reference/data/*.json."""

import json
from pathlib import Path

from django.db import migrations

DATA = Path(__file__).resolve().parent.parent / "data"


def _load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def seed(apps, schema_editor):
    Country = apps.get_model("reference", "Country")
    City = apps.get_model("reference", "City")
    Language = apps.get_model("reference", "Language")
    Specialization = apps.get_model("reference", "Specialization")

    Country.objects.bulk_create(Country(**row) for row in _load("countries.json"))
    Language.objects.bulk_create(Language(**row) for row in _load("languages.json"))
    Specialization.objects.bulk_create(
        Specialization(**row) for row in _load("specializations.json")
    )
    pakistan = Country.objects.get(code="PK")
    City.objects.bulk_create(
        City(country=pakistan, name=name) for name in _load("pakistan_cities.json")
    )


def unseed(apps, schema_editor):
    """Reversing is only possible while no profile references these cities
    (on_delete=PROTECT), i.e. effectively on an empty database."""
    Country = apps.get_model("reference", "Country")
    City = apps.get_model("reference", "City")
    Language = apps.get_model("reference", "Language")
    Specialization = apps.get_model("reference", "Specialization")

    # Every city under a seeded country, not just the seeded Pakistani names:
    # Country rows can't be deleted while any City still points at them.
    City.objects.filter(
        country__code__in=[r["code"] for r in _load("countries.json")]
    ).delete()
    Specialization.objects.filter(
        slug__in=[r["slug"] for r in _load("specializations.json")]
    ).delete()
    Language.objects.filter(
        code__in=[r["code"] for r in _load("languages.json")]
    ).delete()
    Country.objects.filter(
        code__in=[r["code"] for r in _load("countries.json")]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("reference", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
