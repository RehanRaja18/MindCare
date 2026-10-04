"""Re-add Age to the canonical 3-class Anxiety Level model, producing a new
12-feature configuration (10 numeric + 2 categorical) alongside - not in
place of - the current 11-feature canonical model.

This is a clinical/UX decision to restore Age as a collected field, not a
response to a performance finding. Age was one of the 6 lowest-SHAP-ranked
features dropped in reports/feature_reduction_3class.md, and its removal
cost near-zero on validation at the time - but that experiment never tested
this exact 12-feature combination (11-feature set + Age), so this script
measures it for real rather than assuming the earlier near-zero-cost result
carries over unchanged.

Saves NEW files only - the 11-feature (and original 17-feature) artifacts
are never touched:
  data/processed/mindcare_preprocessor_12feature.pkl
  data/processed/mindcare_processed_splits_12feature.npz
  data/processed/mindcare_final_model_12feature.pkl

Test-set policy for this run: the 3-class test set has been used twice
already (17-feature and 11-feature models) and is being treated as fully
spent going forward. Per explicit instruction, this script does not load,
transform, or reference X_test/y_test/test_original_idx anywhere - not even
to pre-transform it for later use (the 11-feature adoption script did that;
this one deliberately does not). The saved 12-feature splits file therefore
contains only train/val arrays, no test arrays.

Writes the real validation-set comparison against the 11-feature baseline to
reports/feature_addition_age_3class.md.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    recall_score,
)
from sklearn.preprocessing import OneHotEncoder, StandardScaler


SEED = 42
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
EXISTING_SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"

NEW_PREPROCESSOR_PATH = ROOT / "data" / "processed" / "mindcare_preprocessor_12feature.pkl"
NEW_SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_12feature.npz"
NEW_MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model_12feature.pkl"
REPORT_PATH = ROOT / "reports" / "feature_addition_age_3class.md"

# 11-feature validation baseline this configuration is compared against
# (reports/feature_reduction_3class.md).
BASELINE_11FEATURE = {
    "accuracy": 0.7770,
    "balanced_accuracy": 0.8084,
    "macro_f1": 0.8204,
    "recall_low": 0.7545,
    "recall_medium": 0.7737,
    "recall_high": 0.8970,
}
CLASS_NAMES = ["Low", "Medium", "High"]

NUMERIC_FEATURES = [
    "Sleep Hours",
    "Physical Activity (hrs/week)",
    "Caffeine Intake (mg/day)",
    "Stress Level (1-10)",
    "Heart Rate (bpm)",
    "Breathing Rate (breaths/min)",
    "Sweating Level (1-5)",
    "Therapy Sessions (per month)",
    "Diet Quality (1-10)",
    "Age",
]
CATEGORICAL_FEATURES = ["Occupation", "Family History of Anxiety"]

TUNED_RF_PARAMS = dict(
    n_estimators=200,
    max_depth=10,
    min_samples_split=10,
    min_samples_leaf=4,
    max_features="sqrt",
    class_weight="balanced",
    random_state=SEED,
    n_jobs=-1,
)


def main() -> None:
    total_features = len(NUMERIC_FEATURES) + len(CATEGORICAL_FEATURES)
    print(f"Numeric features ({len(NUMERIC_FEATURES)}): {NUMERIC_FEATURES}")
    print(f"Categorical features ({len(CATEGORICAL_FEATURES)}): {CATEGORICAL_FEATURES}")
    print(f"Total: {total_features}")
    if total_features != 12:
        raise ValueError(f"Expected 12 features, got {total_features}")

    dataframe = pd.read_csv(DATA_PATH)

    # Only train/val indices are loaded - test_original_idx is intentionally never read.
    with np.load(EXISTING_SPLITS_PATH) as splits:
        train_idx = splits["train_original_idx"]
        val_idx = splits["val_original_idx"]
        y_train = splits["y_train"]
        y_val = splits["y_val"]

    train_rows = dataframe.iloc[train_idx]
    val_rows = dataframe.iloc[val_idx]

    # --- Step 1: build + fit new preprocessor on TRAIN rows only ---
    print("\n--- Step 1: fit new 12-feature preprocessor on train rows only ---")
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    x_train = preprocessor.fit_transform(train_rows[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
    x_val = preprocessor.transform(val_rows[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
    print(f"Shapes: X_train={x_train.shape}, X_val={x_val.shape} (test set NOT loaded/transformed)")

    # --- Step 2: save new preprocessor + splits (train/val only) ---
    NEW_PREPROCESSOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(preprocessor, NEW_PREPROCESSOR_PATH)
    print(f"\n--- Step 2: saved new files ---")
    print(f"Saved: {NEW_PREPROCESSOR_PATH.relative_to(ROOT)}")

    np.savez(
        NEW_SPLITS_PATH,
        X_train=x_train,
        X_val=x_val,
        y_train=y_train,
        y_val=y_val,
        train_original_idx=train_idx,
        val_original_idx=val_idx,
    )
    print(f"Saved: {NEW_SPLITS_PATH.relative_to(ROOT)} (no X_test/y_test/test_original_idx - test set not touched)")

    # --- Step 3: retrain tuned RF on new X_train, save ---
    print("\n--- Step 3: retrain tuned Random Forest on 12-feature X_train ---")
    model = RandomForestClassifier(**TUNED_RF_PARAMS)
    model.fit(x_train, y_train)
    joblib.dump(model, NEW_MODEL_PATH)
    print(f"Saved: {NEW_MODEL_PATH.relative_to(ROOT)}")

    # --- Step 4: evaluate on VALIDATION ONLY, from the saved/reloaded artifacts ---
    print("\n--- Step 4: validation-only evaluation (reloaded from disk) ---")
    reloaded_model = joblib.load(NEW_MODEL_PATH)
    with np.load(NEW_SPLITS_PATH) as reloaded_splits:
        reloaded_x_val = reloaded_splits["X_val"]
        reloaded_y_val = reloaded_splits["y_val"]

    predictions = reloaded_model.predict(reloaded_x_val)
    computed_accuracy = float(accuracy_score(reloaded_y_val, predictions))
    computed_balanced_accuracy = float(balanced_accuracy_score(reloaded_y_val, predictions))
    computed_macro_f1 = float(f1_score(reloaded_y_val, predictions, average="macro"))
    per_class_recall = recall_score(reloaded_y_val, predictions, average=None, labels=[0, 1, 2])
    computed_recall = dict(zip(CLASS_NAMES, (float(r) for r in per_class_recall)))

    print(f"  accuracy:          {computed_accuracy:.4f}")
    print(f"  balanced_accuracy: {computed_balanced_accuracy:.4f}")
    print(f"  macro_f1:          {computed_macro_f1:.4f}")
    for class_name in CLASS_NAMES:
        print(f"  recall_{class_name.lower()}: {computed_recall[class_name]:.4f}")

    deltas = {
        "accuracy": computed_accuracy - BASELINE_11FEATURE["accuracy"],
        "balanced_accuracy": computed_balanced_accuracy - BASELINE_11FEATURE["balanced_accuracy"],
        "macro_f1": computed_macro_f1 - BASELINE_11FEATURE["macro_f1"],
        "recall_low": computed_recall["Low"] - BASELINE_11FEATURE["recall_low"],
        "recall_medium": computed_recall["Medium"] - BASELINE_11FEATURE["recall_medium"],
        "recall_high": computed_recall["High"] - BASELINE_11FEATURE["recall_high"],
    }
    print("\n--- Deltas (12-feature - 11-feature baseline) ---")
    for key, value in deltas.items():
        print(f"  {key}: {value:+.4f}")

    write_report(computed_accuracy, computed_balanced_accuracy, computed_macro_f1, computed_recall, deltas)
    print(f"\nSaved: {REPORT_PATH.relative_to(ROOT)}")
    print("\nDone. NOT touched: 11-feature or 17-feature preprocessor/splits/model, test set, "
          "predict_single.py, API.")


def write_report(accuracy: float, balanced_accuracy: float, macro_f1: float,
                  recall: dict[str, float], deltas: dict[str, float]) -> None:
    largest_metric = max(deltas, key=lambda key: abs(deltas[key]))
    largest_value = deltas[largest_metric]
    meaningful = {key: value for key, value in deltas.items() if abs(value) >= 0.01}

    if meaningful:
        meaningful_lines = "\n".join(
            f"- **{key}**: {value:+.4f}" for key, value in meaningful.items()
        )
        verdict = (
            f"**Re-adding Age carries a real, non-trivial cost/benefit on at least one metric "
            f"(≥1 point).** Metric(s) crossing the 1-point bar used elsewhere in this project:\n\n"
            f"{meaningful_lines}\n\n"
            f"The largest single movement is **{largest_metric}** ({largest_value:+.4f}). This "
            f"should not be waved away as noise; it is reported plainly here regardless of "
            f"direction."
        )
    else:
        verdict = (
            f"**No headline or per-class metric moved by as much as 1 point in either "
            f"direction** (largest absolute change: {largest_metric} at {largest_value:+.4f}, "
            f"{abs(largest_value) * 100:.2f} points). Re-adding Age on top of the current "
            f"11-feature set costs/gains essentially nothing on this validation split. This is "
            f"consistent with Age's bottom-6 SHAP ranking in the original 17-feature analysis "
            f"(`reports/shap_full_ranking_3class.md`), but this exact 12-feature combination had "
            f"never actually been tested before this run - this is a measured result, not an "
            f"assumption carried over from that ranking."
        )

    content = f"""# Feature Addition Experiment: Re-adding Age — 3-Class Target

