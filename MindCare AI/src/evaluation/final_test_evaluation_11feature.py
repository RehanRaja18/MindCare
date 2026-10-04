"""SECOND AND FINAL test-set evaluation for this project - 11-feature
canonical model, 3-class Anxiety Level target.

Disclosed explicitly: this is the second time the test set has been used
in this project. It is justified because this is a genuinely new model
configuration (11 features, adopted in reports/feature_reduction_3class.md
+ src/models/adopt_11feature_model.py to replace the original 17-feature
model) - not iterative tuning or re-evaluation of the same model. After
this, the test set is fully spent for both the 17-feature and 11-feature
models; no further test-set evaluation is permitted for either.

Uses data/processed/mindcare_final_model_11feature.pkl and the X_test/
y_test already saved in data/processed/mindcare_processed_splits_11feature.npz
(preprocessed by src/models/adopt_11feature_model.py) - no refitting, no
retraining, no model-selection change based on these results.
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
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_11feature.npz"
LABEL_ENCODER_PATH = ROOT / "data" / "processed" / "mindcare_label_encoder_3class.pkl"
MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model_11feature.pkl"
REPORT_PATH = ROOT / "reports" / "final_test_evaluation_11feature.md"

# --- Reference numbers, copied verbatim from existing reports ---

# This model's OWN validation numbers (reports/feature_reduction_3class.md,
# reproduced exactly by src/models/adopt_11feature_model.py's verification step).
VAL_11FEATURE = {
    "accuracy": 0.7770,
    "balanced_accuracy": 0.8084,
    "macro_f1": 0.8204,
}

# The ORIGINAL 17-feature model's test-set numbers (reports/final_test_evaluation.md) -
# the first, disclosed use of the test set in this project.
TEST_17FEATURE = {
    "accuracy": 0.7915,
    "balanced_accuracy": 0.8193,
    "macro_f1": 0.8311,
    "macro_auroc": 0.9083,
    "macro_auprc": 0.8691,
    "per_class_auroc": {"Low": 0.8798, "Medium": 0.8607, "High": 0.9843},
    "per_class_auprc": {"Low": 0.8587, "Medium": 0.7920, "High": 0.9566},
    "per_class_precision": {"Low": 0.7987, "Medium": 0.7422, "High": 0.9935},
    "per_class_recall": {"Low": 0.7772, "Medium": 0.7814, "High": 0.8994},
    "per_class_f1": {"Low": 0.7878, "Medium": 0.7613, "High": 0.9441},
}


def main() -> None:
    with np.load(SPLITS_PATH) as splits:
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
    print("SECOND AND FINAL TEST-SET EVALUATION - 11-feature model, 3-class Anxiety Level")
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

    # --- Comparison A: this model's own validation numbers ---
    print("\n" + "=" * 70)
    print("COMPARISON A: 11-feature TEST vs 11-feature VALIDATION (own model, gap check)")
    print("=" * 70)
    gap_a_flags = []

    def compare_a(label: str, val_value: float, test_value: float) -> None:
        gap = test_value - val_value
        flag = "  <-- gap >= 0.03" if abs(gap) >= 0.03 else ""
        if flag:
            gap_a_flags.append((label, val_value, test_value, gap))
        print(f"  {label:<20} val={val_value:.4f}  test={test_value:.4f}  gap(test-val)={gap:+.4f}{flag}")

    compare_a("accuracy", VAL_11FEATURE["accuracy"], accuracy)
    compare_a("balanced_accuracy", VAL_11FEATURE["balanced_accuracy"], balanced_accuracy)
    compare_a("macro_f1", VAL_11FEATURE["macro_f1"], macro_f1)

    # --- Comparison B: original 17-feature model's test numbers ---
    print("\n" + "=" * 70)
    print("COMPARISON B: 11-feature TEST vs 17-feature TEST (does feature reduction hold up on test?)")
    print("=" * 70)
    gap_b_flags = []

    def compare_b(label: str, ref_17: float, value_11: float) -> None:
        delta = value_11 - ref_17
        flag = "  <-- 11-feature WORSE by >=0.01" if delta <= -0.01 else ("  <-- 11-feature better" if delta >= 0.01 else "")
        if delta <= -0.01:
            gap_b_flags.append((label, ref_17, value_11, delta))
        print(f"  {label:<20} 17feat_test={ref_17:.4f}  11feat_test={value_11:.4f}  delta={delta:+.4f}{flag}")

    compare_b("accuracy", TEST_17FEATURE["accuracy"], accuracy)
    compare_b("balanced_accuracy", TEST_17FEATURE["balanced_accuracy"], balanced_accuracy)
    compare_b("macro_f1", TEST_17FEATURE["macro_f1"], macro_f1)
    compare_b("macro_auroc", TEST_17FEATURE["macro_auroc"], macro_auroc)
    compare_b("macro_auprc", TEST_17FEATURE["macro_auprc"], macro_auprc)
    for name, value in zip(class_names, per_class_auroc):
        compare_b(f"auroc_{name}", TEST_17FEATURE["per_class_auroc"][name], value)
    for name, value in zip(class_names, per_class_auprc):
        compare_b(f"auprc_{name}", TEST_17FEATURE["per_class_auprc"][name], value)

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
        compare_b(f"precision_{name}", TEST_17FEATURE["per_class_precision"][name], precision_by_class[name])
        compare_b(f"recall_{name}", TEST_17FEATURE["per_class_recall"][name], recall_by_class[name])
        compare_b(f"f1_{name}", TEST_17FEATURE["per_class_f1"][name], f1_by_class[name])

    print(f"\n[Comparison A] Metrics with |gap| >= 0.03 vs own validation: {len(gap_a_flags)}")
    print(f"[Comparison B] Metrics where 11-feature is WORSE than 17-feature by >= 0.01 on test: {len(gap_b_flags)}")
    for label, ref_17, value_11, delta in gap_b_flags:
        print(f"  {label}: 17feat={ref_17:.4f} 11feat={value_11:.4f} delta={delta:+.4f}")

    # --- Write report ---
    lines: list[str] = [
        "# SECOND AND FINAL Test-Set Evaluation — 11-Feature Model, 3-Class Anxiety Level Target",
        "",
        "**This is the SECOND and FINAL time the test set is used in this project, disclosed"
        " explicitly. It is justified because this evaluates a genuinely new model"
        " configuration (11 features, replacing the original 17-feature model per"
        " `reports/feature_reduction_3class.md` and `src/models/adopt_11feature_model.py`) —"
        " not iterative tuning or re-evaluation of the same model. After this report, the test"
        " set is fully spent for BOTH the 17-feature and 11-feature models. No further"
        " evaluation on X_test/y_test is permitted for either model.**",
        "",
        "## Scope",
        "",
        "- Model: `data/processed/mindcare_final_model_11feature.pkl` — used exactly as-is,"
        " no refitting.",
        f"- Test rows: {len(y_test)}; seed: {SEED}.",
        "- AUROC/AUPRC computed one-vs-rest per class via `label_binarize`.",
        "",
        "## Headline Metrics (11-Feature Model)",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Accuracy | {accuracy:.4f} |",
        f"| Balanced accuracy | {balanced_accuracy:.4f} |",
        f"| Macro-F1 | {macro_f1:.4f} |",
        f"| Macro AUROC | {macro_auroc:.4f} |",
        f"| Macro AUPRC | {macro_auprc:.4f} |",
        "",
        "## Per-Class AUROC / AUPRC — 11-Feature Test",
        "",
        "| Class | AUROC | AUPRC |",
        "|---|---:|---:|",
    ]
    for name, auroc_value, auprc_value in zip(class_names, per_class_auroc, per_class_auprc):
        lines.append(f"| {name} | {auroc_value:.4f} | {auprc_value:.4f} |")

    lines.extend(
        [
            "",
            "## Classification Report — 11-Feature Test",
            "",
            "```",
            report_text.rstrip(),
            "```",
            "",
            "## Confusion Matrix — 11-Feature Test (rows = true, columns = predicted,"
            " order Low/Medium/High)",
            "",
            "```",
            str(matrix),
            "```",
            "",
            "## Comparison A: 11-Feature Test vs. 11-Feature's Own Validation",
            "",
            "| Metric | Validation | Test | Gap (test − val) |",
            "|---|---:|---:|---:|",
            f"| Accuracy | {VAL_11FEATURE['accuracy']:.4f} | {accuracy:.4f} | {accuracy - VAL_11FEATURE['accuracy']:+.4f} |",
            f"| Balanced accuracy | {VAL_11FEATURE['balanced_accuracy']:.4f} | {balanced_accuracy:.4f} | {balanced_accuracy - VAL_11FEATURE['balanced_accuracy']:+.4f} |",
            f"| Macro-F1 | {VAL_11FEATURE['macro_f1']:.4f} | {macro_f1:.4f} | {macro_f1 - VAL_11FEATURE['macro_f1']:+.4f} |",
            "",
        ]
    )
    if gap_a_flags:
        lines.append(f"**{len(gap_a_flags)} metric(s) show a gap of 0.03 or more vs. this model's own validation numbers** — investigate before trusting this model's generalization.")
    else:
        lines.append("**No metric shows a gap of 0.03 or more between this model's validation and test performance** — no evidence of overfitting to the validation split during feature selection.")

    lines.extend(
        [
            "",
            "## Comparison B: 11-Feature Test vs. 17-Feature Test (Honest Head-to-Head)",
            "",
            "The original 17-feature model's test performance, for direct comparison"
            " (`reports/final_test_evaluation.md` — the first, disclosed use of the test set):",
            "",
            "| Metric | 17-feature (test) | 11-feature (test) | Delta (11 − 17) |",
            "|---|---:|---:|---:|",
            f"| Accuracy | {TEST_17FEATURE['accuracy']:.4f} | {accuracy:.4f} | {accuracy - TEST_17FEATURE['accuracy']:+.4f} |",
            f"| Balanced accuracy | {TEST_17FEATURE['balanced_accuracy']:.4f} | {balanced_accuracy:.4f} | {balanced_accuracy - TEST_17FEATURE['balanced_accuracy']:+.4f} |",
            f"| Macro-F1 | {TEST_17FEATURE['macro_f1']:.4f} | {macro_f1:.4f} | {macro_f1 - TEST_17FEATURE['macro_f1']:+.4f} |",
            f"| Macro AUROC | {TEST_17FEATURE['macro_auroc']:.4f} | {macro_auroc:.4f} | {macro_auroc - TEST_17FEATURE['macro_auroc']:+.4f} |",
            f"| Macro AUPRC | {TEST_17FEATURE['macro_auprc']:.4f} | {macro_auprc:.4f} | {macro_auprc - TEST_17FEATURE['macro_auprc']:+.4f} |",
            "",
            "| Class | Precision Δ | Recall Δ | F1 Δ | AUROC Δ | AUPRC Δ |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name in class_names:
        lines.append(
            f"| {name} | {precision_by_class[name] - TEST_17FEATURE['per_class_precision'][name]:+.4f} |"
            f" {recall_by_class[name] - TEST_17FEATURE['per_class_recall'][name]:+.4f} |"
            f" {f1_by_class[name] - TEST_17FEATURE['per_class_f1'][name]:+.4f} |"
            f" {per_class_auroc[class_names.index(name)] - TEST_17FEATURE['per_class_auroc'][name]:+.4f} |"
            f" {per_class_auprc[class_names.index(name)] - TEST_17FEATURE['per_class_auprc'][name]:+.4f} |"
        )

    lines.extend(["", "## Honest Verdict", ""])
    if gap_b_flags:
        lines.append(
            f"**The 11-feature model performs measurably worse than the 17-feature model on"
            f" the test set** on: {', '.join(f'{label} ({delta:+.4f})' for label, _, _, delta in gap_b_flags)}."
            f" This must be reported plainly: the feature-reduction decision, which looked"
            f" like a free win on validation data (`reports/feature_reduction_3class.md`),"
            f" does {'NOT ' if len(gap_b_flags) >= 3 else ''}fully hold up on the held-out"
            f" test set. This is exactly why validation-only findings must eventually be"
            f" checked against test data, and why this second test-set use was disclosed and"
            f" justified rather than skipped."
        )
    else:
        lines.append(
            f"**The 11-feature model's test performance is consistent with (not measurably"
            f" worse than) the 17-feature model's test performance.** The feature-reduction"
            f" finding from `reports/feature_reduction_3class.md` (validation-only) holds up"
            f" on held-out test data: removing the 6 lowest-SHAP-ranked features did not cost"
            f" meaningful generalization performance."
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a prototype-model result on a very likely synthetic dataset (see"
            " `CLAUDE.md`); not clinical validation. This was the second and final disclosed"
            " use of the test set in this project. No retraining, tuning, or model-selection"
            " change was made in response to these numbers. The test set must not be"
            " evaluated again for either the 17-feature or 11-feature model.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
