"""DRF serializers for the psychologists API."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.psychologists.models import NotAcceptingReason, PsychologistProfile
from apps.reference.api.serializers import (
    CitySerializer,
    CountrySerializer,
    LanguageSerializer,
    SpecializationSerializer,
)
from apps.reference.models import Country, Language, Specialization
from apps.relationships.selectors import last_active_band
from core.choices import Gender
from apps.psychologists.models import MAX_YEARS_OF_EXPERIENCE, MIN_YEARS_OF_EXPERIENCE
from core.serializers import (
    RejectUnknownFieldsMixin,
    free_text_field,
    identifier_field,
    organisation_name_field,
    person_name_field,
    search_field,
    whole_number_field,
)
from core.validators import validate_iana_timezone


class PsychologistRegistrationProfileSerializer(
    RejectUnknownFieldsMixin, serializers.Serializer
):
    """The `profile` object in a psychologist's register request. Reused with
    partial=True for PATCH /me/ (credential fields accepted, checked by the
    service's lock)."""

    license_number = identifier_field("License number")
    license_issuing_country = serializers.SlugRelatedField(
        slug_field="code", queryset=Country.objects.all()
    )
    license_issuing_authority = organisation_name_field("Issuing authority")
    qualifications = free_text_field("Qualifications", 10, 1000)
    specializations = serializers.SlugRelatedField(
        slug_field="slug",
        many=True,
        allow_empty=False,
        queryset=Specialization.objects.filter(is_active=True),
    )
    years_of_experience = whole_number_field(
        "Years of experience", MIN_YEARS_OF_EXPERIENCE, MAX_YEARS_OF_EXPERIENCE
    )
    languages = serializers.SlugRelatedField(
        slug_field="code",
        many=True,
        allow_empty=False,
        queryset=Language.objects.filter(is_active=True),
    )
    country = serializers.SlugRelatedField(
        slug_field="code", queryset=Country.objects.all()
    )
    city = person_name_field("City")
    timezone = serializers.CharField(max_length=64, validators=[validate_iana_timezone])
    gender = serializers.ChoiceField(
        choices=Gender.choices, required=False, allow_null=True
    )
    bio = free_text_field("Bio", 30, 2000, required=False, allow_blank=True)


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


DIRECTORY_CARD_FIELDS = [
    "id",
    "full_name",
    "gender",
    "bio",
    "qualifications",
    "license_issuing_country",
    "license_issuing_authority",
    "specializations",
    "languages",
    "years_of_experience",
    "country",
    "city",
    "timezone",
    "is_accepting_patients",
    "last_active",
]


class DirectoryCardSerializer(serializers.ModelSerializer):
    """What patients see. Never license_number, last_active_at,
    not_accepting_reason or other admin-only fields."""

    full_name = serializers.CharField(source="user.full_name", read_only=True)
    license_issuing_country = CountrySerializer(read_only=True)
    specializations = SpecializationSerializer(many=True, read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)
    country = CountrySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    last_active = serializers.SerializerMethodField()

    class Meta:
        model = PsychologistProfile
        fields = DIRECTORY_CARD_FIELDS
        read_only_fields = DIRECTORY_CARD_FIELDS

    @extend_schema_field(OpenApiTypes.STR)
    def get_last_active(self, obj):
        return last_active_band(obj.user.last_active_at)


class MinimalCardSerializer(serializers.ModelSerializer):
    """Shown when a psychologist is no longer approved and active."""

    full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = PsychologistProfile
        fields = ["id", "full_name"]
        read_only_fields = fields


class DirectoryQuerySerializer(serializers.Serializer):
    """Query parameters of GET /psychologists/directory/. CharFields coerce to
    str, `city` to int; malformed values are a 400. A whitespace-only `search`
    is trimmed to "" and means no filter."""

    specialization = serializers.CharField(required=False, max_length=50)
    language = serializers.CharField(required=False, max_length=2)
    gender = serializers.ChoiceField(choices=Gender.choices, required=False)
    country = serializers.CharField(required=False, max_length=2)
    city = serializers.IntegerField(required=False, min_value=1)
    accepting = serializers.BooleanField(required=False, allow_null=True, default=None)
    search = search_field(required=False, allow_blank=True)


class BlankAsNoneChoiceField(serializers.ChoiceField):
    """A ChoiceField where "", "   " and null all mean "no reason given" (None),
    so the service answers its single "choose a reason" message instead of DRF's
    "not a valid choice". DRF doesn't trim whitespace on ChoiceField itself."""

    def __init__(self, **kwargs):
        kwargs.setdefault("allow_null", True)
        kwargs.setdefault("allow_blank", True)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if isinstance(data, str) and not data.strip():
            return None
        return super().to_internal_value(data)


class AvailabilitySerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    """GET/PUT /psychologists/me/availability/. A reason is required (by the
    service) when accepting is false, and cleared when it is true."""

    accepting = serializers.BooleanField()
    reason = BlankAsNoneChoiceField(choices=NotAcceptingReason.choices, required=False)
