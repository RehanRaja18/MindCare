"""DRF serializers for the stats API."""

from rest_framework import serializers


class PublicStatsSerializer(serializers.Serializer):
    people_in_care = serializers.IntegerField()
    verified_therapists = serializers.IntegerField()
    cities = serializers.IntegerField()
