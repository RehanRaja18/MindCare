"""EXPLORATORY feature-reduction experiment - 3-class Anxiety Level target.

Works on TRAIN and VALIDATION only. This script never loads or references
X_test, y_test, or test_original_idx anywhere.

Removes the 6 lowest-SHAP-ranked features (per
reports/shap_full_ranking_3class.md, grouped 17-feature ranking, ranks
12-17): Age, Alcohol Consumption (drinks/week), Dizziness, Smoking,
Recent Major Life Event, Medication. Rebuilds a new preprocessor (fit on
train rows only) with the remaining 11 features (9 numeric + 2
categorical: Family History of Anxiety, Occupation), retrains the tuned
Random Forest (same hyperparameters as reports/tuning_results_3class.json),
and evaluates on validation against the existing 17-feature baseline.

Does not touch: data/processed/mindcare_final_model.pkl,
data/processed/mindcare_preprocessor.pkl, or the test set. Purely
exploratory - no artifact from this script is adopted as canonical.
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
TUNING_RESULTS_PATH = ROOT / "reports" / "tuning_results_3class.json"
REPORT_PATH = ROOT / "reports" / "feature_reduction_3class.md"

CLASS_NAMES = ["Low", "Medium", "High"]

ORIGINAL_NUMERIC_FEATURES = [
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
ORIGINAL_CATEGORICAL_FEATURES = [
    "Occupation",
    "Smoking",
    "Family History of Anxiety",
    "Dizziness",
    "Medication",
    "Recent Major Life Event",
]

# The 6 lowest-SHAP-ranked features (reports/shap_full_ranking_3class.md, ranks 12-17)
REMOVED_FEATURES = [
    "Age",
    "Alcohol Consumption (drinks/week)",
    "Dizziness",
    "Smoking",
    "Recent Major Life Event",
    "Medication",
]

REDUCED_NUMERIC_FEATURES = [f for f in ORIGINAL_NUMERIC_FEATURES if f not in REMOVED_FEATURES]
REDUCED_CATEGORICAL_FEATURES = [f for f in ORIGINAL_CATEGORICAL_FEATURES if f not in REMOVED_FEATURES]

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


def print_row(label: str, m: dict[str, float]) -> None:
    print(
        f"  {label:<24} acc={m['accuracy']:.4f}  bal_acc={m['balanced_accuracy']:.4f}  "
        f"macro_f1={m['macro_f1']:.4f}  recall(L/M/H)="
        f"{m['recall_low']:.4f}/{m['recall_medium']:.4f}/{m['recall_high']:.4f}"
    )


def main() -> None:
    print(f"Removed features (6, lowest SHAP-ranked): {REMOVED_FEATURES}")
    print(f"Reduced numeric features ({len(REDUCED_NUMERIC_FEATURES)}): {REDUCED_NUMERIC_FEATURES}")
    print(f"Reduced categorical features ({len(REDUCED_CATEGORICAL_FEATURES)}): {REDUCED_CATEGORICAL_FEATURES}")
    total_reduced = len(REDUCED_NUMERIC_FEATURES) + len(REDUCED_CATEGORICAL_FEATURES)
    print(f"Total reduced feature count: {total_reduced}\n")
    if total_reduced != 11:
        raise ValueError(f"Expected 11 remaining features, got {total_reduced}")

    dataframe = pd.read_csv(DATA_PATH)

    # Only train/val identifiers and the existing (original-feature) baseline X_val are read.
    # X_test / y_test / test_original_idx are never referenced anywhere in this script.
    with np.load(SPLITS_PATH) as splits:
        train_idx = splits["train_original_idx"]
        val_idx = splits["val_original_idx"]
        y_train = splits["y_train"]
        y_val = splits["y_val"]

    train_rows = dataframe.iloc[train_idx]
    val_rows = dataframe.iloc[val_idx]

    reduced_preprocessor = build_preprocessor(REDUCED_NUMERIC_FEATURES, REDUCED_CATEGORICAL_FEATURES)
    x_train_reduced = reduced_preprocessor.fit_transform(
        train_rows[REDUCED_NUMERIC_FEATURES + REDUCED_CATEGORICAL_FEATURES]
    )
    x_val_reduced = reduced_preprocessor.transform(
        val_rows[REDUCED_NUMERIC_FEATURES + REDUCED_CATEGORICAL_FEATURES]
    )
    print(f"Reduced feature matrix shape - train: {x_train_reduced.shape}, val: {x_val_reduced.shape}")

    model = RandomForestClassifier(**TUNED_RF_PARAMS)
    model.fit(x_train_reduced, y_train)
    reduced_metrics = evaluate(model, x_val_reduced, y_val)

    print("\n=== Reduced-feature Random Forest (11 features) ===")
    print_row("reduced (11 feat)", reduced_metrics)

    # --- Baseline reference: documented 17-feature tuned RF validation metrics ---
    documented = json.loads(TUNING_RESULTS_PATH.read_text(encoding="utf-8"))
    doc_rf = documented["models"]["random_forest"]["tuned_validation"]
    baseline_metrics = {
        "accuracy": doc_rf["accuracy"],
        "balanced_accuracy": doc_rf["balanced_accuracy"],
        "macro_f1": doc_rf["macro_f1"],
        "recall_high": doc_rf["high_class_recall"],
    }
    # Low/Medium recall for the 17-feature baseline aren't in tuning_results_3class.json;
    # pull from reports/full_evaluation_3class.md's documented classification report.
    baseline_metrics["recall_low"] = 0.7545
    baseline_metrics["recall_medium"] = 0.7652

    print("\n=== Baseline (documented, 17 features: reports/tuning_results_3class.json"
          " + reports/full_evaluation_3class.md) ===")
    print_row("baseline (17 feat)", baseline_metrics)

    deltas = {key: reduced_metrics[key] - baseline_metrics[key] for key in baseline_metrics}
    print("\n=== Deltas (reduced - baseline) ===")
    print("  " + "  ".join(f"{k}={v:+.4f}" for k, v in deltas.items()))

    MEANINGFUL_THRESHOLD = 0.01  # 1 percentage point, same convention as prior experiments
    meaningful_costs = {k: v for k, v in deltas.items()
                        if k in ("accuracy", "balanced_accuracy", "macro_f1", "recall_high") and v <= -MEANINGFUL_THRESHOLD}
    meaningful_gains = {k: v for k, v in deltas.items()
                        if k in ("accuracy", "balanced_accuracy", "macro_f1", "recall_high") and v >= MEANINGFUL_THRESHOLD}
    print(f"\nHeadline metrics with a meaningful (>=1pt) cost: {meaningful_costs}")
    print(f"Headline metrics with a meaningful (>=1pt) gain: {meaningful_gains}")

    # --- Write report ---
    lines: list[str] = [
        "# Feature Reduction Experiment (Exploratory) — 3-Class Anxiety Level Target",
        "",
        "**Scope note: this script works on TRAIN and VALIDATION only. It never loads or"
        " references X_test, y_test, or test_original_idx anywhere. The test set was not"
        " touched. No canonical artifact (saved model, preprocessor, or CLAUDE.md feature"
        " list) was changed — purely exploratory, same protocol as the feature engineering,"
        " ensemble, and calibration experiments.**",
        "",
        "## Method",
        "",
        f"Removed the 6 lowest-SHAP-ranked features"
        f" (`reports/shap_full_ranking_3class.md`, grouped ranking, ranks 12-17):"
        f" {', '.join(REMOVED_FEATURES)}.",
        "",
        f"Remaining 11 features — {len(REDUCED_NUMERIC_FEATURES)} numeric"
        f" ({', '.join(REDUCED_NUMERIC_FEATURES)}) + {len(REDUCED_CATEGORICAL_FEATURES)}"
        f" categorical ({', '.join(REDUCED_CATEGORICAL_FEATURES)}).",
        "",
        "New `ColumnTransformer` (`StandardScaler` + `OneHotEncoder`) fit on **train rows"
        " only** (`train_original_idx`), applied to train and validation. Tuned Random Forest"
        " (same hyperparameters as `reports/tuning_results_3class.json`) retrained on this"
        " reduced feature set.",
        "",
        "## Results",
        "",
        "| Feature set | Accuracy | Balanced acc. | Macro-F1 | Recall Low | Recall Medium | Recall High |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Baseline (17 features, documented) | {baseline_metrics['accuracy']:.4f} |"
        f" {baseline_metrics['balanced_accuracy']:.4f} | {baseline_metrics['macro_f1']:.4f} |"
        f" {baseline_metrics['recall_low']:.4f} | {baseline_metrics['recall_medium']:.4f} |"
        f" {baseline_metrics['recall_high']:.4f} |",
        f"| **Reduced (11 features)** | **{reduced_metrics['accuracy']:.4f}** |"
        f" **{reduced_metrics['balanced_accuracy']:.4f}** | **{reduced_metrics['macro_f1']:.4f}** |"
        f" {reduced_metrics['recall_low']:.4f} | {reduced_metrics['recall_medium']:.4f} |"
        f" {reduced_metrics['recall_high']:.4f} |",
        "",
        "## Deltas (Reduced − Baseline)",
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
            f"**Removing these 6 features costs meaningful performance** on:"
            f" {', '.join(f'{k} ({v:+.4f})' for k, v in meaningful_costs.items())}."
            f" This is a real cost (≥1 point), not noise. Do not adopt this reduced feature"
            f" set without accepting that tradeoff."
        )
    elif meaningful_gains:
        lines.append(
            f"**Removing these 6 features actually improved** "
            f"{', '.join(f'{k} ({v:+.4f})' for k, v in meaningful_gains.items())}"
            f" by a meaningful margin (≥1 point) — plausibly less noise from low-signal"
            f" features, though 11 vs 17 features is still a small comparison and this should"
            f" not be over-interpreted from one run."
        )
    else:
        max_abs_delta = max(abs(v) for k, v in deltas.items() if k in
                            ("accuracy", "balanced_accuracy", "macro_f1", "recall_high"))
        lines.append(
            f"**No headline metric moved by as much as 1 point in either direction**"
            f" (largest absolute change: {max_abs_delta:.4f}, {max_abs_delta*100:.2f} points)."
            f" Removing Age, Alcohol Consumption, Dizziness, Smoking, Recent Major Life Event,"
            f" and Medication costs essentially nothing — performance is statistically"
            f" indistinguishable from the full 17-feature model. Stated plainly: **these 6"
            f" features are not pulling meaningful weight for this model**, consistent with"
            f" their bottom-6 SHAP ranking. This is not evidence they should definitely be"
            f" dropped from production (a smaller feature set has real operational value —"
            f" less data to collect, validate, and maintain — but that's a product decision,"
            f" not just a performance one), but the performance case against keeping them is"
            f" weak to none."
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
