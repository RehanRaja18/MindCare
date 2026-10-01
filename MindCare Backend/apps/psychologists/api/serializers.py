"""DRF serializers for the psychologists API."""

from rest_framework import serializers

from apps.psychologists.models import PsychologistProfile
from apps.reference.api.serializers import (
    CitySerializer,
    CountrySerializer,
    LanguageSerializer,
    SpecializationSerializer,
)
from apps.reference.models import Country, Language, Specialization
from core.choices import Gender
from core.serializers import RejectUnknownFieldsMixin
from core.validators import validate_iana_timezone


class PsychologistRegistrationProfileSerializer(
    RejectUnknownFieldsMixin, serializers.Serializer
):
    """The `profile` object in a psychologist's register request. Reused with
    partial=True for PATCH /me/ (credential fields accepted, checked by the
    service's lock)."""

    license_number = serializers.CharField(max_length=64)
    license_issuing_country = serializers.SlugRelatedField(
        slug_field="code", queryset=Country.objects.all()
    )
    license_issuing_authority = serializers.CharField(max_length=200)
    qualifications = serializers.CharField(max_length=1000)
    specializations = serializers.SlugRelatedField(
        slug_field="slug",
        many=True,
        allow_empty=False,
        queryset=Specialization.objects.filter(is_active=True),
    )
    years_of_experience = serializers.IntegerField(min_value=0, max_value=70)
    languages = serializers.SlugRelatedField(
        slug_field="code",
        many=True,
        allow_empty=False,
        queryset=Language.objects.filter(is_active=True),
    )
    country = serializers.SlugRelatedField(
        slug_field="code", queryset=Country.objects.all()
    )
    city = serializers.CharField(max_length=120)
    timezone = serializers.CharField(max_length=64, validators=[validate_iana_timezone])
    gender = serializers.ChoiceField(
        choices=Gender.choices, required=False, allow_null=True
    )
    bio = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class PsychologistProfileOwnerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    license_issuing_country = CountrySerializer(read_only=True)
    specializations = SpecializationSerializer(many=True, read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)
    country = CountrySerializer(read_only=True)
    city = CitySerializer(read_only=True)

    class Meta:
        model = PsychologistProfile
        fields = [
            "full_name",
            "license_number",
            "license_issuing_country",
            "license_issuing_authority",
            "qualifications",
            "specializations",
            "years_of_experience",
            "languages",
            "country",
            "city",
            "timezone",
            "gender",
            "bio",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
