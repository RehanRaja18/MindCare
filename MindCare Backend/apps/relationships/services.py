"""Write-path business logic for care relationships."""

from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.utils import timezone

from apps.accounts.models import ApprovalStatus, Role, User
from apps.patients.models import PatientProfile
from apps.psychologists.models import NotAcceptingReason, PsychologistProfile
from apps.relationships.models import (
    DECLINE_COOLDOWN,
    OPEN_STATUSES,
    PATIENT_END_REASONS,
    PSYCHOLOGIST_END_REASONS,
    REQUEST_EXPIRY,
    SYSTEM_END_REASONS,
    CareRelationship,
    DeclineReason,
    EndedBy,
    EndReason,
    RelationshipStatus,
)
from core.audit import log_relationship_event
from core.exceptions import DomainValidationError

DOB_REQUIRED = (
    "Add your date of birth to your profile before requesting a psychologist."
)
NOT_AVAILABLE = "This psychologist isn't available."
NOT_ACCEPTING = "This psychologist isn't accepting new patients right now."
COOLDOWN = "You can request this psychologist again on {date}."
ALREADY_OPEN = "You already have a psychologist or a pending request."
NOT_PENDING = "This request is no longer pending."
INVALID_REASON = "Choose a valid reason."
NOT_A_PATIENT = "Only patients can request a psychologist."
NO_PSYCHOLOGIST = "You don't have a psychologist right now."
REASON_REQUIRED = "Choose a reason."
CONFIRM_REQUIRED = "Confirm that you want to end this relationship."
ACCEPTING_REASON_REQUIRED = "Choose a reason when you're not accepting new patients."
NOT_ACTIVE = "This relationship isn't active."

_ALLOWED_END_REASONS = {
    EndedBy.PATIENT: PATIENT_END_REASONS,
    EndedBy.PSYCHOLOGIST: PSYCHOLOGIST_END_REASONS,
    EndedBy.SYSTEM: SYSTEM_END_REASONS,
}


def _log_after_commit(**fields):
    """Audit lines describe committed changes only: if the surrounding transaction
    rolls back, nothing is logged. Outside a transaction it runs immediately."""
    transaction.on_commit(lambda: log_relationship_event(**fields))


def _lock(**filters):
    """The row matching filters, locked for this transaction; 404 if none."""
    rel = (
        CareRelationship.objects.select_for_update(of=("self",))
        .filter(**filters)
        .first()
    )
    if rel is None:
        raise Http404
    return rel


def _expire_if_stale(rel, now):
    if rel.status == RelationshipStatus.PENDING and rel.expires_at <= now:
        rel.status = RelationshipStatus.EXPIRED
        rel.save(update_fields=["status", "updated_at"])
        _log_after_commit(
            event="expired", relationship_id=rel.pk, actor_id=None, actor_role="system"
        )
        return True
    return False


def _require_visible_psychologist_user(user):
    if not (user.is_active and user.approval_status == ApprovalStatus.APPROVED):
        raise Http404


def request_psychologist(*, patient_user, psychologist_id):
    patient = PatientProfile.objects.filter(user=patient_user).first()
    if patient is None:
        raise DomainValidationError({"patient": [NOT_A_PATIENT]})
    if patient.date_of_birth is None:
        raise DomainValidationError({"date_of_birth": [DOB_REQUIRED]})
    psychologist = (
        PsychologistProfile.objects.select_related("user")
        .filter(
            pk=psychologist_id,
            user__role=Role.PSYCHOLOGIST,
            user__is_active=True,
            user__approval_status=ApprovalStatus.APPROVED,
        )
        .first()
    )
    if psychologist is None:
        raise DomainValidationError({"psychologist": [NOT_AVAILABLE]})
    if not psychologist.is_accepting_patients:
        raise DomainValidationError({"psychologist": [NOT_ACCEPTING]})

    now = timezone.now()
    with transaction.atomic():
        stale = CareRelationship.objects.select_for_update(of=("self",)).filter(
            patient=patient, status=RelationshipStatus.PENDING, expires_at__lte=now
        )
        for rel in stale:
            _expire_if_stale(rel, now)
        if CareRelationship.objects.filter(
            patient=patient, status__in=OPEN_STATUSES
        ).exists():
            raise DomainValidationError({"relationship": [ALREADY_OPEN]})
        recent_decline = (
            CareRelationship.objects.filter(
                patient=patient,
                psychologist=psychologist,
                status=RelationshipStatus.DECLINED,
                cooldown_until__gt=now,
            )
            .order_by("-cooldown_until")
            .first()
        )
        if recent_decline is not None:
            local = timezone.localtime(
                recent_decline.cooldown_until, ZoneInfo(patient.timezone)
            )
            raise DomainValidationError(
                {"psychologist": [COOLDOWN.format(date=local.date().isoformat())]}
            )
        try:
            with transaction.atomic():
                rel = CareRelationship.objects.create(
                    patient=patient,
                    psychologist=psychologist,
                    status=RelationshipStatus.PENDING,
                    requested_at=now,
                    expires_at=now + REQUEST_EXPIRY,
                )
        except IntegrityError as exc:
            raise DomainValidationError({"relationship": [ALREADY_OPEN]}) from exc
    _log_after_commit(
        event="requested",
        relationship_id=rel.pk,
        actor_id=patient_user.pk,
        actor_role="patient",
    )
    return rel