**Scope note: this script (`src/models/adopt_12feature_model.py`) works on TRAIN and VALIDATION
only. Per explicit instruction, it does not load, transform, or reference X_test, y_test, or
test_original_idx anywhere — the 3-class test set has been used twice already (17-feature,
11-feature) and is being treated as fully spent going forward. This Age re-addition is a
clinical/UX decision, not a performance claim requiring test-set verification, so no test-set
check was performed or is planned for this configuration.**

## Motivation

Age was one of the 6 lowest-SHAP-ranked features dropped when the 11-feature model was adopted
(`reports/feature_reduction_3class.md`) — a product/UX decision to shorten onboarding, not a
performance-driven one. This experiment re-adds Age on top of the current 11-feature set (a
clinical/UX decision to restore it), producing a genuinely new 12-feature configuration that has
never been tested before. The near-zero cost found for the original 6-feature group drop does not
by itself establish the cost of adding back just one of those six in isolation — measured here
for real rather than assumed.

## Method

Starting from the currently-adopted 11-feature set (Sleep Hours, Physical Activity (hrs/week),
Caffeine Intake (mg/day), Stress Level (1-10), Heart Rate (bpm), Breathing Rate (breaths/min),
Sweating Level (1-5), Therapy Sessions (per month), Diet Quality (1-10), Occupation, Family
History of Anxiety), added back `Age`, producing 12 features (10 numeric + 2 categorical). New
`ColumnTransformer` fit on train rows only; tuned Random Forest (same hyperparameters as
`reports/tuning_results_3class.json` / the 11-feature model) retrained from scratch.

