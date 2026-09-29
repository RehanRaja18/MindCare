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
