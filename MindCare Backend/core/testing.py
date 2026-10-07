"""Test factories shared across apps' test suites. Not used by runtime code."""

import importlib
import uuid

from django.test import TransactionTestCase

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


def psychologist_profile_data(**overrides):
    from apps.reference.models import Country, Language, Specialization

    pakistan = Country.objects.get(code="PK")
    data = {
        "license_number": "PMDC-12345",
        "license_issuing_country": pakistan,
        "license_issuing_authority": "Pakistan Medical and Dental Council",
        "qualifications": "MS Clinical Psychology, University of the Punjab",
        "specializations": list(
            Specialization.objects.filter(slug__in=["anxiety", "depression"])
        ),
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


def admin_change_form_data(response):
    """POST data that resubmits an admin change form unchanged, built from the
    GET response's context (form fields plus any inline formsets). Tests then
    override the keys they want to change."""

    def collect(form, data):
        for name in form.fields:
            value = form[name].value()
            key = form.add_prefix(name)
            if value is None or value == "":
                continue
            if value is True:
                data[key] = "on"
            elif value is False:
                continue
            elif isinstance(value, list | tuple | set):
                data[key] = [str(v) for v in value]
            else:
                data[key] = str(value)

    data = {}
    collect(response.context["adminform"].form, data)
    for inline in response.context.get("inline_admin_formsets", []):
        formset = inline.formset
        data.update(
            {
                f"{formset.prefix}-TOTAL_FORMS": str(len(formset.forms)),
                f"{formset.prefix}-INITIAL_FORMS": str(formset.initial_form_count()),
                f"{formset.prefix}-MIN_NUM_FORMS": "0",
                f"{formset.prefix}-MAX_NUM_FORMS": "1000",
            }
        )
        for form in formset.forms:
            collect(form, data)
    return data


def make_patient(*, date_of_birth=None, timezone="Asia/Karachi", **user_extra):
    """A patient user + profile. Pass date_of_birth=False for a profile without
    one; by default the patient is born 1995-01-01."""
    from datetime import date

    from apps.patients.services import create_patient_profile

    user = make_user(role=Role.PATIENT, **user_extra)
    profile = create_patient_profile(user=user, timezone=timezone)
    if date_of_birth is not False:
        profile.date_of_birth = date_of_birth or date(1995, 1, 1)
        profile.save(update_fields=["date_of_birth", "updated_at"])
    return profile


def make_psychologist(
    *,
    approval_status=ApprovalStatus.APPROVED,
    is_active=True,
    full_name=None,
    **profile_overrides,
):
    """An approved, active psychologist user + profile with a unique license."""
    from apps.psychologists.services import create_psychologist_profile

    extra = {"approval_status": approval_status, "is_active": is_active}
    if full_name:
        extra["full_name"] = full_name
    user = make_user(role=Role.PSYCHOLOGIST, **extra)
    profile_overrides.setdefault(
        "license_number", f"LIC-{uuid.uuid4().hex[:8].upper()}"
    )
    return create_psychologist_profile(
        user=user, **psychologist_profile_data(**profile_overrides)
    )


def reseed_reference_data():
    """A TransactionTestCase flushes every table after it runs, including the
    reference data seeded by the RunPython migrations (countries, cities,
    languages, specializations) that make_psychologist and friends need, so the
    next test would start with no countries. Re-run the seed migrations if that
    happened; a no-op when the data is present.
    (serialized_rollback clashes with the content types post_migrate recreates.)"""
    from django.apps import apps

    from apps.reference.models import Country

    if Country.objects.exists():
        return
    seed = importlib.import_module("apps.reference.migrations.0002_seed_reference_data")
    verify = importlib.import_module(
        "apps.reference.migrations.0003_city_is_verified_and_turkiye"
    )
    seed.seed(apps, None)
    verify.verify_seeded_cities_and_rename_turkiye(apps, None)


class ReferenceDataTransactionTestCase(TransactionTestCase):
    """TransactionTestCase that never leaves the reference tables empty: seeds them
    before each test if a previous flush emptied them, and re-seeds them after its own
    flush, so later tests don't depend on running order.

    Overrides Django's internal ``TransactionTestCase._fixture_teardown()`` hook
    (called from ``_post_teardown()``, after ``tearDown()``), which is where the
    flush happens; re-seeding after ``super()`` is the only point that runs after it."""

    def setUp(self):
        super().setUp()
        reseed_reference_data()

    def _fixture_teardown(self):
        super()._fixture_teardown()  # the flush
        reseed_reference_data()
