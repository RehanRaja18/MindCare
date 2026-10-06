"""DRF serializers for the relationships API."""

from django.utils import timezone as dj_timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.psychologists.api.serializers import (
    DirectoryCardSerializer,
    MinimalCardSerializer,
)
from apps.reference.api.serializers import (
    CitySerializer,
    CountrySerializer,
    LanguageSerializer,
)
from apps.relationships.models import (
    PSYCHOLOGIST_END_REASONS,
    CareRelationship,
    DeclineReason,
    RelationshipStatus,
)
from apps.relationships.selectors import psychologist_is_visible, requester_summary
from core.serializers import RejectUnknownFieldsMixin, StrictTrueField
from core.validators import age_on

CONFIRM_MESSAGE = "Confirm that you want to end this relationship."


class RequestCreateSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    psychologist = serializers.IntegerField(min_value=1)


class PatientEndSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    confirm = StrictTrueField(
        error_messages={
            "invalid": CONFIRM_MESSAGE,
            "required": CONFIRM_MESSAGE,
            "null": CONFIRM_MESSAGE,
        }
    )


class RelationshipPatientViewSerializer(serializers.ModelSerializer):
    # Expiry evaluated on read (no write on GET): a stale pending row reads "expired".
    status = serializers.ChoiceField(
        source="effective_status", choices=RelationshipStatus.choices, read_only=True
    )
    psychologist = serializers.SerializerMethodField()

    class Meta:
        model = CareRelationship
        fields = [
            "id",
            "status",
            "psychologist",
            "requested_at",
            "expires_at",
            "responded_at",
            "decline_reason",
            "cooldown_until",
            "ended_at",
            "ended_by",
            "end_reason",
        ]
        read_only_fields = fields

    @extend_schema_field(DirectoryCardSerializer)
    def get_psychologist(self, obj):
        if psychologist_is_visible(obj.psychologist):
            return DirectoryCardSerializer(obj.psychologist).data
        return MinimalCardSerializer(obj.psychologist).data


# --- Psychologist-facing ---------------------------------------------------
# None of these ever expose date_of_birth: age only (docs/decisions.md, 2026-10-06).

ASSIGNED_PATIENT_FIELDS = [
    "relationship_id",
    "accepted_at",
    "full_name",
    "pseudonym",
    "age",
    "gender",
    "phone_number",
    "country",
    "city",
    "preferred_language",
    "timezone",
]


class _RequesterSummarySerializer(serializers.Serializer):
    """Schema-only description of requester_summary()'s output."""

    pseudonym = serializers.CharField()
    preferred_language = LanguageSerializer(allow_null=True)
    timezone = serializers.CharField()
    country = CountrySerializer(allow_null=True)
    gender = serializers.CharField(allow_null=True)
    age = serializers.IntegerField(allow_null=True)


class InboxItemSerializer(serializers.ModelSerializer):
    """A pending request as the psychologist sees it before answering: no name."""

    requester = serializers.SerializerMethodField()

    class Meta:
        model = CareRelationship
        fields = ["id", "requested_at", "expires_at", "requester"]
        read_only_fields = fields

    @extend_schema_field(_RequesterSummarySerializer)
    def get_requester(self, obj):
        return requester_summary(relationship=obj)


class AssignedPatientSerializer(serializers.Serializer):
    """The assigned psychologist's view of a patient: real identity, age only,
    NEVER date_of_birth."""

    relationship_id = serializers.IntegerField(source="id", read_only=True)
    accepted_at = serializers.DateTimeField(source="responded_at", read_only=True)
    full_name = serializers.CharField(source="patient.user.full_name", read_only=True)
    pseudonym = serializers.CharField(source="patient.pseudonym", read_only=True)
    age = serializers.SerializerMethodField()
    gender = serializers.CharField(
        source="patient.gender", read_only=True, allow_null=True
    )
    phone_number = serializers.CharField(
        source="patient.phone_number", read_only=True, allow_null=True
    )
    country = CountrySerializer(
        source="patient.country", read_only=True, allow_null=True
    )
    city = CitySerializer(source="patient.city", read_only=True, allow_null=True)
    preferred_language = LanguageSerializer(
        source="patient.preferred_language", read_only=True, allow_null=True
    )
    timezone = serializers.CharField(source="patient.timezone", read_only=True)

    @extend_schema_field(OpenApiTypes.INT)
    def get_age(self, obj):
        dob = obj.patient.date_of_birth
        return age_on(dob, dj_timezone.localdate()) if dob else None


class HistoryItemSerializer(serializers.Serializer):
    """An ended relationship in the psychologist's history: pseudonym only."""

    relationship_id = serializers.IntegerField(source="id", read_only=True)
    pseudonym = serializers.CharField(source="patient.pseudonym", read_only=True)
    accepted_at = serializers.DateTimeField(source="responded_at", read_only=True)
    ended_at = serializers.DateTimeField(read_only=True)
    ended_by = serializers.CharField(read_only=True)
    end_reason = serializers.CharField(read_only=True)


class DeclineSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    reason = serializers.ChoiceField(
        choices=DeclineReason.choices, required=False, allow_null=True
    )


class PsychologistEndSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    # Optional here so a missing reason reaches the service, which answers
    # {"reason": ["Choose a reason."]}.
    reason = serializers.ChoiceField(
        choices=sorted(r.value for r in PSYCHOLOGIST_END_REASONS),
        required=False,
        allow_null=True,
    )
