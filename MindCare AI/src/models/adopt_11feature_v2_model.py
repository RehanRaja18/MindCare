"""Adopt the 11-feature "v2" XGBoost model as canonical (decided 2026-10-02):
the 12-feature model with Sweating Level (1-5) removed.

Evidence: reports/feature_reduction_sweatlevel_3class.md - removing Sweating
Level cost nothing measurable for the High class (148/165 labelled High and
158/165 flagged, before and after; High recall identical in all 5 paired CV
folds), at most 0.4 points on any Low/Medium metric on the validation split,
and about zero in paired 5-fold CV. Re-running the tuning procedure on the 11
features chose the same hyperparameters, so they are reused unchanged
(reports/tuning_results_12feature.json), as is the 0.025 review threshold.

"v2" because data/processed/*_11feature.* already exists: that is the
superseded 2026-09-22 Random Forest set (no Age, WITH Sweating Level). This set
has Age and no Sweating Level. Nothing existing is overwritten:
  data/processed/mindcare_preprocessor_11feature_v2.pkl
  data/processed/mindcare_processed_splits_11feature_v2.npz   (train + val only)
  data/processed/mindcare_final_model_11feature_v2_xgb.pkl

Train rows only for fitting; the split membership is reused from the 12-feature
splits file (no re-splitting). That file has no test keys and the test set is
never loaded - the 3-class test set is spent. The script verifies the saved
model against the ablation report's numbers and removes its outputs on any
mismatch.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from src.build_3class_target import bin_anxiety_level

SEED = 42
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SOURCE_SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_12feature.npz"
TUNING_PATH = ROOT / "reports" / "tuning_results_12feature.json"
PREPROCESSOR_PATH = ROOT / "data" / "processed" / "mindcare_preprocessor_11feature_v2.pkl"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_11feature_v2.npz"
MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model_11feature_v2_xgb.pkl"

NUMERIC_FEATURES = [
    "Sleep Hours", "Physical Activity (hrs/week)", "Caffeine Intake (mg/day)", "Stress Level (1-10)",
    "Heart Rate (bpm)", "Breathing Rate (breaths/min)", "Therapy Sessions (per month)",
    "Diet Quality (1-10)", "Age",
]
CATEGORICAL_FEATURES = ["Occupation", "Family History of Anxiety"]
HIGH = 2
HIGH_PROBA_THRESHOLD = 0.025

# reports/feature_reduction_sweatlevel_3class.md / .json ("11 features (no Sweating Level)", validation).
EXPECTED = {
    "accuracy": 0.7745, "balanced_accuracy": 0.8055, "macro_f1": 0.8148, "high_recall": 0.8970,
    "flagged": 411, "flagged_true_high": 158, "high_labelled_high": 148,
}


def main() -> None:
    tuning = json.loads(TUNING_PATH.read_text(encoding="utf-8"))["models"]["xgboost"]
    assert tuning["sample_weighting"] == "none"
    df = pd.read_csv(DATA_PATH)
    with np.load(SOURCE_SPLITS_PATH) as source:
        assert "X_test" not in source.files and "test_original_idx" not in source.files
        train_idx, val_idx = source["train_original_idx"], source["val_original_idx"]
        y_train, y_val = source["y_train"], source["y_val"]
    features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    train_rows, val_rows = df.iloc[train_idx], df.iloc[val_idx]
    assert np.array_equal(bin_anxiety_level(train_rows["Anxiety Level (1-10)"].to_numpy()), y_train)
    assert np.array_equal(bin_anxiety_level(val_rows["Anxiety Level (1-10)"].to_numpy()), y_val)

    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])
    x_train = np.asarray(preprocessor.fit_transform(train_rows[features]))
    x_val = np.asarray(preprocessor.transform(val_rows[features]))
    model = XGBClassifier(**tuning["best_params"], objective="multi:softprob", eval_metric="mlogloss",
                          random_state=SEED, n_jobs=-1)
    model.fit(x_train, y_train)

    joblib.dump(preprocessor, PREPROCESSOR_PATH)
    np.savez(SPLITS_PATH, X_train=x_train, X_val=x_val, y_train=y_train, y_val=y_val,
             train_original_idx=train_idx, val_original_idx=val_idx)
    joblib.dump(model, MODEL_PATH)
    print(f"Shapes: X_train={x_train.shape}, X_val={x_val.shape} (test set not loaded)")

    # Verify on reloaded copies, exactly as the API will use them.
    probabilities = joblib.load(MODEL_PATH).predict_proba(joblib.load(PREPROCESSOR_PATH).transform(val_rows[features]))
    predictions = probabilities.argmax(axis=1)
    flagged = probabilities[:, HIGH] >= HIGH_PROBA_THRESHOLD
    actual = {
        "accuracy": accuracy_score(y_val, predictions),
        "balanced_accuracy": balanced_accuracy_score(y_val, predictions),
        "macro_f1": f1_score(y_val, predictions, average="macro"),
        "high_recall": recall_score(y_val, predictions, labels=[HIGH], average=None)[0],
        "flagged": int(flagged.sum()),
        "flagged_true_high": int((flagged & (y_val == HIGH)).sum()),
        "high_labelled_high": int(((predictions == HIGH) & (y_val == HIGH)).sum()),
    }
    print("\n--- Verification against reports/feature_reduction_sweatlevel_3class.md ---")
    mismatches = []
    for key, expected in EXPECTED.items():
        value = actual[key]
        ok = (round(value, 4) == expected) if isinstance(expected, float) else (value == expected)
        print(f"  {key}: expected {expected}, got {value if isinstance(value, int) else f'{value:.6f}'} -> {'MATCH' if ok else 'MISMATCH'}")
        if not ok:
            mismatches.append(key)
    if mismatches:
        for path in (PREPROCESSOR_PATH, SPLITS_PATH, MODEL_PATH):
            path.unlink(missing_ok=True)
        raise SystemExit(f"STOP: {mismatches} do not match - outputs removed. Investigate before adopting.")
    print("  ALL MATCH - 11-feature v2 XGBoost built.")
    for path in (PREPROCESSOR_PATH, SPLITS_PATH, MODEL_PATH):
        print(f"  saved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
