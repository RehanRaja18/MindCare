"""DRF serializers for the relationships API."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.psychologists.api.serializers import (
    DirectoryCardSerializer,
    MinimalCardSerializer,
)
from apps.relationships.models import CareRelationship, RelationshipStatus
from apps.relationships.selectors import psychologist_is_visible
from core.serializers import RejectUnknownFieldsMixin, StrictTrueField

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
