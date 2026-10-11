"""DRF serializers for the ngo API."""

from rest_framework import serializers

from apps.ngo.models import NGOProfile, NGOServiceArea
from apps.reference.api.serializers import CitySerializer, CountrySerializer
from apps.reference.models import Country
from core.serializers import (
    RejectUnknownFieldsMixin,
    free_text_field,
    https_url_field,
    identifier_field,
    organisation_name_field,
    person_name_field,
    phone_field,
)
from core.validators import validate_iana_timezone


class ServiceAreaInputSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    country = serializers.SlugRelatedField(
        slug_field="code", queryset=Country.objects.all()
    )
    city = person_name_field("City", required=False, allow_blank=True, allow_null=True)

    def run_validation(self, data=serializers.empty):
        # Nested serializers inherit the root's partial flag, which would make
        # `country` optional on PATCH; a service area always needs one.
        if isinstance(data, dict) and "country" not in data:
            raise serializers.ValidationError({"country": ["This field is required."]})
        return super().run_validation(data)


class NGORegistrationProfileSerializer(
    RejectUnknownFieldsMixin, serializers.Serializer
):
    """The `profile` object in an NGO's register request; reused with
    partial=True for PATCH /me/."""

    organization_name = organisation_name_field("Organisation name")
    registration_number = identifier_field("Registration number")
    registration_country = serializers.SlugRelatedField(
        slug_field="code", queryset=Country.objects.all()
    )
    registering_authority = organisation_name_field("Registering authority")
    country = serializers.SlugRelatedField(
        slug_field="code", queryset=Country.objects.all()
    )
    city = person_name_field("City")
    timezone = serializers.CharField(max_length=64, validators=[validate_iana_timezone])
    official_phone = phone_field()
    official_email = serializers.EmailField()
    website = https_url_field("Website", required=False, allow_blank=True)
    description = free_text_field(
        "Description", 30, 2000, required=False, allow_blank=True
    )
    service_areas = ServiceAreaInputSerializer(many=True, allow_empty=False)


class ServiceAreaOutputSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)
    city = CitySerializer(read_only=True)

    class Meta:
        model = NGOServiceArea
        fields = ["country", "city"]


class NGOProfileOwnerSerializer(serializers.ModelSerializer):
    representative_name = serializers.CharField(source="user.full_name", read_only=True)
    registration_country = CountrySerializer(read_only=True)
    country = CountrySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    service_areas = ServiceAreaOutputSerializer(many=True, read_only=True)

    class Meta:
        model = NGOProfile
        fields = [
            "representative_name",
            "organization_name",
            "registration_number",
            "registration_country",
            "registering_authority",
            "country",
            "city",
            "timezone",
            "official_phone",
            "official_email",
            "website",
            "description",
            "service_areas",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
