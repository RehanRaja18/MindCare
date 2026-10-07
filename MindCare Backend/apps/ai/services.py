"""Write-path logic for the AI gateway.

Forwards a psychologist-entered set of features to the AI service and returns its
prediction. Nothing is stored and the features are never logged: they are health
data, and no health data is stored before the Phase 5 audit trail (see
docs/decisions.md, 2026-10-07). Who may call this is decided by the view's
permissions (approved, active psychologists only): the prediction is decision
support for a psychologist and never goes to a patient directly.
"""

from django.conf import settings

from integrations.ai_service import client

AI_TIMEOUT_SECONDS = 60  # Render free tier: cold starts take ~35-60 s


class AIServiceUnavailable(Exception):
    """The AI service couldn't answer (asleep, unreachable, 5xx, misconfigured)."""


class AIPredictionRejected(Exception):
    """The AI service refused the input, e.g. an age outside 18-49."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def predict_anxiety_risk(*, features):
    try:
        return client.predict(
            base_url=settings.AI_SERVICE_URL,
            features=features,
            timeout=AI_TIMEOUT_SECONDS,
        )
    except client.AIServiceRejected as exc:
        raise AIPredictionRejected(exc.message) from None
    except client.AIServiceUnavailable:
        raise AIServiceUnavailable() from None
