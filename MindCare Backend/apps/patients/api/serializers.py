"""DRF serializers for the patients API."""

from rest_framework import serializers

from apps.patients.models import PatientProfile
from apps.reference.api.serializers import (
    CitySerializer,
    CountrySerializer,
    LanguageSerializer,
)
from apps.reference.models import Country, Language
from core.choices import Gender
from core.serializers import RejectUnknownFieldsMixin, person_name_field, phone_field
from core.validators import validate_iana_timezone

PUBLIC_FLAG_HELP = (
    "If true, other users see your real name instead of your pseudonym. "
    "Going public is a permanent disclosure: people who see your real name while "
    "public may still recognise you later, even if you switch back to private."
)


class PatientRegistrationProfileSerializer(
    RejectUnknownFieldsMixin, serializers.Serializer
):
    """The `profile` object in a patient's register request. `timezone` is read
    from the device by MindCare App; the patient never types it."""

    timezone = serializers.CharField(max_length=64, validators=[validate_iana_timezone])


class PatientProfileUpdateSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    is_profile_public = serializers.BooleanField(
        required=False, help_text=PUBLIC_FLAG_HELP
    )
    country = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Country.objects.all(),
        required=False,
        allow_null=True,
    )
    city = person_name_field("City", required=False, allow_blank=True, allow_null=True)
    timezone = serializers.CharField(
        max_length=64, required=False, validators=[validate_iana_timezone]
    )
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=Gender.choices, required=False, allow_null=True
    )
    # Blank/None skip validators in DRF; the service turns "" into None.
    phone_number = phone_field(required=False, allow_blank=True, allow_null=True)
    preferred_language = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Language.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )


class PatientProfileOwnerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    country = CountrySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    preferred_language = LanguageSerializer(read_only=True)
    is_profile_public = serializers.BooleanField(
        read_only=True, help_text=PUBLIC_FLAG_HELP
    )

    class Meta:
        model = PatientProfile
        fields = [
            "pseudonym",
            "full_name",
            "is_profile_public",
            "country",
            "city",
            "timezone",
            "date_of_birth",
            "gender",
            "phone_number",
            "preferred_language",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
