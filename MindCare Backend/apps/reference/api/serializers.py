"""DRF serializers for reference data."""

from rest_framework import serializers

from apps.reference.models import City, Country, Language, Specialization


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["code", "name"]


class CitySerializer(serializers.ModelSerializer):
    country = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = City
        fields = ["id", "name", "country"]


class CityQuerySerializer(serializers.Serializer):
    """Query parameters of GET /reference/cities/."""

    country = serializers.CharField(min_length=2, max_length=2)
    search = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def _reject_null_byte(self, value):
        if chr(0) in value:
            raise serializers.ValidationError("Null characters are not allowed.")
        return value

    def validate_country(self, value):
        return self._reject_null_byte(value)

    def validate_search(self, value):
        return self._reject_null_byte(value)


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ["code", "name"]


class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = ["slug", "name"]
