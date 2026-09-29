"""Add City.is_verified, verify the seeded Pakistani cities, and rename
Turkey to its current official name (Türkiye)."""

import json
from pathlib import Path

from django.db import migrations, models

DATA = Path(__file__).resolve().parent.parent / "data"


def verify_seeded_cities_and_rename_turkiye(apps, schema_editor):
    City = apps.get_model("reference", "City")
    Country = apps.get_model("reference", "Country")
    names = json.loads((DATA / "pakistan_cities.json").read_text(encoding="utf-8"))
    City.objects.filter(country__code="PK", name__in=names).update(is_verified=True)
    Country.objects.filter(code="TR").update(name="Türkiye")


def unverify_and_restore_turkey(apps, schema_editor):
    Country = apps.get_model("reference", "Country")
    Country.objects.filter(code="TR").update(name="Turkey")


class Migration(migrations.Migration):
    dependencies = [
        ("reference", "0002_seed_reference_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="city",
            name="is_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            verify_seeded_cities_and_rename_turkiye, unverify_and_restore_turkey
        ),
    ]
