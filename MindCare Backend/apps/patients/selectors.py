"""Read-path query logic for patients.

Views call into these functions to fetch data. Object-level ownership
filtering (e.g. scoping a psychologist's queries to their own patients)
belongs here, not just in permission classes.
"""

from apps.accounts.models import Role
from apps.patients.models import PatientProfile
from core.audit import log_identity_reveal


def get_patient_profile_for_user(*, user):
    return (
        PatientProfile.objects.select_related(
            "user", "country", "city__country", "preferred_language"
        )
        .filter(user=user)
        .first()
    )


def _is_assigned_psychologist(*, viewer, patient_profile):
    # Phase 3: accepted relationship to a currently approved, active psychologist.
    from apps.relationships.selectors import is_assigned_psychologist

    return is_assigned_psychologist(viewer=viewer, patient_profile=patient_profile)


def get_patient_display_identity(*, patient_profile, viewer):
    """The ONE place that decides whether a viewer sees a patient's real name or
    pseudonym. Phases 3 and 11 must call this, not reimplement it. Never add
    gender, age or city here: re-identification risk (docs/decisions.md)."""
    real = {"display_name": patient_profile.user.full_name, "is_real_name": True}
    pseudonymous = {"display_name": patient_profile.pseudonym, "is_real_name": False}

    authenticated = viewer is not None and viewer.is_authenticated
    if authenticated and viewer.pk == patient_profile.user_id:
        return real
    if patient_profile.is_profile_public:
        return real
    if not authenticated:
        return pseudonymous
    if viewer.role == Role.PSYCHOLOGIST and _is_assigned_psychologist(
        viewer=viewer, patient_profile=patient_profile
    ):
        return real
    if viewer.role == Role.ADMIN:
        log_identity_reveal(viewer_id=viewer.pk, patient_id=patient_profile.user_id)
        return real
    return pseudonymous
