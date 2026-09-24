"""Smoke tests for the FastAPI service (src/api/main.py), using FastAPI's
TestClient.

The API's request shape (serving counts for caffeine, 12 features - the
11-feature reduced set plus Age, re-added 2026-09-22,
reports/feature_addition_age_3class.md) differs from
src/inference/predict_single.py's EXAMPLE_PATIENTS (which speaks raw
"Caffeine Intake (mg/day)" directly, since it's an internal debug script,
not the API's patient-facing form) - so patients here are built by taking
EXAMPLE_PATIENTS' non-caffeine fields and substituting serving counts for
caffeine, keeping the same low/high/ambiguous intent. Stress needs no such
substitution: EXAMPLE_PATIENTS already carries the same 4 PSS-4 answer fields
the API accepts (src/inference/stress_scale.py).

Run with: pytest tests/test_api.py -s -v
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, estimate_caffeine_mg
from src.inference.input_validation import InputValidationError
from src.inference.predict_single import EXAMPLE_PATIENTS
from src.inference.stress_scale import PSS_FIELDS, estimate_stress_level


@pytest.fixture(scope="module")
def client():
    # TestClient must be used as a context manager to trigger the app's
    # lifespan (startup/shutdown) events - otherwise ml_artifacts stays empty.
    with TestClient(app) as test_client:
        yield test_client


def _api_payload(example_name: str, **caffeine_servings: int) -> dict:
    """Take an EXAMPLE_PATIENTS entry, drop its raw mg caffeine field, and
    add serving counts instead (defaulting unset servings to 0)."""
    base = {k: v for k, v in EXAMPLE_PATIENTS[example_name].items() if k != "Caffeine Intake (mg/day)"}
    for field in ("cups_of_coffee", "cups_of_tea", "energy_drinks", "cans_of_soda"):
        base[field] = caffeine_servings.get(field, 0)
    return base


API_PATIENTS = {
    # original mg=80 (low) -> 1 cup coffee = 95mg, still clearly low
    "clearly_low_risk": _api_payload("clearly_low_risk", cups_of_coffee=1),
    # original mg=520 (high) -> 5 cups coffee + 1 energy drink = 475+80 = 555mg, comparably high
    "clearly_high_risk": _api_payload("clearly_high_risk", cups_of_coffee=5, energy_drinks=1),
    # original mg=280 (moderate) -> 2 cups coffee + 2 cups tea = 190+94 = 284mg, comparably moderate
    "ambiguous_moderate": _api_payload("ambiguous_moderate", cups_of_coffee=2, cups_of_tea=2),
}


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


def test_estimate_caffeine_mg_arithmetic() -> None:
    # 2 cups coffee + 1 cup tea = 2*95 + 47 = 237mg
    assert estimate_caffeine_mg(cups_of_coffee=2, cups_of_tea=1, energy_drinks=0, cans_of_soda=0) == 237


def test_predict_example_patients(client: TestClient) -> None:
    for name, patient in API_PATIENTS.items():
        response = client.post("/predict", json=patient)
        print(f"\n=== POST /predict — {name} ===")
        print(f"request: {json.dumps(patient, indent=2)}")
        print(f"status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        assert response.status_code == 200

    low_risk = client.post("/predict", json=API_PATIENTS["clearly_low_risk"]).json()
    high_risk = client.post("/predict", json=API_PATIENTS["clearly_high_risk"]).json()
    ambiguous = client.post("/predict", json=API_PATIENTS["ambiguous_moderate"]).json()

    assert low_risk["predicted_class"] == "Low"
    assert low_risk["uncertainty_flag"] is False
    assert low_risk["estimated_caffeine_mg"] == 95
    assert low_risk["estimated_stress_level"] == 2
    assert high_risk["predicted_class"] == "High"
    assert high_risk["uncertainty_flag"] is True
    assert high_risk["estimated_caffeine_mg"] == 555
    assert high_risk["estimated_stress_level"] == 10
    assert ambiguous["predicted_class"] == "Medium"
    assert ambiguous["estimated_caffeine_mg"] == 284
    assert ambiguous["estimated_stress_level"] == 6


def test_caffeine_conversion_in_response(client: TestClient) -> None:
    """2 cups coffee + 1 tea = 2*95 + 47 = 237mg - verify this exact number
    appears in the API response's estimated_caffeine_mg field."""
    patient = _api_payload("ambiguous_moderate", cups_of_coffee=2, cups_of_tea=1)
    response = client.post("/predict", json=patient)
    print("\n=== POST /predict — caffeine conversion check (2 coffee + 1 tea) ===")
    print(f"request: {json.dumps(patient, indent=2)}")
    print(f"status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200
    body = response.json()
    assert body["estimated_caffeine_mg"] == 237
    assert body["warnings"] == []  # 237mg is well within the observed [0, 599] range - no warning expected


def test_caffeine_warn_tier(client: TestClient) -> None:
    """8 cups of coffee = 760mg - inside the hard bound [0, 1200] but outside
    the observed training range [0, 599] - should WARN, not reject."""
    patient = _api_payload("ambiguous_moderate", cups_of_coffee=8)
    response = client.post("/predict", json=patient)
    print("\n=== POST /predict — caffeine warn-tier (8 cups coffee = 760mg) ===")
    print(f"request: {json.dumps(patient, indent=2)}")
    print(f"status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200
    body = response.json()
    assert body["estimated_caffeine_mg"] == 760
    assert len(body["warnings"]) >= 1
    assert "Caffeine Intake" in body["warnings"][0]


def test_caffeine_15_cups_actually_rejects(client: TestClient) -> None:
    """The task's own suggested warn-tier example (15 cups of coffee) is
    checked honestly: 15*95 = 1425mg, which exceeds the hard_max of 1200
    defined in input_validation.py (commonly-cited acute-toxicity threshold)
    - so this actually REJECTS (422), not warns. Documenting this as a real
    finding rather than silently picking a different example."""
    patient = _api_payload("ambiguous_moderate", cups_of_coffee=15)
    response = client.post("/predict", json=patient)
    print("\n=== POST /predict — 15 cups of coffee (1425mg > hard_max 1200) ===")
    print(f"request: {json.dumps(patient, indent=2)}")
    print(f"status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 422
    assert "1425" in response.json()["detail"]


def _pss(uncontrollable: int, confident: int, going_your_way: int, piling_up: int) -> dict:
    return dict(zip(PSS_FIELDS, (uncontrollable, confident, going_your_way, piling_up)))


@pytest.mark.parametrize(
    "answers, expected",
    [
        # Least stressed possible: 0 + (4-4) + (4-4) + 0 = 0 -> 1 + 0 = 1
        ((0, 4, 4, 0), 1),
        # Most stressed possible: 4 + (4-0) + (4-0) + 4 = 16 -> 1 + 9 = 10
        ((4, 0, 0, 4), 10),
        # Literal all-0 is NOT the minimum: the 2 reversed items each score 4 -> total 8 ->
        # 1 + 8*9/16 = 5.5 -> half-up -> 6
        ((0, 0, 0, 0), 6),
        # Literal all-4 is NOT the maximum either: 4 + 0 + 0 + 4 = 8 -> 6
        ((4, 4, 4, 4), 6),
        # total 1 -> 1.5625 -> 2 (clearly_low_risk's answers)
        ((0, 3, 4, 0), 2),
        # total 9 -> 6.0625 -> 6 (ambiguous_moderate's answers)
        ((2, 1, 2, 2), 6),
        # total 12 -> 1 + 6.75 = 7.75 -> 8
        ((3, 1, 1, 3), 8),
    ],
)
def test_estimate_stress_level_arithmetic(answers: tuple[int, int, int, int], expected: int) -> None:
    assert estimate_stress_level(*answers) == expected


def test_estimate_stress_level_rejects_out_of_range_answer() -> None:
    """Direct callers (e.g. predict_single.py) have no Pydantic layer - the
    function itself must refuse an answer outside 0-4."""
    with pytest.raises(InputValidationError, match="pss_confident=5"):
        estimate_stress_level(2, 5, 2, 2)


def test_stress_conversion_in_response(client: TestClient) -> None:
    """PSS answers (3, 1, 1, 3) -> total 12 -> Stress Level 8 - verify this
    exact number appears in the API response's estimated_stress_level field."""
    patient = {**API_PATIENTS["ambiguous_moderate"], **_pss(3, 1, 1, 3)}
    response = client.post("/predict", json=patient)
    print("\n=== POST /predict — stress conversion check (PSS 3,1,1,3) ===")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200
    assert response.json()["estimated_stress_level"] == 8


def test_raw_stress_level_is_ignored(client: TestClient) -> None:
    """A caller still sending the old raw field cannot override the PSS-derived
    value: "Stress Level (1-10)" is no longer in the schema, so Pydantic drops
    it and the computed value (here 1) is what the model receives."""
    patient = {**API_PATIENTS["ambiguous_moderate"], **_pss(0, 4, 4, 0), "Stress Level (1-10)": 10}
    response = client.post("/predict", json=patient)
    print("\n=== POST /predict — raw Stress Level=10 sent alongside min-stress PSS answers ===")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200
    assert response.json()["estimated_stress_level"] == 1


@pytest.mark.parametrize("field", PSS_FIELDS)
@pytest.mark.parametrize("bad_value", [-1, 5])
def test_pss_out_of_range_is_rejected_by_pydantic(client: TestClient, field: str, bad_value: int) -> None:
    """PSS answers outside 0-4 are rejected by the schema's ge/le constraints
    (FastAPI's 422 with a structured error list) before estimate_stress_level()
    or input_validation.py ever run."""
    patient = {**API_PATIENTS["ambiguous_moderate"], field: bad_value}
    response = client.post("/predict", json=patient)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert isinstance(errors, list)  # Pydantic's structured errors, not validate_patient()'s string
    assert errors[0]["loc"] == ["body", field]
    assert errors[0]["type"] == ("greater_than_equal" if bad_value < 0 else "less_than_equal")


def test_pss_field_is_required(client: TestClient) -> None:
    patient = {k: v for k, v in API_PATIENTS["ambiguous_moderate"].items() if k != "pss_confident"}
    response = client.post("/predict", json=patient)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "pss_confident"]


def test_higher_pss_stress_raises_p_high(client: TestClient) -> None:
    """Holding every other field fixed, moving PSS answers from least to most
    stressed should push P(High) up - the same direction raising the raw
    Stress Level used to."""
    low = client.post("/predict", json={**API_PATIENTS["ambiguous_moderate"], **_pss(0, 4, 4, 0)}).json()
    high = client.post("/predict", json={**API_PATIENTS["ambiguous_moderate"], **_pss(4, 0, 0, 4)}).json()
    print(f"\nP(High): stress 1 -> {low['probabilities']['High']:.4f}, stress 10 -> {high['probabilities']['High']:.4f}")
    assert low["estimated_stress_level"] == 1
    assert high["estimated_stress_level"] == 10
    assert high["probabilities"]["High"] > low["probabilities"]["High"]


def test_dropped_fields_still_ignored_by_schema(client: TestClient) -> None:
    """The 5 features still dropped (Alcohol Consumption, Dizziness, Smoking,
    Recent Major Life Event, Medication) are not part of the schema at all -
    sending one should not fail the request. Age is NOT in this list any
    more (re-added 2026-09-22, reports/feature_addition_age_3class.md) - see
    test_age_is_required and test_age_out_of_range_is_rejected below for its
    coverage now that it's a real, required field."""
    patient_with_removed_field = {**API_PATIENTS["ambiguous_moderate"], "Medication": "Yes"}
    response = client.post("/predict", json=patient_with_removed_field)
    print("\n=== POST /predict — dropped field still sent (Medication) ===")
    print(f"status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    # Pydantic's default config ignores unknown extra fields rather than rejecting them,
    # so this should still succeed (200) with Medication silently ignored - verifying that
    # explicitly rather than assuming either behavior.
    assert response.status_code == 200


def test_age_is_required(client: TestClient) -> None:
    """Age is a required field again (re-added 2026-09-22) - omitting it
    should fail Pydantic validation (422), not silently default or 200."""
    patient_without_age = {k: v for k, v in API_PATIENTS["ambiguous_moderate"].items() if k != "Age"}
    response = client.post("/predict", json=patient_without_age)
    print("\n=== POST /predict — missing required field (Age) ===")
    print(f"status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 422


def test_age_out_of_range_is_rejected(client: TestClient) -> None:
    """Age=-5 is physically impossible (outside input_validation.py's
    [0, 120] hard range) - should reject with 422, the same gap Phase 19
    robustness testing originally found and src/inference/input_validation.py
    fixed, now re-verified with Age back as a model input."""
    invalid_patient = {**API_PATIENTS["ambiguous_moderate"], "Age": -5}
    response = client.post("/predict", json=invalid_patient)
    print("\n=== POST /predict — invalid (Age=-5) ===")
    print(f"status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 422
