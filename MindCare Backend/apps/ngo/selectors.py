"""Read-path query logic for ngo.

Views call into these functions to fetch data. Object-level ownership
filtering (e.g. scoping a psychologist's queries to their own patients)
belongs here, not just in permission classes.
"""

from apps.ngo.models import NGOProfile


def get_ngo_profile_for_user(*, user):
    return (
        NGOProfile.objects.select_related(
            "user", "country", "city__country", "registration_country"
        )
        .prefetch_related("service_areas__country", "service_areas__city")
        .filter(user=user)
        .first()
    )
