# Phase 2 — Profiles, Patient Privacy, Reference Data, Public Stats: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every patient / psychologist / NGO account a role-specific profile created atomically at registration, ship the patient privacy system, shared reference data, and `GET /api/v1/stats/public/`.

**Architecture:** Two new Django apps (`apps/reference` for Country/City/Language/Specialization, `apps/stats` for the public counts), profile models in the existing `patients` / `psychologists` / `ngo` apps, and `accounts.services.register_user()` orchestrating profile creation by **direct service calls inside one transaction** (no signals). Shared helpers go in `core/` (validators, choices, a domain exception, a strict-serializer mixin, audit, test factories).

**Tech Stack:** Django 6.1, DRF 3.18, simplejwt, PostgreSQL, pytest-django (tests are `django.test.TestCase` / `rest_framework.test.APITestCase` classes, matching `apps/accounts/tests/`).

**Spec:** `docs/superpowers/specs/2026-09-26-phase2-profiles-design.md` (approved 2026-09-27, incl. §16). Reasoning for every rule: `docs/decisions.md` (entries dated 2026-09-26 / 2026-09-27). Read both before starting.

## Global Constraints

- Branch: `backend-work`. Never commit to `main`. Never touch `MindCare Web/` or `MindCare App/`.
- **No new third-party packages.** Only stdlib + what is already in `requirements/`.
- Views are thin: parse → service (writes) / selector (reads) → serialize. Business rules live in `services.py` / `selectors.py`.
- No PHI in logs. `identity_reveal` logs IDs only.
- Every task appends its rows to `docs/module-reference.md` in the existing table format (sections alphabetical: `apps/accounts`, `apps/ngo`, `apps/patients`, `apps/psychologists`, `apps/reference`, `apps/stats`, then `config/`, `core/`).
- API tests post JSON: `self.client.post(url, data, format="json")`.
- Run tests from `MindCare Backend/` with `venv/Scripts/python -m pytest` (Windows) / `pytest` (CI). Full suite takes ~4 min; run single files while iterating.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Throttle scopes: `reference: "120/min"`, `public_stats: "60/min"` (existing: `login: "5/min"`, `register: "10/hour"`).
- Stats cache: key `stats:public:v1`, timeout `300`.
- Pseudonym: `"Patient-" + secrets.token_hex(3)`, max 5 generation attempts.
- Specialization list is a **placeholder** pending clinical-advisor review (say so in the seed file's companion comment and in admin `verbose_name`).

## File map

| File | Responsibility | Task |
|------|----------------|------|
| `core/exceptions.py` | `DomainValidationError` | 1 |
| `core/validators.py` | timezone / E.164 / 18+ DOB validators, text normalizers, `run_validator` | 1 |
| `core/choices.py` | `Gender` | 1 |
| `core/serializers.py` | `RejectUnknownFieldsMixin` | 1 |
| `core/audit.py` | + `log_identity_reveal()` | 1 |
| `core/tests/` | tests for the above | 1 |
| `apps/reference/**` | models, seed data + migrations, services, selectors, API, admin | 2 |
| `core/testing.py` | test factories (users, profile data, register payloads) | 3 |
| `apps/patients/**` | `PatientProfile`, services, display-identity selector, `/me/`, admin | 3 |
| `apps/psychologists/**` | `PsychologistProfile`, services, `/me/`, admin | 4 |
| `apps/ngo/**` | `NGOProfile`, `NGOServiceArea`, services, `/me/`, admin | 5 |
| `apps/accounts/**` | `adult_confirmed_at`, nested register, orchestration, existing test updates | 6 |
| `apps/accounts/admin.py` | Django admin for `User` (gap fix, see Task 7) | 7 |
| `apps/stats/**` | `GET /api/v1/stats/public/` | 8 |
| docs + DB verification | architecture, decisions, roadmap; real-schema check | 9 |

---

### Task 1: Shared core helpers (validators, choices, domain error, strict serializer, identity-reveal audit)

**Files:**
- Modify: `core/exceptions.py`, `core/audit.py`
- Create: `core/validators.py`, `core/choices.py`, `core/serializers.py`, `core/tests/__init__.py`, `core/tests/test_validators.py`, `core/tests/test_audit.py`, `core/tests/test_serializers.py`

**Interfaces:**
- Produces:
  - `core.exceptions.DomainValidationError(errors: dict[str, list[str]], *, code: str | None = None)` with attributes `.errors`, `.code` (default `"invalid"`).
  - `core.validators.validate_iana_timezone(value: str) -> None` (raises `django.core.exceptions.ValidationError`)
  - `core.validators.E164_VALIDATOR` (a `RegexValidator`)
  - `core.validators.validate_adult_date_of_birth(value: date, *, today: date | None = None) -> None`
  - `core.validators.age_on(dob: date, today: date) -> int`
  - `core.validators.normalize_display_text(value: str) -> str` (strip + collapse internal whitespace)
  - `core.validators.normalize_identifier(value: str) -> str` (strip + upper)
  - `core.validators.run_validator(validator, value, *, field: str) -> None` (re-raises as `DomainValidationError({field: [...]})`)
  - `core.choices.Gender` (`female`, `male`, `other`, `prefer_not_to_say`)
  - `core.serializers.RejectUnknownFieldsMixin`
  - `core.audit.log_identity_reveal(*, viewer_id: int, patient_id: int) -> None`

- [ ] **Step 1: Write the failing tests**

`core/tests/__init__.py`: empty file.

`core/tests/test_validators.py`:

```python
"""Tests for core/validators.py."""

from datetime import date

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from core.exceptions import DomainValidationError
from core.validators import (
    E164_VALIDATOR,
    age_on,
    normalize_display_text,
    normalize_identifier,
    run_validator,
    validate_adult_date_of_birth,
    validate_iana_timezone,
)


class TimezoneValidatorTests(SimpleTestCase):
    def test_accepts_iana_names(self):
        for tz in ["Asia/Karachi", "Europe/London", "America/Toronto", "UTC"]:
            validate_iana_timezone(tz)

    def test_rejects_unknown_names(self):
        for tz in ["Asia/Lahore", "PKT", "GMT+5", ""]:
            with self.assertRaises(ValidationError):
                validate_iana_timezone(tz)


class PhoneValidatorTests(SimpleTestCase):
    def test_accepts_e164(self):
        E164_VALIDATOR("+923001234567")
        E164_VALIDATOR("+442071838750")

    def test_rejects_non_e164(self):
        for value in ["03001234567", "+0123456789", "+92 300 1234567", "+12345"]:
            with self.assertRaises(ValidationError):
                E164_VALIDATOR(value)


class AdultDateOfBirthTests(SimpleTestCase):
    today = date(2026, 9, 28)

    def test_exactly_18_today_passes(self):
        validate_adult_date_of_birth(date(2008, 9, 28), today=self.today)

    def test_one_day_short_of_18_fails(self):
        with self.assertRaises(ValidationError):
            validate_adult_date_of_birth(date(2008, 9, 29), today=self.today)

    def test_future_date_fails(self):
        with self.assertRaises(ValidationError):
            validate_adult_date_of_birth(date(2027, 1, 1), today=self.today)

    def test_leap_day_birthday(self):
        self.assertEqual(age_on(date(2008, 2, 29), date(2026, 2, 28)), 17)
        self.assertEqual(age_on(date(2008, 2, 29), date(2026, 3, 1)), 18)


class NormalizerTests(SimpleTestCase):
    def test_display_text_collapses_whitespace(self):
        self.assertEqual(normalize_display_text("  Rahim   Yar  Khan "), "Rahim Yar Khan")

    def test_identifier_strips_and_uppercases(self):
        self.assertEqual(normalize_identifier("  pmdc-123 "), "PMDC-123")


class RunValidatorTests(SimpleTestCase):
    def test_wraps_django_error_as_domain_error(self):
        with self.assertRaises(DomainValidationError) as ctx:
            run_validator(validate_iana_timezone, "Nowhere/Land", field="timezone")
        self.assertIn("timezone", ctx.exception.errors)
        self.assertEqual(ctx.exception.code, "invalid")
```

`core/tests/test_audit.py`:

```python
"""Tests for core/audit.py's identity_reveal event."""

import json

from django.test import SimpleTestCase

from core.audit import log_identity_reveal


class LogIdentityRevealTests(SimpleTestCase):
    def test_emits_ids_only(self):
        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            log_identity_reveal(viewer_id=7, patient_id=42)
        self.assertEqual(len(captured.records), 1)
        payload = json.loads(captured.records[0].getMessage())
        self.assertEqual(
            set(payload), {"event_type", "timestamp", "viewer_id", "patient_id"}
        )
        self.assertEqual(payload["event_type"], "identity_reveal")
        self.assertEqual(payload["viewer_id"], 7)
        self.assertEqual(payload["patient_id"], 42)
```

`core/tests/test_serializers.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python -m pytest core/tests -q`
Expected: FAIL — `ImportError` / `ModuleNotFoundError` for `core.validators`, `core.serializers`, `log_identity_reveal`.

- [ ] **Step 3: Implement**

Replace `core/exceptions.py` with:

```python
"""
Shared exception types.

DomainValidationError is what services raise when a business rule rejects
input. Views translate it into a DRF ValidationError (400) so every app
renders rule violations the same way. A project-wide DRF exception handler
may be added here later.
"""


class DomainValidationError(Exception):
    """A business rule rejected the input. `errors` maps field name -> messages."""

    default_code = "invalid"

    def __init__(self, errors, *, code=None):
        super().__init__(errors)
        self.errors = errors
        self.code = code or self.default_code
```

Create `core/validators.py`:

```python
"""
Shared field validators and text normalizers used by more than one app.

Validators raise django.core.exceptions.ValidationError so they work on model
fields and DRF serializer fields alike. Services that need the same check
wrap them with run_validator(), which re-raises as DomainValidationError.
"""

from functools import cache
from zoneinfo import available_timezones

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone as dj_timezone

from core.exceptions import DomainValidationError

MINIMUM_AGE = 18

E164_VALIDATOR = RegexValidator(
    regex=r"^\+[1-9]\d{6,14}$",
    message="Enter a phone number in international format, e.g. +923001234567.",
)


@cache
def _iana_timezones():
    return frozenset(available_timezones())


def validate_iana_timezone(value):
    if value not in _iana_timezones():
        raise ValidationError(f"{value!r} is not a recognised IANA timezone.")


def age_on(dob, today):
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def validate_adult_date_of_birth(value, *, today=None):
    today = today or dj_timezone.localdate()
    if value > today:
        raise ValidationError("Date of birth can't be in the future.")
    if age_on(value, today) < MINIMUM_AGE:
        raise ValidationError("You must be 18 or older to use MindCare.")


def normalize_display_text(value):
    return " ".join(value.split())


def normalize_identifier(value):
    return value.strip().upper()


def run_validator(validator, value, *, field):
    try:
        validator(value)
    except ValidationError as exc:
        raise DomainValidationError({field: list(exc.messages)}) from exc

```

Create `core/choices.py`:

```python
"""Shared model choice sets used by more than one app."""

from django.db import models


class Gender(models.TextChoices):
    FEMALE = "female", "Female"
    MALE = "male", "Male"
    OTHER = "other", "Other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"
```

Create `core/serializers.py`:

```python
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
```

Append to `core/audit.py`:

```python


def log_identity_reveal(*, viewer_id, patient_id):
    """An admin resolved a private patient's real identity (see
    apps/patients/selectors.get_patient_display_identity). IDs only — never
    names, emails or anything else."""
    payload = {
        "event_type": "identity_reveal",
        "timestamp": timezone.now().isoformat(),
        "viewer_id": viewer_id,
        "patient_id": patient_id,
    }
    logger.info(json.dumps(payload))
```

Also update the module docstring's first paragraph in `core/audit.py` to mention `log_identity_reveal()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/Scripts/python -m pytest core/tests -q`
Expected: PASS (all tests in the three files).

- [ ] **Step 5: Add module-reference rows** under `### core/`:

```markdown
| `core/exceptions.py` | `DomainValidationError` | Raised by services when a business rule rejects input; views turn it into a 400 | — | neither (internal) |
| `core/validators.py` | `validate_iana_timezone`, `E164_VALIDATOR`, `validate_adult_date_of_birth`, `normalize_display_text`, `normalize_identifier`, `run_validator` | Shared validators/normalizers for profile fields (timezone, phone, 18+ DOB, city names, license/registration numbers) | — | neither (internal) |
| `core/choices.py` | `Gender` | Shared gender choices for patient/psychologist profiles | — | MindCare Web, MindCare App |
| `core/serializers.py` | `RejectUnknownFieldsMixin` | Makes serializers reject undeclared keys (e.g. `pseudonym`) with a 400 | — | neither (internal) |
| `core/audit.py` | `log_identity_reveal()` | Logs `identity_reveal` (viewer id, patient id only) when an admin resolves a private patient's real name | — | neither (internal) |
```

- [ ] **Step 6: Commit**

```bash
git add core docs/module-reference.md
git commit -m "feat(core): shared validators, Gender choices, DomainValidationError, identity_reveal audit

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `apps/reference` — Country, City, Language, Specialization

**Files:**
- Create: `apps/reference/__init__.py`, `apps.py`, `models.py`, `services.py`, `selectors.py`, `admin.py`, `permissions.py`, `tasks.py`, `api/__init__.py`, `api/serializers.py`, `api/views.py`, `api/urls.py`, `migrations/__init__.py`, `migrations/0001_initial.py` (generated), `migrations/0002_seed_reference_data.py`, `data/countries.json`, `data/languages.json`, `data/pakistan_cities.json`, `data/specializations.json`, `tests/__init__.py`, `tests/test_services.py`, `tests/test_selectors.py`, `tests/test_api.py`, `tests/test_seed.py`
- Modify: `config/settings/base.py` (LOCAL_APPS, throttle rate), `config/urls.py` (API_V1_APPS)

**Interfaces:**
- Consumes: `core.validators.normalize_display_text`, `core.exceptions.DomainValidationError`
- Produces:
  - Models `Country(code, name)`, `City(country, name)`, `Language(code, name, is_active)`, `Specialization(slug, name, is_active)`
  - `reference.services.resolve_city(*, country: Country, name: str) -> City`
  - `reference.services.resolve_location_fields(*, current_country: Country | None, current_city: City | None, fields: dict, city_required: bool) -> dict` — mutates and returns `fields`: replaces a `"city"` name with a `City` (or `None`), enforces country rules.
  - `reference.services.ensure_active_choices(*, items: list, field: str) -> None`
  - `reference.selectors.list_countries()`, `search_cities(*, country_code, search=None, limit=20)`, `list_languages()`, `list_specializations()`
  - `reference.api.serializers.CountrySerializer`, `CitySerializer`, `LanguageSerializer`, `SpecializationSerializer`

- [ ] **Step 1: Scaffold the app and data files**

`apps/reference/apps.py`:

```python
from django.apps import AppConfig


class ReferenceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reference"
    verbose_name = "Reference data"
```

`permissions.py` / `tasks.py`: one-line docstrings matching the other apps (`"""App-specific DRF permission classes for reference."""`, `"""Celery tasks for reference. None yet."""`). Empty `__init__.py` files for the package, `api/`, `migrations/`, `tests/`.

Add `"apps.reference"` to `LOCAL_APPS` in `config/settings/base.py` (after `"apps.accounts"`), and `"reference"` to `API_V1_APPS` in `config/urls.py`. Add `"reference": "120/min"` to `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`.

Data files (UTF-8 JSON, arrays):
- `data/countries.json` — **all 249 ISO 3166-1 officially assigned alpha-2 codes** with English short names, e.g. `[{"code": "AF", "name": "Afghanistan"}, ..., {"code": "PK", "name": "Pakistan"}, ...]`. No user-assigned codes (no `XK`).
- `data/languages.json` — **all current ISO 639-1 codes (183)** with English names, e.g. `{"code": "ur", "name": "Urdu"}`. Must include `en ur ar pa ps sd fa hi bn zh de fr es tr`.
- `data/pakistan_cities.json` — exactly this list:

```json
["Karachi", "Lahore", "Faisalabad", "Rawalpindi", "Gujranwala", "Peshawar",
 "Multan", "Hyderabad", "Islamabad", "Quetta", "Bahawalpur", "Sargodha",
 "Sialkot", "Sukkur", "Larkana", "Sheikhupura", "Rahim Yar Khan", "Jhang",
 "Dera Ghazi Khan", "Gujrat", "Sahiwal", "Wah Cantonment", "Mardan", "Kasur",
 "Okara", "Mingora", "Nawabshah", "Chiniot", "Abbottabad", "Gilgit",
 "Muzaffarabad", "Mirpur"]
```

- `data/specializations.json` — exactly:

```json
[
 {"slug": "anxiety", "name": "Anxiety"},
 {"slug": "depression", "name": "Depression"},
 {"slug": "trauma-ptsd", "name": "Trauma / PTSD"},
 {"slug": "couples-relationship", "name": "Couples / Relationship"},
 {"slug": "grief", "name": "Grief"},
 {"slug": "addiction-substance-use", "name": "Addiction / Substance use"},
 {"slug": "stress-management", "name": "Stress management"},
 {"slug": "ocd", "name": "OCD"},
 {"slug": "eating-disorders", "name": "Eating disorders"},
 {"slug": "sleep-issues", "name": "Sleep issues"},
 {"slug": "anger-management", "name": "Anger management"},
 {"slug": "family-therapy", "name": "Family therapy"}
]
```

- [ ] **Step 2: Write the models**

`apps/reference/models.py`:

```python
"""Shared, admin-editable reference data used by every profile app.

Seeded once by data migrations, then maintained in Django admin — corrections
never need a code change or a new migration. Language/Specialization are
retired with is_active=False, never deleted (profiles reference them with
on_delete=PROTECT).
"""

from django.db import models
from django.db.models.functions import Lower


class Country(models.Model):
    code = models.CharField(max_length=2, unique=True)  # ISO 3166-1 alpha-2
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "countries"

    def __str__(self):
        return self.name


class City(models.Model):
    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, related_name="cities"
    )
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "cities"
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "country",
                name="reference_city_unique_name_per_country_ci",
            )
        ]

    def __str__(self):
        return f"{self.name}, {self.country.code}"


