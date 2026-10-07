"""Demo accounts for presentations: 6 approved psychologists and 2 patients.

Every account is clearly fake: names end in "(Demo)", emails are on example.com,
license numbers start with DEMO-. Accounts are created through the real services
(register_user, update_patient_profile, set_accepting_status), so they look
exactly like accounts made through the API. The password is passed in by the
caller (the seed_demo command reads it from DEMO_PASSWORD); none is stored here.

remove_demo_accounts() deletes only the emails listed below. CareRelationship
rows reference profiles with on_delete=PROTECT, so they are deleted first.
"""

from datetime import date

from django.db import transaction
from django.db.models import Q

from apps.accounts.models import ApprovalStatus, Role, User
from apps.accounts.services import register_user
from apps.patients.services import update_patient_profile
from apps.relationships.models import CareRelationship
from apps.relationships.services import set_accepting_status

DEMO_PSYCHOLOGISTS = [
    {
        "email": "demo.psych.sara@example.com",
        "full_name": "Dr. Sara Ahmed (Demo)",
        "accepting": True,
        "profile": {
            "license_number": "DEMO-0001",
            "license_issuing_country": "PK",
            "specializations": ["anxiety", "stress-management"],
            "languages": ["en", "ur"],
            "country": "PK",
            "city": "Lahore",
            "timezone": "Asia/Karachi",
            "gender": "female",
            "years_of_experience": 8,
            "bio": "Demo profile. CBT for anxiety and work stress.",
        },
    },
    {
        "email": "demo.psych.bilal@example.com",
        "full_name": "Dr. Bilal Hussain (Demo)",
        "accepting": True,
        "profile": {
            "license_number": "DEMO-0002",
            "license_issuing_country": "PK",
            "specializations": ["depression", "grief"],
            "languages": ["ur", "pa"],
            "country": "PK",
            "city": "Karachi",
            "timezone": "Asia/Karachi",
            "gender": "male",
            "years_of_experience": 12,
            "bio": "Demo profile. Depression and bereavement support.",
        },
    },
    {
        "email": "demo.psych.ayesha@example.com",
        "full_name": "Dr. Ayesha Malik (Demo)",
        "accepting": False,
        "not_accepting_reason": "fully_booked",
        "profile": {
            "license_number": "DEMO-0003",
            "license_issuing_country": "PK",
            "specializations": ["trauma-ptsd", "anxiety"],
            "languages": ["en", "ur"],
            "country": "PK",
            "city": "Islamabad",
            "timezone": "Asia/Karachi",
            "gender": "female",
            "years_of_experience": 15,
            "bio": "Demo profile. Trauma-focused therapy.",
        },
    },
    {
        "email": "demo.psych.imran@example.com",
        "full_name": "Dr. Imran Khan (Demo)",
        "accepting": True,
        "profile": {
            "license_number": "DEMO-0004",
            "license_issuing_country": "PK",
            "specializations": ["addiction-substance-use", "anger-management"],
            "languages": ["ps", "ur", "en"],
            "country": "PK",
            "city": "Peshawar",
            "timezone": "Asia/Karachi",
            "gender": "male",
            "years_of_experience": 6,
            "bio": "Demo profile. Addiction recovery and anger management.",
        },
    },
    {
        "email": "demo.psych.emily@example.com",
        "full_name": "Dr. Emily Carter (Demo)",
        "accepting": False,
        "not_accepting_reason": "away",
        "profile": {
            "license_number": "DEMO-0005",
            "license_issuing_country": "GB",
            "specializations": ["couples-relationship", "family-therapy"],
            "languages": ["en"],
            "country": "GB",
            "city": "London",
            "timezone": "Europe/London",
            "gender": "female",
            "years_of_experience": 10,
            "bio": "Demo profile. Couples and family therapy, online sessions.",
        },
    },
    {
        "email": "demo.psych.omar@example.com",
        "full_name": "Dr. Omar Farooq (Demo)",
        "accepting": True,
        "profile": {
            "license_number": "DEMO-0006",
            "license_issuing_country": "AE",
            "specializations": ["ocd", "sleep-issues"],
            "languages": ["ar", "en", "ur"],
            "country": "AE",
            "city": "Dubai",
            "timezone": "Asia/Dubai",
            "gender": None,
            "years_of_experience": 4,
            "bio": "Demo profile. OCD and insomnia.",
        },
    },
]

