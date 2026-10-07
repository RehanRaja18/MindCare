"""Shared fixtures for the AI gateway tests. Every HTTP call is mocked: tests never
reach the network."""

import io
import json
from urllib.error import HTTPError

VALID_FEATURES = {
    "Age": 34,
    "Sleep Hours": 8.2,
    "Physical Activity (hrs/week)": 5.5,
    "cups_of_coffee": 1,
    "cups_of_tea": 0,
    "energy_drinks": 0,
    "cans_of_soda": 0,
    "pss_uncontrollable": 0,
    "pss_confident": 3,
    "pss_going_your_way": 4,
    "pss_difficulties_piling_up": 0,
    "Heart Rate (bpm)": 68,
    "Breathing Rate (breaths/min)": 14,
    "Therapy Sessions (per month)": 0,
    "Diet Quality (1-10)": 9,
    "Occupation": "Teacher",
    "Family History of Anxiety": "No",
}

AI_RESPONSE = {
    "predicted_class": "Low",
    "probabilities": {"Low": 0.966, "Medium": 0.0333, "High": 0.0007},
    "uncertainty_flag": False,
    "warnings": [],
    "estimated_caffeine_mg": 95.0,
    "estimated_stress_level": 2,
    "confidence": 0.966,
    "confidence_label": "confident",
    "borderline_reasons": [],
    "borderline_between": None,
}

URLOPEN = "integrations.ai_service.client.urlopen"


class FakeResponse:
    def __init__(self, payload, status=200):
        self._body = json.dumps(payload).encode()
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(status, payload):
    return HTTPError(
        "http://ai.invalid/predict",
        status,
        "error",
        {},
        io.BytesIO(json.dumps(payload).encode()),
    )