class Language(models.Model):
    code = models.CharField(max_length=2, unique=True)  # ISO 639-1
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Specialization(models.Model):
    """PLACEHOLDER taxonomy — must be reviewed by a clinical advisor before
    real launch (docs/decisions.md, 2026-09-26)."""

    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "specialization (placeholder list)"

    def __str__(self):
        return self.name
```

Run: `venv/Scripts/python manage.py makemigrations reference`
Expected: `apps/reference/migrations/0001_initial.py` created with 4 models and the functional unique constraint.

- [ ] **Step 3: Write the seed test (fails first)**

`apps/reference/tests/test_seed.py`:

```python
"""The seed data migration loaded the expected reference rows."""

import json
from pathlib import Path

from django.test import TestCase

from apps.reference.models import City, Country, Language, Specialization

DATA = Path(__file__).resolve().parent.parent / "data"


def _load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


class SeedDataTests(TestCase):
    def test_all_iso_countries_seeded(self):
        self.assertEqual(Country.objects.count(), 249)
        self.assertEqual(len({c["code"] for c in _load("countries.json")}), 249)
        for code in ["PK", "GB", "US", "DE", "AE", "SA", "IN", "CN", "CA"]:
            self.assertTrue(Country.objects.filter(code=code).exists(), code)

    def test_languages_seeded_and_active(self):
        self.assertEqual(Language.objects.count(), len(_load("languages.json")))
        self.assertGreaterEqual(Language.objects.count(), 180)
        for code in ["en", "ur", "ar", "pa", "ps", "sd", "fa", "hi", "zh"]:
            self.assertTrue(Language.objects.filter(code=code, is_active=True).exists(), code)

    def test_pakistani_cities_seeded(self):
        expected = _load("pakistan_cities.json")
        self.assertEqual(City.objects.filter(country__code="PK").count(), len(expected))
        self.assertTrue(City.objects.filter(country__code="PK", name="Lahore").exists())

    def test_placeholder_specializations_seeded(self):
        self.assertEqual(Specialization.objects.filter(is_active=True).count(), 12)
```

Run: `venv/Scripts/python -m pytest apps/reference/tests/test_seed.py -q`
Expected: FAIL (counts are 0 — no data migration yet).

- [ ] **Step 4: Write the data migration**

`apps/reference/migrations/0002_seed_reference_data.py`:

```python
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
    Country = apps.get_model("reference", "Country")
    City = apps.get_model("reference", "City")
    Language = apps.get_model("reference", "Language")
    Specialization = apps.get_model("reference", "Specialization")

    City.objects.filter(
        country__code="PK", name__in=_load("pakistan_cities.json")
    ).delete()
    Specialization.objects.filter(
        slug__in=[r["slug"] for r in _load("specializations.json")]
    ).delete()
    Language.objects.filter(code__in=[r["code"] for r in _load("languages.json")]).delete()
    Country.objects.filter(code__in=[r["code"] for r in _load("countries.json")]).delete()


class Migration(migrations.Migration):
    dependencies = [("reference", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
```

Run: `venv/Scripts/python -m pytest apps/reference/tests/test_seed.py -q`
Expected: PASS.

- [ ] **Step 5: Write failing service + selector tests**

`apps/reference/tests/test_services.py`:

```python
"""Service-layer tests for reference."""

from django.test import TestCase

from apps.reference.models import City, Country, Language
from apps.reference.services import (
    ensure_active_choices,
    resolve_city,
    resolve_location_fields,
)
from core.exceptions import DomainValidationError


class ResolveCityTests(TestCase):
    def setUp(self):
        self.pk = Country.objects.get(code="PK")
        self.gb = Country.objects.get(code="GB")

    def test_reuses_seeded_city_case_and_whitespace_insensitively(self):
        city = resolve_city(country=self.pk, name="  lahore ")
        self.assertEqual(city.name, "Lahore")
        self.assertEqual(City.objects.filter(country=self.pk, name__iexact="lahore").count(), 1)

    def test_creates_new_city_once(self):
        first = resolve_city(country=self.gb, name="london")
        second = resolve_city(country=self.gb, name="LONDON")
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.name, "london")

    def test_same_name_in_different_countries_is_distinct(self):
        a = resolve_city(country=self.pk, name="Hyderabad")
        b = resolve_city(country=Country.objects.get(code="IN"), name="Hyderabad")
        self.assertNotEqual(a.pk, b.pk)

    def test_blank_name_rejected(self):
        with self.assertRaises(DomainValidationError) as ctx:
            resolve_city(country=self.pk, name="   ")
        self.assertIn("city", ctx.exception.errors)

    def test_too_long_name_rejected(self):
        with self.assertRaises(DomainValidationError):
            resolve_city(country=self.pk, name="x" * 121)


class ResolveLocationFieldsTests(TestCase):
    def setUp(self):
        self.pk = Country.objects.get(code="PK")
        self.gb = Country.objects.get(code="GB")
        self.lahore = City.objects.get(country=self.pk, name="Lahore")

    def test_city_name_resolved_against_new_country(self):
        fields = resolve_location_fields(
            current_country=None, current_city=None,
            fields={"country": self.gb, "city": "Leeds"}, city_required=False,
        )
        self.assertEqual(fields["city"].country, self.gb)

    def test_city_without_any_country_rejected(self):
        with self.assertRaises(DomainValidationError):
            resolve_location_fields(
                current_country=None, current_city=None,
                fields={"city": "Leeds"}, city_required=False,
            )

    def test_country_cannot_be_cleared_once_set(self):
        with self.assertRaises(DomainValidationError):
            resolve_location_fields(
                current_country=self.pk, current_city=self.lahore,
                fields={"country": None}, city_required=False,
            )

    def test_changing_country_clears_stale_optional_city(self):
        fields = resolve_location_fields(
            current_country=self.pk, current_city=self.lahore,
            fields={"country": self.gb}, city_required=False,
        )
        self.assertIsNone(fields["city"])

    def test_changing_country_without_city_rejected_when_city_required(self):
        with self.assertRaises(DomainValidationError):
            resolve_location_fields(
                current_country=self.pk, current_city=self.lahore,
                fields={"country": self.gb}, city_required=True,
            )

    def test_blank_city_rejected_when_required(self):
        with self.assertRaises(DomainValidationError):
            resolve_location_fields(
                current_country=self.pk, current_city=self.lahore,
                fields={"city": ""}, city_required=True,
            )


class EnsureActiveChoicesTests(TestCase):
    def test_empty_rejected(self):
        with self.assertRaises(DomainValidationError):
            ensure_active_choices(items=[], field="languages")

    def test_inactive_rejected(self):
        lang = Language.objects.get(code="en")
        lang.is_active = False
        lang.save()
        with self.assertRaises(DomainValidationError):
            ensure_active_choices(items=[lang], field="languages")

    def test_active_passes(self):
        ensure_active_choices(items=[Language.objects.get(code="ur")], field="languages")
```

`apps/reference/tests/test_selectors.py`:

```python
"""Selector tests for reference."""

from django.test import TestCase

from apps.reference.models import Language
from apps.reference.selectors import (
    list_languages,
    list_specializations,
    search_cities,
)


class SearchCitiesTests(TestCase):
    def test_prefix_search_case_insensitive_and_scoped_to_country(self):
        names = [c.name for c in search_cities(country_code="pk", search="la")]
        self.assertIn("Lahore", names)
        self.assertIn("Larkana", names)
        self.assertNotIn("Islamabad", names)

    def test_limit(self):
        self.assertEqual(len(search_cities(country_code="PK", limit=5)), 5)


class ActiveListTests(TestCase):
    def test_inactive_language_hidden(self):
        Language.objects.filter(code="en").update(is_active=False)
        self.assertNotIn("en", [lang.code for lang in list_languages()])

    def test_specializations_listed(self):
        self.assertEqual(len(list_specializations()), 12)
```

Run: `venv/Scripts/python -m pytest apps/reference/tests/test_services.py apps/reference/tests/test_selectors.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 6: Implement services and selectors**

`apps/reference/services.py`:

```python
"""Write-path business logic for reference data.

Cities are created only as a side effect of a profile write — there is no
public city-create endpoint (spec §3.4).
"""

from django.db import IntegrityError, transaction

from apps.reference.models import City
from core.exceptions import DomainValidationError
from core.validators import normalize_display_text

CITY_NAME_MAX_LENGTH = 120


def resolve_city(*, country, name):
    cleaned = normalize_display_text(name or "")
    if not cleaned:
        raise DomainValidationError({"city": ["City name can't be empty."]})
    if len(cleaned) > CITY_NAME_MAX_LENGTH:
        raise DomainValidationError({"city": ["City name is too long."]})

    existing = City.objects.filter(country=country, name__iexact=cleaned).first()
    if existing is not None:
        return existing
    try:
        with transaction.atomic():
            return City.objects.create(country=country, name=cleaned)
    except IntegrityError:
        # Another request created the same city between our lookup and insert.
        return City.objects.get(country=country, name__iexact=cleaned)


def resolve_location_fields(*, current_country, current_city, fields, city_required):
    """Validate/resolve `country` + `city` in a profile write. `fields["city"]`
    comes in as a name (str) and leaves as a City or None. Mutates `fields`."""
    if "country" in fields and fields["country"] is None and current_country is not None:
        raise DomainValidationError({"country": ["Country can't be removed once set."]})
    country = fields.get("country", current_country)

    if "city" in fields:
        name = fields["city"]
        if not name:
            if city_required:
                raise DomainValidationError({"city": ["City is required."]})
            fields["city"] = None
        else:
            if country is None:
                raise DomainValidationError({"city": ["Choose a country before a city."]})
            fields["city"] = resolve_city(country=country, name=name)
    elif (
        "country" in fields
        and current_city is not None
        and current_city.country_id != country.pk
    ):
        if city_required:
            raise DomainValidationError(
                {"city": ["Changing country needs a city in the new country."]}
            )
        fields["city"] = None
    return fields


def ensure_active_choices(*, items, field):
    if not items:
        raise DomainValidationError({field: ["Choose at least one."]})
    inactive = [str(item) for item in items if not item.is_active]
    if inactive:
        raise DomainValidationError(
            {field: [f"No longer available: {', '.join(inactive)}."]}
        )
```

`apps/reference/selectors.py`:

```python
"""Read-path query logic for reference data. All public (no PHI)."""

from apps.reference.models import City, Country, Language, Specialization
from core.validators import normalize_display_text


def list_countries():
    return Country.objects.all()


def search_cities(*, country_code, search=None, limit=20):
    qs = City.objects.filter(country__code=country_code.upper()).select_related("country")
    if search:
        qs = qs.filter(name__istartswith=normalize_display_text(search))
    return list(qs.order_by("name")[:limit])


def list_languages():
    return Language.objects.filter(is_active=True)


def list_specializations():
    return list(Specialization.objects.filter(is_active=True))
```

Run: `venv/Scripts/python -m pytest apps/reference/tests -q`
Expected: PASS.

- [ ] **Step 7: Write failing API tests**

`apps/reference/tests/test_api.py`:

```python
"""API-layer tests for reference (all public, read-only)."""

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

BASE = "/api/v1/reference"


class ReferenceAPITests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_countries_public(self):
        r = self.client.get(f"{BASE}/countries/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn({"code": "PK", "name": "Pakistan"}, r.data)

    def test_cities_requires_country(self):
        self.assertEqual(
            self.client.get(f"{BASE}/cities/").status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_cities_search(self):
        r = self.client.get(f"{BASE}/cities/", {"country": "PK", "search": "lah"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data[0]["name"], "Lahore")
        self.assertEqual(r.data[0]["country"], "PK")
        self.assertIn("id", r.data[0])

    def test_languages_and_specializations_public(self):
        langs = self.client.get(f"{BASE}/languages/")
        specs = self.client.get(f"{BASE}/specializations/")
        self.assertEqual(langs.status_code, status.HTTP_200_OK)
        self.assertEqual(specs.status_code, status.HTTP_200_OK)
        self.assertIn("anxiety", [s["slug"] for s in specs.data])

    def test_invalid_bearer_token_does_not_block_public_endpoint(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        self.assertEqual(
            self.client.get(f"{BASE}/countries/").status_code, status.HTTP_200_OK
        )

    def test_no_write_methods(self):
        r = self.client.post(f"{BASE}/cities/", {"country": "PK", "name": "X"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
```

Run: `venv/Scripts/python -m pytest apps/reference/tests/test_api.py -q`
Expected: FAIL (404s).

- [ ] **Step 8: Implement serializers, views, urls, admin**

`apps/reference/api/serializers.py`:

```python
"""DRF serializers for reference data."""

from rest_framework import serializers

from apps.reference.models import City, Country, Language, Specialization


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["code", "name"]


class CitySerializer(serializers.ModelSerializer):
    country = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = City
        fields = ["id", "name", "country"]


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ["code", "name"]


class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = ["slug", "name"]
```

`apps/reference/api/views.py`:

```python
"""DRF views for reference data.

Public (registration forms need them before the user has an account), so
authentication is disabled: an expired token must not turn a dropdown into a
401. Rate-limited per IP.
"""

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.reference import selectors
from apps.reference.api.serializers import (
    CitySerializer,
    CountrySerializer,
    LanguageSerializer,
    SpecializationSerializer,
)


class ReferenceRateThrottle(AnonRateThrottle):
    scope = "reference"


class _PublicReferenceView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ReferenceRateThrottle]


class CountryListView(_PublicReferenceView):
    def get(self, request):
        return Response(CountrySerializer(selectors.list_countries(), many=True).data)


class CityListView(_PublicReferenceView):
    def get(self, request):
        country = request.query_params.get("country")
        if not country:
            raise ValidationError({"country": ["This query parameter is required."]})
        cities = selectors.search_cities(
            country_code=country, search=request.query_params.get("search")
        )
        return Response(CitySerializer(cities, many=True).data)


class LanguageListView(_PublicReferenceView):
    def get(self, request):
        return Response(LanguageSerializer(selectors.list_languages(), many=True).data)


class SpecializationListView(_PublicReferenceView):
    def get(self, request):
        return Response(
            SpecializationSerializer(selectors.list_specializations(), many=True).data
        )
```

`apps/reference/api/urls.py`:

```python
"""URL routes for the reference API, included under /api/v1/reference/."""

from django.urls import path

from apps.reference.api.views import (
    CityListView,
    CountryListView,
    LanguageListView,
    SpecializationListView,
)

app_name = "reference"

urlpatterns = [
    path("countries/", CountryListView.as_view(), name="countries"),
    path("cities/", CityListView.as_view(), name="cities"),
    path("languages/", LanguageListView.as_view(), name="languages"),
    path("specializations/", SpecializationListView.as_view(), name="specializations"),
]
```

`apps/reference/admin.py`:

```python
"""Django admin for reference data — the place admins correct it."""

from django.contrib import admin

from apps.reference.models import City, Country, Language, Specialization


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["code", "name"]
    search_fields = ["code", "name"]


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "country"]
    list_filter = ["country"]
    search_fields = ["name"]
    autocomplete_fields = ["country"]


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["slug", "name"]
    prepopulated_fields = {"slug": ["name"]}
```

Run: `venv/Scripts/python -m pytest apps/reference -q`
Expected: PASS.

- [ ] **Step 9: Add module-reference rows** — new `### apps/reference` section:

```markdown
| `apps/reference/models.py` | `Country`, `City`, `Language`, `Specialization` | Shared reference data; seeded by migration 0002 (ISO 3166-1, ISO 639-1, major Pakistani cities, PLACEHOLDER specializations), maintained in Django admin | — | MindCare Web, MindCare App |
| `apps/reference/services.py` | `resolve_city()` | Case/whitespace-insensitive city match per country, creating it if new (race-safe) | — (used by profile writes) | MindCare Web, MindCare App |
| `apps/reference/services.py` | `resolve_location_fields()` | Shared country/city rules for profile writes | — | neither (internal) |
| `apps/reference/services.py` | `ensure_active_choices()` | Rejects empty or retired language/specialization choices | — | neither (internal) |
| `apps/reference/selectors.py` | `list_countries()`, `search_cities()`, `list_languages()`, `list_specializations()` | Public dropdown data | see views | MindCare Web, MindCare App |
| `apps/reference/api/views.py` | `CountryListView` | List countries | `GET /api/v1/reference/countries/` | MindCare Web, MindCare App |
| `apps/reference/api/views.py` | `CityListView` | Prefix city search within a country (max 20) | `GET /api/v1/reference/cities/?country=PK&search=lah` | MindCare Web, MindCare App |
| `apps/reference/api/views.py` | `LanguageListView` | List active languages | `GET /api/v1/reference/languages/` | MindCare Web, MindCare App |
| `apps/reference/api/views.py` | `SpecializationListView` | List active specializations | `GET /api/v1/reference/specializations/` | MindCare Web |
```

- [ ] **Step 10: Commit**

```bash
git add apps/reference config docs/module-reference.md
git commit -m "feat(reference): countries, cities, languages, specializations with seed data and public endpoints

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `apps/patients` — PatientProfile, privacy selector, `/me/`

**Files:**
- Create: `core/testing.py`, `apps/patients/admin.py`, `apps/patients/migrations/0001_initial.py` (generated), `apps/patients/tests/test_selectors.py`
- Modify: `apps/patients/models.py`, `services.py`, `selectors.py`, `api/serializers.py`, `api/views.py`, `api/urls.py`, `tests/test_services.py`, `tests/test_api.py`

**Interfaces:**
- Consumes: Task 1 (`DomainValidationError`, validators, `Gender`, `RejectUnknownFieldsMixin`, `log_identity_reveal`), Task 2 (`Country`, `City`, `Language`, `resolve_location_fields`, reference serializers)
- Produces:
  - `PatientProfile` (spec §5.1); `patients.models.generate_pseudonym() -> str`; `PSEUDONYM_PREFIX = "Patient-"`
  - `patients.services.create_patient_profile(*, user, timezone) -> PatientProfile`
  - `patients.services.update_patient_profile(*, profile, **fields) -> PatientProfile`
  - `patients.services.PseudonymGenerationError`
  - `patients.selectors.get_patient_profile_for_user(*, user) -> PatientProfile | None`
  - `patients.selectors.get_patient_display_identity(*, patient_profile, viewer) -> {"display_name": str, "is_real_name": bool}`
  - `patients.api.serializers.PatientRegistrationProfileSerializer`, `PatientProfileOwnerSerializer`
  - `core.testing.make_user(*, role, approval_status=ApprovalStatus.APPROVED, **extra) -> User`, `core.testing.make_admin(**extra) -> User`, `core.testing.PATIENT_PROFILE_DATA = {"timezone": "Asia/Karachi"}`

- [ ] **Step 1: Create the test factories**

`core/testing.py` (imported by tests only; Tasks 4–6 extend it):

```python
"""Test factories shared across apps' test suites. Not used by runtime code."""

import uuid

from apps.accounts.models import ApprovalStatus, Role, User

PASSWORD = "strongpass123"
PATIENT_PROFILE_DATA = {"timezone": "Asia/Karachi"}


def make_user(*, role, approval_status=ApprovalStatus.APPROVED, **extra):
    tag = uuid.uuid4().hex[:8]
    return User.objects.create_user(
        email=extra.pop("email", f"{role}-{tag}@example.com"),
        password=PASSWORD,
        full_name=extra.pop("full_name", f"Test {role.title()} {tag}"),
        role=role,
        approval_status=approval_status,
        **extra,
    )


def make_admin(**extra):
    return make_user(role=Role.ADMIN, **extra)
```

- [ ] **Step 2: Model**

Replace `apps/patients/models.py`:

```python
"""Database models for the patients app.

Phase 2 PatientProfile holds identity, demographics and preferences only — no
health data before the Phase 5 audit trail (docs/decisions.md, 2026-09-26).
"""

import secrets

from django.conf import settings
from django.db import models

from core.choices import Gender
from core.validators import E164_VALIDATOR, validate_iana_timezone

PSEUDONYM_PREFIX = "Patient-"


def generate_pseudonym():
    return f"{PSEUDONYM_PREFIX}{secrets.token_hex(3)}"


class PatientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile",
    )
    # Immutable, never usable for login. Shown instead of the real name unless
    # is_profile_public (see selectors.get_patient_display_identity).
    pseudonym = models.CharField(max_length=16, unique=True, editable=False)
    is_profile_public = models.BooleanField(default=False)
    country = models.ForeignKey(
        "reference.Country", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    city = models.ForeignKey(
        "reference.City", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    timezone = models.CharField(max_length=64, validators=[validate_iana_timezone])
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, null=True, blank=True)
    # Contact number only — NOT a login identifier. Phone-number login, if built,
    # gets its own unique, verified field on User (docs/decisions.md, 2026-09-26).
    phone_number = models.CharField(
        max_length=20, null=True, blank=True, validators=[E164_VALIDATOR]
    )
    preferred_language = models.ForeignKey(
        "reference.Language", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.pseudonym
```

Run: `venv/Scripts/python manage.py makemigrations patients`
Expected: `apps/patients/migrations/0001_initial.py` depending on `accounts` and `reference`.

- [ ] **Step 3: Write failing service tests**

`apps/patients/tests/test_services.py` (keep the module docstring, replace the rest):

```python
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone as dj_timezone

from apps.accounts.models import Role
from apps.patients.services import (
    PseudonymGenerationError,
    create_patient_profile,
    update_patient_profile,
)
from apps.reference.models import City, Country, Language
from core.exceptions import DomainValidationError
from core.testing import make_user


def _eighteenth_birthday_today():
    today = dj_timezone.localdate()
    try:
        return today.replace(year=today.year - 18)
    except ValueError:  # today is Feb 29
        return today.replace(year=today.year - 18, day=28)


class CreatePatientProfileTests(TestCase):
    def test_creates_profile_with_pseudonym_and_private_default(self):
        profile = create_patient_profile(user=make_user(role=Role.PATIENT), timezone="Asia/Karachi")
        self.assertRegex(profile.pseudonym, r"^Patient-[0-9a-f]{6}$")
        self.assertFalse(profile.is_profile_public)
        self.assertEqual(profile.timezone, "Asia/Karachi")

    def test_rejects_non_patient_user(self):
        with self.assertRaises(ValueError):
            create_patient_profile(user=make_user(role=Role.PSYCHOLOGIST), timezone="UTC")

    def test_rejects_invalid_timezone(self):
        with self.assertRaises(DomainValidationError):
            create_patient_profile(user=make_user(role=Role.PATIENT), timezone="Mars/Base")

    def test_retries_on_pseudonym_collision(self):
        first = create_patient_profile(user=make_user(role=Role.PATIENT), timezone="UTC")
        with patch(
            "apps.patients.services.generate_pseudonym",
            side_effect=[first.pseudonym, "Patient-abcdef"],
        ):
            second = create_patient_profile(user=make_user(role=Role.PATIENT), timezone="UTC")
        self.assertEqual(second.pseudonym, "Patient-abcdef")

    def test_gives_up_after_five_collisions(self):
        first = create_patient_profile(user=make_user(role=Role.PATIENT), timezone="UTC")
        with patch("apps.patients.services.generate_pseudonym", return_value=first.pseudonym):
            with self.assertRaises(PseudonymGenerationError):
                create_patient_profile(user=make_user(role=Role.PATIENT), timezone="UTC")


class UpdatePatientProfileTests(TestCase):
    def setUp(self):
        self.profile = create_patient_profile(
            user=make_user(role=Role.PATIENT), timezone="Asia/Karachi"
        )
        self.pk = Country.objects.get(code="PK")
        self.gb = Country.objects.get(code="GB")

    def test_updates_location_and_preferences(self):
        update_patient_profile(
            profile=self.profile,
            country=self.pk,
            city="lahore",
            gender="female",
            phone_number="+923001234567",
            preferred_language=Language.objects.get(code="ur"),
            is_profile_public=True,
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.city, City.objects.get(country=self.pk, name="Lahore"))
        self.assertTrue(self.profile.is_profile_public)

    def test_pseudonym_never_changes(self):
        original = self.profile.pseudonym
        with self.assertRaises(DomainValidationError):
            update_patient_profile(profile=self.profile, pseudonym="Patient-000000")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.pseudonym, original)

    def test_dob_exactly_18_accepted_one_day_short_rejected(self):
        birthday = _eighteenth_birthday_today()
        update_patient_profile(profile=self.profile, date_of_birth=birthday)
        with self.assertRaises(DomainValidationError) as ctx:
            update_patient_profile(profile=self.profile, date_of_birth=birthday + timedelta(days=1))
        self.assertIn("date_of_birth", ctx.exception.errors)

    def test_dob_can_be_cleared(self):
        update_patient_profile(profile=self.profile, date_of_birth=None)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.date_of_birth)

    def test_city_without_country_rejected(self):
        with self.assertRaises(DomainValidationError):
            update_patient_profile(profile=self.profile, city="Lahore")

    def test_changing_country_clears_stale_city(self):
        update_patient_profile(profile=self.profile, country=self.pk, city="Lahore")
        profile = update_patient_profile(profile=self.profile, country=self.gb)
        self.assertIsNone(profile.city)

    def test_invalid_phone_rejected(self):
        with self.assertRaises(DomainValidationError):
            update_patient_profile(profile=self.profile, phone_number="03001234567")

    def test_unknown_field_rejected(self):
        with self.assertRaises(DomainValidationError):
            update_patient_profile(profile=self.profile, diagnosis="x")
