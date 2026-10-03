"""Single-patient inference for the canonical XGBoost model, 3-class Anxiety
Level target. Takes raw feature values (a dict using the exact 11 column
names from CLAUDE.md's current feature set - the 11-feature reduced set
(reports/feature_reduction_3class.md) plus Age, re-added as a clinical/UX
decision (reports/feature_addition_age_3class.md)), runs them through the
saved preprocessor, predicts with the saved final model
(data/processed/mindcare_final_model_11feature_v2_xgb.pkl, built by
src/models/adopt_11feature_v2_model.py - XGBoost without Sweating Level, since 2026-10-02), and reports the uncertainty-flagging
status.

Note on caffeine: this internal script speaks "Caffeine Intake (mg/day)"
directly (a pre-computed mg value), unlike the patient-facing API
(src/api/main.py), which collects serving counts (cups of coffee/tea,
energy drinks, cans of soda) and converts them via estimate_caffeine_mg().
That's appropriate here since this is a developer-facing test/debug script,
not the API's patient-facing form.

Note on stress: unlike caffeine, this script DOES use the same input format
as the API - the 4 PSS-4 answers (pss_uncontrollable, pss_confident,
pss_going_your_way, pss_difficulties_piling_up), converted to the model's
"Stress Level (1-10)" by src/inference/stress_scale.py's
estimate_stress_level() before validation and prediction.

This is a decision-support illustration only — per CLAUDE.md's critical
workflow constraint, no prediction from this script may reach a patient
without psychologist review.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.inference.input_validation import InputValidationError, validate_patient
from src.inference.stress_scale import PSS_FIELDS, estimate_stress_level


ROOT = Path(__file__).resolve().parents[2]
PREPROCESSOR_PATH = ROOT / "data" / "processed" / "mindcare_preprocessor_11feature_v2.pkl"
LABEL_ENCODER_PATH = ROOT / "data" / "processed" / "mindcare_label_encoder_3class.pkl"
MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model_11feature_v2_xgb.pkl"

CLASS_NAMES = ["Low", "Medium", "High"]
HIGH_INDEX = CLASS_NAMES.index("High")
# Priority-review flag on P(High). 0.025 for XGBoost (was 0.10 for the Random Forest): the level at
# which XGBoost matches the Random Forest's validation coverage - 158/165 true-High rows and 10/17
# true-High rows predicted Medium (src/models/adopt_xgboost_12feature_model.py).
HIGH_PROBA_THRESHOLD = 0.025

NUMERIC_FEATURES = [
    "Sleep Hours",
    "Physical Activity (hrs/week)",
    "Caffeine Intake (mg/day)",
    "Stress Level (1-10)",
    "Heart Rate (bpm)",
    "Breathing Rate (breaths/min)",
    "Therapy Sessions (per month)",
    "Diet Quality (1-10)",
    "Age",
]
CATEGORICAL_FEATURES = [
    "Occupation",
    "Family History of Anxiety",
]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

EXAMPLE_PATIENTS = {
    "clearly_low_risk": {
        "Sleep Hours": 8.2,
        "Physical Activity (hrs/week)": 5.5,
        "Caffeine Intake (mg/day)": 80,
        # PSS-4 total = 0 + (4-3) + (4-4) + 0 = 1 -> Stress Level 2 (same as the old raw value)
        "pss_uncontrollable": 0,
        "pss_confident": 3,
        "pss_going_your_way": 4,
        "pss_difficulties_piling_up": 0,
        "Heart Rate (bpm)": 68,
        "Breathing Rate (breaths/min)": 14,
        "Therapy Sessions (per month)": 0,
        "Diet Quality (1-10)": 9,
        "Age": 29,
        "Occupation": "Teacher",
        "Family History of Anxiety": "No",
    },
    "clearly_high_risk": {
        "Sleep Hours": 3.5,
        "Physical Activity (hrs/week)": 0.2,
        "Caffeine Intake (mg/day)": 520,
        # PSS-4 total = 4 + (4-0) + (4-0) + 4 = 16 -> Stress Level 10 (same as the old raw value)
        "pss_uncontrollable": 4,
        "pss_confident": 0,
        "pss_going_your_way": 0,
        "pss_difficulties_piling_up": 4,
        "Heart Rate (bpm)": 112,
        "Breathing Rate (breaths/min)": 27,
        "Therapy Sessions (per month)": 6,
        "Diet Quality (1-10)": 2,
        "Age": 47,
        "Occupation": "Scientist",
        "Family History of Anxiety": "Yes",
    },
    "ambiguous_moderate": {
        "Sleep Hours": 6.5,
        "Physical Activity (hrs/week)": 3.0,
        "Caffeine Intake (mg/day)": 280,
        # PSS-4 total = 2 + (4-1) + (4-2) + 2 = 9 -> 1 + 9*9/16 = 6.06 -> Stress Level 6 (same as
        # the old raw value)
        "pss_uncontrollable": 2,
        "pss_confident": 1,
        "pss_going_your_way": 2,
        "pss_difficulties_piling_up": 2,
        "Heart Rate (bpm)": 91,
        "Breathing Rate (breaths/min)": 21,
        "Therapy Sessions (per month)": 2,
        "Diet Quality (1-10)": 5,
        "Age": 38,
        "Occupation": "Nurse",
        "Family History of Anxiety": "Yes",
    },
}


def to_model_features(patient: dict) -> dict:
    """Replace the 4 PSS-4 answers with the computed "Stress Level (1-10)" the
    model expects. Raises InputValidationError for a missing or out-of-range
    PSS answer (a missing one arrives as None, which estimate_stress_level() rejects)."""
    features = {k: v for k, v in patient.items() if k not in PSS_FIELDS}
    features["Stress Level (1-10)"] = estimate_stress_level(**{f: patient.get(f) for f in PSS_FIELDS})
    return features


def predict_patient(patient: dict, preprocessor: object, model: object) -> dict:
    # Validates before any prediction is attempted: raises InputValidationError
    # (physically/logically impossible values, or missing/unrecognized fields) or
    # returns a list of warnings (valid but outside the training data's observed range).
    # Stress Level is checked as the value computed from the PSS-4 answers.
    patient = to_model_features(patient)
    warnings = validate_patient(patient)

    row = pd.DataFrame([{feature: patient[feature] for feature in ALL_FEATURES}])
    x = preprocessor.transform(row)
    probabilities = model.predict_proba(x)[0]
    predicted_index = int(np.argmax(probabilities))
    p_high = float(probabilities[HIGH_INDEX])
    return {
        "predicted_class": CLASS_NAMES[predicted_index],
        "probabilities": {name: float(p) for name, p in zip(CLASS_NAMES, probabilities)},
        "p_high": p_high,
        "stress_level": patient["Stress Level (1-10)"],
        "uncertainty_flag": p_high >= HIGH_PROBA_THRESHOLD,
        "warnings": warnings,
    }


# The exact style of input that silently produced a confident (wrong-headed) prediction in
# Phase 19's robustness testing (reports/robustness_3class.md, Test 3) - each overrides one
# field of an otherwise-realistic patient, the same methodology used there. "negative_age" is
# back now that Age is a model input again (re-added 2026-09-22,
# reports/feature_addition_age_3class.md); "impossible_caffeine" was added when caffeine
# handling changed to serving counts. "impossible_stress" (Stress Level=250) became
# "impossible_pss_answer" when stress moved to PSS-4 answers - a computed Stress Level can no
# longer be out of range, so the probe now targets an out-of-range PSS answer instead.
INVALID_PROBE_PATIENTS = {
    "impossible_pss_answer": {**EXAMPLE_PATIENTS["ambiguous_moderate"], "pss_uncontrollable": 9},
    "impossible_heart_rate": {**EXAMPLE_PATIENTS["ambiguous_moderate"], "Heart Rate (bpm)": 9000},
    "impossible_caffeine": {**EXAMPLE_PATIENTS["ambiguous_moderate"], "Caffeine Intake (mg/day)": 5000},
    "negative_age": {**EXAMPLE_PATIENTS["ambiguous_moderate"], "Age": -5},
    # Plausible ages outside the supported 18-49 range (decided 2026-09-27) - rejected as out of scope.
    "minor_age": {**EXAMPLE_PATIENTS["ambiguous_moderate"], "Age": 16},
    "age_over_supported_range": {**EXAMPLE_PATIENTS["ambiguous_moderate"], "Age": 55},
}


def main() -> None:
    preprocessor = joblib.load(PREPROCESSOR_PATH)
    model = joblib.load(MODEL_PATH)

    for name, patient in EXAMPLE_PATIENTS.items():
        result = predict_patient(patient, preprocessor, model)
        print(f"=== {name} ===")
        for warning in result["warnings"]:
            print(f"  WARNING: {warning}")
        print(f"Stress Level (computed from PSS-4): {result['stress_level']}")
        print(f"Predicted class: {result['predicted_class']}")
        print("Probability distribution:")
        for class_name in CLASS_NAMES:
            print(f"  {class_name}: {result['probabilities'][class_name]:.4f}")
        print(
            f"Uncertainty flag (P(High) >= {HIGH_PROBA_THRESHOLD}): "
            f"{'YES - recommend review' if result['uncertainty_flag'] else 'no'} "
            f"(P(High)={result['p_high']:.4f})"
        )
        print()

    print(
        "Reminder: this is a decision-support illustration only. Per CLAUDE.md's critical "
        "workflow constraint, no prediction here may reach a patient without psychologist "
        "review."
    )

    print("\n--- Input validation probes (same style of input that exposed the gap in Phase 19"
          " robustness testing) ---")
    for name, patient in INVALID_PROBE_PATIENTS.items():
        print(f"\n=== {name} ===")
        try:
            result = predict_patient(patient, preprocessor, model)
            print(
                f"  NOT REJECTED - predicted={result['predicted_class']} "
                f"(this would be a validation gap)"
            )
        except InputValidationError as exc:
            print(f"  REJECTED as expected:\n{exc}")


if __name__ == "__main__":
    main()
