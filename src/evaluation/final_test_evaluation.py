"""FINAL, ONE-TIME test-set evaluation - 3-class Anxiety Level target.

This is the only script in this project that touches X_test/y_test from
mindcare_processed_splits_3class.npz. It uses the already-saved final model
(data/processed/mindcare_final_model.pkl, the tuned Random Forest from
reports/tuning_results_3class.json) exactly as-is. Nothing here may inform
any further retraining, tuning, or model-selection decision - the test set
is a one-way door, per CLAUDE.md's engineering rules.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.preprocessing import label_binarize


SEED = 42
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
LABEL_ENCODER_PATH = ROOT / "data" / "processed" / "mindcare_label_encoder_3class.pkl"
MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model.pkl"
REPORT_PATH = ROOT / "reports" / "final_test_evaluation.md"

# Validation-set reference numbers, copied verbatim from reports/full_evaluation_3class.md
# (same model, same hyperparameters, evaluated on X_val instead of X_test).
VAL_REFERENCE = {
    "accuracy": 0.7733,
    "balanced_accuracy": 0.8056,
    "macro_f1": 0.8177,
    "per_class_auroc": {"Low": 0.8745, "Medium": 0.8517, "High": 0.9850},
    "per_class_auprc": {"Low": 0.8556, "Medium": 0.7699, "High": 0.9511},
    "macro_auroc": 0.9037,
    "macro_auprc": 0.8589,
    "per_class_precision": {"Low": 0.7806, "Medium": 0.7223, "High": 0.9933},
    "per_class_recall": {"Low": 0.7545, "Medium": 0.7652, "High": 0.8970},
    "per_class_f1": {"Low": 0.7673, "Medium": 0.7431, "High": 0.9427},
}


def format_metric(value: float) -> str:
    return f"{value:.4f}"


def main() -> None:
    splits = np.load(SPLITS_PATH)
    x_test, y_test = splits["X_test"], splits["y_test"]

    label_encoder = joblib.load(LABEL_ENCODER_PATH)
    class_names = list(label_encoder.classes_)
    n_classes = len(class_names)
    class_index = np.arange(n_classes)

    model = joblib.load(MODEL_PATH)

    predictions = model.predict(x_test)
    probabilities = model.predict_proba(x_test)

    accuracy = float(accuracy_score(y_test, predictions))
    balanced_accuracy = float(balanced_accuracy_score(y_test, predictions))
    macro_f1 = float(f1_score(y_test, predictions, average="macro"))

    y_test_binarized = label_binarize(y_test, classes=class_index)
    per_class_auroc = roc_auc_score(y_test_binarized, probabilities, average=None, multi_class="ovr")
    macro_auroc = roc_auc_score(y_test_binarized, probabilities, average="macro", multi_class="ovr")
    per_class_auprc = average_precision_score(y_test_binarized, probabilities, average=None)
    macro_auprc = average_precision_score(y_test_binarized, probabilities, average="macro")

    report_text = classification_report(
        y_test, predictions, labels=class_index, target_names=class_names, digits=4
    )
    matrix = confusion_matrix(y_test, predictions, labels=class_index)

    print("=" * 70)
    print("FINAL, ONE-TIME TEST-SET EVALUATION - 3-class Anxiety Level target")
    print(f"Test rows: {len(y_test)}")
    print("=" * 70)
    print(f"\naccuracy: {accuracy:.6f}")
    print(f"balanced_accuracy: {balanced_accuracy:.6f}")
    print(f"macro_f1: {macro_f1:.6f}")

    print("\nPer-class AUROC:")
    for name, value in zip(class_names, per_class_auroc):
        print(f"  {name}: {value:.6f}")
    print(f"Macro AUROC: {macro_auroc:.6f}")

    print("\nPer-class AUPRC:")
    for name, value in zip(class_names, per_class_auprc):
        print(f"  {name}: {value:.6f}")
    print(f"Macro AUPRC: {macro_auprc:.6f}")

    print("\nClassification report:")
    print(report_text)

    print("Confusion matrix (rows=true, cols=predicted, order=Low/Medium/High):")
    print(matrix)

    # --- Compare directly to the validation-set reference numbers ---
    print("\n" + "=" * 70)
    print("VAL vs TEST comparison")
    print("=" * 70)
    gap_flags = []

    def compare(label: str, val_value: float, test_value: float) -> None:
        gap = test_value - val_value
        flag = "  <-- gap >= 0.03" if abs(gap) >= 0.03 else ""
        if flag:
            gap_flags.append((label, val_value, test_value, gap))
        print(f"  {label:<24} val={val_value:.4f}  test={test_value:.4f}  gap(test-val)={gap:+.4f}{flag}")

    compare("accuracy", VAL_REFERENCE["accuracy"], accuracy)
    compare("balanced_accuracy", VAL_REFERENCE["balanced_accuracy"], balanced_accuracy)
    compare("macro_f1", VAL_REFERENCE["macro_f1"], macro_f1)
    compare("macro_auroc", VAL_REFERENCE["macro_auroc"], macro_auroc)
    compare("macro_auprc", VAL_REFERENCE["macro_auprc"], macro_auprc)
    for name, value in zip(class_names, per_class_auroc):
        compare(f"auroc_{name}", VAL_REFERENCE["per_class_auroc"][name], value)
    for name, value in zip(class_names, per_class_auprc):
        compare(f"auprc_{name}", VAL_REFERENCE["per_class_auprc"][name], value)

    precision_by_class = {}
    recall_by_class = {}
    f1_by_class = {}
    for line in report_text.splitlines():
        parts = line.split()
        if parts and parts[0] in class_names:
            precision_by_class[parts[0]] = float(parts[1])
            recall_by_class[parts[0]] = float(parts[2])
            f1_by_class[parts[0]] = float(parts[3])
    for name in class_names:
        compare(f"precision_{name}", VAL_REFERENCE["per_class_precision"][name], precision_by_class[name])
        compare(f"recall_{name}", VAL_REFERENCE["per_class_recall"][name], recall_by_class[name])
        compare(f"f1_{name}", VAL_REFERENCE["per_class_f1"][name], f1_by_class[name])

    print(f"\nMetrics with |gap| >= 0.03: {len(gap_flags)}")
    for label, val_value, test_value, gap in gap_flags:
        print(f"  {label}: val={val_value:.4f} test={test_value:.4f} gap={gap:+.4f}")

    # --- Write report ---
    lines: list[str] = [
        "# FINAL Test-Set Evaluation (One-Time) — 3-Class Anxiety Level Target",
        "",
        "**This is the only evaluation in this project that uses X_test/y_test. The test set was"
        " untouched until this report. No retraining, tuning, or model-selection decision may be"
        " made based on these results — this was a one-way door.**",
        "",
        "## Scope",
        "",
        "- Model: the saved final tuned Random Forest (`data/processed/mindcare_final_model.pkl`),"
        " hyperparameters from `reports/tuning_results_3class.json` — used exactly as-is, no"
        " refitting.",
        f"- Test rows: {len(y_test)}; seed: {SEED}.",
        "- AUROC/AUPRC computed one-vs-rest per class via `label_binarize`.",
        "",
        "## Headline Metrics",
        "",
        "| Metric | Validation (reports/full_evaluation_3class.md) | Test | Gap (test − val) |",
        "|---|---:|---:|---:|",
        f"| Accuracy | {VAL_REFERENCE['accuracy']:.4f} | {accuracy:.4f} | {accuracy - VAL_REFERENCE['accuracy']:+.4f} |",
        f"| Balanced accuracy | {VAL_REFERENCE['balanced_accuracy']:.4f} | {balanced_accuracy:.4f} | {balanced_accuracy - VAL_REFERENCE['balanced_accuracy']:+.4f} |",
        f"| Macro-F1 | {VAL_REFERENCE['macro_f1']:.4f} | {macro_f1:.4f} | {macro_f1 - VAL_REFERENCE['macro_f1']:+.4f} |",
        f"| Macro AUROC | {VAL_REFERENCE['macro_auroc']:.4f} | {macro_auroc:.4f} | {macro_auroc - VAL_REFERENCE['macro_auroc']:+.4f} |",
        f"| Macro AUPRC | {VAL_REFERENCE['macro_auprc']:.4f} | {macro_auprc:.4f} | {macro_auprc - VAL_REFERENCE['macro_auprc']:+.4f} |",
        "",
        "## Per-Class AUROC / AUPRC — Test",
        "",
        "| Class | AUROC (val) | AUROC (test) | Gap | AUPRC (val) | AUPRC (test) | Gap |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, auroc_value, auprc_value in zip(class_names, per_class_auroc, per_class_auprc):
        val_auroc = VAL_REFERENCE["per_class_auroc"][name]
        val_auprc = VAL_REFERENCE["per_class_auprc"][name]
        lines.append(
            f"| {name} | {val_auroc:.4f} | {auroc_value:.4f} | {auroc_value - val_auroc:+.4f} |"
            f" {val_auprc:.4f} | {auprc_value:.4f} | {auprc_value - val_auprc:+.4f} |"
        )

    lines.extend(
        [
            "",
            "## Classification Report — Test",
            "",
            "```",
            report_text.rstrip(),
            "```",
            "",
            "## Classification Report — Val vs Test, Per-Class",
            "",
            "| Class | Precision (val) | Precision (test) | Recall (val) | Recall (test) |"
            " F1 (val) | F1 (test) |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name in class_names:
        lines.append(
            f"| {name} | {VAL_REFERENCE['per_class_precision'][name]:.4f} |"
            f" {precision_by_class[name]:.4f} | {VAL_REFERENCE['per_class_recall'][name]:.4f} |"
            f" {recall_by_class[name]:.4f} | {VAL_REFERENCE['per_class_f1'][name]:.4f} |"
            f" {f1_by_class[name]:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Confusion Matrix — Test (rows = true, columns = predicted, order Low/Medium/High)",
            "",
            "```",
            str(matrix),
            "```",
            "",
            "## Val-vs-Test Gap Assessment",
            "",
        ]
    )
    if gap_flags:
        lines.append(
            f"**{len(gap_flags)} metric(s) show a gap of 0.03 or more between validation and test:**"
        )
        lines.append("")
        lines.append("| Metric | Val | Test | Gap |")
        lines.append("|---|---:|---:|---:|")
        for label, val_value, test_value, gap in gap_flags:
            lines.append(f"| {label} | {val_value:.4f} | {test_value:.4f} | {gap:+.4f} |")
    else:
        lines.append(
            "**No metric shows a gap of 0.03 or more between validation and test.** Test-set"
            " performance is consistent with the validation-set numbers already reported in"
            " `reports/full_evaluation_3class.md` — no evidence of overfitting to the"
            " validation split during the tuning/analysis process."
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a prototype-model result on a very likely synthetic dataset (see"
            " `CLAUDE.md`); not clinical validation. This evaluation was performed exactly once,"
            " against the already-saved final model, with no retraining, tuning, or"
            " model-selection change made in response to these numbers.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
