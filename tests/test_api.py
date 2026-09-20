"""Smoke tests for the FastAPI service (src/api/main.py), using FastAPI's
TestClient. Reuses the exact example patients from
src/inference/predict_single.py so results are directly comparable to that
script's output.

Run with: pytest tests/test_api.py -s -v
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.inference.predict_single import EXAMPLE_PATIENTS


@pytest.fixture(scope="module")
def client():
    # TestClient must be used as a context manager to trigger the app's
    # lifespan (startup/shutdown) events - otherwise ml_artifacts stays empty.
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    print("\n=== GET /health ===")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["preprocessor_loaded"] is True
    assert body["label_encoder_loaded"] is True


def test_predict_example_patients(client: TestClient) -> None:
    for name, patient in EXAMPLE_PATIENTS.items():
        response = client.post("/predict", json=patient)
        print(f"\n=== POST /predict — {name} ===")
        print(f"status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        assert response.status_code == 200

    low_risk = client.post("/predict", json=EXAMPLE_PATIENTS["clearly_low_risk"]).json()
    high_risk = client.post("/predict", json=EXAMPLE_PATIENTS["clearly_high_risk"]).json()
    ambiguous = client.post("/predict", json=EXAMPLE_PATIENTS["ambiguous_moderate"]).json()

    assert low_risk["predicted_class"] == "Low"
    assert low_risk["uncertainty_flag"] is False
    assert high_risk["predicted_class"] == "High"
    assert high_risk["uncertainty_flag"] is True
    assert ambiguous["predicted_class"] == "Medium"


def test_predict_rejects_invalid_input(client: TestClient) -> None:
    invalid_patient = {**EXAMPLE_PATIENTS["ambiguous_moderate"], "Age": -5}
    response = client.post("/predict", json=invalid_patient)
    print("\n=== POST /predict — invalid (Age=-5) ===")
    print(f"status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 422
    assert "Age=-5" in response.json()["detail"]
    assert "physically plausible range" in response.json()["detail"]