```

Run: `venv/Scripts/python -m pytest apps/patients/tests/test_services.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 4: Implement services**

`apps/patients/services.py` (keep docstring, then):

```python
from django.db import IntegrityError, transaction

from apps.accounts.models import Role
from apps.patients.models import PatientProfile, generate_pseudonym
from apps.reference.services import resolve_location_fields
from core.exceptions import DomainValidationError
from core.validators import (
    E164_VALIDATOR,
    run_validator,
    validate_adult_date_of_birth,
    validate_iana_timezone,
)

MAX_PSEUDONYM_ATTEMPTS = 5

UPDATABLE_FIELDS = {
    "is_profile_public",
    "country",
    "city",
    "timezone",
    "date_of_birth",
    "gender",
    "phone_number",
    "preferred_language",
}


class PseudonymGenerationError(Exception):
    """Could not generate a unique pseudonym after MAX_PSEUDONYM_ATTEMPTS."""


def create_patient_profile(*, user, timezone):
    if user.role != Role.PATIENT:
        raise ValueError("Patient profiles can only be created for patient users.")
    run_validator(validate_iana_timezone, timezone, field="timezone")

    for _ in range(MAX_PSEUDONYM_ATTEMPTS):
        try:
            with transaction.atomic():
                return PatientProfile.objects.create(
                    user=user, pseudonym=generate_pseudonym(), timezone=timezone
                )
        except IntegrityError:
            if PatientProfile.objects.filter(user=user).exists():
                raise
            # Otherwise it was a pseudonym collision: try a fresh one.
    raise PseudonymGenerationError("Could not generate a unique pseudonym.")


def update_patient_profile(*, profile, **fields):
    unknown = sorted(set(fields) - UPDATABLE_FIELDS)
    if unknown:
        raise DomainValidationError({name: ["This field can't be updated."] for name in unknown})

    if fields.get("timezone") is not None:
        run_validator(validate_iana_timezone, fields["timezone"], field="timezone")
    if fields.get("phone_number"):
        run_validator(E164_VALIDATOR, fields["phone_number"], field="phone_number")
    elif "phone_number" in fields:
        fields["phone_number"] = None
    if fields.get("date_of_birth") is not None:
        run_validator(validate_adult_date_of_birth, fields["date_of_birth"], field="date_of_birth")

    resolve_location_fields(
        current_country=profile.country,
        current_city=profile.city,
        fields=fields,
        city_required=False,
    )

    for name, value in fields.items():
        setattr(profile, name, value)
    profile.save()
    return profile
```

Run: `venv/Scripts/python -m pytest apps/patients/tests/test_services.py -q`
Expected: PASS.

- [ ] **Step 5: Write failing selector tests**

`apps/patients/tests/test_selectors.py`:

```python
"""Selector tests for patients, focused on the display-identity privacy rules."""

import json

from django.test import TestCase

from apps.accounts.models import Role
from apps.patients.selectors import get_patient_display_identity
from apps.patients.services import create_patient_profile, update_patient_profile
from core.testing import make_admin, make_user


class DisplayIdentityTests(TestCase):
    def setUp(self):
        self.patient = make_user(role=Role.PATIENT, full_name="Ayesha Khan")
        self.profile = create_patient_profile(user=self.patient, timezone="UTC")

    def _identity(self, viewer):
        return get_patient_display_identity(patient_profile=self.profile, viewer=viewer)

    def test_result_has_only_two_keys(self):
        self.assertEqual(set(self._identity(None)), {"display_name", "is_real_name"})

    def test_patient_sees_own_real_name(self):
        self.assertEqual(self._identity(self.patient)["display_name"], "Ayesha Khan")

    def test_anonymous_and_other_patients_see_pseudonym_when_private(self):
        for viewer in [None, make_user(role=Role.PATIENT)]:
            result = self._identity(viewer)
            self.assertEqual(result["display_name"], self.profile.pseudonym)
            self.assertFalse(result["is_real_name"])

    def test_psychologist_sees_pseudonym_until_phase3(self):
        self.assertFalse(self._identity(make_user(role=Role.PSYCHOLOGIST))["is_real_name"])

    def test_public_profile_shows_real_name_to_anyone(self):
        update_patient_profile(profile=self.profile, is_profile_public=True)
        self.assertEqual(self._identity(None)["display_name"], "Ayesha Khan")

    def test_admin_on_private_profile_sees_real_name_and_is_logged_with_ids_only(self):
        admin = make_admin()
        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            result = self._identity(admin)
        self.assertTrue(result["is_real_name"])
        self.assertEqual(len(captured.records), 1)
        message = captured.records[0].getMessage()
        payload = json.loads(message)
        self.assertEqual(payload["event_type"], "identity_reveal")
        self.assertEqual(payload["viewer_id"], admin.pk)
        self.assertEqual(payload["patient_id"], self.patient.pk)
        self.assertNotIn("Ayesha", message)
        self.assertNotIn(self.patient.email, message)

    def test_admin_on_public_profile_is_not_logged(self):
        update_patient_profile(profile=self.profile, is_profile_public=True)
        with self.assertNoLogs("mindcare.audit", level="INFO"):
            self._identity(make_admin())
```

Run: `venv/Scripts/python -m pytest apps/patients/tests/test_selectors.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 6: Implement selectors**

`apps/patients/selectors.py` (keep docstring, then):

```python
from apps.accounts.models import Role
from apps.patients.models import PatientProfile
from core.audit import log_identity_reveal


def get_patient_profile_for_user(*, user):
    return (
        PatientProfile.objects.select_related(
            "user", "country", "city__country", "preferred_language"
        )
        .filter(user=user)
        .first()
    )


