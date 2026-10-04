"""Phase 12 (Advanced Models), 3-class Anxiety Level target.

Per docs/master_project_instructions.md PHASE 12: only after establishing
strong baselines (done: Phases 11/13 for this target), evaluate a more
advanced model class ("neural networks... depending on the data") without
using deep learning merely because it is more sophisticated. This dataset
is small tabular data (7700 train rows, 34 preprocessed features) with no
image/text/sequence structure, so the applicable "advanced" candidate is a
shallow MLP (sklearn's MLPClassifier), not a deep architecture or
transformer, which would be inappropriate for this data shape. Selection
should balance: performance + calibration + interpretability + robustness +
computational cost + clinical usability, not accuracy alone.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score
from sklearn.model_selection import RandomizedSearchCV
from sklearn.neural_network import MLPClassifier

import warnings

SEED = 42
CV_FOLDS = 5
N_ITERATIONS = 20
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
TUNING_RESULTS_PATH = ROOT / "reports" / "tuning_results_3class.json"
RESULTS_PATH = ROOT / "reports" / "advanced_models_3class.json"

CLASS_NAMES = ["Low", "Medium", "High"]
HIGH_INDEX = CLASS_NAMES.index("High")


def evaluate(estimator: object, x_val: np.ndarray, y_val: np.ndarray) -> dict[str, float]:
    predictions = estimator.predict(x_val)
    per_class_recall = recall_score(
        y_val, predictions, labels=np.arange(len(CLASS_NAMES)), average=None, zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(y_val, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_val, predictions)),
        "macro_f1": float(f1_score(y_val, predictions, average="macro")),
        "high_class_recall": float(per_class_recall[HIGH_INDEX]),
    }


def tune_mlp(x_train: np.ndarray, y_train: np.ndarray) -> RandomizedSearchCV:
    estimator = MLPClassifier(
        max_iter=500,
        early_stopping=True,
        n_iter_no_change=15,
        random_state=SEED,
    )
    parameter_distributions = {
        "hidden_layer_sizes": [(32,), (64,), (32, 16), (64, 32), (100,)],
        "activation": ["relu", "tanh"],
        "alpha": [0.0001, 0.001, 0.01, 0.1],
        "learning_rate_init": [0.0005, 0.001, 0.01],
    }
    search = RandomizedSearchCV(
        estimator=estimator,
        param_distributions=parameter_distributions,
        n_iter=N_ITERATIONS,
        scoring="balanced_accuracy",
        cv=CV_FOLDS,
        random_state=SEED,
        n_jobs=-1,
        refit=True,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=ConvergenceWarning)
        search.fit(x_train, y_train)
    return search


def main() -> None:
    splits = np.load(SPLITS_PATH)
    x_train, y_train = splits["X_train"], splits["y_train"]
    x_val, y_val = splits["X_val"], splits["y_val"]

    tuning_results = json.loads(TUNING_RESULTS_PATH.read_text(encoding="utf-8"))
    rf_tuned = tuning_results["models"]["random_forest"]["tuned_validation"]
    xgb_tuned = tuning_results["models"]["xgboost"]["tuned_validation"]

    print("Tuning MLPClassifier (shallow neural network)...")
    start = time.time()
    search = tune_mlp(x_train, y_train)
    elapsed = time.time() - start

    mlp_metrics = evaluate(search.best_estimator_, x_val, y_val)

    print(f"\nTuning time: {elapsed:.1f}s")
    print(f"Best CV balanced_accuracy: {search.best_score_:.6f}")
    print(f"Best params: {search.best_params_}")
    print(f"n_iter_ actually used (early stopping): {search.best_estimator_.n_iter_}")

    print("\n--- Comparison, tuned validation metrics ---")
    print(f"{'model':<20}{'accuracy':>12}{'balanced_acc':>14}{'macro_f1':>12}{'high_recall':>14}")
    print(f"{'random_forest':<20}{rf_tuned['accuracy']:>12.4f}{rf_tuned['balanced_accuracy']:>14.4f}"
          f"{rf_tuned['macro_f1']:>12.4f}{rf_tuned['high_class_recall']:>14.4f}")
    print(f"{'xgboost':<20}{xgb_tuned['accuracy']:>12.4f}{xgb_tuned['balanced_accuracy']:>14.4f}"
          f"{xgb_tuned['macro_f1']:>12.4f}{xgb_tuned['high_class_recall']:>14.4f}")
    print(f"{'mlp (neural net)':<20}{mlp_metrics['accuracy']:>12.4f}{mlp_metrics['balanced_accuracy']:>14.4f}"
          f"{mlp_metrics['macro_f1']:>12.4f}{mlp_metrics['high_class_recall']:>14.4f}")

    results = {
        "seed": SEED,
        "cv_folds": CV_FOLDS,
        "n_iter": N_ITERATIONS,
        "cv_scoring": "balanced_accuracy",
        "search_training_split": "train",
        "evaluation_split": "validation",
        "class_names": CLASS_NAMES,
        "tuning_time_seconds": elapsed,
        "mlp": {
            "best_cv_score": float(search.best_score_),
            "best_params": {k: (list(v) if isinstance(v, tuple) else v) for k, v in search.best_params_.items()},
            "actual_training_iterations": int(search.best_estimator_.n_iter_),
            "tuned_validation": mlp_metrics,
        },
        "comparison": {
            "random_forest_tuned": rf_tuned,
            "xgboost_tuned": xgb_tuned,
            "mlp_tuned": mlp_metrics,
        },
    }
    RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved results to {RESULTS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
