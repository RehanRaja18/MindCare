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
