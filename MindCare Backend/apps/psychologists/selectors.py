"""Read-path query logic for psychologists.

Views call into these functions to fetch data. Object-level ownership
filtering (e.g. scoping a psychologist's queries to their own patients)
belongs here, not just in permission classes.
"""

from django.db.models import F

from apps.accounts.models import ApprovalStatus, Role
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


def visible_psychologists():
    """Approved, active psychologists: the only ones patients can see or request."""
    return (
        PsychologistProfile.objects.filter(
            user__role=Role.PSYCHOLOGIST,
            user__is_active=True,
            user__approval_status=ApprovalStatus.APPROVED,
        )
        .select_related("user", "country", "city__country", "license_issuing_country")
        .prefetch_related("specializations", "languages")
    )


def list_directory(
    *,
    specialization=None,
    language=None,
    gender=None,
    country=None,
    city=None,
    accepting=None,
    search=None,
):
    """Patient-facing directory. Filters combine with AND. Accepting first, then
    most recently active (never active last), then name."""
    qs = visible_psychologists()
    if specialization:
        qs = qs.filter(specializations__slug=specialization)
    if language:
        qs = qs.filter(languages__code=language)
    if gender:
        qs = qs.filter(gender=gender)
    if country:
        qs = qs.filter(country__code=country.upper())
    if city:
        qs = qs.filter(city_id=city)
    if accepting is not None:
        qs = qs.filter(is_accepting_patients=accepting)
    if search:
        qs = qs.filter(user__full_name__icontains=search.strip())
    return qs.order_by(
        F("is_accepting_patients").desc(),
        F("user__last_active_at").desc(nulls_last=True),
        "user__full_name",
        "pk",
    )


def get_directory_entry(*, profile_id):
    return visible_psychologists().filter(pk=profile_id).first()