## Results

| Feature set | Accuracy | Balanced acc. | Macro-F1 | Recall Low | Recall Medium | Recall High |
|---|---:|---:|---:|---:|---:|---:|
| Current 11-feature (baseline) | {BASELINE_11FEATURE['accuracy']:.4f} | {BASELINE_11FEATURE['balanced_accuracy']:.4f} | {BASELINE_11FEATURE['macro_f1']:.4f} | {BASELINE_11FEATURE['recall_low']:.4f} | {BASELINE_11FEATURE['recall_medium']:.4f} | {BASELINE_11FEATURE['recall_high']:.4f} |
| **With Age (12 features)** | **{accuracy:.4f}** | **{balanced_accuracy:.4f}** | **{macro_f1:.4f}** | {recall['Low']:.4f} | {recall['Medium']:.4f} | {recall['High']:.4f} |

## Deltas (With Age − 11-Feature Baseline)

| Metric | Δ |
|---|---:|
| Accuracy | {deltas['accuracy']:+.4f} |
| Balanced accuracy | {deltas['balanced_accuracy']:+.4f} |
| Macro-F1 | {deltas['macro_f1']:+.4f} |
| Recall Low | {deltas['recall_low']:+.4f} |
| Recall Medium | {deltas['recall_medium']:+.4f} |
| Recall High | {deltas['recall_high']:+.4f} |

## Honest Verdict

{verdict}

## Decision

**Age is re-added as a model input regardless of this validation result** — this was explicitly a
clinical/UX decision (restoring a field product/clinical stakeholders want collected), not
something contingent on a performance finding. This report exists so that decision is made with
real numbers in hand rather than an assumption, and so that if the result had shown a real cost,
that cost would be visible and disclosed rather than hidden. See `CLAUDE.md` and
`docs/model_card.md` for how this decision and its measured cost/benefit are documented going
forward.

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not clinical
validation. Validation-set result only — this configuration has not been, and per explicit
instruction will not be, evaluated against the test set (X_test/y_test), which is being treated
as fully spent for the 3-class target after its two prior uses (17-feature, 11-feature).
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
