"""EXPLORATORY feature-reduction experiment - does dropping Caffeine Intake
too (on top of the already-adopted 11-feature set) cost meaningful
performance? 3-class Anxiety Level target.

Works on TRAIN and VALIDATION only. Never loads or references X_test,
y_test, or test_original_idx - the 3-class test set is fully spent (see
CLAUDE.md, "TEST SET USED" entries) and must not be touched again.

Motivation: after adopting the 11-feature model (dropping the bottom-6
SHAP-ranked features - reports/feature_reduction_3class.md), a further
product-UX question was raised: could the onboarding form be simplified
even more by also dropping Caffeine Intake? Caffeine ranks 4th by SHAP
importance in the full 17-feature ranking (reports/shap_full_ranking_3class.md)
- a real signal, not a low-signal feature like the bottom 6 - so this is a
genuinely separate question from the original reduction, tested explicitly
rather than assumed.

Does not touch: data/processed/mindcare_final_model_11feature.pkl, the
11-feature preprocessor, or the test set. Purely exploratory.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score
from sklearn.preprocessing import OneHotEncoder, StandardScaler


SEED = 42
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
REPORT_PATH = ROOT / "reports" / "feature_reduction_caffeine_3class.md"

CLASS_NAMES = ["Low", "Medium", "High"]

# The currently-adopted 11 features (reports/feature_reduction_3class.md)
CURRENT_NUMERIC_FEATURES = [
    "Sleep Hours",
    "Physical Activity (hrs/week)",
    "Caffeine Intake (mg/day)",
    "Stress Level (1-10)",
    "Heart Rate (bpm)",
    "Breathing Rate (breaths/min)",
    "Sweating Level (1-5)",
    "Therapy Sessions (per month)",
    "Diet Quality (1-10)",
]
CURRENT_CATEGORICAL_FEATURES = ["Occupation", "Family History of Anxiety"]

# Candidate further reduction: drop Caffeine Intake too
REDUCED_NUMERIC_FEATURES = [f for f in CURRENT_NUMERIC_FEATURES if f != "Caffeine Intake (mg/day)"]

# Documented baseline: the CURRENT 11-feature model's own validation numbers
# (reports/feature_reduction_3class.md, reproduced exactly by
# src/models/adopt_11feature_model.py's verification step)
BASELINE_11FEATURE = {
    "accuracy": 0.7770,
    "balanced_accuracy": 0.8084,
    "macro_f1": 0.8204,
    "recall_low": 0.7545,
    "recall_medium": 0.7737,
    "recall_high": 0.8970,
}

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


def build_preprocessor(numeric_features: list[str], categorical_features: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ]
    )


def evaluate(model, x_val: np.ndarray, y_val: np.ndarray) -> dict[str, float]:
    predictions = model.predict(x_val)
    per_class_recall = recall_score(
        y_val, predictions, labels=np.arange(len(CLASS_NAMES)), average=None, zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(y_val, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_val, predictions)),
        "macro_f1": float(f1_score(y_val, predictions, average="macro")),
        "recall_low": float(per_class_recall[0]),
        "recall_medium": float(per_class_recall[1]),
        "recall_high": float(per_class_recall[2]),
    }


def main() -> None:
    print(f"Current 11-feature set: {CURRENT_NUMERIC_FEATURES + CURRENT_CATEGORICAL_FEATURES}")
    print(f"Candidate reduction (drop Caffeine Intake): {REDUCED_NUMERIC_FEATURES + CURRENT_CATEGORICAL_FEATURES}")
    print(f"Resulting feature count: {len(REDUCED_NUMERIC_FEATURES) + len(CURRENT_CATEGORICAL_FEATURES)}\n")

    dataframe = pd.read_csv(DATA_PATH)

    with np.load(SPLITS_PATH) as splits:
        train_idx = splits["train_original_idx"]
        val_idx = splits["val_original_idx"]
        y_train = splits["y_train"]
        y_val = splits["y_val"]

    train_rows = dataframe.iloc[train_idx]
    val_rows = dataframe.iloc[val_idx]

    preprocessor = build_preprocessor(REDUCED_NUMERIC_FEATURES, CURRENT_CATEGORICAL_FEATURES)
    x_train = preprocessor.fit_transform(train_rows[REDUCED_NUMERIC_FEATURES + CURRENT_CATEGORICAL_FEATURES])
    x_val = preprocessor.transform(val_rows[REDUCED_NUMERIC_FEATURES + CURRENT_CATEGORICAL_FEATURES])
    print(f"Feature matrix shape - train: {x_train.shape}, val: {x_val.shape}")

    model = RandomForestClassifier(**TUNED_RF_PARAMS)
    model.fit(x_train, y_train)
    metrics = evaluate(model, x_val, y_val)

    print("\n=== Without Caffeine Intake (10 features) ===")
    print(f"  acc={metrics['accuracy']:.4f}  bal_acc={metrics['balanced_accuracy']:.4f}  "
          f"macro_f1={metrics['macro_f1']:.4f}  "
          f"recall(L/M/H)={metrics['recall_low']:.4f}/{metrics['recall_medium']:.4f}/{metrics['recall_high']:.4f}")

    print("\n=== Baseline: current 11-feature model (documented) ===")
    print(f"  acc={BASELINE_11FEATURE['accuracy']:.4f}  bal_acc={BASELINE_11FEATURE['balanced_accuracy']:.4f}  "
          f"macro_f1={BASELINE_11FEATURE['macro_f1']:.4f}  "
          f"recall(L/M/H)={BASELINE_11FEATURE['recall_low']:.4f}/{BASELINE_11FEATURE['recall_medium']:.4f}/{BASELINE_11FEATURE['recall_high']:.4f}")

    deltas = {key: metrics[key] - BASELINE_11FEATURE[key] for key in BASELINE_11FEATURE}
    print("\n=== Deltas (without-caffeine minus 11-feature baseline) ===")
    print("  " + "  ".join(f"{k}={v:+.4f}" for k, v in deltas.items()))

    MEANINGFUL_THRESHOLD = 0.01
    meaningful_costs = {k: v for k, v in deltas.items()
                        if k in ("accuracy", "balanced_accuracy", "macro_f1", "recall_high") and v <= -MEANINGFUL_THRESHOLD}
    print(f"\nHeadline metrics with a meaningful (>=1pt) cost: {meaningful_costs}")

    # --- Write report ---
    lines: list[str] = [
        "# Feature Reduction Experiment: Caffeine Intake Removal (Exploratory) — 3-Class Target",
        "",
        "**Scope note: this script works on TRAIN and VALIDATION only. It never loads or"
        " references X_test, y_test, or test_original_idx anywhere — the 3-class test set is"
        " fully spent (see `CLAUDE.md`, \"TEST SET USED\" entries) and must not be touched"
        " again. No canonical artifact was changed — purely exploratory.**",
        "",
        "## Motivation",
        "",
        "After adopting the 11-feature model (dropping the bottom-6 SHAP-ranked features —"
        " `reports/feature_reduction_3class.md`), a further product-UX question was raised:"
        " could the onboarding form be simplified even more by also dropping Caffeine Intake?"
        " Caffeine ranks **4th** by SHAP importance in the full ranking"
        " (`reports/shap_full_ranking_3class.md`) — a real signal, unlike the bottom-6 features"
        " that were actually dropped — so this is a genuinely separate, higher-stakes question,"
        " tested explicitly rather than assumed.",
        "",
        "## Method",
        "",
        f"Starting from the currently-adopted 11-feature set"
        f" ({', '.join(CURRENT_NUMERIC_FEATURES + CURRENT_CATEGORICAL_FEATURES)}), additionally"
        f" removed `Caffeine Intake (mg/day)`, leaving"
        f" {len(REDUCED_NUMERIC_FEATURES) + len(CURRENT_CATEGORICAL_FEATURES)} features"
        f" ({len(REDUCED_NUMERIC_FEATURES)} numeric + {len(CURRENT_CATEGORICAL_FEATURES)}"
        f" categorical). New `ColumnTransformer` fit on train rows only; tuned Random Forest"
        f" (same hyperparameters as `reports/tuning_results_3class.json`) retrained from scratch.",
        "",
        "## Results",
        "",
        "| Feature set | Accuracy | Balanced acc. | Macro-F1 | Recall Low | Recall Medium | Recall High |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Current 11-feature (baseline) | {BASELINE_11FEATURE['accuracy']:.4f} |"
        f" {BASELINE_11FEATURE['balanced_accuracy']:.4f} | {BASELINE_11FEATURE['macro_f1']:.4f} |"
        f" {BASELINE_11FEATURE['recall_low']:.4f} | {BASELINE_11FEATURE['recall_medium']:.4f} |"
        f" {BASELINE_11FEATURE['recall_high']:.4f} |",
        f"| **Without Caffeine Intake (10 features)** | **{metrics['accuracy']:.4f}** |"
        f" **{metrics['balanced_accuracy']:.4f}** | **{metrics['macro_f1']:.4f}** |"
        f" {metrics['recall_low']:.4f} | {metrics['recall_medium']:.4f} |"
        f" {metrics['recall_high']:.4f} |",
        "",
        "## Deltas (Without Caffeine − 11-Feature Baseline)",
        "",
        "| Metric | Δ |",
        "|---|---:|",
    ]
    for key, label in [
        ("accuracy", "Accuracy"), ("balanced_accuracy", "Balanced accuracy"),
        ("macro_f1", "Macro-F1"), ("recall_low", "Recall Low"),
        ("recall_medium", "Recall Medium"), ("recall_high", "Recall High"),
    ]:
        lines.append(f"| {label} | {deltas[key]:+.4f} |")

    lines.extend(["", "## Honest Verdict", ""])
    if meaningful_costs:
        lines.append(
            f"**Dropping Caffeine Intake costs meaningful performance**"
            f" ({', '.join(f'{k} {v:+.4f}' for k, v in meaningful_costs.items())}, ≥1 point)."
            f" Unlike the bottom-6 features (near-zero cost when dropped), Caffeine Intake"
            f" carries real, measurable signal, consistent with its 4th-place SHAP rank."
            f" **Decision: KEEP Caffeine Intake as a model input.** The onboarding-simplification"
            f" goal is instead served by changing *how* it's collected — four everyday serving"
            f" counts (cups of coffee/tea, energy drinks, cans of soda) converted server-side to"
            f" the mg/day figure the model needs (`src/api/main.py`,"
            f" `estimate_caffeine_mg()`) — rather than dropping the feature outright."
        )
    else:
        lines.append(
            f"No headline metric moved by as much as 1 point (largest change:"
            f" {max(abs(v) for k, v in deltas.items() if k in ('accuracy', 'balanced_accuracy', 'macro_f1', 'recall_high')):.4f})."
            f" Contrary to the SHAP ranking, dropping Caffeine Intake did not cost meaningful"
            f" performance in this run either."
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not"
            " clinical validation. This was an exploratory experiment only — no canonical"
            " artifact (preprocessor, saved model, or CLAUDE.md feature list) was changed as a"
            " result. The test set was never touched by this script.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
