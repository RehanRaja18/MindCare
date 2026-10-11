"""One seeded quote's author ("British wartime poster, 1939") breaks the person-
name rule (digits and a comma; docs/validation-rules.md). It is our own seed
content, not user data, so it is corrected here."""

from django.db import migrations

OLD = "British wartime poster, 1939"
NEW = "British wartime poster"


def forwards(apps, schema_editor):
    apps.get_model("motivation", "Quote").objects.filter(author=OLD).update(author=NEW)


def backwards(apps, schema_editor):
    apps.get_model("motivation", "Quote").objects.filter(
        author=NEW, text="Keep calm and carry on."
    ).update(author=OLD)


class Migration(migrations.Migration):
    dependencies = [("motivation", "0003_alter_quote_author_alter_quote_text")]

    operations = [migrations.RunPython(forwards, backwards)]
