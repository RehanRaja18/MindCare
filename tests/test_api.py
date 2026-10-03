"""Smoke tests for the FastAPI service (src/api/main.py), using FastAPI's
TestClient.

The API's request shape (serving counts for caffeine, 11 features - the
"11-feature v2" set: Age re-added 2026-09-22,
reports/feature_addition_age_3class.md, and Sweating Level removed
2026-10-02, reports/feature_reduction_sweatlevel_3class.md) differs from
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


def test_serves_xgboost_with_its_review_threshold(client: TestClient) -> None:
    """XGBoost became the canonical model on 2026-09-28
    (reports/model_comparison_12feature.md), with the priority-review
    threshold lowered from 0.10 to 0.025 to match the Random Forest's
    validation coverage. Guards against the API silently loading the old
    Random Forest artifact or threshold."""
    from xgboost import XGBClassifier

    from src.api.main import HIGH_PROBA_THRESHOLD, MODEL_PATH, ml_artifacts

    assert MODEL_PATH.name == "mindcare_final_model_11feature_v2_xgb.pkl"  # Sweating Level removed 2026-10-02
    assert isinstance(ml_artifacts["model"], XGBClassifier)
    assert HIGH_PROBA_THRESHOLD == 0.025


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


def test_sweating_level_is_no_longer_an_input(client: TestClient) -> None:
    """Sweating Level (1-5) was removed on 2026-10-02
    (reports/feature_reduction_sweatlevel_3class.md). It is not required, and a caller that
    still sends it gets exactly the same prediction - the value is ignored, whatever it is."""
    from src.inference.input_validation import ALL_FEATURES

    assert "Sweating Level (1-5)" not in ALL_FEATURES and len(ALL_FEATURES) == 11
    patient = API_PATIENTS["ambiguous_moderate"]
    assert "Sweating Level (1-5)" not in patient
    without = client.post("/predict", json=patient)
    assert without.status_code == 200
    for value in (1, 5, 250):
        with_field = client.post("/predict", json={**patient, "Sweating Level (1-5)": value})
        assert with_field.status_code == 200
        assert with_field.json() == without.json()


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


@pytest.mark.parametrize("age", [0, 16, 17])
def test_under_18_is_rejected_as_not_eligible(client: TestClient, age: int) -> None:
    """Minors may not register for MindCare at all (decided 2026-09-28), so a
    minor reaching the model means the web app's registration check failed.
    422, "not eligible", and deliberately NO psychologist referral."""
    response = client.post("/predict", json={**API_PATIENTS["ambiguous_moderate"], "Age": age})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert f"Age={age} is under 18 - not eligible for MindCare" in detail
    assert "psychologist" not in detail


@pytest.mark.parametrize("age", [50, 55, 64, 120])
def test_over_49_is_rejected_with_psychologist_referral(client: TestClient, age: int) -> None:
    """Adults 50+ may use MindCare but get no AI pre-assessment (the training
    data has almost no High cases from 50 on) - 422 telling the caller to
    refer them directly to a psychologist. 50-64 were accepted before the
    2026-09-27 age rule (inside the observed range), so they are covered
    explicitly."""
    response = client.post("/predict", json={**API_PATIENTS["ambiguous_moderate"], "Age": age})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert f"Age={age} is outside the supported range for AI pre-assessment [18, 49]" in detail
    assert "refer this person directly to a psychologist" in detail


@pytest.mark.parametrize("age", [18, 49])
def test_age_supported_range_boundaries_are_accepted(client: TestClient, age: int) -> None:
    response = client.post("/predict", json={**API_PATIENTS["ambiguous_moderate"], "Age": age})
    assert response.status_code == 200
    assert response.json()["warnings"] == []  # 18-49 is inside the observed training range too


# --- POST /patient-summary: prediction + estimated Severity tier + recommendation bundle ------------

SUMMARY_WITH_EXTRAS = {**API_PATIENTS["ambiguous_moderate"], "Gender": "Male", "Alcohol Consumption (drinks/week)": 0}


def test_patient_summary_prediction_fields_match_predict(client: TestClient) -> None:
    """The summary adds fields but never changes the prediction: for identical input, every
    /predict field is identical in the summary (with or without the optional extras)."""
    for name, patient in API_PATIENTS.items():
        prediction = client.post("/predict", json=patient).json()
        for payload in (patient, {**patient, "Gender": "Female", "Alcohol Consumption (drinks/week)": 4}):
            summary = client.post("/patient-summary", json=payload)
            assert summary.status_code == 200, name
            body = summary.json()
            assert {k: body[k] for k in prediction} == prediction, name
            assert body["estimated_severity_tier"] != body["predicted_class"]  # distinct field, tier labels differ


def test_patient_summary_caveat_is_always_present_and_first(client: TestClient) -> None:
    from src.inference.template_advice import CAVEAT

    assert CAVEAT == (
        "Estimated severity and recommendation are a best-guess reconstruction (~88% accurate at best, "
        "lower given this model's own prediction error) from synthetic dataset templates. This is "
        "decision support for clinician review, not a recommendation to show a patient directly and "
        "not validated clinical advice."
    )
    for payload in (API_PATIENTS["ambiguous_moderate"], SUMMARY_WITH_EXTRAS, *API_PATIENTS.values()):
        body = client.post("/patient-summary", json=payload).json()
        assert body["caveat"] == CAVEAT
        assert list(body)[0] == "caveat"


def test_patient_summary_without_gender_or_alcohol_does_not_crash(client: TestClient) -> None:
    """Both extras omitted, or sent as null: 200, and exactly their slots say "not provided"."""
    for payload in (API_PATIENTS["ambiguous_moderate"],
                    {**API_PATIENTS["ambiguous_moderate"], "Gender": None, "Alcohol Consumption (drinks/week)": None}):
        response = client.post("/patient-summary", json=payload)
        assert response.status_code == 200
        nutrition = response.json()["recommendation_bundle"]["nutrition"]
        assert nutrition.startswith("Protein: not provided (needs Gender)")
        assert "Alcohol: not provided (needs Alcohol Consumption)" in nutrition
        assert "current: 284 mg" in nutrition  # caffeine slot still filled: 2 coffee + 2 tea = 284 mg > 200


def test_patient_summary_fills_slots_when_provided(client: TestClient) -> None:
    bundle = client.post("/patient-summary", json=SUMMARY_WITH_EXTRAS).json()["recommendation_bundle"]
    assert bundle["nutrition"].startswith("Protein: 58 g/day")  # Male -> 58
    assert bundle["nutrition"].endswith("No alcohol: good")  # 0 drinks
    assert "not provided" not in bundle["nutrition"]
    assert "Current: 6.5 hrs" in bundle["sleep_schedule"]


def test_patient_summary_rejects_what_predict_rejects(client: TestClient) -> None:
    """Same validation path: an out-of-range age gets the same 422 from both endpoints."""
    patient = {**API_PATIENTS["ambiguous_moderate"], "Age": 55}
    prediction = client.post("/predict", json=patient)
    summary = client.post("/patient-summary", json={**patient, "Gender": "Other"})
    assert prediction.status_code == summary.status_code == 422
    assert summary.json() == prediction.json()


def test_predict_returns_no_reconstruction(client: TestClient) -> None:
    body = client.post("/predict", json=SUMMARY_WITH_EXTRAS).json()
    assert not {"caveat", "estimated_severity_tier", "recommendation_bundle"} & set(body)


def test_severity_reconstruction_accuracy_matches_investigation() -> None:
    """The best-guess rule (3-class label + Stress Level -> most common Severity tier) is documented
    in reports/recommendation_mapping_investigation.md at 88.0% on the 9,350 train + validation rows,
    using the TRUE 3-class label. Check (a) the shipped lookup reproduces that exactly, and (b) the
    RULE holds up out of sample: rebuilt on 80% of train + validation rows, scored on the held-out
    20%. The test split is never loaded (the 12-feature splits file has no test keys)."""
    import numpy as np
    import pandas as pd
    from src.inference.template_advice import estimate_tier

    df = pd.read_csv("data/raw/mindcare_dataset_final.csv")
    splits = np.load("data/processed/mindcare_processed_splits_12feature.npz")
    assert "test_original_idx" not in splits.files
    rows = np.concatenate([splits["train_original_idx"], splits["val_original_idx"]])
    d = df.iloc[rows].reset_index(drop=True)
    d["label"] = pd.cut(d["Anxiety Level (1-10)"], [0, 3, 6, 10], labels=["Low", "Medium", "High"]).astype(str)
    stress = d["Stress Level (1-10)"]

    shipped = [estimate_tier(lbl, int(s))["tier"] for lbl, s in zip(d["label"], stress)]
    in_sample = float(np.mean(np.array(shipped) == d["Severity"].to_numpy()))
    assert round(in_sample, 3) == 0.880

    held_out = d.sample(frac=0.2, random_state=42)
    fit = d.drop(held_out.index)
    table = fit.groupby(["label", "Stress Level (1-10)"])["Severity"].agg(lambda x: x.value_counts().index[0])
    guesses = [table.get((lbl, s)) for lbl, s in zip(held_out["label"], held_out["Stress Level (1-10)"])]
    out_of_sample = float(np.mean([g == t for g, t in zip(guesses, held_out["Severity"])]))
    print(f"\nreconstruction accuracy: shipped lookup in-sample {in_sample:.4f}; "
          f"rebuilt on 80%, held-out 20% ({len(held_out)} rows) {out_of_sample:.4f}")
    assert abs(out_of_sample - 0.880) < 0.03


def test_estimate_tier_lookup_and_fallback() -> None:
    from src.inference.template_advice import estimate_tier, severity_band

    seen = estimate_tier("Medium", 9)  # 699 train+val patients; most common tier High (7-8), 63%
    assert seen["tier"] == "High (7-8)" and seen["n"] == 699 and 0.6 < seen["share"] < 0.65
    unseen = estimate_tier("High", 1)  # High with stress 1-4 never occurs -> band rule, anxiety midpoint 8.5
    assert unseen["n"] == 0 and unseen["share"] is None
    assert unseen["tier"] == severity_band(8.5, 1) == "Moderate (5-6)"

