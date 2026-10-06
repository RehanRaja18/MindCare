"""Care relationships between a patient and a psychologist (Phase 3).

One row per request; the row becomes the relationship once accepted. A patient
has at most one open row (pending or accepted). Every ending goes through
services.end_relationship(). Phase 9 adds Subscription -> CareRelationship.
"""

from datetime import timedelta

from django.db import models
from django.db.models import Q
from django.utils import timezone

REQUEST_EXPIRY = timedelta(days=3)
DECLINE_COOLDOWN = timedelta(days=30)


class RelationshipStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"
    ENDED = "ended", "Ended"


OPEN_STATUSES = (RelationshipStatus.PENDING, RelationshipStatus.ACCEPTED)


class DeclineReason(models.TextChoices):
    OUTSIDE_SPECIALIZATIONS = "outside_specializations", "Outside my specializations"
    LANGUAGE_OR_TIMEZONE_MISMATCH = (
        "language_or_timezone_mismatch",
        "Language or time-zone mismatch",
    )
    CASE_TYPE_NOT_TAKEN = "case_type_not_taken", "Not taking this type of case"
    OTHER = "other", "Other"


class EndReason(models.TextChoices):
    TREATMENT_COMPLETED = "treatment_completed", "Treatment completed"
    REFERRED_ELSEWHERE = "referred_elsewhere", "Referred to another professional"
    OTHER = "other", "Other"
    PATIENT_ENDED = "patient_ended", "Ended by the patient"
    ACCOUNT_UNAVAILABLE = "account_unavailable", "Account unavailable"
    # Reserved for Phase 9 (subscription lapse); unused in Phase 3.
    SUBSCRIPTION_LAPSED = "subscription_lapsed", "Subscription lapsed"


PSYCHOLOGIST_END_REASONS = frozenset(
    {EndReason.TREATMENT_COMPLETED, EndReason.REFERRED_ELSEWHERE, EndReason.OTHER}
)
PATIENT_END_REASONS = frozenset({EndReason.PATIENT_ENDED})
SYSTEM_END_REASONS = frozenset(
    {EndReason.ACCOUNT_UNAVAILABLE, EndReason.SUBSCRIPTION_LAPSED}
)


class EndedBy(models.TextChoices):
    PATIENT = "patient", "Patient"
    PSYCHOLOGIST = "psychologist", "Psychologist"
    SYSTEM = "system", "System"


class CareRelationship(models.Model):
    # PROTECT: care history can't disappear by accident. Consequence: a user with
    # relationship rows can't be deleted in Django admin; delete the rows first
    # (SQL in docs/deployment.md).
    patient = models.ForeignKey(
        "patients.PatientProfile",
        on_delete=models.PROTECT,
        related_name="care_relationships",
    )
    psychologist = models.ForeignKey(
        "psychologists.PsychologistProfile",
        on_delete=models.PROTECT,
        related_name="care_relationships",
    )
    status = models.CharField(
        max_length=20,
        choices=RelationshipStatus.choices,
        default=RelationshipStatus.PENDING,
    )
    requested_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.CharField(
        max_length=40, choices=DeclineReason.choices, null=True, blank=True
    )
    cooldown_until = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    ended_by = models.CharField(
        max_length=20, choices=EndedBy.choices, null=True, blank=True
    )
    end_reason = models.CharField(
        max_length=40, choices=EndReason.choices, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient"],
                condition=Q(status__in=["pending", "accepted"]),
                name="relationships_one_open_per_patient",
            )
        ]
        indexes = [
            models.Index(
                fields=["psychologist", "status"],
                name="relationships_psych_status_idx",
            )
        ]

    def __str__(self):
        return f"Care relationship #{self.pk} ({self.status})"
