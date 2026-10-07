"""Train and evaluate baseline classifiers on the 3-class (Low/Medium/High)
Anxiety Level splits. Same model set, hyperparameters, and SEED as
train_baselines.py; adds per-class High recall given the ~10% High
class imbalance in this target.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    recall_score,
)
from xgboost import XGBClassifier


SEED = 42
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
RESULTS_PATH = ROOT / "reports" / "baseline_results_3class.json"
CLASS_NAMES = ["Low", "Medium", "High"]
HIGH_CLASS_INDEX = CLASS_NAMES.index("High")


def load_splits() -> dict[str, np.ndarray]:
    with np.load(SPLITS_PATH) as splits:
        return {name: splits[name] for name in splits.files}


def build_models() -> dict[str, object]:
    return {
        "majority_dummy": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": LogisticRegression(
            max_iter=2000,
            random_state=SEED,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            random_state=SEED,
            n_jobs=-1,
        ),
        "xgboost": XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=SEED,
            n_jobs=-1,
        ),
    }


def evaluate_model(model: object, x_train: np.ndarray, y_train: np.ndarray,
                   x_val: np.ndarray, y_val: np.ndarray,
                   labels: np.ndarray) -> dict[str, object]:
    model.fit(x_train, y_train)
    predictions = model.predict(x_val)
    matrix = confusion_matrix(y_val, predictions, labels=labels)
    per_class_recall = recall_score(y_val, predictions, labels=labels, average=None, zero_division=0)
    return {
        "accuracy": float(accuracy_score(y_val, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_val, predictions)),
        "macro_f1": float(f1_score(y_val, predictions, average="macro")),
        "confusion_matrix": matrix.tolist(),
        "per_class_recall": {
            name: float(per_class_recall[i]) for i, name in enumerate(CLASS_NAMES)
        },
        "high_class_recall": float(per_class_recall[HIGH_CLASS_INDEX]),
    }


def main() -> None:
    splits = load_splits()
    x_train, y_train = splits["X_train"], splits["y_train"]
    x_val, y_val = splits["X_val"], splits["y_val"]
    labels = np.unique(y_train)

    results: dict[str, object] = {
        "seed": SEED,
        "evaluation_split": "validation",
        "class_labels": labels.tolist(),
        "class_names": CLASS_NAMES,
        "models": {},
    }

    for name, model in build_models().items():
        metrics = evaluate_model(model, x_train, y_train, x_val, y_val, labels)
        results["models"][name] = metrics
        print(f"\n{name}")
        print(f"accuracy: {metrics['accuracy']:.6f}")
        print(f"balanced_accuracy: {metrics['balanced_accuracy']:.6f}")
        print(f"macro_f1: {metrics['macro_f1']:.6f}")
        print("confusion_matrix (rows=true, cols=predicted, order=Low/Medium/High):")
        print(np.asarray(metrics["confusion_matrix"]))
        print("per_class_recall:")
        for class_name in CLASS_NAMES:
            print(f"  {class_name}: {metrics['per_class_recall'][class_name]:.6f}")
        print(f"HIGH class recall: {metrics['high_class_recall']:.6f}")

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved results to {RESULTS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
