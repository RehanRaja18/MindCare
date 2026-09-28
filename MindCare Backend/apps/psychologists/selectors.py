"""Read-path query logic for psychologists.

Views call into these functions to fetch data. Object-level ownership
filtering (e.g. scoping a psychologist's queries to their own patients)
belongs here, not just in permission classes.
"""

from apps.psychologists.models import PsychologistProfile


def get_psychologist_profile_for_user(*, user):
    return (
        PsychologistProfile.objects.select_related(
            "user", "country", "city__country", "license_issuing_country"
        )
        .prefetch_related("specializations", "languages")
        .filter(user=user)
        .first()
    )