def _is_assigned_psychologist(*, viewer, patient_profile):
    # Phase 3 hook: return True when `viewer` has an accepted relationship with
    # this patient. Until the relationship model exists, psychologists get the
    # pseudonym like any other viewer (docs/decisions.md, 2026-09-26).
    return False


def get_patient_display_identity(*, patient_profile, viewer):
    """The ONE place that decides whether a viewer sees a patient's real name or
    pseudonym. Phases 3 and 11 must call this, not reimplement it. Never add
    gender, age or city here: re-identification risk (docs/decisions.md)."""
    real = {"display_name": patient_profile.user.full_name, "is_real_name": True}
    pseudonymous = {"display_name": patient_profile.pseudonym, "is_real_name": False}

    authenticated = viewer is not None and viewer.is_authenticated
    if authenticated and viewer.pk == patient_profile.user_id:
        return real
    if patient_profile.is_profile_public:
        return real
    if not authenticated:
        return pseudonymous
    if viewer.role == Role.PSYCHOLOGIST and _is_assigned_psychologist(
        viewer=viewer, patient_profile=patient_profile
    ):
        return real
    if viewer.role == Role.ADMIN:
        log_identity_reveal(viewer_id=viewer.pk, patient_id=patient_profile.user_id)
        return real
    return pseudonymous
```

Run: `venv/Scripts/python -m pytest apps/patients/tests -q`
Expected: PASS.

- [ ] **Step 7: Write failing API tests**

`apps/patients/tests/test_api.py` (keep docstring, replace the rest):

```python
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.patients.services import create_patient_profile
from core.testing import make_user

ME_URL = "/api/v1/patients/me/"


