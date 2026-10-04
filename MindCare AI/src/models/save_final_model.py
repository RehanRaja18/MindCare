"""Fit the tuned Random Forest (3-class Anxiety Level target) one final time
and persist it to data/processed/mindcare_final_model.pkl.

Verification performed:
1. Recompute accuracy/balanced_accuracy/macro_f1/high_class_recall on X_val
   from the freshly-fit model and compare them to the exact values already
   documented in reports/tuning_results_3class.json (random_forest.tuned_validation).
2. Reload the saved .pkl in a genuinely separate, fresh Python subprocess,
   predict on X_val there, and confirm np.array_equal against this process's
   own predictions - i.e. the saved artifact reproduces the exact same
   predictions as a fresh fit with the documented hyperparameters, not just
   matching aggregate metrics.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score


SEED = 42
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
TUNING_RESULTS_PATH = ROOT / "reports" / "tuning_results_3class.json"
MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model.pkl"

CLASS_NAMES = ["Low", "Medium", "High"]
HIGH_INDEX = CLASS_NAMES.index("High")

# Tuned Random Forest best params from reports/tuning_results_3class.json
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

_RELOAD_SCRIPT = """
import sys
import joblib
import numpy as np

model_path, splits_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
model = joblib.load(model_path)
splits = np.load(splits_path)
predictions = model.predict(splits["X_val"])
np.save(out_path, predictions)
"""


def main() -> None:
    splits = np.load(SPLITS_PATH)
    x_train, y_train = splits["X_train"], splits["y_train"]
    x_val, y_val = splits["X_val"], splits["y_val"]

    model = RandomForestClassifier(**TUNED_RF_PARAMS)
    model.fit(x_train, y_train)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH.relative_to(ROOT)}")

    # --- Verification 1: metrics match reports/tuning_results_3class.json exactly ---
    predictions_this_process = model.predict(x_val)
    per_class_recall = recall_score(
        y_val, predictions_this_process, labels=np.arange(len(CLASS_NAMES)), average=None, zero_division=0
    )
    computed_metrics = {
        "accuracy": float(accuracy_score(y_val, predictions_this_process)),
        "balanced_accuracy": float(balanced_accuracy_score(y_val, predictions_this_process)),
        "macro_f1": float(f1_score(y_val, predictions_this_process, average="macro")),
        "high_class_recall": float(per_class_recall[HIGH_INDEX]),
    }
    documented = json.loads(TUNING_RESULTS_PATH.read_text(encoding="utf-8"))
    documented_metrics = documented["models"]["random_forest"]["tuned_validation"]

    print("\n--- Verification 1: metrics vs reports/tuning_results_3class.json ---")
    all_match = True
    for key in ("accuracy", "balanced_accuracy", "macro_f1", "high_class_recall"):
        match = computed_metrics[key] == documented_metrics[key]
        all_match = all_match and match
        print(f"  {key}: computed={computed_metrics[key]!r} documented={documented_metrics[key]!r} match={match}")
    print(f"  ALL METRICS MATCH EXACTLY: {all_match}")

    # --- Verification 2: reload in a fresh subprocess, compare predictions via np.array_equal ---
    print("\n--- Verification 2: predictions from a fresh Python subprocess ---")
    with tempfile.TemporaryDirectory() as tmp_dir:
        reload_script_path = Path(tmp_dir) / "_reload_and_predict.py"
        out_path = Path(tmp_dir) / "predictions.npy"
        reload_script_path.write_text(_RELOAD_SCRIPT, encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(reload_script_path), str(MODEL_PATH), str(SPLITS_PATH), str(out_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        predictions_subprocess = np.load(out_path)

    predictions_match = np.array_equal(predictions_this_process, predictions_subprocess)
    print(f"  lengths: {len(predictions_this_process)} (this process) vs {len(predictions_subprocess)} (subprocess)")
    print(f"  first 10 (this process): {predictions_this_process[:10]}")
    print(f"  first 10 (subprocess):   {predictions_subprocess[:10]}")
    print(f"  np.array_equal(this_process_predictions, subprocess_predictions): {predictions_match}")

    print(f"\nOverall verification passed: {all_match and predictions_match}")


if __name__ == "__main__":
    main()
