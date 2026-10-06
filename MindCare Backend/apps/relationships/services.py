"""Write-path business logic for care relationships."""

from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.http import Http404
from django.utils import timezone

from apps.accounts.models import ApprovalStatus, Role
from apps.patients.models import PatientProfile
from apps.psychologists.models import PsychologistProfile
from apps.relationships.models import (
    DECLINE_COOLDOWN,
    OPEN_STATUSES,
    REQUEST_EXPIRY,
    CareRelationship,
    DeclineReason,
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
