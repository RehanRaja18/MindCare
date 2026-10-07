"""
PHI-safe access logging.

Provides log_auth_event() and log_identity_reveal(), which record auth events
(login, failed login, logout, token refresh, registration) and identity
revelations as structured JSON log lines, without ever writing PHI (patient
names, journal content, clinical notes, health data) into plaintext application
logs. All access to sensitive resources should go through here instead of
`logging` directly.
"""

import json
import logging

from django.utils import timezone

logger = logging.getLogger("mindcare.audit")

AUTH_EVENT_TYPES = {"register", "login", "login_failed", "logout", "token_refresh"}


def log_auth_event(
    event_type, *, user_id=None, email=None, role=None, ip=None, success=True
):
    if event_type not in AUTH_EVENT_TYPES:
        raise ValueError(f"Unknown auth event_type: {event_type!r}")
    payload = {
        "event_type": event_type,
        "timestamp": timezone.now().isoformat(),
        "user_id": user_id,
        "email": email,
        "role": role,
        "ip": ip,
        "success": success,
    }
    logger.info(json.dumps(payload))


def log_identity_reveal(*, viewer_id, patient_id):
    """An admin resolved a private patient's real identity (see
    apps/patients/selectors.get_patient_display_identity). IDs only — never
    names, emails or anything else."""
    payload = {
        "event_type": "identity_reveal",
        "timestamp": timezone.now().isoformat(),
        "viewer_id": viewer_id,
        "patient_id": patient_id,
    }
    logger.info(json.dumps(payload))


RELATIONSHIP_EVENTS = {
    "requested",
    "cancelled",
    "accepted",
    "declined",
    "expired",
    "ended",
}


def log_relationship_event(
    *, event, relationship_id, actor_id, actor_role, reason=None
):
    """A care-relationship state change. IDs and codes only: never names, never
    anything typed by a person, never patient_id and psychologist_id together."""
    if event not in RELATIONSHIP_EVENTS:
        raise ValueError(f"Unknown relationship event: {event!r}")
    payload = {
        "event_type": "relationship",
        "event": event,
        "relationship_id": relationship_id,
        "reason": reason,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "timestamp": timezone.now().isoformat(),
    }
    logger.info(json.dumps(payload))
