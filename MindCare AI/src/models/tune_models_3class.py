"""Tune Random Forest and XGBoost for the 3-class Anxiety Level target,
using training data only. Mirrors tune_models.py's search setup (same CV
folds, n_iter, seed, and balanced_accuracy scoring), since High is still a
minority class (~10%) in the 3-class target.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score
from sklearn.model_selection import RandomizedSearchCV
from xgboost import XGBClassifier


SEED = 42
CV_FOLDS = 5
N_ITERATIONS = 20
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
BASELINE_RESULTS_PATH = ROOT / "reports" / "baseline_results_3class.json"
RESULTS_PATH = ROOT / "reports" / "tuning_results_3class.json"

CLASS_NAMES = ["Low", "Medium", "High"]
HIGH_CLASS_INDEX = CLASS_NAMES.index("High")


def load_splits() -> dict[str, np.ndarray]:
    with np.load(SPLITS_PATH) as splits:
        return {name: splits[name] for name in splits.files}


def evaluate(estimator: object, x_val: np.ndarray, y_val: np.ndarray) -> dict[str, float]:
    predictions = estimator.predict(x_val)
    per_class_recall = recall_score(
        y_val, predictions, labels=np.arange(len(CLASS_NAMES)), average=None, zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(y_val, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_val, predictions)),
        "macro_f1": float(f1_score(y_val, predictions, average="macro")),
        "high_class_recall": float(per_class_recall[HIGH_CLASS_INDEX]),
    }


def tune_random_forest(
    x_train: np.ndarray, y_train: np.ndarray
) -> RandomizedSearchCV:
    estimator = RandomForestClassifier(random_state=SEED, n_jobs=1)
    parameter_distributions = {
        "n_estimators": [200, 300, 500],
        "max_depth": [None, 10, 20, 30],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
        "max_features": ["sqrt", "log2", None],
        "class_weight": [None, "balanced"],
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
    search.fit(x_train, y_train)
    return search


def tune_xgboost(x_train: np.ndarray, y_train: np.ndarray) -> RandomizedSearchCV:
    estimator = XGBClassifier(
        objective="multi:softprob",
        eval_metric="mlogloss",
        random_state=SEED,
        n_jobs=1,
    )
    parameter_distributions = {
        "n_estimators": [200, 300, 500],
        "max_depth": [3, 4, 6, 8],
        "learning_rate": [0.03, 0.05, 0.1, 0.2],
        "subsample": [0.8, 1.0],
        "colsample_bytree": [0.8, 1.0],
        "min_child_weight": [1, 3, 5],
        "gamma": [0, 0.1],
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
    search.fit(x_train, y_train)
    return search


def main() -> None:
    splits = load_splits()
    x_train, y_train = splits["X_train"], splits["y_train"]
    x_val, y_val = splits["X_val"], splits["y_val"]
    baseline = json.loads(BASELINE_RESULTS_PATH.read_text(encoding="utf-8"))

    searches = {
        "random_forest": tune_random_forest(x_train, y_train),
        "xgboost": tune_xgboost(x_train, y_train),
    }
    results: dict[str, object] = {
        "seed": SEED,
        "cv_folds": CV_FOLDS,
        "n_iter": N_ITERATIONS,
        "cv_scoring": "balanced_accuracy",
        "search_training_split": "train",
        "evaluation_split": "validation",
        "class_names": CLASS_NAMES,
        "models": {},
    }

    for name, search in searches.items():
        tuned_metrics = evaluate(search.best_estimator_, x_val, y_val)
        untuned_metrics = baseline["models"][name]
        untuned_summary = {
            "accuracy": untuned_metrics["accuracy"],
            "balanced_accuracy": untuned_metrics["balanced_accuracy"],
            "macro_f1": untuned_metrics["macro_f1"],
            "high_class_recall": untuned_metrics["high_class_recall"],
        }
        results["models"][name] = {
            "best_cv_score": float(search.best_score_),
            "best_params": search.best_params_,
            "untuned_validation": untuned_summary,
            "tuned_validation": tuned_metrics,
        }
        print(f"\n{name}")
        print(f"best_cv_balanced_accuracy: {search.best_score_:.6f}")
        print(f"best_params: {search.best_params_}")
        print(f"untuned_validation: {untuned_summary}")
        print(f"tuned_validation:   {tuned_metrics}")

    RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved results to {RESULTS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
