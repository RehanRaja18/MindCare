"""EXPLORATORY soft-voting ensemble experiment - 3-class Anxiety Level target.

Works on TRAIN and VALIDATION only. This script never loads or references
X_test, y_test, or test_original_idx from mindcare_processed_splits_3class.npz
anywhere.

Uses the existing (original 11 numeric + 6 categorical feature) preprocessed
splits - not the engineered feature set from the prior experiment, since
that experiment found no benefit. Builds a soft-voting ensemble of tuned
Random Forest and tuned XGBoost (same hyperparameters as
reports/tuning_results_3class.json for both): averages predicted
probabilities, argmax for the ensemble prediction.

Does not touch: data/processed/mindcare_final_model.pkl,
data/processed/mindcare_preprocessor.pkl, or the test set. Purely
exploratory - no artifact from this script is adopted as canonical.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score
from xgboost import XGBClassifier


SEED = 42
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
TUNING_RESULTS_PATH = ROOT / "reports" / "tuning_results_3class.json"
REPORT_PATH = ROOT / "reports" / "ensemble_3class.md"

CLASS_NAMES = ["Low", "Medium", "High"]
MEANINGFUL_THRESHOLD = 0.01  # 1 percentage point

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


def evaluate_from_predictions(y_val: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
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
    # Only train/val arrays are read. X_test / y_test / test_original_idx are never
    # referenced anywhere in this script.
    with np.load(SPLITS_PATH) as splits:
        x_train = splits["X_train"]
        y_train = splits["y_train"]
        x_val = splits["X_val"]
        y_val = splits["y_val"]

    rf = RandomForestClassifier(**TUNED_RF_PARAMS)
    rf.fit(x_train, y_train)
    rf_proba = rf.predict_proba(x_val)
    rf_predictions = rf.predict(x_val)
    rf_metrics = evaluate_from_predictions(y_val, rf_predictions)

    xgb = XGBClassifier(**TUNED_XGB_PARAMS)
    xgb.fit(x_train, y_train)
    xgb_proba = xgb.predict_proba(x_val)
    xgb_predictions = xgb.predict(x_val)
    xgb_metrics = evaluate_from_predictions(y_val, xgb_predictions)

    ensemble_proba = (rf_proba + xgb_proba) / 2.0
    ensemble_predictions = np.argmax(ensemble_proba, axis=1)
    ensemble_metrics = evaluate_from_predictions(y_val, ensemble_predictions)

    print("=== Individual models and soft-voting ensemble (validation set) ===")
    print_row("random_forest", rf_metrics)
    print_row("xgboost", xgb_metrics)
    print_row("ensemble (avg proba)", ensemble_metrics)

    # --- Sanity check vs documented tuning results ---
    documented = json.loads(TUNING_RESULTS_PATH.read_text(encoding="utf-8"))
    doc_rf = documented["models"]["random_forest"]["tuned_validation"]
    doc_xgb = documented["models"]["xgboost"]["tuned_validation"]
    print("\n=== Sanity check vs reports/tuning_results_3class.json ===")
    rf_acc_match = abs(rf_metrics["accuracy"] - doc_rf["accuracy"]) < 1e-9
    rf_bal_match = abs(rf_metrics["balanced_accuracy"] - doc_rf["balanced_accuracy"]) < 1e-9
    xgb_acc_match = abs(xgb_metrics["accuracy"] - doc_xgb["accuracy"]) < 1e-9
    xgb_bal_match = abs(xgb_metrics["balanced_accuracy"] - doc_xgb["balanced_accuracy"]) < 1e-9
    print(f"  RF  accuracy match: {rf_acc_match}  ({rf_metrics['accuracy']:.4f} vs {doc_rf['accuracy']:.4f})")
    print(f"  RF  balanced_accuracy match: {rf_bal_match}  ({rf_metrics['balanced_accuracy']:.4f} vs {doc_rf['balanced_accuracy']:.4f})")
    print(f"  XGB accuracy match: {xgb_acc_match}  ({xgb_metrics['accuracy']:.4f} vs {doc_xgb['accuracy']:.4f})")
    print(f"  XGB balanced_accuracy match: {xgb_bal_match}  ({xgb_metrics['balanced_accuracy']:.4f} vs {doc_xgb['balanced_accuracy']:.4f})")

    # --- Deltas: ensemble vs each individual model, and vs the better of the two ---
    best_individual_name = "random_forest" if rf_metrics["macro_f1"] >= xgb_metrics["macro_f1"] else "xgboost"
    best_individual = rf_metrics if best_individual_name == "random_forest" else xgb_metrics

    delta_vs_rf = {k: ensemble_metrics[k] - rf_metrics[k] for k in rf_metrics}
    delta_vs_xgb = {k: ensemble_metrics[k] - xgb_metrics[k] for k in xgb_metrics}
    delta_vs_best = {k: ensemble_metrics[k] - best_individual[k] for k in best_individual}

    print(f"\nBest individual model by macro-F1: {best_individual_name} ({best_individual['macro_f1']:.4f})")
    print("Ensemble delta vs RF:      " + "  ".join(f"{k}={v:+.4f}" for k, v in delta_vs_rf.items()))
    print("Ensemble delta vs XGBoost: " + "  ".join(f"{k}={v:+.4f}" for k, v in delta_vs_xgb.items()))
    print("Ensemble delta vs BEST individual: " + "  ".join(f"{k}={v:+.4f}" for k, v in delta_vs_best.items()))

    beats_both = ensemble_metrics["macro_f1"] > rf_metrics["macro_f1"] and ensemble_metrics["macro_f1"] > xgb_metrics["macro_f1"]
    meaningful_vs_best = abs(delta_vs_best["macro_f1"]) >= MEANINGFUL_THRESHOLD
    print(f"\nEnsemble beats BOTH individual models on macro-F1: {beats_both}")
    print(f"Improvement over best individual model >= 1 point: {meaningful_vs_best}")

    # --- Write report ---
    lines: list[str] = [
        "# Soft-Voting Ensemble Experiment (Exploratory) — 3-Class Anxiety Level Target",
        "",
        "**Scope note: this script works on TRAIN and VALIDATION only. It never loads or"
        " references X_test, y_test, or test_original_idx anywhere. The test set was not"
        " touched by this experiment. No artifact here replaces the saved final model,"
        " preprocessor, or any canonical pipeline file — this is exploratory only.**",
        "",
        "## Method",
        "",
        "Original 11 numeric + 6 categorical feature set (existing"
        " `mindcare_processed_splits_3class.npz`) — not the engineered feature set from the"
        " prior experiment, since that experiment found no benefit. Tuned Random Forest and"
        " tuned XGBoost (both from `reports/tuning_results_3class.json`) are each fit on"
        " `X_train`/`y_train`, `predict_proba` is computed on `X_val` for each, the two"
        " probability arrays are averaged, and `argmax` gives the ensemble prediction.",
        "",
        "## Sanity Check",
        "",
        f"- RF accuracy: computed {rf_metrics['accuracy']:.4f} vs documented {doc_rf['accuracy']:.4f}"
        f" (match: {rf_acc_match})",
        f"- RF balanced accuracy: computed {rf_metrics['balanced_accuracy']:.4f} vs documented"
        f" {doc_rf['balanced_accuracy']:.4f} (match: {rf_bal_match})",
        f"- XGBoost accuracy: computed {xgb_metrics['accuracy']:.4f} vs documented"
        f" {doc_xgb['accuracy']:.4f} (match: {xgb_acc_match})",
        f"- XGBoost balanced accuracy: computed {xgb_metrics['balanced_accuracy']:.4f} vs"
        f" documented {doc_xgb['balanced_accuracy']:.4f} (match: {xgb_bal_match})",
        "",
        "## Results",
        "",
        "| Model | Accuracy | Balanced acc. | Macro-F1 | Recall Low | Recall Medium | Recall High |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Random Forest | {rf_metrics['accuracy']:.4f} | {rf_metrics['balanced_accuracy']:.4f} |"
        f" {rf_metrics['macro_f1']:.4f} | {rf_metrics['recall_low']:.4f} |"
        f" {rf_metrics['recall_medium']:.4f} | {rf_metrics['recall_high']:.4f} |",
        f"| XGBoost | {xgb_metrics['accuracy']:.4f} | {xgb_metrics['balanced_accuracy']:.4f} |"
        f" {xgb_metrics['macro_f1']:.4f} | {xgb_metrics['recall_low']:.4f} |"
        f" {xgb_metrics['recall_medium']:.4f} | {xgb_metrics['recall_high']:.4f} |",
        f"| **Ensemble (soft vote)** | **{ensemble_metrics['accuracy']:.4f}** |"
        f" **{ensemble_metrics['balanced_accuracy']:.4f}** | **{ensemble_metrics['macro_f1']:.4f}** |"
        f" {ensemble_metrics['recall_low']:.4f} | {ensemble_metrics['recall_medium']:.4f} |"
        f" {ensemble_metrics['recall_high']:.4f} |",
        "",
        "## Deltas",
        "",
        "| Comparison | Δ Accuracy | Δ Balanced acc. | Δ Macro-F1 | Δ Recall Low | Δ Recall Medium | Δ Recall High |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Ensemble − RF | {delta_vs_rf['accuracy']:+.4f} | {delta_vs_rf['balanced_accuracy']:+.4f} |"
        f" {delta_vs_rf['macro_f1']:+.4f} | {delta_vs_rf['recall_low']:+.4f} |"
        f" {delta_vs_rf['recall_medium']:+.4f} | {delta_vs_rf['recall_high']:+.4f} |",
        f"| Ensemble − XGBoost | {delta_vs_xgb['accuracy']:+.4f} | {delta_vs_xgb['balanced_accuracy']:+.4f} |"
        f" {delta_vs_xgb['macro_f1']:+.4f} | {delta_vs_xgb['recall_low']:+.4f} |"
        f" {delta_vs_xgb['recall_medium']:+.4f} | {delta_vs_xgb['recall_high']:+.4f} |",
        f"| Ensemble − best individual ({best_individual_name}) | {delta_vs_best['accuracy']:+.4f} |"
        f" {delta_vs_best['balanced_accuracy']:+.4f} | {delta_vs_best['macro_f1']:+.4f} |"
        f" {delta_vs_best['recall_low']:+.4f} | {delta_vs_best['recall_medium']:+.4f} |"
        f" {delta_vs_best['recall_high']:+.4f} |",
        "",
        "## Honest Verdict",
        "",
    ]

    if beats_both and meaningful_vs_best:
        lines.append(
            f"The ensemble beats **both** individual models on macro-F1, by"
            f" {delta_vs_best['macro_f1']:+.4f} over the best individual model"
            f" ({best_individual_name}) — a genuine improvement of ≥1 point."
        )
    elif beats_both:
        lines.append(
            f"The ensemble beats both individual models on macro-F1, but only marginally"
            f" ({delta_vs_best['macro_f1']:+.4f} over the best individual model,"
            f" {best_individual_name}) — under the 1-point bar. **This should be read as"
            f" splitting the difference between the two models with a very slight edge, not"
            f" as a meaningful win.**"
        )
    else:
        lines.append(
            f"**The ensemble does NOT beat both individual models — it lands between them,"
            f" i.e. it splits the difference rather than improving on the best one.** On"
            f" macro-F1: RF={rf_metrics['macro_f1']:.4f}, XGBoost={xgb_metrics['macro_f1']:.4f},"
            f" Ensemble={ensemble_metrics['macro_f1']:.4f}. The ensemble is"
            f" {'better than' if ensemble_metrics['macro_f1'] > min(rf_metrics['macro_f1'], xgb_metrics['macro_f1']) else 'not better than'}"
            f" the *worse* of the two individual models, but"
            f" {'is' if ensemble_metrics['macro_f1'] >= best_individual['macro_f1'] else 'is NOT'}"
            f" better than the *best* individual model"
            f" ({best_individual_name}, {best_individual['macro_f1']:.4f}). Stated plainly: this"
            f" is not a case where the ensemble captures complementary strengths of both models"
            f" — averaging two similarly-performing models that make similar kinds of errors"
            f" mostly just averages their scores, it doesn't compound their strengths."
        )

    lines.extend(
        [
            "",
            "## Interpretability Cost If This Were Adopted",
            "",
            "Neither individual model needed this tradeoff — Random Forest already has a cheap,"
            " exact `shap.TreeExplainer` (used throughout Phase 17), and XGBoost would too if it"
            " were ever adopted on its own. **A soft-voting ensemble of two different model"
            " types has no single, cheap explainer that covers the combined prediction.** In"
            " practice, adopting this ensemble would mean one of:",
            "",
            "1. **Running SHAP separately on each sub-model** (two `TreeExplainer` runs, RF and"
            " XGBoost independently) and then trying to combine or reconcile two different"
            " attribution sets for the same prediction — doable, but doubles the explainability"
            " workload and gives a psychologist reviewer two potentially-disagreeing"
            " explanations to reconcile, not one.",
            "2. **Using a model-agnostic method like `KernelExplainer` (KernelSHAP) on the"
            " ensemble's combined `predict_proba` directly** — this treats the ensemble as a"
            " black box and works correctly, but is dramatically slower than `TreeExplainer`"
            " (KernelSHAP requires many perturbed-input model evaluations per row, typically"
            " orders of magnitude more compute than a tree-structure-aware explainer), which"
            " matters for a workflow that's supposed to support real-time or near-real-time"
            " psychologist review.",
            "",
            "Given the ensemble's actual performance in this experiment (see verdict above),"
            " this added interpretability cost is very unlikely to be worth paying — the"
            " Model Selection Rationale in `docs/model_card.md` already named interpretability"
            " as a deciding factor in choosing Random Forest over XGBoost alone; an ensemble of"
            " the two moves further in the wrong direction on that same criterion for, at best,"
            " a marginal accuracy gain.",
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
