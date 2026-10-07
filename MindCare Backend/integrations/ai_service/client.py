"""
Client for the separate AI inference service (MindCare AI, FastAPI on Render).

Thin HTTP wrapper around the service's `POST /predict`, using only the standard
library (no HTTP package in requirements/base.txt). It knows nothing about
users or permissions; apps/ai/services.py decides who may call it. Per the
project's hard rule, model output must never reach a patient without
psychologist review.

The request body is patient health data: it is sent, never stored or logged.
Failures are logged with the exception type and HTTP status only.
"""

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("mindcare.integrations.ai_service")

PREDICT_PATH = "/predict"
# Statuses that mean "this input was refused". Any other 4xx (404 from a wrong
# URL or a missing Render service, 429, ...) is a service problem, not the input's.
REJECTION_STATUSES = {400, 422}


class AIServiceUnavailable(Exception):
    """Timed out, unreachable, a 5xx or other non-input 4xx, a non-JSON answer, or
    no URL configured."""


class AIServiceRejected(Exception):
    """The AI service refused the input (400/422). `message` is its explanation."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _detail_message(body):
    """The AI's `detail`: a string (plausibility/age rules) or FastAPI's list of
    {loc, msg} items (schema errors), flattened to one readable string."""
    try:
        detail = json.loads(body).get("detail")
    except (ValueError, AttributeError):
        detail = None
    if isinstance(detail, str) and detail:
        return detail
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                loc = item.get("loc") or []
                field = loc[-1] if loc else "input"
                parts.append(f"{field}: {item.get('msg', 'invalid')}")
        if parts:
            return "; ".join(parts)
    return "The AI service rejected this input."


def predict(*, base_url, features, timeout):
    if not base_url:
        logger.warning("AI_SERVICE_URL is not set")
        raise AIServiceUnavailable("AI_SERVICE_URL is not set")

    request = Request(
        base_url.rstrip("/") + PREDICT_PATH,
        data=json.dumps(features).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
    except HTTPError as exc:
        with exc:  # closes the error's response body
            if exc.code in REJECTION_STATUSES:
                logger.info("AI service rejected input: HTTP %s", exc.code)
                raise AIServiceRejected(_detail_message(exc.read())) from None
            logger.warning("AI service error: HTTP %s", exc.code)
            raise AIServiceUnavailable(f"HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError) as exc:
        logger.warning("AI service unreachable: %s", type(exc).__name__)
        raise AIServiceUnavailable(type(exc).__name__) from None

    try:
        return json.loads(body)
    except ValueError:
        logger.warning("AI service returned a non-JSON answer")
        raise AIServiceUnavailable("non-JSON answer") from None
