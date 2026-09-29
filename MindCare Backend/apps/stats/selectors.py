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