def _answer(rel_filters, now, apply):
    """Lock the row, expire it if stale, else apply() it if still pending. The
    expiry commits even when the request is rejected afterwards."""
    with transaction.atomic():
        rel = _lock(**rel_filters)
        stale = _expire_if_stale(rel, now)
        if not stale and rel.status == RelationshipStatus.PENDING:
            apply(rel)
            return rel
    raise DomainValidationError({"relationship": [NOT_PENDING]})


def cancel_request(*, patient_user, relationship_id):
    now = timezone.now()

    def apply(rel):
        rel.status = RelationshipStatus.CANCELLED
        rel.save(update_fields=["status", "updated_at"])

    rel = _answer({"pk": relationship_id, "patient__user": patient_user}, now, apply)
    _log_after_commit(
        event="cancelled",
        relationship_id=rel.pk,
        actor_id=patient_user.pk,
        actor_role="patient",
    )
    return rel


def accept_request(*, psychologist_user, relationship_id):
    _require_visible_psychologist_user(psychologist_user)
    now = timezone.now()

    def apply(rel):
        rel.status = RelationshipStatus.ACCEPTED
        rel.responded_at = now
        rel.save(update_fields=["status", "responded_at", "updated_at"])

    rel = _answer(
        {"pk": relationship_id, "psychologist__user": psychologist_user}, now, apply
    )
    _log_after_commit(
        event="accepted",
        relationship_id=rel.pk,
        actor_id=psychologist_user.pk,
        actor_role="psychologist",
    )
    return rel


def decline_request(*, psychologist_user, relationship_id, reason=None):
    _require_visible_psychologist_user(psychologist_user)
    if reason is not None and reason not in DeclineReason.values:
        raise DomainValidationError({"reason": [INVALID_REASON]})
    now = timezone.now()

    def apply(rel):
        rel.status = RelationshipStatus.DECLINED
        rel.responded_at = now
        rel.cooldown_until = now + DECLINE_COOLDOWN
        rel.decline_reason = reason
        rel.save(
            update_fields=[
                "status",
                "responded_at",
                "cooldown_until",
                "decline_reason",
                "updated_at",
            ]
        )

    rel = _answer(
        {"pk": relationship_id, "psychologist__user": psychologist_user}, now, apply
    )
    _log_after_commit(
        event="declined",
        relationship_id=rel.pk,
        actor_id=psychologist_user.pk,
        actor_role="psychologist",
        reason=reason,
    )
    return rel


def end_relationship(*, relationship, ended_by, reason, actor_id=None):
    """The ONLY way an accepted relationship ends (Phase 9 calls this with
    ended_by="system", reason="subscription_lapsed")."""
    if reason not in _ALLOWED_END_REASONS.get(ended_by, ()):
        raise DomainValidationError({"reason": [INVALID_REASON]})
    with transaction.atomic():
        rel = _lock(pk=relationship.pk)
        if rel.status != RelationshipStatus.ACCEPTED:
            raise DomainValidationError({"relationship": [NOT_ACTIVE]})
        rel.status = RelationshipStatus.ENDED
        rel.ended_at = timezone.now()
        rel.ended_by = ended_by
        rel.end_reason = reason
        rel.save(
            update_fields=["status", "ended_at", "ended_by", "end_reason", "updated_at"]
        )
        _log_after_commit(
            event="ended",
            relationship_id=rel.pk,
            actor_id=actor_id,
            actor_role=ended_by,
            reason=reason,
        )
    return rel


