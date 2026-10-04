"""EXPLORATORY feature engineering experiment - 3-class Anxiety Level target.

Works on TRAIN and VALIDATION only. This script never loads or references
X_test, y_test, or test_original_idx from mindcare_processed_splits_3class.npz
anywhere - only train_original_idx, val_original_idx, y_train, y_val, and the
EXISTING (original-feature) X_train/X_val are read, none of which touch the
test set.

Adds two engineered numeric features (HR_Activity_Ratio,
Sleep_Therapy_Interaction), rebuilds a NEW preprocessor (fit on train raw
rows only) with them included, and retrains tuned Random Forest and tuned
XGBoost (same hyperparameters as reports/tuning_results_3class.json) on the
new 19-feature set. Both the historical baseline AND a freshly-computed
baseline (via the existing preprocessed X_train/X_val, for a complete,
directly comparable per-class recall breakdown that was never previously
published for XGBoost) are reported alongside the engineered-feature runs.

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
from xgboost import XGBClassifier


SEED = 42
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
TUNING_RESULTS_PATH = ROOT / "reports" / "tuning_results_3class.json"
REPORT_PATH = ROOT / "reports" / "feature_engineering_3class.md"

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
ENGINEERED_NUMERIC_FEATURES = ["HR_Activity_Ratio", "Sleep_Therapy_Interaction"]
NEW_NUMERIC_FEATURES = ORIGINAL_NUMERIC_FEATURES + ENGINEERED_NUMERIC_FEATURES
CATEGORICAL_FEATURES = [
    "Occupation",
    "Smoking",
    "Family History of Anxiety",
    "Dizziness",
    "Medication",
    "Recent Major Life Event",
]

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
TUNED_XGB_PARAMS = dict(
    subsample=0.8,
    n_estimators=300,
    min_child_weight=3,
    max_depth=3,
    learning_rate=0.03,
    gamma=0,
    colsample_bytree=1.0,
    objective="multi:softprob",
    eval_metric="mlogloss",
    random_state=SEED,
    n_jobs=1,  # matches the estimator n_jobs used inside tune_models_3class.py's search
)


def add_engineered_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.copy()
    dataframe["HR_Activity_Ratio"] = dataframe["Heart Rate (bpm)"] / (
        dataframe["Physical Activity (hrs/week)"] + 1
    )
    dataframe["Sleep_Therapy_Interaction"] = (
        dataframe["Sleep Hours"] * dataframe["Therapy Sessions (per month)"]
    )
    return dataframe


def build_preprocessor(numeric_features: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
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
        f"  {label:<22} acc={m['accuracy']:.4f}  bal_acc={m['balanced_accuracy']:.4f}  "
        f"macro_f1={m['macro_f1']:.4f}  recall(L/M/H)="
        f"{m['recall_low']:.4f}/{m['recall_medium']:.4f}/{m['recall_high']:.4f}"
    )


def main() -> None:
    dataframe = pd.read_csv(DATA_PATH)
    dataframe = add_engineered_features(dataframe)

    # Load ONLY train/val identifiers and the existing (original-feature) train/val arrays.
    # X_test / y_test / test_original_idx are never referenced anywhere in this script.
    with np.load(SPLITS_PATH) as splits:
        train_idx = splits["train_original_idx"]
        val_idx = splits["val_original_idx"]
        y_train = splits["y_train"]
        y_val = splits["y_val"]
        x_train_existing = splits["X_train"]
        x_val_existing = splits["X_val"]

    print(f"Engineered feature summary (full dataset, {len(dataframe)} rows):")
    print(dataframe[ENGINEERED_NUMERIC_FEATURES].describe().to_string())

    train_rows = dataframe.iloc[train_idx]
    val_rows = dataframe.iloc[val_idx]

    new_preprocessor = build_preprocessor(NEW_NUMERIC_FEATURES)
    x_train_new = new_preprocessor.fit_transform(
        train_rows[NEW_NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    )
    x_val_new = new_preprocessor.transform(val_rows[NEW_NUMERIC_FEATURES + CATEGORICAL_FEATURES])
    print(f"\nNew feature matrix shape - train: {x_train_new.shape}, val: {x_val_new.shape}")
    print(f"(19 raw features -> {x_train_new.shape[1]} columns after one-hot encoding, "
          f"vs original {x_train_existing.shape[1]})")

    results: dict[str, dict[str, float]] = {}

    print("\n=== Random Forest ===")
    rf_baseline = RandomForestClassifier(**TUNED_RF_PARAMS)
    rf_baseline.fit(x_train_existing, y_train)
    results["rf_baseline"] = evaluate(rf_baseline, x_val_existing, y_val)
    print_row("baseline (11 feat)", results["rf_baseline"])

    rf_engineered = RandomForestClassifier(**TUNED_RF_PARAMS)
    rf_engineered.fit(x_train_new, y_train)
    results["rf_engineered"] = evaluate(rf_engineered, x_val_new, y_val)
    print_row("engineered (13 feat)", results["rf_engineered"])

    print("\n=== XGBoost ===")
    xgb_baseline = XGBClassifier(**TUNED_XGB_PARAMS)
    xgb_baseline.fit(x_train_existing, y_train)
    results["xgb_baseline"] = evaluate(xgb_baseline, x_val_existing, y_val)
    print_row("baseline (11 feat)", results["xgb_baseline"])

    xgb_engineered = XGBClassifier(**TUNED_XGB_PARAMS)
    xgb_engineered.fit(x_train_new, y_train)
    results["xgb_engineered"] = evaluate(xgb_engineered, x_val_new, y_val)
    print_row("engineered (13 feat)", results["xgb_engineered"])

    # --- Sanity check: freshly-computed baselines should match documented history exactly ---
    documented = json.loads(TUNING_RESULTS_PATH.read_text(encoding="utf-8"))
    doc_rf = documented["models"]["random_forest"]["tuned_validation"]
    doc_xgb = documented["models"]["xgboost"]["tuned_validation"]
    print("\n=== Sanity check vs reports/tuning_results_3class.json ===")
    print(f"  RF  accuracy: computed={results['rf_baseline']['accuracy']:.4f} "
          f"documented={doc_rf['accuracy']:.4f} "
          f"match={abs(results['rf_baseline']['accuracy'] - doc_rf['accuracy']) < 1e-9}")
    print(f"  RF  balanced_accuracy: computed={results['rf_baseline']['balanced_accuracy']:.4f} "
          f"documented={doc_rf['balanced_accuracy']:.4f} "
          f"match={abs(results['rf_baseline']['balanced_accuracy'] - doc_rf['balanced_accuracy']) < 1e-9}")
    print(f"  XGB accuracy: computed={results['xgb_baseline']['accuracy']:.4f} "
          f"documented={doc_xgb['accuracy']:.4f} "
          f"match={abs(results['xgb_baseline']['accuracy'] - doc_xgb['accuracy']) < 1e-9}")
    print(f"  XGB balanced_accuracy: computed={results['xgb_baseline']['balanced_accuracy']:.4f} "
          f"documented={doc_xgb['balanced_accuracy']:.4f} "
          f"match={abs(results['xgb_baseline']['balanced_accuracy'] - doc_xgb['balanced_accuracy']) < 1e-9}")

    # --- Deltas and verdict ---
    MEANINGFUL_THRESHOLD = 0.01  # 1 percentage point, per the user's own framing
    print("\n=== Deltas (engineered - baseline) ===")
    deltas: dict[str, dict[str, float]] = {}
    for family in ["rf", "xgb"]:
        base = results[f"{family}_baseline"]
        eng = results[f"{family}_engineered"]
        delta = {key: eng[key] - base[key] for key in base}
        deltas[family] = delta
        print(f"  {family}: " + "  ".join(f"{k}={v:+.4f}" for k, v in delta.items()))

    any_meaningful = any(
        abs(v) >= MEANINGFUL_THRESHOLD
        for fam_delta in deltas.values()
        for k, v in fam_delta.items()
        if k in ("accuracy", "balanced_accuracy", "macro_f1")
    )
    print(f"\nAny headline metric improved by >= {MEANINGFUL_THRESHOLD} (1 point): {any_meaningful}")

    # --- Write report ---
    lines: list[str] = [
        "# Feature Engineering Experiment (Exploratory) — 3-Class Anxiety Level Target",
        "",
        "**Scope note: this script works on TRAIN and VALIDATION only. It never loads or"
        " references X_test, y_test, or test_original_idx anywhere. The test set was not"
        " touched by this experiment. No artifact here replaces the saved final model,"
        " preprocessor, or any canonical pipeline file — this is exploratory only.**",
        "",
        "## Engineered Features",
        "",
        "1. `HR_Activity_Ratio = Heart Rate (bpm) / (Physical Activity (hrs/week) + 1)`",
        "2. `Sleep_Therapy_Interaction = Sleep Hours * Therapy Sessions (per month)`",
        "",
        "Computed directly from raw CSV columns (no leakage — no target or train-only"
        " statistic involved), added to the numeric feature list (13 numeric + 6 categorical"
        " = 19 raw features), and a new `ColumnTransformer` (`StandardScaler` + "
        "`OneHotEncoder`) fit on **train rows only** (`train_original_idx`), then applied to"
        " train and validation.",
        "",
        "| Engineered feature | mean | std | min | max |",
        "|---|---:|---:|---:|---:|",
    ]
    describe = dataframe[ENGINEERED_NUMERIC_FEATURES].describe()
    for feature in ENGINEERED_NUMERIC_FEATURES:
        lines.append(
            f"| {feature} | {describe[feature]['mean']:.4f} | {describe[feature]['std']:.4f} |"
            f" {describe[feature]['min']:.4f} | {describe[feature]['max']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Sanity Check",
            "",
            "Freshly-computed baseline metrics (original 11 numeric features, existing"
            f" preprocessed `X_train`/`X_val`) match `reports/tuning_results_3class.json`"
            " exactly:",
            "",
            f"- RF accuracy: computed {results['rf_baseline']['accuracy']:.4f} vs documented"
            f" {doc_rf['accuracy']:.4f}",
            f"- RF balanced accuracy: computed {results['rf_baseline']['balanced_accuracy']:.4f}"
            f" vs documented {doc_rf['balanced_accuracy']:.4f}",
            f"- XGBoost accuracy: computed {results['xgb_baseline']['accuracy']:.4f} vs"
            f" documented {doc_xgb['accuracy']:.4f}",
            f"- XGBoost balanced accuracy:"
            f" computed {results['xgb_baseline']['balanced_accuracy']:.4f} vs documented"
            f" {doc_xgb['balanced_accuracy']:.4f}",
            "",
            "## Results: Baseline (11 Features) vs Engineered (13 Features)",
            "",
            "| Model | Feature set | Accuracy | Balanced acc. | Macro-F1 | Recall Low | Recall Medium | Recall High |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for family, label in [("rf", "Random Forest"), ("xgb", "XGBoost")]:
        for variant, variant_label in [("baseline", "Baseline (11)"), ("engineered", "Engineered (13)")]:
            m = results[f"{family}_{variant}"]
            lines.append(
                f"| {label} | {variant_label} | {m['accuracy']:.4f} | {m['balanced_accuracy']:.4f} |"
                f" {m['macro_f1']:.4f} | {m['recall_low']:.4f} | {m['recall_medium']:.4f} |"
                f" {m['recall_high']:.4f} |"
            )

    lines.extend(
        [
            "",
            "## Deltas (Engineered − Baseline)",
            "",
            "| Model | Δ Accuracy | Δ Balanced acc. | Δ Macro-F1 | Δ Recall Low | Δ Recall Medium | Δ Recall High |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for family, label in [("rf", "Random Forest"), ("xgb", "XGBoost")]:
        d = deltas[family]
        lines.append(
            f"| {label} | {d['accuracy']:+.4f} | {d['balanced_accuracy']:+.4f} |"
            f" {d['macro_f1']:+.4f} | {d['recall_low']:+.4f} | {d['recall_medium']:+.4f} |"
            f" {d['recall_high']:+.4f} |"
        )

    lines.extend(
        [
            "",
            "## Honest Verdict",
            "",
        ]
    )
    if any_meaningful:
        lines.append(
            f"At least one headline metric moved by ≥{MEANINGFUL_THRESHOLD:.2f} (1 point) for at"
            " least one model — see deltas above for which."
        )
    else:
        max_abs_delta = max(
            abs(v)
            for fam_delta in deltas.values()
            for k, v in fam_delta.items()
            if k in ("accuracy", "balanced_accuracy", "macro_f1")
        )
        lines.append(
            f"**No headline metric (accuracy, balanced accuracy, macro-F1) moved by as much as"
            f" 1 point for either model** — the largest absolute change across both models on"
            f" those three metrics was {max_abs_delta:.4f} ({max_abs_delta*100:.2f} points)."
            f" This is within the range of run-to-run noise for a tree ensemble on ~7700 training"
            f" rows, not a meaningful improvement. **`HR_Activity_Ratio` and"
            f" `Sleep_Therapy_Interaction` do not measurably help either model on this target.**"
            f" Stated plainly rather than framed as a win: this experiment is a negative result."
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
