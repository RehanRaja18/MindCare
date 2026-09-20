"""Single-patient inference for the tuned Random Forest, 3-class Anxiety
Level target. Takes raw feature values (a dict using the exact 17 column
names from CLAUDE.md), runs them through the saved preprocessor, predicts
with the saved final model (data/processed/mindcare_final_model.pkl, built
by src/models/save_final_model.py), and reports the uncertainty-flagging
status.

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


ROOT = Path(__file__).resolve().parents[2]
PREPROCESSOR_PATH = ROOT / "data" / "processed" / "mindcare_preprocessor.pkl"
LABEL_ENCODER_PATH = ROOT / "data" / "processed" / "mindcare_label_encoder_3class.pkl"
MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model.pkl"

CLASS_NAMES = ["Low", "Medium", "High"]
HIGH_INDEX = CLASS_NAMES.index("High")
HIGH_PROBA_THRESHOLD = 0.10  # production uncertainty-flagging rule (src/models/uncertainty_flagging.py)

NUMERIC_FEATURES = [
    "Age",
    "Sleep Hours",
    "Physical Activity (hrs/week)",
    "Caffeine Intake (mg/day)",
    "Alcohol Consumption (drinks/week)",
    "Stress Level (1-10)",
    "Heart Rate (bpm)",
    "Breathing Rate (breaths/min)",
    "Sweating Level (1-5)",
    "Therapy Sessions (per month)",
    "Diet Quality (1-10)",
]
CATEGORICAL_FEATURES = [
    "Occupation",
    "Smoking",
    "Family History of Anxiety",
    "Dizziness",
    "Medication",
    "Recent Major Life Event",
]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

EXAMPLE_PATIENTS = {
    "clearly_low_risk": {
        "Age": 29,
        "Sleep Hours": 8.2,
        "Physical Activity (hrs/week)": 5.5,
        "Caffeine Intake (mg/day)": 80,
        "Alcohol Consumption (drinks/week)": 1,
        "Stress Level (1-10)": 2,
        "Heart Rate (bpm)": 68,
        "Breathing Rate (breaths/min)": 14,
        "Sweating Level (1-5)": 1,
        "Therapy Sessions (per month)": 0,
        "Diet Quality (1-10)": 9,
        "Occupation": "Teacher",
        "Smoking": "No",
        "Family History of Anxiety": "No",
        "Dizziness": "No",
        "Medication": "No",
        "Recent Major Life Event": "No",
    },
    "clearly_high_risk": {
        "Age": 34,
        "Sleep Hours": 3.5,
        "Physical Activity (hrs/week)": 0.2,
        "Caffeine Intake (mg/day)": 520,
        "Alcohol Consumption (drinks/week)": 16,
        "Stress Level (1-10)": 10,
        "Heart Rate (bpm)": 112,
        "Breathing Rate (breaths/min)": 27,
        "Sweating Level (1-5)": 5,
        "Therapy Sessions (per month)": 6,
        "Diet Quality (1-10)": 2,
        "Occupation": "Scientist",
        "Smoking": "Yes",
        "Family History of Anxiety": "Yes",
        "Dizziness": "Yes",
        "Medication": "Yes",
        "Recent Major Life Event": "Yes",
    },
    "ambiguous_moderate": {
        "Age": 40,
        "Sleep Hours": 6.5,
        "Physical Activity (hrs/week)": 3.0,
        "Caffeine Intake (mg/day)": 280,
        "Alcohol Consumption (drinks/week)": 9,
        "Stress Level (1-10)": 6,
        "Heart Rate (bpm)": 91,
        "Breathing Rate (breaths/min)": 21,
        "Sweating Level (1-5)": 3,
        "Therapy Sessions (per month)": 2,
        "Diet Quality (1-10)": 5,
        "Occupation": "Nurse",
        "Smoking": "No",
        "Family History of Anxiety": "Yes",
        "Dizziness": "No",
        "Medication": "No",
        "Recent Major Life Event": "No",
    },
}


def predict_patient(patient: dict, preprocessor: object, model: object) -> dict:
    # Validates before any prediction is attempted: raises InputValidationError
    # (physically/logically impossible values, or missing/unrecognized fields) or
    # returns a list of warnings (valid but outside the training data's observed range).
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
        "uncertainty_flag": p_high >= HIGH_PROBA_THRESHOLD,
        "warnings": warnings,
    }


# The exact style of input that silently produced a confident (wrong-headed) prediction in
# Phase 19's robustness testing (reports/robustness_3class.md, Test 3) - each overrides one
# field of an otherwise-realistic patient, the same methodology used there.
INVALID_PROBE_PATIENTS = {
    "negative_age": {**EXAMPLE_PATIENTS["ambiguous_moderate"], "Age": -5},
    "impossible_stress": {**EXAMPLE_PATIENTS["ambiguous_moderate"], "Stress Level (1-10)": 250},
    "impossible_heart_rate": {**EXAMPLE_PATIENTS["ambiguous_moderate"], "Heart Rate (bpm)": 9000},
}


def main() -> None:
    preprocessor = joblib.load(PREPROCESSOR_PATH)
    model = joblib.load(MODEL_PATH)

    for name, patient in EXAMPLE_PATIENTS.items():
        result = predict_patient(patient, preprocessor, model)
        print(f"=== {name} ===")
        for warning in result["warnings"]:
            print(f"  WARNING: {warning}")
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