def patient_end_relationship(*, patient_user, confirm):
    if confirm is not True:
        raise DomainValidationError({"confirm": [CONFIRM_REQUIRED]})
    rel = CareRelationship.objects.filter(
        patient__user=patient_user, status=RelationshipStatus.ACCEPTED
    ).first()
    if rel is None:
        raise DomainValidationError({"relationship": [NO_PSYCHOLOGIST]})
    try:
        return end_relationship(
            relationship=rel,
            ended_by=EndedBy.PATIENT,
            reason=EndReason.PATIENT_ENDED,
            actor_id=patient_user.pk,
        )
    except DomainValidationError as exc:
        if "relationship" in exc.errors:  # ended concurrently
            raise DomainValidationError({"relationship": [NO_PSYCHOLOGIST]}) from exc
        raise


def psychologist_end_relationship(*, psychologist_user, relationship_id, reason):
    _require_visible_psychologist_user(psychologist_user)
    if not reason:
        raise DomainValidationError({"reason": [REASON_REQUIRED]})
    if reason not in PSYCHOLOGIST_END_REASONS:
        raise DomainValidationError({"reason": [INVALID_REASON]})
    rel = CareRelationship.objects.filter(
        pk=relationship_id,
        psychologist__user=psychologist_user,
        status=RelationshipStatus.ACCEPTED,
    ).first()
    if rel is None:
        raise Http404
    try:
        return end_relationship(
            relationship=rel,
            ended_by=EndedBy.PSYCHOLOGIST,
            reason=reason,
            actor_id=psychologist_user.pk,
        )
    except DomainValidationError as exc:
        # Ended concurrently between the read above and the row lock: answer
        # the same 404 as when the read itself misses.
        if "relationship" in exc.errors:
            raise Http404 from exc
        raise


def end_for_unavailable_account(*, user):
    """Called when a user is DEACTIVATED or REJECTED (never when a psychologist
    becomes pending: that is a pause). Accepted rows end, pending rows expire."""
    with transaction.atomic():
        rows = list(
            CareRelationship.objects.select_for_update(of=("self",)).filter(
                Q(patient__user=user) | Q(psychologist__user=user),
                status__in=OPEN_STATUSES,
            )
        )
        for rel in rows:
            if rel.status == RelationshipStatus.ACCEPTED:
                end_relationship(
                    relationship=rel,
                    ended_by=EndedBy.SYSTEM,
                    reason=EndReason.ACCOUNT_UNAVAILABLE,
                )
            else:
                rel.status = RelationshipStatus.EXPIRED
                rel.save(update_fields=["status", "updated_at"])
                _log_after_commit(
                    event="expired",
                    relationship_id=rel.pk,
                    actor_id=None,
                    actor_role="system",
                )


def set_accepting_status(*, psychologist_user, accepting, reason=None):
    profile = PsychologistProfile.objects.get(user=psychologist_user)
    if accepting:
        profile.is_accepting_patients = True
        profile.not_accepting_reason = None
    else:
        if not reason:
            raise DomainValidationError({"reason": [ACCEPTING_REASON_REQUIRED]})
        if reason not in NotAcceptingReason.values:
            raise DomainValidationError({"reason": [INVALID_REASON]})
        profile.is_accepting_patients = False
        profile.not_accepting_reason = reason
    profile.save(
        update_fields=["is_accepting_patients", "not_accepting_reason", "updated_at"]
    )
    return profile


ACTIVITY_CACHE_SECONDS = 15 * 60


def record_activity(*, user):
    """Psychologists only. At most one write per 15 minutes; a cache outage skips
    the update and never breaks authentication."""
    if getattr(user, "role", None) != Role.PSYCHOLOGIST:
        return None
    key = f"last_active:{user.pk}"
    try:
        if cache.get(key):
            return None
        cache.set(key, 1, ACTIVITY_CACHE_SECONDS)
    except Exception:  # any cache failure must not affect authentication
        return None
    User.objects.filter(pk=user.pk).update(last_active_at=timezone.now())
    return None
