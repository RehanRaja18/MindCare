"""Adopt XGBoost as the canonical 3-class Anxiety Level model (decided
2026-09-28), replacing the 12-feature Random Forest.

Evidence: reports/model_comparison_12feature.md. Performance was a tie with
the Random Forest (5-fold CV balanced accuracy 0.8085 vs 0.8093), but XGBoost
is 3-5x better calibrated, more robust to input noise, does not depend on a
"High needs high caffeine" shortcut the Random Forest learned, is unaffected
by the dataset's age-50 artifact, and is ~30x faster and ~9x smaller.

Hyperparameters: reports/tuning_results_12feature.json (re-tuned on the 12
features by src/models/tune_models_12feature.py; unweighted beat balanced
sample weights in CV). Trained on the 12-feature TRAIN split only, reusing the
existing 12-feature preprocessor - no re-splitting, no re-preprocessing.

Review threshold: 0.025 on P(High) (was 0.10 for the Random Forest). 0.10 was
the High base rate, but XGBoost's better-calibrated probabilities put most
borderline High cases below it (152/165 High caught, 4/17 hard misses). 0.025
is the threshold at which XGBoost matches the Random Forest's validation
coverage exactly: 158/165 true-High rows and 10/17 of the true-High rows
predicted Medium, for 410 flagged rows instead of 363.

Validation only - the 12-feature splits contain no test arrays. The script
verifies the saved model reproduces the comparison report's numbers exactly
and raises (writing nothing it would leave inconsistent) if not.

Saves a NEW file; the Random Forest artifact is kept for history:
  data/processed/mindcare_final_model_12feature_xgb.pkl
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score
from xgboost import XGBClassifier


SEED = 42
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_12feature.npz"
TUNING_PATH = ROOT / "reports" / "tuning_results_12feature.json"
MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model_12feature_xgb.pkl"

HIGH = 2
HIGH_PROBA_THRESHOLD = 0.025

# From reports/model_comparison_12feature.md (xgb_retuned) and the threshold analysis above.
EXPECTED = {
    "accuracy": 0.7776,
    "balanced_accuracy": 0.8078,
    "macro_f1": 0.8171,
    "high_recall": 0.8970,
    "flagged": 410,
    "flagged_true_high": 158,
    "hard_misses_flagged": 10,
    "hard_misses": 17,
}


def main() -> None:
    tuning = json.loads(TUNING_PATH.read_text(encoding="utf-8"))["models"]["xgboost"]
    assert tuning["sample_weighting"] == "none", "this script fits unweighted, matching the tuning winner"
    with np.load(SPLITS_PATH) as splits:
        assert "X_test" not in splits.files
        x_train, y_train = splits["X_train"], splits["y_train"]
        x_val, y_val = splits["X_val"], splits["y_val"]

    model = XGBClassifier(
        **tuning["best_params"], objective="multi:softprob", eval_metric="mlogloss",
        random_state=SEED, n_jobs=-1,
    )
    model.fit(x_train, y_train)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Saved {MODEL_PATH.relative_to(ROOT)}")

    # Verify on a reloaded copy, exactly as the API will load it.
    reloaded = joblib.load(MODEL_PATH)
    probabilities = reloaded.predict_proba(x_val)
    predictions = probabilities.argmax(axis=1)
    flagged = probabilities[:, HIGH] >= HIGH_PROBA_THRESHOLD
    hard = (y_val == HIGH) & (predictions != HIGH)
    actual = {
        "accuracy": accuracy_score(y_val, predictions),
        "balanced_accuracy": balanced_accuracy_score(y_val, predictions),
        "macro_f1": f1_score(y_val, predictions, average="macro"),
        "high_recall": recall_score(y_val, predictions, labels=[HIGH], average=None)[0],
        "flagged": int(flagged.sum()),
        "flagged_true_high": int((flagged & (y_val == HIGH)).sum()),
        "hard_misses_flagged": int((flagged & hard).sum()),
        "hard_misses": int(hard.sum()),
    }
    print("\n--- Verification against reports/model_comparison_12feature.md ---")
    mismatches = []
    for key, expected in EXPECTED.items():
        value = actual[key]
        ok = (round(value, 4) == expected) if isinstance(expected, float) else (value == expected)
        print(f"  {key}: expected {expected}, got {value if isinstance(value, int) else f'{value:.6f}'} -> {'MATCH' if ok else 'MISMATCH'}")
        if not ok:
            mismatches.append(key)
    if mismatches:
        MODEL_PATH.unlink()
        raise SystemExit(f"STOP: {mismatches} do not match - saved model removed. Investigate before adopting.")
    print("  ALL MATCH - XGBoost adopted as the canonical model.")


if __name__ == "__main__":
    main()
