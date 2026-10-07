"""Read-path query logic for care relationships (incl. ownership filtering)."""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import ApprovalStatus, Role
from apps.relationships.models import CareRelationship, RelationshipStatus
from core.validators import age_on

RECENT_LIMIT = 10
_PSYCH_VISIBLE = Q(
    psychologist__user__is_active=True,
    psychologist__user__approval_status=ApprovalStatus.APPROVED,
)


def psychologist_is_visible(psychologist_profile):
    user = psychologist_profile.user
    return user.is_active and user.approval_status == ApprovalStatus.APPROVED


def _user_is_visible_psychologist(user):
    return (
        user is not None
        and getattr(user, "is_authenticated", False)
        and user.role == Role.PSYCHOLOGIST
        and user.is_active
        and user.approval_status == ApprovalStatus.APPROVED
    )


def get_active_relationship(*, patient):
    """The ONE answer to "is this patient in active care?". Phase 9 adds
    "and the subscription is paid" here."""
    return (
        CareRelationship.objects.filter(
            patient=patient, status=RelationshipStatus.ACCEPTED
        )
        .filter(_PSYCH_VISIBLE)
        .select_related("psychologist__user")
        .first()
    )


def is_assigned_psychologist(*, viewer, patient_profile):
    if not _user_is_visible_psychologist(viewer):
        return False
    return CareRelationship.objects.filter(
        patient=patient_profile,
        psychologist__user=viewer,
        status=RelationshipStatus.ACCEPTED,
    ).exists()


def _code_name(obj):
    return None if obj is None else {"code": obj.code, "name": obj.name}


def requester_summary(*, relationship):
    """What a psychologist sees before accepting. Never the name, city, phone or
    exact date of birth (docs/decisions.md, 2026-10-06)."""
    p = relationship.patient
    today = timezone.localdate()
    return {
        "pseudonym": p.pseudonym,
        "preferred_language": _code_name(p.preferred_language),
        "timezone": p.timezone,
        "country": _code_name(p.country),
        "gender": p.gender,
        "age": age_on(p.date_of_birth, today) if p.date_of_birth else None,
    }


def psychologist_inbox(*, psychologist_user):
    if not _user_is_visible_psychologist(psychologist_user):
        return CareRelationship.objects.none()
    return (
        CareRelationship.objects.filter(
            psychologist__user=psychologist_user,
            status=RelationshipStatus.PENDING,
            expires_at__gt=timezone.now(),
        )
        .select_related("patient__country", "patient__preferred_language")
        .order_by("requested_at", "pk")
    )


def psychologist_patients(*, psychologist_user):
    if not _user_is_visible_psychologist(psychologist_user):
        return CareRelationship.objects.none()
    return (
        CareRelationship.objects.filter(
            psychologist__user=psychologist_user, status=RelationshipStatus.ACCEPTED
        )
        .select_related(
            "patient__user",
            "patient__country",
            "patient__city__country",
            "patient__preferred_language",
        )
        .order_by("-responded_at", "-pk")
    )


def psychologist_patient(*, psychologist_user, relationship_id):
    return (
        psychologist_patients(psychologist_user=psychologist_user)
        .filter(pk=relationship_id)
        .first()
    )


def psychologist_history(*, psychologist_user):
    return (
        CareRelationship.objects.filter(
            psychologist__user=psychologist_user, status=RelationshipStatus.ENDED
        )
        .select_related("patient")
        .order_by("-ended_at", "-pk")
    )


_PSYCH_CARD_RELATED = (
    "psychologist__user",
    "psychologist__country",
    "psychologist__city__country",
    "psychologist__license_issuing_country",
)


def patient_current(*, patient_user):
    return (
        CareRelationship.objects.filter(patient__user=patient_user)
        .filter(
            Q(status=RelationshipStatus.ACCEPTED)
            | Q(status=RelationshipStatus.PENDING, expires_at__gt=timezone.now())
        )
        .select_related(*_PSYCH_CARD_RELATED)
        .prefetch_related("psychologist__specializations", "psychologist__languages")
        .first()
    )


def patient_requests(*, patient_user):
    return (
        CareRelationship.objects.filter(patient__user=patient_user)
        .select_related(*_PSYCH_CARD_RELATED)
        .prefetch_related("psychologist__specializations", "psychologist__languages")
        .order_by("-requested_at", "-pk")
    )


def recent_psychologists(*, patient_user, limit=RECENT_LIMIT):
    open_psych_ids = CareRelationship.objects.filter(
        patient__user=patient_user,
        status__in=[RelationshipStatus.PENDING, RelationshipStatus.ACCEPTED],
    ).values_list("psychologist_id", flat=True)
    rows = (
        CareRelationship.objects.filter(
            patient__user=patient_user, status=RelationshipStatus.ENDED
        )
        .filter(_PSYCH_VISIBLE)
        .exclude(psychologist_id__in=list(open_psych_ids))
        .select_related(*_PSYCH_CARD_RELATED)
        .prefetch_related("psychologist__specializations", "psychologist__languages")
        .order_by("-ended_at", "-pk")
    )
    seen, result = set(), []
    for row in rows:
        if row.psychologist_id not in seen:
            seen.add(row.psychologist_id)
            result.append(row.psychologist)
            if len(result) == limit:
                break
    return result


def last_active_band(dt, *, now=None):
    if dt is None:
        return "never"
    age = (now or timezone.now()) - dt
    if age < timedelta(hours=24):
        return "today"
    if age < timedelta(days=7):
        return "this_week"
    if age < timedelta(days=30):
        return "this_month"
    return "over_a_month"