DEMO_PATIENTS = [
    {
        "email": "demo.patient.hina@example.com",
        "full_name": "Hina Raza (Demo)",
        "timezone": "Asia/Karachi",
        "date_of_birth": date(1998, 4, 12),
        "gender": "female",
    },
    {
        "email": "demo.patient.daniyal@example.com",
        "full_name": "Daniyal Shah (Demo)",
        "timezone": "Europe/London",
        "date_of_birth": date(1991, 9, 3),
        "gender": "male",
    },
]

DEMO_PSYCHOLOGIST_EMAILS = [p["email"] for p in DEMO_PSYCHOLOGISTS]
DEMO_PATIENT_EMAILS = [p["email"] for p in DEMO_PATIENTS]
DEMO_EMAILS = DEMO_PSYCHOLOGIST_EMAILS + DEMO_PATIENT_EMAILS


def _psychologist_profile_data(spec):
    from apps.reference.models import Country, Language, Specialization

    p = spec["profile"]
    country = Country.objects.get(code=p["country"])
    return {
        "license_number": p["license_number"],
        "license_issuing_country": Country.objects.get(
            code=p["license_issuing_country"]
        ),
        "license_issuing_authority": "Demo Licensing Authority (fictional)",
        "qualifications": "Demo qualification (fictional)",
        "specializations": list(
            Specialization.objects.filter(slug__in=p["specializations"])
        ),
        "years_of_experience": p["years_of_experience"],
        "languages": list(Language.objects.filter(code__in=p["languages"])),
        "country": country,
        "city": p["city"],
        "timezone": p["timezone"],
        "gender": p["gender"],
        "bio": p["bio"],
    }


@transaction.atomic
def seed_demo_accounts(*, password):
    """Create any missing demo account; existing ones are left as they are,
    apart from re-applying approval, the accepting switch and date of birth."""
    created = existing = 0

    for spec in DEMO_PSYCHOLOGISTS:
        user = User.objects.filter(email=spec["email"]).first()
        if user is None:
            user = register_user(
                email=spec["email"],
                password=password,
                full_name=spec["full_name"],
                role=Role.PSYCHOLOGIST,
                is_adult_confirmed=True,
                profile_data=_psychologist_profile_data(spec),
            )
            created += 1
        else:
            existing += 1
        # No approval service exists until Phase 2.5; this is what Django admin does.
        if user.approval_status != ApprovalStatus.APPROVED:
            user.approval_status = ApprovalStatus.APPROVED
            user.save(update_fields=["approval_status"])
        set_accepting_status(
            psychologist_user=user,
            accepting=spec["accepting"],
            reason=spec.get("not_accepting_reason"),
        )

    for spec in DEMO_PATIENTS:
        user = User.objects.filter(email=spec["email"]).first()
        if user is None:
            user = register_user(
                email=spec["email"],
                password=password,
                full_name=spec["full_name"],
                role=Role.PATIENT,
                is_adult_confirmed=True,
                profile_data={"timezone": spec["timezone"]},
            )
            created += 1
        else:
            existing += 1
        update_patient_profile(
            profile=user.patient_profile,
            date_of_birth=spec["date_of_birth"],
            gender=spec["gender"],
        )

    return {"created": created, "existing": existing}


@transaction.atomic
def remove_demo_accounts():
    """Delete the demo accounts only: their relationship rows first (PROTECT),
    then the users (profiles cascade)."""
    users = User.objects.filter(email__in=DEMO_EMAILS)
    rels = CareRelationship.objects.filter(
        Q(patient__user__in=users) | Q(psychologist__user__in=users)
    )
    relationships = rels.count()
    rels.delete()
    count = users.count()
    users.delete()
    return {"users": count, "relationships": relationships}
