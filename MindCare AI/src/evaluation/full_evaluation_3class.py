"""Phase 14: full validation-set evaluation of the tuned Random Forest,
3-class Anxiety Level target. Reports per-class and macro AUROC/AUPRC
(one-vs-rest) plus the full classification_report.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    roc_auc_score,
)
from sklearn.preprocessing import label_binarize


SEED = 42
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
LABEL_ENCODER_PATH = ROOT / "data" / "processed" / "mindcare_label_encoder_3class.pkl"
REPORT_PATH = ROOT / "reports" / "full_evaluation_3class.md"

# Tuned hyperparameters from reports/tuning_results_3class.json (models.random_forest.best_params)
RF_PARAMS = dict(
    n_estimators=200,
    max_depth=10,
    min_samples_split=10,
    min_samples_leaf=4,
    max_features="sqrt",
    class_weight="balanced",
    random_state=SEED,
    n_jobs=-1,
)


def format_metric(value: float) -> str:
    return f"{value:.4f}"


def main() -> None:
    splits = np.load(SPLITS_PATH)
    x_train, y_train = splits["X_train"], splits["y_train"]
    x_val, y_val = splits["X_val"], splits["y_val"]

    label_encoder = joblib.load(LABEL_ENCODER_PATH)
    class_names = list(label_encoder.classes_)
    n_classes = len(class_names)
    class_index = np.arange(n_classes)

    model = RandomForestClassifier(**RF_PARAMS)
    model.fit(x_train, y_train)

    predictions = model.predict(x_val)
    probabilities = model.predict_proba(x_val)

    y_val_binarized = label_binarize(y_val, classes=class_index)

    per_class_auroc = roc_auc_score(
        y_val_binarized, probabilities, average=None, multi_class="ovr"
    )
    macro_auroc = roc_auc_score(
        y_val_binarized, probabilities, average="macro", multi_class="ovr"
    )

    per_class_auprc = average_precision_score(
        y_val_binarized, probabilities, average=None
    )
    macro_auprc = average_precision_score(
        y_val_binarized, probabilities, average="macro"
    )

    report_text = classification_report(
        y_val, predictions, labels=class_index, target_names=class_names, digits=4
    )

    print("Tuned Random Forest (3-class) - validation set (X_val, n=%d)" % len(y_val))
    print("\nPer-class AUROC (one-vs-rest):")
    for name, value in zip(class_names, per_class_auroc):
        print(f"  {name}: {value:.6f}")
    print(f"Macro AUROC: {macro_auroc:.6f}")

    print("\nPer-class AUPRC (one-vs-rest):")
    for name, value in zip(class_names, per_class_auprc):
        print(f"  {name}: {value:.6f}")
    print(f"Macro AUPRC: {macro_auprc:.6f}")

    print("\nClassification report:")
    print(report_text)

    lines: list[str] = [
        "# Full Evaluation Report (Phase 14) — 3-Class Anxiety Level Target",
        "",
        "## Scope",
        "",
        "- Model: tuned Random Forest from `reports/tuning_results_3class.json`"
        " (n_estimators=200, max_depth=10, min_samples_split=10,"
        " min_samples_leaf=4, max_features='sqrt', class_weight='balanced').",
        "- Training: existing `X_train`/`y_train` only; no refitting of preprocessing.",
        "- Evaluation: existing `X_val`/`y_val` only; test set untouched.",
        f"- Validation rows: {len(y_val)}; seed: {SEED}.",
        "- AUROC/AUPRC computed one-vs-rest per class via `label_binarize`.",
        "",
        "## Per-Class AUROC and AUPRC (One-vs-Rest)",
        "",
        "| Class | AUROC | AUPRC |",
        "|---|---:|---:|",
    ]
    for name, auroc_value, auprc_value in zip(class_names, per_class_auroc, per_class_auprc):
        lines.append(f"| {name} | {format_metric(auroc_value)} | {format_metric(auprc_value)} |")
    lines.extend(
        [
            f"| **Macro average** | **{format_metric(macro_auroc)}** | **{format_metric(macro_auprc)}** |",
            "",
            "## Classification Report",
            "",
            "```",
            report_text.rstrip(),
            "```",
            "",
            "## Interpretation",
            "",
            "These are prototype-model metrics on a very likely synthetic dataset"
            " (see CLAUDE.md) and should not be read as clinical validation.",
            "Per CLAUDE.md, Stress Level correlates 0.65 (ordinal) with this 3-class target"
            " and removing it drops Logistic Regression accuracy by 17.6 points (77.8% -> 60.1%,"
            " still well above the 47.2% majority baseline) — a materially smaller single-feature"
            " dependency than the 5-class Severity target (0.91 correlation, ~49-point drop).",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