class PatientMeAPITests(APITestCase):
    def setUp(self):
        self.user = make_user(role=Role.PATIENT, full_name="Ayesha Khan")
        self.profile = create_patient_profile(user=self.user, timezone="Asia/Karachi")
        self.client.force_authenticate(self.user)

    def test_get_own_profile(self):
        r = self.client.get(ME_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["pseudonym"], self.profile.pseudonym)
        self.assertEqual(r.data["full_name"], "Ayesha Khan")
        self.assertFalse(r.data["is_profile_public"])

    def test_patch_updates_fields(self):
        r = self.client.patch(
            ME_URL, {"country": "PK", "city": "Lahore", "preferred_language": "ur"}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertEqual(r.data["city"]["name"], "Lahore")
        self.assertEqual(r.data["country"]["code"], "PK")
        self.assertEqual(r.data["preferred_language"]["code"], "ur")

    def test_patch_pseudonym_rejected(self):
        r = self.client.patch(ME_URL, {"pseudonym": "Patient-000000"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pseudonym", r.data)

    def test_patch_under_18_dob_rejected(self):
        r = self.client.patch(ME_URL, {"date_of_birth": "2020-01-01"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_of_birth", r.data)

    def test_other_roles_forbidden(self):
        self.client.force_authenticate(make_user(role=Role.PSYCHOLOGIST))
        self.assertEqual(self.client.get(ME_URL).status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_unauthorized(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(ME_URL).status_code, status.HTTP_401_UNAUTHORIZED)
```

Run: `venv/Scripts/python -m pytest apps/patients/tests/test_api.py -q`
Expected: FAIL (404).

- [ ] **Step 8: Implement serializers, view, URL, admin**

`apps/patients/api/serializers.py` (keep docstring, then):

```python
from rest_framework import serializers

from apps.patients.models import PatientProfile
from apps.reference.api.serializers import CitySerializer, CountrySerializer, LanguageSerializer
from apps.reference.models import Country, Language
from core.choices import Gender
from core.serializers import RejectUnknownFieldsMixin
from core.validators import E164_VALIDATOR, validate_iana_timezone

PUBLIC_FLAG_HELP = (
    "If true, other users see your real name instead of your pseudonym. "
    "Going public is a permanent disclosure: people who see your real name while "
    "public may still recognise you later, even if you switch back to private."
)


class PatientRegistrationProfileSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    """The `profile` object in a patient's register request. `timezone` is read
    from the device by MindCare App; the patient never types it."""

    timezone = serializers.CharField(max_length=64, validators=[validate_iana_timezone])


class PatientProfileUpdateSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    is_profile_public = serializers.BooleanField(required=False, help_text=PUBLIC_FLAG_HELP)
    country = serializers.SlugRelatedField(
        slug_field="code", queryset=Country.objects.all(), required=False, allow_null=True
    )
    city = serializers.CharField(max_length=120, required=False, allow_blank=True, allow_null=True)
    timezone = serializers.CharField(max_length=64, required=False, validators=[validate_iana_timezone])
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=Gender.choices, required=False, allow_null=True)
    # Blank/None skip validators in DRF; the service turns "" into None.
    phone_number = serializers.CharField(
        max_length=20, required=False, allow_blank=True, allow_null=True, validators=[E164_VALIDATOR]
    )
    preferred_language = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Language.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )


class PatientProfileOwnerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    country = CountrySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    preferred_language = LanguageSerializer(read_only=True)
    is_profile_public = serializers.BooleanField(read_only=True, help_text=PUBLIC_FLAG_HELP)

    class Meta:
        model = PatientProfile
        fields = [
            "pseudonym", "full_name", "is_profile_public", "country", "city",
            "timezone", "date_of_birth", "gender", "phone_number",
            "preferred_language", "created_at", "updated_at",
        ]
        read_only_fields = fields
```

`apps/patients/api/views.py` (keep docstring, then):

```python
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.patients import selectors, services
from apps.patients.api.serializers import (
    PatientProfileOwnerSerializer,
    PatientProfileUpdateSerializer,
)
from core.exceptions import DomainValidationError
from core.permissions import IsPatient


class MyPatientProfileView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def _profile(self, request):
        profile = selectors.get_patient_profile_for_user(user=request.user)
        if profile is None:
            raise NotFound("Profile not found.")
        return profile

    def get(self, request):
        return Response(PatientProfileOwnerSerializer(self._profile(request)).data)

    def patch(self, request):
        profile = self._profile(request)
        serializer = PatientProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            profile = services.update_patient_profile(profile=profile, **serializer.validated_data)
        except DomainValidationError as exc:
            raise ValidationError(exc.errors, code=exc.code) from exc
        return Response(PatientProfileOwnerSerializer(profile).data)
```

`apps/patients/api/urls.py`:

```python
"""URL routes for the patients API, included under /api/v1/patients/."""

from django.urls import path

from apps.patients.api.views import MyPatientProfileView

app_name = "patients"

urlpatterns = [
    path("me/", MyPatientProfileView.as_view(), name="me"),
]
```

`apps/patients/admin.py`:

```python
"""Django admin for patient profiles.

Known limitation (spec §5.3): viewing a patient here shows the real name without
an identity_reveal log. Phase 2.5's admin API must use the logged selector.
"""

from django.contrib import admin

from apps.patients.models import PatientProfile


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ["pseudonym", "is_profile_public", "country", "created_at"]
    list_filter = ["is_profile_public", "country"]
    search_fields = ["pseudonym", "user__email"]
    readonly_fields = ["pseudonym", "created_at", "updated_at"]
    autocomplete_fields = ["country", "city", "preferred_language"]
    raw_id_fields = ["user"]
```

Run: `venv/Scripts/python -m pytest apps/patients -q`
Expected: PASS.

- [ ] **Step 9: Module-reference rows** in a new `### apps/patients` section:

```markdown
| `apps/patients/models.py` | `PatientProfile` | Patient demographics/preferences, immutable pseudonym, `is_profile_public` (default False); no health data | — | MindCare App |
| `apps/patients/services.py` | `create_patient_profile()` | Creates the profile at registration with a unique pseudonym (retries collisions) | via `POST /api/v1/accounts/register/` | MindCare App |
| `apps/patients/services.py` | `update_patient_profile()` | Owner edits; rejects pseudonym changes, under-18 DOB, bad timezone/phone; resolves city | `PATCH /api/v1/patients/me/` | MindCare App |
| `apps/patients/selectors.py` | `get_patient_profile_for_user()` | Loads the requesting patient's own profile | `GET /api/v1/patients/me/` | MindCare App |
| `apps/patients/selectors.py` | `get_patient_display_identity()` | Single rule for real name vs pseudonym; an admin reveal of a private profile logs `identity_reveal`; Phases 3/11 must use it | — (no endpoint in Phase 2) | MindCare Web, MindCare App (Phase 3+) |
| `apps/patients/api/views.py` | `MyPatientProfileView` | Owner-only read/update of the patient profile | `GET`/`PATCH /api/v1/patients/me/` | MindCare App |
```

- [ ] **Step 10: Commit**

```bash
git add core/testing.py apps/patients docs/module-reference.md
git commit -m "feat(patients): PatientProfile, pseudonym privacy selector, /me endpoint

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `apps/psychologists` — PsychologistProfile, credential lock, `/me/`

**Files:**
- Create: `apps/psychologists/admin.py`, `apps/psychologists/migrations/0001_initial.py` (generated)
- Modify: `core/testing.py`, `apps/psychologists/models.py`, `services.py`, `selectors.py`, `api/serializers.py`, `api/views.py`, `api/urls.py`, `tests/test_services.py`, `tests/test_api.py`

**Interfaces:**
- Consumes: Tasks 1–3 (`DomainValidationError`, validators, `Gender`, `RejectUnknownFieldsMixin`, reference models/services/serializers, `core.testing.make_user`)
- Produces:
  - `PsychologistProfile` (spec §6.1); `psychologists.models.CREDENTIAL_FIELDS = ("license_number", "license_issuing_country", "license_issuing_authority", "qualifications")`
  - `psychologists.services.create_psychologist_profile(*, user, license_number, license_issuing_country, license_issuing_authority, qualifications, specializations, years_of_experience, languages, country, city, timezone, gender=None, bio="") -> PsychologistProfile`
  - `psychologists.services.update_psychologist_profile(*, profile, **fields) -> PsychologistProfile`
  - `psychologists.services.DuplicateLicenseError`, `CredentialFieldLockedError` (both `DomainValidationError`; lock error code `"credential_field_locked"`)
  - `psychologists.selectors.get_psychologist_profile_for_user(*, user)`
  - `psychologists.api.serializers.PsychologistRegistrationProfileSerializer`, `PsychologistProfileOwnerSerializer`
  - `core.testing.psychologist_profile_data(**overrides) -> dict` (model values, for service calls); `core.testing.psychologist_profile_payload(**overrides) -> dict` (JSON codes, for API calls)

- [ ] **Step 1: Extend test factories**

Append to `core/testing.py`:

```python


def psychologist_profile_data(**overrides):
    from apps.reference.models import Country, Language, Specialization

    pakistan = Country.objects.get(code="PK")
    data = {
        "license_number": "PMDC-12345",
        "license_issuing_country": pakistan,
        "license_issuing_authority": "Pakistan Medical and Dental Council",
        "qualifications": "MS Clinical Psychology, University of the Punjab",
        "specializations": list(Specialization.objects.filter(slug__in=["anxiety", "depression"])),
        "years_of_experience": 5,
        "languages": list(Language.objects.filter(code__in=["en", "ur"])),
        "country": pakistan,
        "city": "Lahore",
        "timezone": "Asia/Karachi",
    }
    data.update(overrides)
    return data


def psychologist_profile_payload(**overrides):
    data = {
        "license_number": "PMDC-12345",
        "license_issuing_country": "PK",
        "license_issuing_authority": "Pakistan Medical and Dental Council",
        "qualifications": "MS Clinical Psychology, University of the Punjab",
        "specializations": ["anxiety", "depression"],
        "years_of_experience": 5,
        "languages": ["en", "ur"],
        "country": "PK",
        "city": "Lahore",
        "timezone": "Asia/Karachi",
    }
    data.update(overrides)
    return data
```

- [ ] **Step 2: Model**

Replace `apps/psychologists/models.py`:

```python
"""Database models for the psychologists app.

Credential fields are sent at registration and LOCKED afterwards: they are what
an admin reviews for approval (docs/decisions.md, 2026-09-26). Corrections go
through Django admin until Phase 2.5's re-review flow.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models

from core.choices import Gender
from core.validators import validate_iana_timezone

CREDENTIAL_FIELDS = (
    "license_number",
    "license_issuing_country",
    "license_issuing_authority",
    "qualifications",
)


class PsychologistProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="psychologist_profile",
    )
    # Admin-only; stored normalized (stripped, upper-cased).
    license_number = models.CharField(max_length=64)
    license_issuing_country = models.ForeignKey(
        "reference.Country", on_delete=models.PROTECT, related_name="+"
    )
    license_issuing_authority = models.CharField(max_length=200)
    qualifications = models.TextField(max_length=1000)
    specializations = models.ManyToManyField("reference.Specialization", related_name="+")
    years_of_experience = models.PositiveSmallIntegerField(validators=[MaxValueValidator(70)])
    languages = models.ManyToManyField("reference.Language", related_name="+")
    country = models.ForeignKey("reference.Country", on_delete=models.PROTECT, related_name="+")
    city = models.ForeignKey("reference.City", on_delete=models.PROTECT, related_name="+")
    timezone = models.CharField(max_length=64, validators=[validate_iana_timezone])
    gender = models.CharField(max_length=20, choices=Gender.choices, null=True, blank=True)
    bio = models.TextField(max_length=2000, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["license_issuing_country", "license_number"],
                name="psychologists_unique_license_per_country",
            )
        ]

    def __str__(self):
        return f"Psychologist profile #{self.pk}"
```

Run: `venv/Scripts/python manage.py makemigrations psychologists`
Expected: `0001_initial.py` with the unique constraint and two M2M tables.

- [ ] **Step 3: Write failing service tests**

`apps/psychologists/tests/test_services.py` (keep docstring, then):

```python
from django.test import TestCase

from apps.accounts.models import Role
from apps.psychologists.services import (
    CredentialFieldLockedError,
    DuplicateLicenseError,
    create_psychologist_profile,
    update_psychologist_profile,
)
from apps.reference.models import City, Country, Specialization
from core.exceptions import DomainValidationError
from core.testing import make_user, psychologist_profile_data


def _create(**overrides):
    return create_psychologist_profile(
        user=make_user(role=Role.PSYCHOLOGIST), **psychologist_profile_data(**overrides)
    )


class CreatePsychologistProfileTests(TestCase):
    def test_creates_profile_with_m2m_and_normalized_license(self):
        profile = _create(license_number="  pmdc-777 ")
        self.assertEqual(profile.license_number, "PMDC-777")
        self.assertEqual(profile.city, City.objects.get(country__code="PK", name="Lahore"))
        self.assertEqual(profile.specializations.count(), 2)
        self.assertEqual(profile.languages.count(), 2)

    def test_duplicate_license_same_country_rejected_after_normalization(self):
        _create(license_number="PMDC-1")
        with self.assertRaises(DuplicateLicenseError) as ctx:
            _create(license_number=" pmdc-1")
        self.assertEqual(ctx.exception.errors, {"license_number": ["This license is already registered."]})

    def test_same_license_number_in_another_country_allowed(self):
        _create(license_number="X-1")
        _create(license_number="X-1", license_issuing_country=Country.objects.get(code="GB"))

    def test_requires_at_least_one_specialization_and_language(self):
        with self.assertRaises(DomainValidationError):
            _create(specializations=[])
        with self.assertRaises(DomainValidationError):
            _create(languages=[])

    def test_inactive_specialization_rejected(self):
        Specialization.objects.filter(slug="anxiety").update(is_active=False)
        with self.assertRaises(DomainValidationError):
            _create(specializations=list(Specialization.objects.filter(slug="anxiety")))

    def test_rejects_non_psychologist_user(self):
        with self.assertRaises(ValueError):
            create_psychologist_profile(user=make_user(role=Role.PATIENT), **psychologist_profile_data())


class UpdatePsychologistProfileTests(TestCase):
    def setUp(self):
        self.profile = _create()

    def test_non_credential_fields_editable(self):
        update_psychologist_profile(
            profile=self.profile, bio="Hello", years_of_experience=6,
            specializations=list(Specialization.objects.filter(slug="grief")),
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, "Hello")
        self.assertEqual(list(self.profile.specializations.values_list("slug", flat=True)), ["grief"])

    def test_changed_credential_rejected(self):
        with self.assertRaises(CredentialFieldLockedError) as ctx:
            update_psychologist_profile(profile=self.profile, license_number="PMDC-99999")
        self.assertEqual(ctx.exception.code, "credential_field_locked")
        self.assertIn("license_number", ctx.exception.errors)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.license_number, "PMDC-12345")

    def test_unchanged_credentials_accepted_on_full_object_patch(self):
        data = psychologist_profile_data(license_number=" pmdc-12345 ", bio="Updated")
        update_psychologist_profile(profile=self.profile, **data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, "Updated")

    def test_every_credential_field_is_locked(self):
        changes = {
            "license_issuing_country": Country.objects.get(code="GB"),
            "license_issuing_authority": "Someone else",
            "qualifications": "PhD",
        }
        for field, value in changes.items():
            with self.assertRaises(CredentialFieldLockedError):
                update_psychologist_profile(profile=self.profile, **{field: value})

    def test_city_cannot_be_cleared(self):
        with self.assertRaises(DomainValidationError):
            update_psychologist_profile(profile=self.profile, city="")
```

Run: `venv/Scripts/python -m pytest apps/psychologists/tests/test_services.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 4: Implement services and selector**

`apps/psychologists/services.py` (keep docstring, then):

```python
from django.db import IntegrityError, transaction

from apps.accounts.models import Role
from apps.psychologists.models import CREDENTIAL_FIELDS, PsychologistProfile
from apps.reference.services import (
    ensure_active_choices,
    resolve_city,
    resolve_location_fields,
)
from core.exceptions import DomainValidationError
from core.validators import (
    normalize_display_text,
    normalize_identifier,
    run_validator,
    validate_iana_timezone,
)

EDITABLE_FIELDS = {
    "specializations",
    "years_of_experience",
    "languages",
    "country",
    "city",
    "timezone",
    "gender",
    "bio",
}


class DuplicateLicenseError(DomainValidationError):
    def __init__(self):
        # Deliberately generic: never confirm who holds the license.
        super().__init__({"license_number": ["This license is already registered."]})


class CredentialFieldLockedError(DomainValidationError):
    default_code = "credential_field_locked"

    def __init__(self, fields):
        super().__init__(
            {
                field: ["This credential can't be changed after registration. Contact support to correct it."]
                for field in fields
            }
        )


def _normalize_credential(field, value):
    if field == "license_number":
        return normalize_identifier(value)
    if field == "license_issuing_authority":
        return normalize_display_text(value)
    if field == "qualifications":
        return value.strip()
    return value  # license_issuing_country: a Country instance


def create_psychologist_profile(
    *,
    user,
    license_number,
    license_issuing_country,
    license_issuing_authority,
    qualifications,
    specializations,
    years_of_experience,
    languages,
    country,
    city,
    timezone,
    gender=None,
    bio="",
):
    if user.role != Role.PSYCHOLOGIST:
        raise ValueError("Psychologist profiles can only be created for psychologist users.")
    ensure_active_choices(items=specializations, field="specializations")
    ensure_active_choices(items=languages, field="languages")
    run_validator(validate_iana_timezone, timezone, field="timezone")

    normalized_license = _normalize_credential("license_number", license_number)
    if PsychologistProfile.objects.filter(
        license_issuing_country=license_issuing_country, license_number=normalized_license
    ).exists():
        raise DuplicateLicenseError()

    try:
        with transaction.atomic():
            profile = PsychologistProfile.objects.create(
                user=user,
                license_number=normalized_license,
                license_issuing_country=license_issuing_country,
                license_issuing_authority=_normalize_credential(
                    "license_issuing_authority", license_issuing_authority
                ),
                qualifications=_normalize_credential("qualifications", qualifications),
                years_of_experience=years_of_experience,
                country=country,
                city=resolve_city(country=country, name=city),
                timezone=timezone,
                gender=gender,
                bio=bio or "",
            )
            profile.specializations.set(specializations)
            profile.languages.set(languages)
    except IntegrityError as exc:
        if PsychologistProfile.objects.filter(
            license_issuing_country=license_issuing_country, license_number=normalized_license
        ).exists():
            raise DuplicateLicenseError() from exc
        raise
    return profile


def update_psychologist_profile(*, profile, **fields):
    changed = [
        field
        for field in CREDENTIAL_FIELDS
        if field in fields
        and _normalize_credential(field, fields[field]) != getattr(profile, field)
    ]
    if changed:
        raise CredentialFieldLockedError(changed)
    for field in CREDENTIAL_FIELDS:
        fields.pop(field, None)

    unknown = sorted(set(fields) - EDITABLE_FIELDS)
    if unknown:
        raise DomainValidationError({name: ["This field can't be updated."] for name in unknown})

    specializations = fields.pop("specializations", None)
    languages = fields.pop("languages", None)
    if specializations is not None:
        ensure_active_choices(items=specializations, field="specializations")
    if languages is not None:
        ensure_active_choices(items=languages, field="languages")
    if fields.get("timezone") is not None:
        run_validator(validate_iana_timezone, fields["timezone"], field="timezone")
    if "bio" in fields and fields["bio"] is None:
        fields["bio"] = ""

    resolve_location_fields(
        current_country=profile.country,
        current_city=profile.city,
        fields=fields,
        city_required=True,
    )

    with transaction.atomic():
        for name, value in fields.items():
            setattr(profile, name, value)
        profile.save()
        if specializations is not None:
            profile.specializations.set(specializations)
        if languages is not None:
            profile.languages.set(languages)
    return profile
```

`apps/psychologists/selectors.py` (keep docstring, then):

```python
from apps.psychologists.models import PsychologistProfile


def get_psychologist_profile_for_user(*, user):
    return (
        PsychologistProfile.objects.select_related(
            "user", "country", "city__country", "license_issuing_country"
        )
        .prefetch_related("specializations", "languages")
        .filter(user=user)
        .first()
    )
```

Run: `venv/Scripts/python -m pytest apps/psychologists/tests/test_services.py -q`
Expected: PASS.

- [ ] **Step 5: Write failing API tests**

`apps/psychologists/tests/test_api.py` (keep docstring, then):

```python
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.psychologists.services import create_psychologist_profile
from core.testing import make_user, psychologist_profile_data, psychologist_profile_payload

ME_URL = "/api/v1/psychologists/me/"


class PsychologistMeAPITests(APITestCase):
    def setUp(self):
        self.user = make_user(role=Role.PSYCHOLOGIST)
        create_psychologist_profile(user=self.user, **psychologist_profile_data())
        self.client.force_authenticate(self.user)

    def test_owner_sees_license_number(self):
        r = self.client.get(ME_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["license_number"], "PMDC-12345")
        self.assertEqual(r.data["license_issuing_country"]["code"], "PK")
        self.assertEqual({s["slug"] for s in r.data["specializations"]}, {"anxiety", "depression"})

    def test_patch_editable_fields(self):
        r = self.client.patch(ME_URL, {"bio": "Hi", "languages": ["en"]}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertEqual([lang["code"] for lang in r.data["languages"]], ["en"])

    def test_patch_changed_license_is_locked(self):
        r = self.client.patch(ME_URL, {"license_number": "NEW-1"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["license_number"][0].code, "credential_field_locked")

    def test_full_object_patch_with_unchanged_credentials_ok(self):
        r = self.client.patch(ME_URL, psychologist_profile_payload(bio="Same creds"), format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)

    def test_patient_forbidden(self):
        self.client.force_authenticate(make_user(role=Role.PATIENT))
        self.assertEqual(self.client.get(ME_URL).status_code, status.HTTP_403_FORBIDDEN)
```

Run: `venv/Scripts/python -m pytest apps/psychologists/tests/test_api.py -q`
Expected: FAIL (404).

- [ ] **Step 6: Implement serializers, view, URL, admin**

`apps/psychologists/api/serializers.py` (keep docstring, then):

```python
from rest_framework import serializers

from apps.psychologists.models import PsychologistProfile
from apps.reference.api.serializers import (
    CitySerializer,
    CountrySerializer,
    LanguageSerializer,
    SpecializationSerializer,
)
from apps.reference.models import Country, Language, Specialization
from core.choices import Gender
from core.serializers import RejectUnknownFieldsMixin
from core.validators import validate_iana_timezone


class PsychologistRegistrationProfileSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    """The `profile` object in a psychologist's register request. Reused with
    partial=True for PATCH /me/ (credential fields accepted, checked by the
    service's lock)."""

    license_number = serializers.CharField(max_length=64)
    license_issuing_country = serializers.SlugRelatedField(
        slug_field="code", queryset=Country.objects.all()
    )
    license_issuing_authority = serializers.CharField(max_length=200)
    qualifications = serializers.CharField(max_length=1000)
    specializations = serializers.SlugRelatedField(
        slug_field="slug",
        many=True,
        allow_empty=False,
        queryset=Specialization.objects.filter(is_active=True),
    )
    years_of_experience = serializers.IntegerField(min_value=0, max_value=70)
    languages = serializers.SlugRelatedField(
        slug_field="code",
        many=True,
        allow_empty=False,
        queryset=Language.objects.filter(is_active=True),
    )
    country = serializers.SlugRelatedField(slug_field="code", queryset=Country.objects.all())
    city = serializers.CharField(max_length=120)
    timezone = serializers.CharField(max_length=64, validators=[validate_iana_timezone])
    gender = serializers.ChoiceField(choices=Gender.choices, required=False, allow_null=True)
    bio = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class PsychologistProfileOwnerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    license_issuing_country = CountrySerializer(read_only=True)
    specializations = SpecializationSerializer(many=True, read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)
    country = CountrySerializer(read_only=True)
    city = CitySerializer(read_only=True)

    class Meta:
        model = PsychologistProfile
        fields = [
            "full_name", "license_number", "license_issuing_country",
            "license_issuing_authority", "qualifications", "specializations",
            "years_of_experience", "languages", "country", "city", "timezone",
            "gender", "bio", "created_at", "updated_at",
        ]
        read_only_fields = fields
```

`apps/psychologists/api/views.py` (keep docstring, then):

```python
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.psychologists import selectors, services
from apps.psychologists.api.serializers import (
    PsychologistProfileOwnerSerializer,
    PsychologistRegistrationProfileSerializer,
)
from core.exceptions import DomainValidationError
from core.permissions import IsPsychologist


class MyPsychologistProfileView(APIView):
    permission_classes = [IsAuthenticated, IsPsychologist]

    def _profile(self, request):
        profile = selectors.get_psychologist_profile_for_user(user=request.user)
        if profile is None:
            raise NotFound("Profile not found.")
        return profile

    def get(self, request):
        return Response(PsychologistProfileOwnerSerializer(self._profile(request)).data)

    def patch(self, request):
        profile = self._profile(request)
        serializer = PsychologistRegistrationProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            profile = services.update_psychologist_profile(
                profile=profile, **serializer.validated_data
            )
        except DomainValidationError as exc:
            raise ValidationError(exc.errors, code=exc.code) from exc
        profile = selectors.get_psychologist_profile_for_user(user=request.user)
        return Response(PsychologistProfileOwnerSerializer(profile).data)
```

`apps/psychologists/api/urls.py`:

```python
"""URL routes for the psychologists API, included under /api/v1/psychologists/."""

from django.urls import path

from apps.psychologists.api.views import MyPsychologistProfileView

app_name = "psychologists"

urlpatterns = [
    path("me/", MyPsychologistProfileView.as_view(), name="me"),
]
```

`apps/psychologists/admin.py`:

```python
"""Django admin for psychologist profiles. Credential fields ARE editable here:
this is the interim correction path until Phase 2.5's re-review flow."""

from django.contrib import admin

from apps.psychologists.models import PsychologistProfile


@admin.register(PsychologistProfile)
class PsychologistProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "license_number", "license_issuing_country", "country", "created_at"]
    list_filter = ["license_issuing_country", "country"]
    search_fields = ["user__email", "user__full_name", "license_number"]
    autocomplete_fields = ["license_issuing_country", "country", "city"]
    filter_horizontal = ["specializations", "languages"]
    raw_id_fields = ["user"]
    readonly_fields = ["created_at", "updated_at"]
```

Run: `venv/Scripts/python -m pytest apps/psychologists -q`
Expected: PASS.

- [ ] **Step 7: Module-reference rows** in a new `### apps/psychologists` section:

```markdown
| `apps/psychologists/models.py` | `PsychologistProfile` | Credentials (locked after registration; license number admin-only, unique per issuing country) + editable professional details | — | MindCare Web |
| `apps/psychologists/services.py` | `create_psychologist_profile()` | Creates the profile at registration; normalizes license; generic duplicate-license error | via `POST /api/v1/accounts/register/` | MindCare Web |
| `apps/psychologists/services.py` | `update_psychologist_profile()` | Owner edits; rejects changed credential fields (`credential_field_locked`), accepts unchanged ones | `PATCH /api/v1/psychologists/me/` | MindCare Web |
| `apps/psychologists/selectors.py` | `get_psychologist_profile_for_user()` | Loads the requesting psychologist's own profile | `GET /api/v1/psychologists/me/` | MindCare Web |
| `apps/psychologists/api/views.py` | `MyPsychologistProfileView` | Owner-only read/update of the psychologist profile | `GET`/`PATCH /api/v1/psychologists/me/` | MindCare Web |
```

- [ ] **Step 8: Commit**

```bash
git add core/testing.py apps/psychologists docs/module-reference.md
git commit -m "feat(psychologists): PsychologistProfile with locked credentials and /me endpoint

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: `apps/ngo` — NGOProfile, service areas, credential lock, `/me/`

**Files:**
- Create: `apps/ngo/admin.py`, `apps/ngo/migrations/0001_initial.py` (generated)
- Modify: `core/testing.py`, `apps/ngo/models.py`, `services.py`, `selectors.py`, `api/serializers.py`, `api/views.py`, `api/urls.py`, `tests/test_services.py`, `tests/test_api.py`

**Interfaces:**
- Consumes: Tasks 1–4 (same helpers; `CredentialFieldLockedError` pattern is re-declared here, not imported from psychologists)
- Produces:
  - `NGOProfile`, `NGOServiceArea` (spec §7.1); `ngo.models.CREDENTIAL_FIELDS = ("organization_name", "registration_number", "registration_country", "registering_authority")`
  - `ngo.services.create_ngo_profile(*, user, organization_name, registration_number, registration_country, registering_authority, country, city, timezone, official_phone, official_email, service_areas, website="", description="") -> NGOProfile` — `service_areas: list[{"country": Country, "city": str | None}]`
  - `ngo.services.update_ngo_profile(*, profile, **fields) -> NGOProfile` (a provided `service_areas` list replaces the set)
  - `ngo.services.DuplicateNGORegistrationError`, `ngo.services.CredentialFieldLockedError`
  - `ngo.selectors.get_ngo_profile_for_user(*, user)`
  - `ngo.api.serializers.NGORegistrationProfileSerializer`, `NGOProfileOwnerSerializer`
  - `core.testing.ngo_profile_data(**overrides)`, `core.testing.ngo_profile_payload(**overrides)`

- [ ] **Step 1: Extend test factories**

Append to `core/testing.py`:

```python


def ngo_profile_data(**overrides):
    from apps.reference.models import Country

    pakistan = Country.objects.get(code="PK")
    data = {
        "organization_name": "Helping Hands Foundation",
        "registration_number": "SECP-0001",
        "registration_country": pakistan,
        "registering_authority": "SECP",
        "country": pakistan,
        "city": "Karachi",
        "timezone": "Asia/Karachi",
        "official_phone": "+922111234567",
        "official_email": "contact@helpinghands.example",
        "service_areas": [{"country": pakistan, "city": None}],
    }
    data.update(overrides)
    return data


def ngo_profile_payload(**overrides):
    data = {
        "organization_name": "Helping Hands Foundation",
        "registration_number": "SECP-0001",
        "registration_country": "PK",
        "registering_authority": "SECP",
        "country": "PK",
        "city": "Karachi",
        "timezone": "Asia/Karachi",
        "official_phone": "+922111234567",
        "official_email": "contact@helpinghands.example",
        "service_areas": [{"country": "PK"}],
    }
    data.update(overrides)
    return data
```

- [ ] **Step 2: Models**

Replace `apps/ngo/models.py`:

```python
"""Database models for the ngo app.

NGOProfile is pulled forward into Phase 2 because it's created at registration;
the rest of NGO onboarding stays in Phase 12. Credential fields are locked after
registration (docs/decisions.md, 2026-09-26). Service areas are what Phase 13
will match on; they are deliberately separate from the headquarters location.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from core.validators import E164_VALIDATOR, validate_iana_timezone

CREDENTIAL_FIELDS = (
    "organization_name",
    "registration_number",
    "registration_country",
    "registering_authority",
)


class NGOProfile(models.Model):
    # The account holder is the NGO's representative, not the organisation.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ngo_profile"
    )
    organization_name = models.CharField(max_length=200)
    # Admin-only; stored normalized (stripped, upper-cased).
    registration_number = models.CharField(max_length=64)
    registration_country = models.ForeignKey(
        "reference.Country", on_delete=models.PROTECT, related_name="+"
    )
    registering_authority = models.CharField(max_length=200)
    country = models.ForeignKey("reference.Country", on_delete=models.PROTECT, related_name="+")
    city = models.ForeignKey("reference.City", on_delete=models.PROTECT, related_name="+")
    timezone = models.CharField(max_length=64, validators=[validate_iana_timezone])
    # Admin-only for now; Phase 13 decides who else sees them.
    official_phone = models.CharField(max_length=20, validators=[E164_VALIDATOR])
    official_email = models.EmailField()
    website = models.URLField(blank=True, default="")
    description = models.TextField(max_length=2000, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "NGO profile"
        constraints = [
            models.UniqueConstraint(
                fields=["registration_country", "registration_number"],
                name="ngo_unique_registration_per_country",
            )
        ]

    def __str__(self):
        return self.organization_name


class NGOServiceArea(models.Model):
    """A country, optionally narrowed to one city. city=NULL means nationwide."""

    ngo = models.ForeignKey(NGOProfile, on_delete=models.CASCADE, related_name="service_areas")
    country = models.ForeignKey("reference.Country", on_delete=models.PROTECT, related_name="+")
    city = models.ForeignKey(
        "reference.City", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ngo", "country"],
                condition=Q(city__isnull=True),
                name="ngo_service_area_unique_nationwide",
            ),
            models.UniqueConstraint(
                fields=["ngo", "country", "city"],
                condition=Q(city__isnull=False),
                name="ngo_service_area_unique_city",
            ),
        ]

    def __str__(self):
        return f"{self.city or 'All of'} {self.country}"
```

Run: `venv/Scripts/python manage.py makemigrations ngo`
Expected: `0001_initial.py` with both models and three constraints.

- [ ] **Step 3: Write failing service tests**

`apps/ngo/tests/test_services.py` (keep docstring, then):

```python
from django.test import TestCase

from apps.accounts.models import Role
from apps.ngo.services import (
    CredentialFieldLockedError,
    DuplicateNGORegistrationError,
    create_ngo_profile,
    update_ngo_profile,
)
from apps.reference.models import Country
from core.exceptions import DomainValidationError
from core.testing import make_user, ngo_profile_data


def _create(**overrides):
    return create_ngo_profile(user=make_user(role=Role.NGO), **ngo_profile_data(**overrides))


class CreateNGOProfileTests(TestCase):
    def test_creates_profile_and_nationwide_service_area(self):
        profile = _create(registration_number=" secp-9 ")
        self.assertEqual(profile.registration_number, "SECP-9")
        area = profile.service_areas.get()
        self.assertEqual(area.country.code, "PK")
        self.assertIsNone(area.city)

    def test_city_and_nationwide_areas_in_different_countries(self):
        gb = Country.objects.get(code="GB")
        profile = _create(
            service_areas=[
                {"country": Country.objects.get(code="PK"), "city": None},
                {"country": gb, "city": "london"},
            ]
        )
        self.assertEqual(profile.service_areas.count(), 2)
        self.assertEqual(profile.service_areas.get(country=gb).city.name, "london")

    def test_requires_at_least_one_service_area(self):
        with self.assertRaises(DomainValidationError):
            _create(service_areas=[])

    def test_duplicate_service_areas_rejected(self):
        pk = Country.objects.get(code="PK")
        with self.assertRaises(DomainValidationError):
            _create(service_areas=[{"country": pk, "city": "Lahore"}, {"country": pk, "city": "lahore"}])

    def test_duplicate_registration_rejected_generically(self):
        _create(registration_number="SECP-1")
        with self.assertRaises(DuplicateNGORegistrationError) as ctx:
            _create(registration_number="secp-1")
        self.assertEqual(
            ctx.exception.errors,
            {"registration_number": ["This organisation registration is already on file."]},
        )


class UpdateNGOProfileTests(TestCase):
    def setUp(self):
        self.profile = _create()

    def test_service_areas_replaced(self):
        pk = Country.objects.get(code="PK")
        update_ngo_profile(profile=self.profile, service_areas=[{"country": pk, "city": "Quetta"}])
        self.assertEqual(
            list(self.profile.service_areas.values_list("city__name", flat=True)), ["Quetta"]
        )

    def test_changed_credential_locked(self):
        with self.assertRaises(CredentialFieldLockedError) as ctx:
            update_ngo_profile(profile=self.profile, organization_name="Renamed Org")
        self.assertEqual(ctx.exception.code, "credential_field_locked")

    def test_unchanged_credentials_accepted(self):
        update_ngo_profile(profile=self.profile, **ngo_profile_data(description="Updated"))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.description, "Updated")
```

Run: `venv/Scripts/python -m pytest apps/ngo/tests/test_services.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 4: Implement services and selector**

`apps/ngo/services.py` (keep docstring, then):

```python
from django.db import IntegrityError, transaction

from apps.accounts.models import Role
from apps.ngo.models import CREDENTIAL_FIELDS, NGOProfile, NGOServiceArea
from apps.reference.services import resolve_city, resolve_location_fields
from core.exceptions import DomainValidationError
from core.validators import (
    E164_VALIDATOR,
    normalize_display_text,
    normalize_identifier,
    run_validator,
    validate_iana_timezone,
)

EDITABLE_FIELDS = {
    "country",
    "city",
    "timezone",
    "official_phone",
    "official_email",
    "website",
    "description",
    "service_areas",
}


class DuplicateNGORegistrationError(DomainValidationError):
    def __init__(self):
        super().__init__(
            {"registration_number": ["This organisation registration is already on file."]}
        )


class CredentialFieldLockedError(DomainValidationError):
    default_code = "credential_field_locked"

    def __init__(self, fields):
        super().__init__(
            {
                field: ["This credential can't be changed after registration. Contact support to correct it."]
                for field in fields
            }
        )


def _normalize_credential(field, value):
    if field == "registration_number":
        return normalize_identifier(value)
    if field in ("organization_name", "registering_authority"):
        return normalize_display_text(value)
    return value  # registration_country: a Country instance


def _resolve_service_areas(service_areas):
    if not service_areas:
        raise DomainValidationError({"service_areas": ["Add at least one service area."]})
    resolved, seen = [], set()
    for area in service_areas:
        country = area["country"]
        city = resolve_city(country=country, name=area["city"]) if area.get("city") else None
        key = (country.pk, city.pk if city else None)
        if key in seen:
            raise DomainValidationError({"service_areas": ["Each service area can only be listed once."]})
        seen.add(key)
        resolved.append((country, city))
    return resolved


def _replace_service_areas(profile, resolved):
    profile.service_areas.all().delete()
    NGOServiceArea.objects.bulk_create(
        NGOServiceArea(ngo=profile, country=country, city=city) for country, city in resolved
    )


def create_ngo_profile(
    *,
    user,
    organization_name,
    registration_number,
    registration_country,
    registering_authority,
    country,
    city,
    timezone,
    official_phone,
    official_email,
    service_areas,
    website="",
    description="",
):
    if user.role != Role.NGO:
        raise ValueError("NGO profiles can only be created for NGO users.")
    run_validator(validate_iana_timezone, timezone, field="timezone")
    run_validator(E164_VALIDATOR, official_phone, field="official_phone")

    normalized_number = _normalize_credential("registration_number", registration_number)
    duplicate = NGOProfile.objects.filter(
        registration_country=registration_country, registration_number=normalized_number
    )
    if duplicate.exists():
        raise DuplicateNGORegistrationError()

    resolved_areas = _resolve_service_areas(service_areas)
    try:
        with transaction.atomic():
            profile = NGOProfile.objects.create(
                user=user,
                organization_name=_normalize_credential("organization_name", organization_name),
                registration_number=normalized_number,
                registration_country=registration_country,
                registering_authority=_normalize_credential(
                    "registering_authority", registering_authority
                ),
                country=country,
                city=resolve_city(country=country, name=city),
                timezone=timezone,
                official_phone=official_phone,
                official_email=official_email,
                website=website or "",
                description=description or "",
            )
            _replace_service_areas(profile, resolved_areas)
    except IntegrityError as exc:
        if duplicate.exists():
            raise DuplicateNGORegistrationError() from exc
        raise
    return profile


def update_ngo_profile(*, profile, **fields):
    changed = [
        field
        for field in CREDENTIAL_FIELDS
        if field in fields
        and _normalize_credential(field, fields[field]) != getattr(profile, field)
    ]
    if changed:
        raise CredentialFieldLockedError(changed)
    for field in CREDENTIAL_FIELDS:
        fields.pop(field, None)

    unknown = sorted(set(fields) - EDITABLE_FIELDS)
    if unknown:
        raise DomainValidationError({name: ["This field can't be updated."] for name in unknown})

    service_areas = fields.pop("service_areas", None)
    resolved_areas = _resolve_service_areas(service_areas) if service_areas is not None else None
    if fields.get("timezone") is not None:
        run_validator(validate_iana_timezone, fields["timezone"], field="timezone")
    if "official_phone" in fields:
        run_validator(E164_VALIDATOR, fields["official_phone"] or "", field="official_phone")
    for text_field in ("website", "description"):
        if text_field in fields and fields[text_field] is None:
            fields[text_field] = ""

    resolve_location_fields(
        current_country=profile.country,
        current_city=profile.city,
        fields=fields,
        city_required=True,
    )

    with transaction.atomic():
        for name, value in fields.items():
            setattr(profile, name, value)
        profile.save()
        if resolved_areas is not None:
            _replace_service_areas(profile, resolved_areas)
    return profile
```

`apps/ngo/selectors.py` (keep docstring, then):

```python
from apps.ngo.models import NGOProfile


def get_ngo_profile_for_user(*, user):
    return (
        NGOProfile.objects.select_related("user", "country", "city__country", "registration_country")
        .prefetch_related("service_areas__country", "service_areas__city")
        .filter(user=user)
        .first()
    )
```

Run: `venv/Scripts/python -m pytest apps/ngo/tests/test_services.py -q`
Expected: PASS.

- [ ] **Step 5: Write failing API tests**

`apps/ngo/tests/test_api.py` (keep docstring, then):

```python
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.ngo.services import create_ngo_profile
from core.testing import make_user, ngo_profile_data, ngo_profile_payload

ME_URL = "/api/v1/ngo/me/"


class NGOMeAPITests(APITestCase):
    def setUp(self):
        self.user = make_user(role=Role.NGO)
        create_ngo_profile(user=self.user, **ngo_profile_data())
        self.client.force_authenticate(self.user)

    def test_owner_view_includes_admin_only_fields_and_areas(self):
        r = self.client.get(ME_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["registration_number"], "SECP-0001")
        self.assertEqual(r.data["service_areas"], [{"country": {"code": "PK", "name": "Pakistan"}, "city": None}])

    def test_patch_replaces_service_areas(self):
        r = self.client.patch(
            ME_URL, {"service_areas": [{"country": "GB", "city": "Leeds"}]}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertEqual(r.data["service_areas"][0]["city"]["name"], "Leeds")

    def test_patch_empty_service_areas_rejected(self):
        r = self.client.patch(ME_URL, {"service_areas": []}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_changed_registration_number_locked(self):
        r = self.client.patch(ME_URL, {"registration_number": "NEW"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["registration_number"][0].code, "credential_field_locked")

    def test_full_object_patch_ok(self):
        r = self.client.patch(ME_URL, ngo_profile_payload(description="x"), format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)

    def test_patient_forbidden(self):
        self.client.force_authenticate(make_user(role=Role.PATIENT))
        self.assertEqual(self.client.get(ME_URL).status_code, status.HTTP_403_FORBIDDEN)
```

Run: `venv/Scripts/python -m pytest apps/ngo/tests/test_api.py -q`
Expected: FAIL (404).

- [ ] **Step 6: Implement serializers, view, URL, admin**

`apps/ngo/api/serializers.py` (keep docstring, then):

```python
from rest_framework import serializers

from apps.ngo.models import NGOProfile, NGOServiceArea
from apps.reference.api.serializers import CitySerializer, CountrySerializer
from apps.reference.models import Country
from core.serializers import RejectUnknownFieldsMixin
from core.validators import E164_VALIDATOR, validate_iana_timezone


class ServiceAreaInputSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    country = serializers.SlugRelatedField(slug_field="code", queryset=Country.objects.all())
    city = serializers.CharField(max_length=120, required=False, allow_blank=True, allow_null=True)


class NGORegistrationProfileSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    """The `profile` object in an NGO's register request; reused with
    partial=True for PATCH /me/."""

    organization_name = serializers.CharField(max_length=200)
    registration_number = serializers.CharField(max_length=64)
    registration_country = serializers.SlugRelatedField(slug_field="code", queryset=Country.objects.all())
    registering_authority = serializers.CharField(max_length=200)
    country = serializers.SlugRelatedField(slug_field="code", queryset=Country.objects.all())
    city = serializers.CharField(max_length=120)
    timezone = serializers.CharField(max_length=64, validators=[validate_iana_timezone])
    official_phone = serializers.CharField(max_length=20, validators=[E164_VALIDATOR])
    official_email = serializers.EmailField()
    website = serializers.URLField(required=False, allow_blank=True)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    service_areas = ServiceAreaInputSerializer(many=True, allow_empty=False)


class ServiceAreaOutputSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)
    city = CitySerializer(read_only=True)

    class Meta:
        model = NGOServiceArea
        fields = ["country", "city"]


class NGOProfileOwnerSerializer(serializers.ModelSerializer):
    representative_name = serializers.CharField(source="user.full_name", read_only=True)
    registration_country = CountrySerializer(read_only=True)
    country = CountrySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    service_areas = ServiceAreaOutputSerializer(many=True, read_only=True)

    class Meta:
        model = NGOProfile
        fields = [
            "representative_name", "organization_name", "registration_number",
            "registration_country", "registering_authority", "country", "city",
            "timezone", "official_phone", "official_email", "website",
            "description", "service_areas", "created_at", "updated_at",
        ]
        read_only_fields = fields
```

`CitySerializer` includes `id`, `name`, `country`; the NGO API test compares `service_areas` for a nationwide area only (city `None`), so that exact-dict assertion holds.

`apps/ngo/api/views.py` (keep docstring, then):

```python
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ngo import selectors, services
from apps.ngo.api.serializers import NGOProfileOwnerSerializer, NGORegistrationProfileSerializer
from core.exceptions import DomainValidationError
from core.permissions import IsNGO


class MyNGOProfileView(APIView):
    permission_classes = [IsAuthenticated, IsNGO]

    def _profile(self, request):
        profile = selectors.get_ngo_profile_for_user(user=request.user)
        if profile is None:
            raise NotFound("Profile not found.")
        return profile

    def get(self, request):
        return Response(NGOProfileOwnerSerializer(self._profile(request)).data)

    def patch(self, request):
        profile = self._profile(request)
        serializer = NGORegistrationProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            services.update_ngo_profile(profile=profile, **serializer.validated_data)
        except DomainValidationError as exc:
            raise ValidationError(exc.errors, code=exc.code) from exc
        profile = selectors.get_ngo_profile_for_user(user=request.user)
        return Response(NGOProfileOwnerSerializer(profile).data)
```

`apps/ngo/api/urls.py`:

```python
"""URL routes for the ngo API, included under /api/v1/ngo/."""

from django.urls import path

from apps.ngo.api.views import MyNGOProfileView

app_name = "ngo"

urlpatterns = [
    path("me/", MyNGOProfileView.as_view(), name="me"),
]
```

`apps/ngo/admin.py`:

```python
"""Django admin for NGO profiles. Credential fields ARE editable here: the
interim correction path until Phase 2.5's re-review flow."""

from django.contrib import admin

from apps.ngo.models import NGOProfile, NGOServiceArea


class NGOServiceAreaInline(admin.TabularInline):
    model = NGOServiceArea
    extra = 0
    autocomplete_fields = ["country", "city"]


@admin.register(NGOProfile)
class NGOProfileAdmin(admin.ModelAdmin):
    list_display = ["organization_name", "registration_number", "registration_country", "country"]
    list_filter = ["registration_country", "country"]
    search_fields = ["organization_name", "registration_number", "user__email"]
    autocomplete_fields = ["registration_country", "country", "city"]
    raw_id_fields = ["user"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [NGOServiceAreaInline]
```

Run: `venv/Scripts/python -m pytest apps/ngo -q`
Expected: PASS.

- [ ] **Step 7: Module-reference rows** in a new `### apps/ngo` section:

```markdown
| `apps/ngo/models.py` | `NGOProfile`, `NGOServiceArea` | NGO organisation details (credentials locked; registration number and official contacts admin-only) and service areas (country + optional city; no city = nationwide) | — | MindCare Web |
| `apps/ngo/services.py` | `create_ngo_profile()` | Creates the profile + service areas at registration; generic duplicate-registration error | via `POST /api/v1/accounts/register/` | MindCare Web |
| `apps/ngo/services.py` | `update_ngo_profile()` | Owner edits; credential lock; a provided `service_areas` list replaces the set | `PATCH /api/v1/ngo/me/` | MindCare Web |
| `apps/ngo/selectors.py` | `get_ngo_profile_for_user()` | Loads the requesting NGO's own profile | `GET /api/v1/ngo/me/` | MindCare Web |
| `apps/ngo/api/views.py` | `MyNGOProfileView` | Owner-only read/update of the NGO profile | `GET`/`PATCH /api/v1/ngo/me/` | MindCare Web |
```

- [ ] **Step 8: Commit**

```bash
git add core/testing.py apps/ngo docs/module-reference.md
git commit -m "feat(ngo): NGOProfile with service areas, locked credentials, /me endpoint

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: `apps/accounts` — 18+ declaration, nested register body, atomic profile orchestration

**Files:**
- Create: `apps/accounts/migrations/0002_user_adult_confirmed_at.py` (generated)
- Modify: `apps/accounts/models.py`, `services.py`, `api/serializers.py`, `api/views.py`, `tests/test_services.py`, `tests/test_api.py`, `core/testing.py`

**Interfaces:**
- Consumes: `create_patient_profile`, `create_psychologist_profile`, `create_ngo_profile`; the three `*RegistrationProfileSerializer` and `*OwnerSerializer` classes; factories from `core.testing`.
- Produces:
  - `User.adult_confirmed_at` (nullable `DateTimeField`)
  - `accounts.services.register_user(*, email, password, full_name, role, is_adult_confirmed, profile_data) -> User`
  - `accounts.services.PROFILE_CREATORS: dict[Role, callable]`
  - `core.testing.register_payload(*, role, **overrides) -> dict` (full JSON register body)

- [ ] **Step 1: Model field + migration**

In `apps/accounts/models.py`, add to `User` after `is_super_admin`:

```python
    # Set when the user declared "I am 18 or older" at public registration
    # (docs/decisions.md, 2026-09-26). NULL for createsuperuser accounts.
    adult_confirmed_at = models.DateTimeField(null=True, blank=True)
```

Run: `venv/Scripts/python manage.py makemigrations accounts`
Expected: `0002_user_adult_confirmed_at.py` (one `AddField`).

- [ ] **Step 2: Extend factories**

Append to `core/testing.py`:

```python


def register_payload(*, role, **overrides):
    profiles = {
        Role.PATIENT: lambda: dict(PATIENT_PROFILE_DATA),
        Role.PSYCHOLOGIST: psychologist_profile_payload,
        Role.NGO: ngo_profile_payload,
    }
    tag = uuid.uuid4().hex[:8]
    data = {
        "email": f"{role}-{tag}@example.com",
        "password": PASSWORD,
        "full_name": f"New {role.title()}",
        "role": str(role),
        "is_adult_confirmed": True,
        "profile": profiles[Role(role)](),
    }
    data.update(overrides)
    return data
```

- [ ] **Step 3: Update existing service tests, add new ones (failing)**

In `apps/accounts/tests/test_services.py`, every existing `register_user(...)` call gains two keyword arguments. Patient calls (lines ~90, 119, 126, 143, 151, 161, 208) get:

```python
            is_adult_confirmed=True,
            profile_data=dict(PATIENT_PROFILE_DATA),
```

The psychologist call (`test_psychologist_registration_is_pending`, ~line 99) gets `is_adult_confirmed=True, profile_data=psychologist_profile_data(),` and the NGO call (`test_ngo_registration_is_pending`, ~line 108) gets `is_adult_confirmed=True, profile_data=ngo_profile_data(),`. Add the import:

```python
from core.testing import (
    PATIENT_PROFILE_DATA,
    ngo_profile_data,
    psychologist_profile_data,
)
```

Append a new test class:

```python
class RegisterUserProfileOrchestrationTests(TestCase):
    def test_each_role_gets_its_profile_and_adult_timestamp(self):
        patient = register_user(
            email="p@example.com", password="strongpass123", full_name="P",
            role=Role.PATIENT, is_adult_confirmed=True, profile_data=dict(PATIENT_PROFILE_DATA),
        )
        psych = register_user(
            email="d@example.com", password="strongpass123", full_name="D",
            role=Role.PSYCHOLOGIST, is_adult_confirmed=True, profile_data=psychologist_profile_data(),
        )
        ngo = register_user(
            email="n@example.com", password="strongpass123", full_name="N",
            role=Role.NGO, is_adult_confirmed=True, profile_data=ngo_profile_data(),
        )
        self.assertTrue(hasattr(patient, "patient_profile"))
        self.assertTrue(hasattr(psych, "psychologist_profile"))
        self.assertTrue(hasattr(ngo, "ngo_profile"))
        for user in (patient, psych, ngo):
            self.assertIsNotNone(user.adult_confirmed_at)

    def test_missing_adult_declaration_rejected_and_nothing_created(self):
        from core.exceptions import DomainValidationError

        with self.assertRaises(DomainValidationError):
            register_user(
                email="kid@example.com", password="strongpass123", full_name="K",
                role=Role.PATIENT, is_adult_confirmed=False, profile_data=dict(PATIENT_PROFILE_DATA),
            )
        self.assertFalse(User.objects.filter(email="kid@example.com").exists())

    def test_profile_failure_rolls_back_user(self):
        from unittest.mock import patch

        with patch.dict(
            "apps.accounts.services.PROFILE_CREATORS",
            {Role.PATIENT: lambda **kw: (_ for _ in ()).throw(RuntimeError("boom"))},
        ):
            with self.assertRaises(RuntimeError):
                register_user(
                    email="rollback@example.com", password="strongpass123", full_name="R",
                    role=Role.PATIENT, is_adult_confirmed=True, profile_data=dict(PATIENT_PROFILE_DATA),
                )
        self.assertFalse(User.objects.filter(email="rollback@example.com").exists())

    def test_duplicate_license_rolls_back_second_user(self):
        from apps.psychologists.services import DuplicateLicenseError

        register_user(
            email="d1@example.com", password="strongpass123", full_name="D1",
            role=Role.PSYCHOLOGIST, is_adult_confirmed=True, profile_data=psychologist_profile_data(),
        )
        with self.assertRaises(DuplicateLicenseError):
            register_user(
                email="d2@example.com", password="strongpass123", full_name="D2",
                role=Role.PSYCHOLOGIST, is_adult_confirmed=True, profile_data=psychologist_profile_data(),
            )
        self.assertFalse(User.objects.filter(email="d2@example.com").exists())

    def test_no_audit_event_when_registration_fails(self):
        from core.exceptions import DomainValidationError

        with self.assertNoLogs("mindcare.audit", level="INFO"):
            with self.assertRaises(DomainValidationError):
                register_user(
                    email="x@example.com", password="strongpass123", full_name="X",
                    role=Role.PATIENT, is_adult_confirmed=True, profile_data={"timezone": "Nope/Nope"},
                )
```

Run: `venv/Scripts/python -m pytest apps/accounts/tests/test_services.py -q`
Expected: FAIL (`register_user()` got unexpected keyword arguments).

- [ ] **Step 4: Implement orchestration**

In `apps/accounts/services.py`, change the imports and `register_user`:

```python
from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.utils.timezone import now

from apps.accounts.models import ApprovalStatus, Role, User
from apps.ngo.services import create_ngo_profile
from apps.patients.services import create_patient_profile
from apps.psychologists.services import create_psychologist_profile
from core.audit import log_auth_event
from core.exceptions import DomainValidationError

ROLES_REQUIRING_APPROVAL = {Role.PSYCHOLOGIST, Role.NGO}

# Direct calls, NOT signals: "every user has a profile, or neither exists" must
# be visible and testable (docs/decisions.md, 2026-09-26).
PROFILE_CREATORS = {
    Role.PATIENT: create_patient_profile,
    Role.PSYCHOLOGIST: create_psychologist_profile,
    Role.NGO: create_ngo_profile,
}


def register_user(*, email, password, full_name, role, is_adult_confirmed, profile_data):
    if is_adult_confirmed is not True:
        raise DomainValidationError(
            {"is_adult_confirmed": ["You must confirm you are 18 or older."]}
        )
    email = email.lower()
    approval_status = (
        ApprovalStatus.PENDING
        if role in ROLES_REQUIRING_APPROVAL
        else ApprovalStatus.APPROVED
    )
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=full_name,
                role=role,
                approval_status=approval_status,
                adult_confirmed_at=now(),
            )
            PROFILE_CREATORS[role](user=user, **profile_data)
    except IntegrityError as exc:
        if User.objects.filter(email__iexact=email).exists():
            raise DuplicateEmailError("A user with this email already exists.") from exc
        raise
    log_auth_event("register", user_id=user.id, email=user.email, role=user.role)
    return user
```

(Everything else in the file is unchanged.)

Run: `venv/Scripts/python -m pytest apps/accounts/tests/test_services.py -q`
Expected: PASS.

- [ ] **Step 5: Update existing API tests, add new ones (failing)**

In `apps/accounts/tests/test_api.py`, add `from core.testing import register_payload`. Replace **every** `self.client.post(REGISTER_URL, {...})` body with `register_payload(...)` plus `format="json"`, keeping each test's email / full_name / role / password overrides. For example `test_patient_can_register_and_is_approved` becomes:

```python
        response = self.client.post(
            REGISTER_URL,
            register_payload(role="patient", email="newpatient@example.com", full_name="New Patient"),
            format="json",
        )
```

`test_admin_role_is_rejected` builds `payload = register_payload(role="patient", email="wannabeadmin@example.com")`, then sets `payload["role"] = "admin"` before posting. The weak-password tests pass `password="password"` / `password="12345678"`. The throttle test uses `register_payload(role="patient", email=f"throttleuser{i}@example.com")`.

Append:

```python
class RegisterWithProfileAPITests(APITestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def test_psychologist_register_returns_profile(self):
        r = self.client.post(REGISTER_URL, register_payload(role="psychologist"), format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["approval_status"], "pending")
        self.assertEqual(r.data["profile"]["license_number"], "PMDC-12345")

    def test_patient_register_returns_pseudonym(self):
        r = self.client.post(REGISTER_URL, register_payload(role="patient"), format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertRegex(r.data["profile"]["pseudonym"], r"^Patient-[0-9a-f]{6}$")

    def test_adult_declaration_required(self):
        for value in (False, None):
            payload = register_payload(role="patient", is_adult_confirmed=value)
            r = self.client.post(REGISTER_URL, payload, format="json")
            self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("is_adult_confirmed", r.data)

    def test_missing_psychologist_credentials_rejected_nothing_created(self):
        payload = register_payload(role="psychologist", email="nocreds@example.com")
        del payload["profile"]["license_number"]
        r = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("license_number", r.data["profile"])
        self.assertFalse(User.objects.filter(email="nocreds@example.com").exists())

    def test_unknown_profile_key_rejected(self):
        payload = register_payload(role="patient")
        payload["profile"]["pseudonym"] = "Patient-000000"
        r = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_license_is_generic_400(self):
        self.client.post(REGISTER_URL, register_payload(role="psychologist"), format="json")
        r = self.client.post(
            REGISTER_URL, register_payload(role="psychologist", email="second@example.com"), format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            r.data["profile"]["license_number"], ["This license is already registered."]
        )
        self.assertFalse(User.objects.filter(email="second@example.com").exists())
```

Run: `venv/Scripts/python -m pytest apps/accounts/tests/test_api.py -q`
Expected: FAIL.

- [ ] **Step 6: Implement serializer + view changes**

In `apps/accounts/api/serializers.py`, add imports and extend `RegisterSerializer`:

```python
from apps.ngo.api.serializers import NGOProfileOwnerSerializer, NGORegistrationProfileSerializer
from apps.patients.api.serializers import (
    PatientProfileOwnerSerializer,
    PatientRegistrationProfileSerializer,
)
from apps.psychologists.api.serializers import (
    PsychologistProfileOwnerSerializer,
    PsychologistRegistrationProfileSerializer,
)

# role -> (registration input serializer, owner output serializer, User reverse accessor)
PROFILE_SERIALIZERS = {
    Role.PATIENT: (PatientRegistrationProfileSerializer, PatientProfileOwnerSerializer, "patient_profile"),
    Role.PSYCHOLOGIST: (
        PsychologistRegistrationProfileSerializer,
        PsychologistProfileOwnerSerializer,
        "psychologist_profile",
    ),
    Role.NGO: (NGORegistrationProfileSerializer, NGOProfileOwnerSerializer, "ngo_profile"),
}
```

Inside `RegisterSerializer` add the fields and a `validate()`:

```python
    is_adult_confirmed = serializers.BooleanField(
        help_text="Must be true: the user declares they are 18 or older."
    )
    profile = serializers.DictField(help_text="Role-specific profile object; see API docs.")

    def validate_is_adult_confirmed(self, value):
        if value is not True:
            raise serializers.ValidationError("You must confirm you are 18 or older.")
        return value

    def validate(self, attrs):
        input_serializer_class = PROFILE_SERIALIZERS[attrs["role"]][0]
        profile = input_serializer_class(data=attrs["profile"])
        if not profile.is_valid():
            raise serializers.ValidationError({"profile": profile.errors})
        attrs["profile"] = profile.validated_data
        return attrs
```

Note: `BooleanField` rejects `None` as "This field may not be null." — still a 400 under `is_adult_confirmed`, which the test expects.

Add a response serializer helper next to `UserPublicSerializer`:

```python
def registration_response_data(user):
    _, owner_serializer_class, accessor = PROFILE_SERIALIZERS[user.role]
    data = dict(UserPublicSerializer(user).data)
    data["profile"] = owner_serializer_class(getattr(user, accessor)).data
    return data
```

In `apps/accounts/api/views.py`, `RegisterView.post` becomes:

```python
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = services.register_user(
                email=data["email"],
                password=data["password"],
                full_name=data["full_name"],
                role=data["role"],
                is_adult_confirmed=data["is_adult_confirmed"],
                profile_data=data["profile"],
            )
        except services.DuplicateEmailError as exc:
            raise ValidationError({"email": str(exc)}) from exc
        except DomainValidationError as exc:
            errors = exc.errors if "is_adult_confirmed" in exc.errors else {"profile": exc.errors}
            raise ValidationError(errors, code=exc.code) from exc
        return Response(registration_response_data(user), status=status.HTTP_201_CREATED)
```

with imports `from core.exceptions import DomainValidationError` and `registration_response_data` from the serializers module.

Run: `venv/Scripts/python -m pytest apps/accounts -q`
Expected: PASS (existing + new).

- [ ] **Step 7: Module-reference** — update the existing `register_user()` and `RegisterView` rows in `### apps/accounts`:

```markdown
| `apps/accounts/services.py` | `register_user()` | Requires the 18+ declaration (stamps `adult_confirmed_at`), creates `User` + role profile in one transaction via `PROFILE_CREATORS` (no signals), logs a `register` audit event only on success | `POST /api/v1/accounts/register/` | MindCare Web, MindCare App |
| `apps/accounts/api/views.py` | `RegisterView` | Public registration for patient/psychologist/NGO (never admin); nested role-specific `profile` + `is_adult_confirmed`; returns the user and their profile | `POST /api/v1/accounts/register/` | MindCare Web, MindCare App |
```

and update the `User` row's purpose to mention `adult_confirmed_at`.

- [ ] **Step 8: Commit**

```bash
git add apps/accounts core/testing.py docs/module-reference.md
git commit -m "feat(accounts): 18+ declaration and atomic profile creation in register_user

BREAKING (API contract): register body now requires is_adult_confirmed and a
role-specific nested profile object.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Django admin for `User` (gap fix)

**Why this task exists:** there is **no `admin.py` anywhere in the repo** (verified 2026-09-28). The Phase 1 summary said there's a Django admin panel for approving pending accounts, and the spec (§10) relies on Django admin as the interim correction path, but in the code neither exists, so pending psychologists/NGOs can currently only be approved via the shell. This task is deliberately separate so it can be dropped if the user decides otherwise.

**Files:**
- Create: `apps/accounts/admin.py`, `apps/accounts/tests/test_admin.py`

**Interfaces:**
- Consumes: `User`, `ApprovalStatus`, `core.testing.make_admin`
- Produces: `UserAdmin` (approval status editable; `password`, `is_superuser`, `is_super_admin` not editable)

- [ ] **Step 1: Write the failing test**

`apps/accounts/tests/test_admin.py`:

```python
"""Django admin smoke tests for accounts."""

from django.contrib.admin.sites import site
from django.test import TestCase

from apps.accounts.models import ApprovalStatus, Role, User
from core.testing import make_user


class UserAdminTests(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser(email="root@example.com", password="strongpass123")
        self.client.force_login(self.root)

    def test_user_registered_with_safe_readonly_fields(self):
        model_admin = site._registry[User]
        readonly = set(model_admin.get_readonly_fields(None))
        self.assertTrue({"is_superuser", "is_super_admin", "adult_confirmed_at"} <= readonly)
        self.assertNotIn("password", model_admin.get_fields(None))

    def test_admin_can_approve_pending_psychologist(self):
        pending = make_user(role=Role.PSYCHOLOGIST, approval_status=ApprovalStatus.PENDING)
        url = f"/admin/accounts/user/{pending.pk}/change/"
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(
            url,
            {
                "email": pending.email,
                "full_name": pending.full_name,
                "role": pending.role,
                "approval_status": ApprovalStatus.APPROVED,
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        pending.refresh_from_db()
        self.assertEqual(pending.approval_status, ApprovalStatus.APPROVED)
```

Run: `venv/Scripts/python -m pytest apps/accounts/tests/test_admin.py -q`
Expected: FAIL (`KeyError: User` not registered).

- [ ] **Step 2: Implement**

`apps/accounts/admin.py`:

```python
"""Django admin for users — the interim approval path for pending psychologist
and NGO accounts until Phase 2.5's approval endpoints.

Deliberately NOT editable here: password (use the manage.py changepassword
command), is_superuser and is_super_admin (Phase 2.5 owns promote/demote and
the at-least-one-super-admin invariant).
"""

from django.contrib import admin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "full_name", "role", "approval_status", "is_active", "created_at"]
    list_filter = ["role", "approval_status", "is_active"]
    search_fields = ["email", "full_name"]
    ordering = ["-created_at"]
    fields = [
        "email", "full_name", "role", "approval_status", "is_active", "is_staff",
        "is_superuser", "is_super_admin", "adult_confirmed_at", "last_login",
        "created_at", "updated_at",
    ]
    readonly_fields = [
        "is_superuser", "is_super_admin", "adult_confirmed_at", "last_login",
        "created_at", "updated_at",
    ]
```

Run: `venv/Scripts/python -m pytest apps/accounts/tests/test_admin.py -q`
Expected: PASS.

- [ ] **Step 3: Module-reference row** under `### apps/accounts`:

```markdown
| `apps/accounts/admin.py` | `UserAdmin` | Interim Django-admin approval of pending psychologist/NGO accounts; password and super-admin flags not editable | `/admin/accounts/user/` | neither (Django admin) |
```

- [ ] **Step 4: Commit**

```bash
git add apps/accounts/admin.py apps/accounts/tests/test_admin.py docs/module-reference.md
git commit -m "feat(accounts): register User in Django admin as the interim approval path

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: `apps/stats` — `GET /api/v1/stats/public/`

**Files:**
- Create: `apps/stats/__init__.py`, `apps.py`, `models.py`, `selectors.py`, `api/__init__.py`, `api/serializers.py`, `api/views.py`, `api/urls.py`, `migrations/__init__.py`, `tests/__init__.py`, `tests/test_selectors.py`, `tests/test_api.py`
- Modify: `config/settings/base.py` (LOCAL_APPS, `public_stats` throttle), `config/urls.py` (API_V1_APPS)

**Interfaces:**
- Consumes: all three profile models, `User`, factories.
- Produces: `stats.selectors.get_public_platform_stats() -> {"people_in_care": int, "verified_therapists": int, "cities": int}`; `CACHE_KEY = "stats:public:v1"`, `CACHE_TIMEOUT = 300`.

- [ ] **Step 1: Scaffold**

`apps/stats/apps.py`:

```python
from django.apps import AppConfig


class StatsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.stats"
    verbose_name = "Public stats"
```

`apps/stats/models.py`: `"""No models: stats are computed from other apps' tables."""`. Empty `__init__.py` files for the package, `api/`, `migrations/`, `tests/`. Add `"apps.stats"` to `LOCAL_APPS`, `"stats"` to `API_V1_APPS`, `"public_stats": "60/min"` to the throttle rates.

- [ ] **Step 2: Write failing selector tests**

`apps/stats/tests/test_selectors.py`:

```python
"""Selector tests for the public stats."""

from django.core.cache import cache
from django.test import TestCase

from apps.accounts.models import ApprovalStatus, Role
from apps.ngo.services import create_ngo_profile
from apps.patients.services import create_patient_profile, update_patient_profile
from apps.psychologists.services import create_psychologist_profile
from apps.reference.models import Country
from apps.stats.selectors import CACHE_KEY, get_public_platform_stats
from core.testing import make_user, ngo_profile_data, psychologist_profile_data


class PublicStatsTests(TestCase):
    def setUp(self):
        cache.clear()
        pk = Country.objects.get(code="PK")
        # Patients: 2 active (one in Lahore), 1 deactivated.
        p1 = create_patient_profile(user=make_user(role=Role.PATIENT), timezone="UTC")
        update_patient_profile(profile=p1, country=pk, city="Lahore")
        create_patient_profile(user=make_user(role=Role.PATIENT), timezone="UTC")
        create_patient_profile(user=make_user(role=Role.PATIENT, is_active=False), timezone="UTC")
        # Psychologists: 1 approved (Lahore), 1 pending (Islamabad).
        create_psychologist_profile(
            user=make_user(role=Role.PSYCHOLOGIST), **psychologist_profile_data()
        )
        create_psychologist_profile(
            user=make_user(role=Role.PSYCHOLOGIST, approval_status=ApprovalStatus.PENDING),
            **psychologist_profile_data(license_number="OTHER-1", city="Islamabad"),
        )
        # NGO HQ in Karachi, nationwide + Quetta service areas (not counted).
        create_ngo_profile(
            user=make_user(role=Role.NGO),
            **ngo_profile_data(service_areas=[{"country": pk, "city": "Quetta"}]),
        )

    def test_counts(self):
        stats = get_public_platform_stats()
        # TEMPORARY definition: active patients (Phase 3 switches to accepted patients).
        self.assertEqual(stats["people_in_care"], 2)
        self.assertEqual(stats["verified_therapists"], 1)
        # Lahore (patient + psychologist, counted once), Islamabad, Karachi. Not Quetta.
        self.assertEqual(stats["cities"], 3)

    def test_result_is_cached(self):
        get_public_platform_stats()
        self.assertIsNotNone(cache.get(CACHE_KEY))
        create_patient_profile(user=make_user(role=Role.PATIENT), timezone="UTC")
        self.assertEqual(get_public_platform_stats()["people_in_care"], 2)
```

Run: `venv/Scripts/python -m pytest apps/stats/tests/test_selectors.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implement selector**

`apps/stats/selectors.py`:

```python
"""Read-path logic for the public platform stats served to MindCare Web.

Aggregate counts only; no per-user data. Cached so an unauthenticated endpoint
that counts across tables can't be used to load the database.
"""

from django.core.cache import cache

from apps.accounts.models import ApprovalStatus, Role, User
from apps.ngo.models import NGOProfile
from apps.patients.models import PatientProfile
from apps.psychologists.models import PsychologistProfile

CACHE_KEY = "stats:public:v1"
CACHE_TIMEOUT = 300


def _compute():
    # TEMPORARY interim definition (docs/decisions.md, 2026-09-26): registered
    # active patients. Phase 3 MUST switch this to patients with an accepted
    # psychologist once the relationship model exists.
    people_in_care = User.objects.filter(role=Role.PATIENT, is_active=True).count()
    verified_therapists = User.objects.filter(
        role=Role.PSYCHOLOGIST, is_active=True, approval_status=ApprovalStatus.APPROVED
    ).count()
    # Each profile's own city (NGO = headquarters). NGO service areas describe
    # reach, not presence, and are not counted. Early undercount of patient
    # cities is expected (patients fill in their city later).
    city_ids = (
        PatientProfile.objects.filter(city__isnull=False, user__is_active=True)
        .values("city_id")
        .union(
            PsychologistProfile.objects.filter(user__is_active=True).values("city_id"),
            NGOProfile.objects.filter(user__is_active=True).values("city_id"),
        )
    )
    return {
        "people_in_care": people_in_care,
        "verified_therapists": verified_therapists,
        "cities": city_ids.count(),
    }


def get_public_platform_stats():
    return cache.get_or_set(CACHE_KEY, _compute, CACHE_TIMEOUT)
```

Run: `venv/Scripts/python -m pytest apps/stats/tests/test_selectors.py -q`
Expected: PASS.

- [ ] **Step 4: Write failing API test**

`apps/stats/tests/test_api.py`:

```python
"""API tests for the public stats endpoint (contract used by MindCare Web)."""

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

URL = "/api/v1/stats/public/"


class PublicStatsAPITests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_unauthenticated_and_exact_contract(self):
        r = self.client.get(URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(set(r.data), {"people_in_care", "verified_therapists", "cities"})
        self.assertTrue(all(isinstance(v, int) for v in r.data.values()))

    def test_invalid_token_ignored(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer junk")
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_200_OK)

    def test_throttle_scope(self):
        from apps.stats.api.views import PublicStatsView

        self.assertEqual(PublicStatsView.throttle_classes[0].scope, "public_stats")
```

Run: `venv/Scripts/python -m pytest apps/stats/tests/test_api.py -q`
Expected: FAIL (404).

- [ ] **Step 5: Implement serializer, view, URL**

`apps/stats/api/serializers.py`:

```python
"""DRF serializers for the stats API."""

from rest_framework import serializers


class PublicStatsSerializer(serializers.Serializer):
    people_in_care = serializers.IntegerField()
    verified_therapists = serializers.IntegerField()
    cities = serializers.IntegerField()
```

`apps/stats/api/views.py`:

```python
"""DRF views for the stats API. Thin: selector -> serializer."""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.stats import selectors
from apps.stats.api.serializers import PublicStatsSerializer


class PublicStatsRateThrottle(AnonRateThrottle):
    scope = "public_stats"


class PublicStatsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PublicStatsRateThrottle]

    def get(self, request):
        return Response(PublicStatsSerializer(selectors.get_public_platform_stats()).data)
```

`apps/stats/api/urls.py`:

```python
"""URL routes for the stats API, included under /api/v1/stats/."""

from django.urls import path

from apps.stats.api.views import PublicStatsView

app_name = "stats"

urlpatterns = [
    path("public/", PublicStatsView.as_view(), name="public"),
]
```

Run: `venv/Scripts/python -m pytest apps/stats -q`
Expected: PASS.

- [ ] **Step 6: Module-reference rows** in a new `### apps/stats` section:

```markdown
| `apps/stats/selectors.py` | `get_public_platform_stats()` | Cached (5 min) aggregate counts: active patients (TEMPORARY until Phase 3), approved psychologists, distinct profile cities (not NGO service areas) | `GET /api/v1/stats/public/` | MindCare Web |
| `apps/stats/api/views.py` | `PublicStatsView` | Unauthenticated, rate-limited (`public_stats`, 60/min) public counts; exact contract `{people_in_care, verified_therapists, cities}` | `GET /api/v1/stats/public/` | MindCare Web |
```

- [ ] **Step 7: Commit**

```bash
git add apps/stats config docs/module-reference.md
git commit -m "feat(stats): public platform stats endpoint for MindCare Web

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Docs, real-schema verification, full suite

**Files:**
- Modify: `docs/architecture.md`, `docs/decisions.md`, `docs/roadmap.md`

- [ ] **Step 1: Docs**

`docs/architecture.md`, Modules list, add:

```markdown
- **reference** — shared, admin-editable reference data (countries, cities, languages,
  specializations) used by every profile app.
- **stats** — public aggregate platform counts for the marketing site (no models).
```

and extend the `core/` line with `validators.py`, `choices.py`, `serializers.py`, `testing.py` (test factories only).

`docs/decisions.md`, append:

```markdown
## 2026-09-28 - Two new apps (`reference`, `stats`) and direct-call profile orchestration
**Why:** Country/City/Language/Specialization are shared by three profile apps and
`core/` can't own models, so they get one owner, `apps/reference`. `GET
/stats/public/` must live at `/api/v1/stats/` to match the URL contract MindCare
Web already calls, so it gets `apps/stats`, which has no models. `register_user()`
creates each profile by calling that app's service directly inside one
transaction, not through a signal: "every user has a profile, or neither exists"
must stay visible and testable.
**Alternatives considered:** Reference tables in `accounts` (unrelated to auth);
stats in `reports` (wrong URL); `post_save` signals (the rollback guarantee would
depend on a handler that's easy to break without anyone noticing).
```

`docs/roadmap.md`: leave Phase 2 as "In progress" (it becomes "Done" when the PR merges).

- [ ] **Step 2: Full suite + lint**

Run: `venv/Scripts/python -m pytest -q`
Expected: all tests pass (50 existing, updated, plus new ones).

Run: `venv/Scripts/python -m ruff check . && venv/Scripts/python -m ruff format --check .` (or `pre-commit run --all-files` from the repo root)
Expected: clean.

- [ ] **Step 3: Migrate the dev database and verify the real schema**

First confirm with the user that the local `.env` `DATABASE_URL` points at a **development** database, not the production Supabase project. Report host and database name only, never credentials.

Check the seed is reversible first. At this point no profile tables exist yet, so `PROTECT` can't block the unseed:

```bash
venv/Scripts/python manage.py migrate reference
venv/Scripts/python manage.py migrate reference 0001
venv/Scripts/python manage.py migrate reference
```

Expected: the second command unapplies `0002_seed_reference_data` without error, and the third re-applies it.

Run: `venv/Scripts/python manage.py migrate`
Expected: applies `accounts.0002`, `patients.0001`, `psychologists.0001`, `ngo.0001` (reference is already migrated).

Then verify via the Postgres MCP (`mcp__postgres__query`), or `venv/Scripts/python manage.py dbshell` if the MCP is still unavailable (and say which was used):

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('reference_country','reference_city','reference_language',
                     'reference_specialization','patients_patientprofile',
                     'psychologists_psychologistprofile','ngo_ngoprofile','ngo_ngoservicearea');
-- expect 8 rows

SELECT conname FROM pg_constraint
WHERE conname IN ('psychologists_unique_license_per_country',
                  'ngo_unique_registration_per_country');
-- expect 2 rows

SELECT indexname, indexdef FROM pg_indexes
WHERE indexname IN ('reference_city_unique_name_per_country_ci',
                    'ngo_service_area_unique_nationwide',
                    'ngo_service_area_unique_city');
-- expect 3 rows; the city index uses lower(name); the service-area ones have WHERE clauses

SELECT (SELECT count(*) FROM reference_country)        AS countries,   -- 249
       (SELECT count(*) FROM reference_language)       AS languages,   -- 183
       (SELECT count(*) FROM reference_specialization) AS specs,       -- 12
       (SELECT count(*) FROM reference_city c JOIN reference_country k ON k.id = c.country_id
         WHERE k.code = 'PK')                          AS pk_cities;   -- 32

SELECT column_name, is_nullable FROM information_schema.columns
WHERE table_name = 'accounts_user' AND column_name = 'adult_confirmed_at';
-- expect 1 row, is_nullable = YES
```

(Functional and conditional unique constraints are created as unique **indexes** in Postgres, which is why they're checked in `pg_indexes`, not `pg_constraint`.)

- [ ] **Step 4: Commit**

```bash
git add docs
git commit -m "docs: record reference/stats apps and profile orchestration decision

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Hand back for the PR** (do not open it inside this task). Before the PR: merge `origin/main` into `backend-work` again if it has moved, re-run the full suite, then open the PR with `gh` (user-approved), including the frontend handoff notes from spec §15.
