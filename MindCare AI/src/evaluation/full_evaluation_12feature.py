"""Phase-14-style full validation-set evaluation of the canonical 12-feature
model (3-class Anxiety Level target): full classification_report, confusion
matrix, and per-class + macro AUROC/AUPRC (one-vs-rest).

Unlike src/evaluation/full_evaluation_3class.py (which refits the 17-feature
Random Forest), this evaluates the SAVED artifact exactly as the API serves
it: data/processed/mindcare_final_model_12feature.pkl, built by
src/models/adopt_12feature_model.py.

Validation only. The 12-feature splits file contains no test arrays at all
(adopt_12feature_model.py never creates them - the 3-class test set is
treated as fully spent), and this script never asks for them.

Before anything new is reported, the headline metrics are checked against
reports/feature_addition_age_3class.md (accuracy 0.7739, balanced accuracy
0.8062, macro-F1 0.8182, and its per-class recalls). If any differs at the
4 decimal places that report uses, the script raises and writes nothing.
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
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import label_binarize


ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_12feature.npz"
MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model_12feature.pkl"
LABEL_ENCODER_PATH = ROOT / "data" / "processed" / "mindcare_label_encoder_3class.pkl"
REPORT_PATH = ROOT / "reports" / "full_evaluation_12feature.md"

# Documented in reports/feature_addition_age_3class.md, "With Age (12 features)" row.
EXPECTED = {
    "accuracy": 0.7739,
    "balanced_accuracy": 0.8062,
    "macro_f1": 0.8182,
    "recall_Low": 0.7506,
    "recall_Medium": 0.7709,
    "recall_High": 0.8970,
}

# 17-feature model, same validation rows - reports/full_evaluation_3class.md (Phase 14).
PHASE14_17FEATURE = {
    "auroc": {"Low": 0.8745, "Medium": 0.8517, "High": 0.9850, "macro": 0.9037},
    "auprc": {"Low": 0.8556, "Medium": 0.7699, "High": 0.9511, "macro": 0.8589},
}


def fmt(value: float) -> str:
    return f"{value:.4f}"


def main() -> None:
    with np.load(SPLITS_PATH) as splits:
        x_val, y_val = splits["X_val"], splits["y_val"]
        split_keys = sorted(splits.files)

    model = joblib.load(MODEL_PATH)
    class_names = list(joblib.load(LABEL_ENCODER_PATH).classes_)
    class_index = np.arange(len(class_names))

    predictions = model.predict(x_val)
    probabilities = model.predict_proba(x_val)

    # --- Step 1: reproduce the documented headline numbers before reporting anything new ---
    per_class_recall = recall_score(y_val, predictions, labels=class_index, average=None)
    actual = {
        "accuracy": accuracy_score(y_val, predictions),
        "balanced_accuracy": balanced_accuracy_score(y_val, predictions),
        "macro_f1": f1_score(y_val, predictions, average="macro"),
        **{f"recall_{name}": value for name, value in zip(class_names, per_class_recall)},
    }
    print("--- Check against reports/feature_addition_age_3class.md ---")
    mismatches = []
    for key, expected in EXPECTED.items():
        ok = round(actual[key], 4) == expected
        print(f"  {key}: documented {expected:.4f}, recomputed {actual[key]:.6f} -> {'MATCH' if ok else 'MISMATCH'}")
        if not ok:
            mismatches.append(key)
    if mismatches:
        raise SystemExit(
            f"STOP: {mismatches} do not match reports/feature_addition_age_3class.md - "
            "no report written. Investigate before reporting new metrics."
        )
    print("  ALL MATCH\n")

    # --- Step 2: the new metrics ---
    y_val_binarized = label_binarize(y_val, classes=class_index)
    per_class_auroc = roc_auc_score(y_val_binarized, probabilities, average=None)
    macro_auroc = roc_auc_score(y_val_binarized, probabilities, average="macro")
    per_class_auprc = average_precision_score(y_val_binarized, probabilities, average=None)
    macro_auprc = average_precision_score(y_val_binarized, probabilities, average="macro")
    report_text = classification_report(
        y_val, predictions, labels=class_index, target_names=class_names, digits=4
    )
    matrix = confusion_matrix(y_val, predictions, labels=class_index)

    print(f"12-feature model - validation set (n={len(y_val)})")
    print(report_text)
    print("Confusion matrix (rows = true, columns = predicted):", class_names)
    print(matrix)
    for name, auroc, auprc in zip(class_names, per_class_auroc, per_class_auprc):
        print(f"  {name}: AUROC {auroc:.6f}  AUPRC {auprc:.6f}")
    print(f"  macro: AUROC {macro_auroc:.6f}  AUPRC {macro_auprc:.6f}")

    # Largest off-diagonal cell, for the interpretation section.
    off_diagonal = matrix.copy()
    np.fill_diagonal(off_diagonal, 0)
    worst_true, worst_pred = np.unravel_index(np.argmax(off_diagonal), off_diagonal.shape)
    low, medium, high = (class_names.index(name) for name in ("Low", "Medium", "High"))
    low_medium_errors = int(matrix[low, medium] + matrix[medium, low])
    total_errors = int(off_diagonal.sum())
    high_missed_as = {class_names[j]: int(matrix[high, j]) for j in class_index if j != high}
    predicted_high_wrong = {class_names[i]: int(matrix[i, high]) for i in class_index if i != high}

    lines = [
        "# Full Evaluation Report (Phase-14 style) — 12-Feature Model, 3-Class Anxiety Level",
        "",
        "## Scope",
        "",
        "- Model: the saved canonical artifact `data/processed/mindcare_final_model_12feature.pkl`"
        " (built by `src/models/adopt_12feature_model.py`), evaluated as-is — not refit.",
        "- Data: `X_val`/`y_val` from `data/processed/mindcare_processed_splits_12feature.npz`"
        f" ({len(y_val)} rows). That file contains only {', '.join(f'`{k}`' for k in split_keys)}"
        " — **no test arrays exist for this configuration, and none were used.** The 3-class"
        " test set is treated as fully spent (see CLAUDE.md); these are validation-only numbers.",
        "- AUROC/AUPRC computed one-vs-rest per class via `label_binarize`.",
        "- Script: `src/evaluation/full_evaluation_12feature.py`.",
        "",
        "## Consistency Check (run before anything below was computed)",
        "",
        "Recomputed from the saved model and compared with `reports/feature_addition_age_3class.md`"
        " at its 4 decimal places. The script stops without writing this report on any mismatch.",
        "",
        "| Metric | Documented | Recomputed | Match |",
        "|---|---:|---:|:---:|",
    ]
    for key, expected in EXPECTED.items():
        lines.append(f"| {key} | {expected:.4f} | {actual[key]:.6f} | yes |")
    lines += [
        "",
        "## Classification Report",
        "",
        "```",
        report_text.rstrip(),
        "```",
        "",
        "## Confusion Matrix",
        "",
        "Rows = true class, columns = predicted class.",
        "",
        "| True \\ Predicted | " + " | ".join(class_names) + " | Total |",
        "|---|" + "---:|" * (len(class_names) + 1),
    ]
    for i, name in enumerate(class_names):
        lines.append(f"| **{name}** | " + " | ".join(str(v) for v in matrix[i]) + f" | {matrix[i].sum()} |")
    lines += [
        "",
        "## Per-Class AUROC and AUPRC (One-vs-Rest)",
        "",
        "With the 17-feature model's Phase 14 validation numbers (`reports/full_evaluation_3class.md`,"
        " same 1650 validation rows) for reference.",
        "",
        "| Class | AUROC | AUPRC | 17-feature AUROC | 17-feature AUPRC | Δ AUROC | Δ AUPRC |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, auroc, auprc in zip(class_names, per_class_auroc, per_class_auprc):
        ref_auroc, ref_auprc = PHASE14_17FEATURE["auroc"][name], PHASE14_17FEATURE["auprc"][name]
        lines.append(
            f"| {name} | {fmt(auroc)} | {fmt(auprc)} | {fmt(ref_auroc)} | {fmt(ref_auprc)}"
            f" | {auroc - ref_auroc:+.4f} | {auprc - ref_auprc:+.4f} |"
        )
    ref_auroc, ref_auprc = PHASE14_17FEATURE["auroc"]["macro"], PHASE14_17FEATURE["auprc"]["macro"]
    lines += [
        f"| **Macro average** | **{fmt(macro_auroc)}** | **{fmt(macro_auprc)}** | {fmt(ref_auroc)}"
        f" | {fmt(ref_auprc)} | {macro_auroc - ref_auroc:+.4f} | {macro_auprc - ref_auprc:+.4f} |",
        "",
        "## Interpretation",
        "",
        f"- The largest single error cell is true **{class_names[worst_true]}** predicted as"
        f" **{class_names[worst_pred]}** ({off_diagonal[worst_true, worst_pred]} rows). Low↔Medium"
        f" confusion accounts for {low_medium_errors} of {total_errors} errors"
        f" ({low_medium_errors / total_errors:.1%}). Low↔High confusion:"
        f" {int(matrix[low, high])} true-Low predicted High, {int(matrix[high, low])} true-High"
        " predicted Low.",
        f"- High: {matrix[high, high]} of {matrix[high].sum()} true-High rows caught; the misses were"
        f" predicted as {', '.join(f'{k} ({v})' for k, v in high_missed_as.items())}. Rows wrongly"
        f" predicted High: {', '.join(f'{k} ({v})' for k, v in predicted_high_wrong.items())}.",
        "- The comparison columns above are both validation-set numbers on the same rows, so they"
        " are directly comparable — but they are not test-set results, and no test-set number"
        " exists for this model.",
        "- These are prototype-model metrics on a very likely synthetic dataset (see CLAUDE.md) and"
        " should not be read as clinical validation.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
