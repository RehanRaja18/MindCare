"""Re-tune Random Forest and XGBoost on the 12-feature data (3-class Anxiety
Level target) under one identical procedure, as step 1 of the RF-vs-XGBoost
comparison (reports/model_comparison_12feature.md).

Why re-tune: both models' existing hyperparameters (reports/
tuning_results_3class.json) were tuned on the old 17-feature data, and the
search was not symmetric - Random Forest could choose class_weight="balanced"
but XGBoost had no class-balancing option at all, on a target where High is
only ~10%. A fair rematch tunes both on the current 12 features with the same
budget and the same balancing freedom.

Procedure (mirrors tune_models_3class.py: RandomizedSearchCV, 5-fold CV on
the TRAINING split only, balanced_accuracy scoring, seed 42), with an equal
budget of 40 sampled configurations per model:
- Random Forest: 40 draws from the same search space as before, which
  includes class_weight in {None, "balanced"}.
- XGBoost: XGBClassifier has no class_weight parameter, so balancing is
  applied as sample weights: 20 draws unweighted + 20 draws with
  compute_sample_weight("balanced"), same search space as before. The better
  of the two (by CV score) is kept, and which one won is recorded.

The validation split is used only to report the winners' scores afterwards,
never to choose between configurations. The test set does not exist in the
12-feature splits file and is not used.

Writes reports/tuning_results_12feature.json. Saves no model artifacts -
src/evaluation/compare_models_12feature.py refits both candidates from the
saved parameters.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score
from sklearn.model_selection import RandomizedSearchCV
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier


SEED = 42
CV_FOLDS = 5
BUDGET_PER_MODEL = 40
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_12feature.npz"
RESULTS_PATH = ROOT / "reports" / "tuning_results_12feature.json"

CLASS_NAMES = ["Low", "Medium", "High"]
HIGH_INDEX = CLASS_NAMES.index("High")

RF_SPACE = {
    "n_estimators": [200, 300, 500],
    "max_depth": [None, 10, 20, 30],
    "min_samples_split": [2, 5, 10],
    "min_samples_leaf": [1, 2, 4],
    "max_features": ["sqrt", "log2", None],
    "class_weight": [None, "balanced"],
}
XGB_SPACE = {
    "n_estimators": [200, 300, 500],
    "max_depth": [3, 4, 6, 8],
    "learning_rate": [0.03, 0.05, 0.1, 0.2],
    "subsample": [0.8, 1.0],
    "colsample_bytree": [0.8, 1.0],
    "min_child_weight": [1, 3, 5],
    "gamma": [0, 0.1],
}


def validation_metrics(model: object, x_val: np.ndarray, y_val: np.ndarray) -> dict[str, float]:
    predictions = model.predict(x_val)
    return {
        "accuracy": float(accuracy_score(y_val, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_val, predictions)),
        "macro_f1": float(f1_score(y_val, predictions, average="macro")),
        "high_class_recall": float(
            recall_score(y_val, predictions, labels=[HIGH_INDEX], average=None)[0]
        ),
    }


def search(estimator: object, space: dict, n_iter: int) -> RandomizedSearchCV:
    return RandomizedSearchCV(
        estimator=estimator,
        param_distributions=space,
        n_iter=n_iter,
        scoring="balanced_accuracy",
        cv=CV_FOLDS,
        random_state=SEED,
        n_jobs=-1,
        refit=True,
    )


def main() -> None:
    with np.load(SPLITS_PATH) as splits:
        x_train, y_train = splits["X_train"], splits["y_train"]
        x_val, y_val = splits["X_val"], splits["y_val"]

    print(f"Random Forest: {BUDGET_PER_MODEL} configurations...")
    rf_search = search(RandomForestClassifier(random_state=SEED, n_jobs=1), RF_SPACE, BUDGET_PER_MODEL)
    rf_search.fit(x_train, y_train)

    xgb_searches = {}
    for weighting in ("none", "balanced"):
        print(f"XGBoost ({weighting} sample weights): {BUDGET_PER_MODEL // 2} configurations...")
        xgb = XGBClassifier(objective="multi:softprob", eval_metric="mlogloss", random_state=SEED, n_jobs=1)
        fit_kwargs = {"sample_weight": compute_sample_weight("balanced", y_train)} if weighting == "balanced" else {}
        xgb_search = search(xgb, XGB_SPACE, BUDGET_PER_MODEL // 2)
        xgb_search.fit(x_train, y_train, **fit_kwargs)
        xgb_searches[weighting] = xgb_search
        print(f"  best CV balanced accuracy: {xgb_search.best_score_:.6f}")
    xgb_weighting = max(xgb_searches, key=lambda w: xgb_searches[w].best_score_)

    results = {
        "seed": SEED,
        "cv_folds": CV_FOLDS,
        "budget_per_model": BUDGET_PER_MODEL,
        "cv_scoring": "balanced_accuracy",
        "search_training_split": "train (12-feature)",
        "validation_use": "reporting the winners only - never used to choose a configuration",
        "models": {
            "random_forest": {
                "best_cv_score": float(rf_search.best_score_),
                "best_cv_std": float(rf_search.cv_results_["std_test_score"][rf_search.best_index_]),
                "best_params": rf_search.best_params_,
                "validation": validation_metrics(rf_search.best_estimator_, x_val, y_val),
            },
            "xgboost": {
                "best_cv_score": float(xgb_searches[xgb_weighting].best_score_),
                "best_cv_std": float(
                    xgb_searches[xgb_weighting].cv_results_["std_test_score"][xgb_searches[xgb_weighting].best_index_]
                ),
                "best_params": xgb_searches[xgb_weighting].best_params_,
                "sample_weighting": xgb_weighting,
                "cv_score_by_weighting": {w: float(s.best_score_) for w, s in xgb_searches.items()},
                "validation": validation_metrics(xgb_searches[xgb_weighting].best_estimator_, x_val, y_val),
            },
        },
    }
    for name, entry in results["models"].items():
        print(f"\n{name}: CV {entry['best_cv_score']:.4f} +/- {entry['best_cv_std']:.4f}")
        print(f"  params: {entry['best_params']}" + (f"  (sample weighting: {entry['sample_weighting']})" if "sample_weighting" in entry else ""))
        print(f"  validation: {entry['validation']}")

    RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved {RESULTS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
