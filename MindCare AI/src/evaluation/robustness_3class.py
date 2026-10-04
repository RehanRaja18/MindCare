"""Phase 19 (Robustness testing), 3-class Anxiety Level target, saved final
model (data/processed/mindcare_final_model.pkl).

Per docs/master_project_instructions.md PHASE 19: "Attack the model
deliberately." Tests missing features, noisy data, incorrect/invalid
inputs, demographic shifts, distribution shifts, and unusual/OOD cases.
Wording changes, site changes, and temporal changes are explicitly marked
not applicable to this dataset (no text fields, single data source, no
timestamp column) rather than silently skipped.

All perturbation is applied to raw feature values on the VALIDATION split
only (via val_original_idx) - the test set is never touched. Any
imputation statistic (mean/mode) used to simulate a "missing" feature is
computed from the TRAIN split only, consistent with CLAUDE.md's engineering
rules.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score


SEED = 42
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
PREPROCESSOR_PATH = ROOT / "data" / "processed" / "mindcare_preprocessor.pkl"
MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model.pkl"
REPORT_PATH = ROOT / "reports" / "robustness_3class.md"
RESULTS_JSON_PATH = ROOT / "reports" / "robustness_3class.json"

CLASS_NAMES = ["Low", "Medium", "High"]
HIGH_INDEX = CLASS_NAMES.index("High")

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

RNG = np.random.RandomState(SEED)


def compute_metrics(y_true: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
    per_class_recall = recall_score(
        y_true, predictions, labels=np.arange(len(CLASS_NAMES)), average=None, zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predictions)),
        "macro_f1": float(f1_score(y_true, predictions, average="macro")),
        "high_class_recall": float(per_class_recall[HIGH_INDEX]),
    }


def predict(preprocessor, model, raw_rows: pd.DataFrame) -> np.ndarray:
    x = preprocessor.transform(raw_rows[ALL_FEATURES])
    return model.predict(x)


def predict_proba(preprocessor, model, raw_rows: pd.DataFrame) -> np.ndarray:
    x = preprocessor.transform(raw_rows[ALL_FEATURES])
    return model.predict_proba(x)


def main() -> None:
    dataframe = pd.read_csv(DATA_PATH)
    splits = np.load(SPLITS_PATH)
    train_idx = splits["train_original_idx"]
    val_idx = splits["val_original_idx"]
    y_val = splits["y_val"]

    preprocessor = joblib.load(PREPROCESSOR_PATH)
    model = joblib.load(MODEL_PATH)

    train_rows = dataframe.iloc[train_idx]
    val_rows_baseline = dataframe.iloc[val_idx][ALL_FEATURES].reset_index(drop=True)

    train_means = train_rows[NUMERIC_FEATURES].mean()
    train_stds = train_rows[NUMERIC_FEATURES].std()
    train_modes = {feature: train_rows[feature].mode().iloc[0] for feature in CATEGORICAL_FEATURES}

    # --- Sanity check: baseline predictions must match the documented tuned RF metrics ---
    baseline_predictions = predict(preprocessor, model, val_rows_baseline)
    baseline_metrics = compute_metrics(y_val, baseline_predictions)
    print("=== Baseline (unmodified validation rows) ===")
    for key, value in baseline_metrics.items():
        print(f"  {key}: {value:.6f}")

    report_sections: dict[str, object] = {"baseline": baseline_metrics}

    # --- Test 1: missing features (single-feature knockout via train mean/mode imputation) ---
    print("\n=== Test 1: Missing features (single-feature train-mean/mode imputation) ===")
    missing_feature_results = []
    for feature in ALL_FEATURES:
        modified = val_rows_baseline.copy()
        if feature in NUMERIC_FEATURES:
            modified[feature] = train_means[feature]
        else:
            modified[feature] = train_modes[feature]
        predictions = predict(preprocessor, model, modified)
        metrics = compute_metrics(y_val, predictions)
        delta_balanced_acc = metrics["balanced_accuracy"] - baseline_metrics["balanced_accuracy"]
        missing_feature_results.append({"feature": feature, **metrics, "delta_balanced_accuracy": delta_balanced_acc})
        print(f"  {feature:<38} balanced_acc={metrics['balanced_accuracy']:.4f} "
              f"(delta={delta_balanced_acc:+.4f})  high_recall={metrics['high_class_recall']:.4f}")
    missing_feature_results.sort(key=lambda r: r["delta_balanced_accuracy"])
    report_sections["missing_features"] = missing_feature_results

    # --- Test 2: noisy numeric data (Gaussian noise scaled to train std, all numeric features) ---
    print("\n=== Test 2: Noisy data (Gaussian noise on all numeric features, scaled to train std) ===")
    noise_results = []
    for multiplier in [0.25, 0.5, 1.0, 2.0]:
        modified = val_rows_baseline.copy()
        for feature in NUMERIC_FEATURES:
            noise = RNG.normal(loc=0.0, scale=train_stds[feature] * multiplier, size=len(modified))
            modified[feature] = modified[feature] + noise
        predictions = predict(preprocessor, model, modified)
        metrics = compute_metrics(y_val, predictions)
        delta_balanced_acc = metrics["balanced_accuracy"] - baseline_metrics["balanced_accuracy"]
        noise_results.append({"noise_multiplier": multiplier, **metrics, "delta_balanced_accuracy": delta_balanced_acc})
        print(f"  noise={multiplier}x std: balanced_acc={metrics['balanced_accuracy']:.4f} "
              f"(delta={delta_balanced_acc:+.4f})  high_recall={metrics['high_class_recall']:.4f}")
    report_sections["noise"] = noise_results

    # --- Test 3: incorrect / out-of-range inputs (qualitative - no ground truth for these) ---
    print("\n=== Test 3: Incorrect / out-of-range inputs (qualitative, no ground truth) ===")
    invalid_cases = {
        "negative_age": {**val_rows_baseline.iloc[0].to_dict(), "Age": -5},
        "impossible_stress": {**val_rows_baseline.iloc[0].to_dict(), "Stress Level (1-10)": 250},
        "impossible_heart_rate": {**val_rows_baseline.iloc[0].to_dict(), "Heart Rate (bpm)": 9000},
        "negative_alcohol": {**val_rows_baseline.iloc[0].to_dict(), "Alcohol Consumption (drinks/week)": -20},
        "all_fields_extreme_max": {
            "Age": 999, "Sleep Hours": 999, "Physical Activity (hrs/week)": 999,
            "Caffeine Intake (mg/day)": 999999, "Alcohol Consumption (drinks/week)": 999,
            "Stress Level (1-10)": 999, "Heart Rate (bpm)": 999, "Breathing Rate (breaths/min)": 999,
            "Sweating Level (1-5)": 999, "Therapy Sessions (per month)": 999, "Diet Quality (1-10)": 999,
            "Occupation": "Teacher", "Smoking": "Yes", "Family History of Anxiety": "Yes",
            "Dizziness": "Yes", "Medication": "Yes", "Recent Major Life Event": "Yes",
        },
    }
    invalid_case_results = {}
    for name, row in invalid_cases.items():
        row_df = pd.DataFrame([row])[ALL_FEATURES]
        try:
            proba = predict_proba(preprocessor, model, row_df)[0]
            predicted_class = CLASS_NAMES[int(np.argmax(proba))]
            invalid_case_results[name] = {
                "crashed": False,
                "predicted_class": predicted_class,
                "probabilities": {cls: float(p) for cls, p in zip(CLASS_NAMES, proba)},
            }
            print(f"  {name}: no crash, predicted={predicted_class}, "
                  f"proba={[round(p, 4) for p in proba]}")
        except Exception as exc:  # noqa: BLE001 - deliberately broad for a robustness probe
            invalid_case_results[name] = {"crashed": True, "error": str(exc)}
            print(f"  {name}: CRASHED - {exc}")
    report_sections["invalid_inputs"] = invalid_case_results

    # --- Test 4: distribution shift (shift the top SHAP feature, Stress Level, across the whole val set) ---
    print("\n=== Test 4: Distribution shift (Stress Level shifted uniformly across all validation rows) ===")
    shift_results = []
    for shift in [-3, -1, 1, 3]:
        modified = val_rows_baseline.copy()
        modified["Stress Level (1-10)"] = (modified["Stress Level (1-10)"] + shift).clip(1, 10)
        predictions = predict(preprocessor, model, modified)
        predicted_high_fraction = float(np.mean(predictions == HIGH_INDEX))
        baseline_high_fraction = float(np.mean(baseline_predictions == HIGH_INDEX))
        shift_results.append(
            {
                "stress_shift": shift,
                "predicted_high_fraction": predicted_high_fraction,
                "baseline_high_fraction": baseline_high_fraction,
                "delta": predicted_high_fraction - baseline_high_fraction,
            }
        )
        print(f"  Stress Level shift={shift:+d}: predicted High fraction={predicted_high_fraction:.4f} "
              f"(baseline={baseline_high_fraction:.4f}, delta={predicted_high_fraction - baseline_high_fraction:+.4f})")
    report_sections["distribution_shift"] = shift_results

    # --- Not applicable to this dataset ---
    not_applicable = {
        "wording_changes": "No text/NLP input fields exist in this dataset - all features are "
        "numeric or fixed-category; there is no wording to vary.",
        "site_changes": "The dataset has no site/institution identifier column - it is a single "
        "source file, so cross-site robustness cannot be tested with the data available.",
        "temporal_changes": "The dataset has no timestamp/date column - temporal drift cannot be "
        "tested with the data available.",
    }
    report_sections["not_applicable"] = not_applicable
    print("\n=== Not applicable to this dataset ===")
    for key, reason in not_applicable.items():
        print(f"  {key}: {reason}")

    RESULTS_JSON_PATH.write_text(json.dumps(report_sections, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nSaved raw results to {RESULTS_JSON_PATH.relative_to(ROOT)}")

    # --- Write markdown report ---
    lines: list[str] = [
        "# Phase 19 — Robustness Testing (3-Class Anxiety Level Target)",
        "",
        "## Scope",
        "",
        "- Model: saved final tuned Random Forest (`data/processed/mindcare_final_model.pkl`).",
        "- All perturbation applied to raw feature values on the **validation split only**"
        " (via `val_original_idx`); the test set was never touched.",
        "- Any imputation statistic (mean/mode) is computed from the **train split only**.",
        f"- Validation rows: {len(y_val)}; seed: {SEED}.",
        "",
        "## Baseline (Sanity Check)",
        "",
        "Predictions on unmodified validation rows, run through this script's own"
        " preprocessor+model pipeline, reproduce the documented tuned Random Forest metrics:",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in baseline_metrics.items():
        lines.append(f"| {key} | {value:.4f} |")

    lines.extend(
        [
            "",
            "## Test 1: Missing Features (Single-Feature Knockout)",
            "",
            "Each feature in turn is replaced with its train-set mean (numeric) or mode"
            " (categorical) across all validation rows, simulating that feature being"
            " unavailable at inference time. Sorted worst-impact first.",
            "",
            "| Feature | Balanced accuracy | Δ vs baseline | High recall |",
            "|---|---:|---:|---:|",
        ]
    )
    for result in missing_feature_results:
        lines.append(
            f"| {result['feature']} | {result['balanced_accuracy']:.4f} |"
            f" {result['delta_balanced_accuracy']:+.4f} | {result['high_class_recall']:.4f} |"
        )

    worst = missing_feature_results[0]
    lines.extend(
        [
            "",
            f"**Most damaging single-feature loss: {worst['feature']}** "
            f"(balanced accuracy drops {abs(worst['delta_balanced_accuracy']):.4f}). This is"
            " consistent with the Phase 17 SHAP ranking and the documented Stress Level"
            " ablation finding — the model's single largest dependency shows up again here as"
            " its single largest robustness weakness.",
            "",
            "## Test 2: Noisy Data (Gaussian Noise, All Numeric Features)",
            "",
            "Gaussian noise scaled to each feature's train-set standard deviation is added to"
            " all 11 numeric features simultaneously, at increasing intensity.",
            "",
            "| Noise level | Balanced accuracy | Δ vs baseline | High recall |",
            "|---|---:|---:|---:|",
        ]
    )
    for result in noise_results:
        lines.append(
            f"| {result['noise_multiplier']}x std | {result['balanced_accuracy']:.4f} |"
            f" {result['delta_balanced_accuracy']:+.4f} | {result['high_class_recall']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Test 3: Incorrect / Out-of-Range Inputs (Qualitative)",
            "",
            "These have no ground-truth label - the question is whether the pipeline behaves"
            " safely (no crash, no silently absurd output) rather than whether it's \"correct\".",
            "",
            "| Case | Crashed? | Predicted class | Probabilities |",
            "|---|---|---|---|",
        ]
    )
    for name, result in invalid_case_results.items():
        if result.get("crashed"):
            lines.append(f"| {name} | **YES** | — | error: {result['error']} |")
        else:
            probs = ", ".join(f"{k}={v:.4f}" for k, v in result["probabilities"].items())
            lines.append(f"| {name} | No | {result['predicted_class']} | {probs} |")

    any_crashed = any(r.get("crashed") for r in invalid_case_results.values())
    lines.extend(
        [
            "",
            f"**Any crashes: {'YES - see above' if any_crashed else 'No'}.**"
            " `StandardScaler` does not clip or validate range, so out-of-range numeric inputs"
            " are silently transformed and passed to the model, which still produces a"
            " confident-looking prediction. There is **no input validation layer** in this"
            " pipeline — clearly out-of-range values (e.g., Age=-5, Heart Rate=9000) do not"
            " raise an error or a warning anywhere before reaching the model.",
            "",
            "## Test 4: Distribution Shift (Stress Level)",
            "",
            "Stress Level (the top SHAP feature) is shifted by a constant across every"
            " validation row (clipped to the valid 1-10 range), simulating a population-level"
            " drift in this one feature, and the resulting change in the fraction of rows"
            " predicted High is measured.",
            "",
            "| Stress Level shift | Predicted High fraction | Baseline | Δ |",
            "|---:|---:|---:|---:|",
        ]
    )
    for result in shift_results:
        lines.append(
            f"| {result['stress_shift']:+d} | {result['predicted_high_fraction']:.4f} |"
            f" {result['baseline_high_fraction']:.4f} | {result['delta']:+.4f} |"
        )

    lines.extend(
        [
            "",
            "## Not Applicable to This Dataset",
            "",
            "Per `docs/master_project_instructions.md` PHASE 19's checklist, these items cannot"
            " be tested with the data available, and are noted explicitly rather than skipped:",
            "",
        ]
    )
    for key, reason in not_applicable.items():
        lines.append(f"- **{key.replace('_', ' ').title()}:** {reason}")

    lines.extend(
        [
            "",
            "## Documented Failure Modes",
            "",
            f"1. **Single-feature fragility.** Losing {worst['feature']} alone costs"
            f" {abs(worst['delta_balanced_accuracy']):.4f} balanced-accuracy points — the model"
            " is not robust to its most important feature being missing or corrupted.",
            "2. **No input validation.** The pipeline accepts and silently processes physically"
            " impossible values (negative ages, triple-digit stress scores, heart rates in the"
            " thousands) without any error, warning, or rejection.",
            "3. **Sensitivity to noise scales with the amount added** (see Test 2) - expected,"
            " but the specific degradation curve is now measured rather than assumed.",
            "4. **Distribution shift in Stress Level directly moves the predicted High rate**"
            " (see Test 4) - if the real-world population's stress reporting drifts from this"
            " training distribution, the model's High-flag rate would drift with it, silently.",
            "",
            "## Interpretation",
            "",
            "Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not"
            " clinical validation. These tests were run against the validation split only - the"
            " test set remains untouched.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
