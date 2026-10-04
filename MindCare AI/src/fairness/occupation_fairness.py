"""Evaluate tuned Random Forest precision and recall by occupation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score


SEED = 42
RECALL_GAP_THRESHOLD = 0.10
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits.npz"
REPORT_PATH = ROOT / "reports" / "fairness_report.md"

NUMERIC_FEATURES = [
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
CATEGORICAL_FEATURES = [
    "Occupation",
    "Smoking",
    "Family History of Anxiety",
    "Dizziness",
    "Medication",
    "Recent Major Life Event",
]
CLASSES = ["High", "Mild", "Minimal", "Moderate", "Severe"]


def format_metric(value: float) -> str:
    return f"{value:.4f}"


def main() -> None:
    dataframe = pd.read_csv(DATA_PATH)
    splits = np.load(SPLITS_PATH)
    x_train, y_train = splits["X_train"], splits["y_train"]
    x_val, y_val = splits["X_val"], splits["y_val"]
    validation_indices = splits["val_original_idx"]
    occupations = dataframe.iloc[validation_indices]["Occupation"].to_numpy()

    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=30,
        min_samples_split=10,
        min_samples_leaf=4,
        max_features="sqrt",
        class_weight="balanced",
        random_state=SEED,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)
    predictions = model.predict(x_val)

    overall_recall = recall_score(
        y_val, predictions, labels=np.arange(len(CLASSES)), average=None, zero_division=0
    )
    overall_precision = precision_score(
        y_val, predictions, labels=np.arange(len(CLASSES)), average=None, zero_division=0
    )

    occupations_sorted = sorted(np.unique(occupations))
    subgroup_metrics: dict[str, dict[str, dict[str, float | int]]] = {}
    flagged: list[dict[str, object]] = []
    for occupation in occupations_sorted:
        mask = occupations == occupation
        subgroup_recall = recall_score(
            y_val[mask],
            predictions[mask],
            labels=np.arange(len(CLASSES)),
            average=None,
            zero_division=0,
        )
        subgroup_precision = precision_score(
            y_val[mask],
            predictions[mask],
            labels=np.arange(len(CLASSES)),
            average=None,
            zero_division=0,
        )
        subgroup_metrics[occupation] = {}
        for class_index, class_name in enumerate(CLASSES):
            subgroup_metrics[occupation][class_name] = {
                "support": int(np.sum(y_val[mask] == class_index)),
                "precision": float(subgroup_precision[class_index]),
                "recall": float(subgroup_recall[class_index]),
            }
            if class_name in {"High", "Severe"}:
                gap = float(overall_recall[class_index] - subgroup_recall[class_index])
                if gap >= RECALL_GAP_THRESHOLD:
                    flagged.append(
                        {
                            "occupation": occupation,
                            "class": class_name,
                            "subgroup_recall": float(subgroup_recall[class_index]),
                            "overall_recall": float(overall_recall[class_index]),
                            "gap": gap,
                        }
                    )

    report: list[str] = [
        "# Occupation Fairness Report",
        "",
        "## Scope",
        "",
        "- Model: tuned Random Forest from `reports/tuning_results.json`.",
        "- Training: existing `X_train`/`y_train` only; no refitting of preprocessing.",
        "- Evaluation: existing `X_val`/`y_val` only.",
        "- Occupation: original unencoded CSV column joined by reproduced validation row index.",
        f"- Validation rows: {len(y_val)}; seed: {SEED}.",
        f"- Meaningful recall gap: subgroup recall at least {RECALL_GAP_THRESHOLD:.2f} below overall validation recall.",
        "",
        "## Overall Validation Precision and Recall",
        "",
        "| Class | Support | Precision | Recall |",
        "|---|---:|---:|---:|",
    ]
    for index, class_name in enumerate(CLASSES):
        report.append(
            f"| {class_name} | {int(np.sum(y_val == index))} | "
            f"{format_metric(overall_precision[index])} | {format_metric(overall_recall[index])} |"
        )

    report.extend(["", "## Occupation Subgroup Metrics", ""])
    for occupation in occupations_sorted:
        report.extend(
            [
                f"### {occupation}",
                "",
                "| Class | Support | Precision | Recall |",
                "|---|---:|---:|---:|",
            ]
        )
        for class_name in CLASSES:
            metrics = subgroup_metrics[occupation][class_name]
            report.append(
                f"| {class_name} | {metrics['support']} | "
                f"{format_metric(metrics['precision'])} | {format_metric(metrics['recall'])} |"
            )
        report.append("")

    report.extend(["## Clinically Important Recall Flags", ""])
    if flagged:
        report.extend(
            [
                "The following occupation/class combinations meet the predefined meaningful-gap rule:",
                "",
                "| Occupation | Class | Subgroup Recall | Overall Recall | Gap |",
                "|---|---|---:|---:|---:|",
            ]
        )
        for item in flagged:
            report.append(
                f"| {item['occupation']} | {item['class']} | "
                f"{format_metric(item['subgroup_recall'])} | "
                f"{format_metric(item['overall_recall'])} | {format_metric(item['gap'])} |"
            )
    else:
        report.append("No occupation had High or Severe recall at least 0.10 below the overall validation recall.")

    report.extend(
        [
            "",
            "## Interpretation",
            "",
            "These are prototype subgroup estimates on a synthetic dataset and should not be interpreted as clinical validation.",
            "Low subgroup support, especially for Severe, can make recall estimates unstable and should be considered before drawing conclusions.",
        ]
    )
    REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")

    print("Overall validation recall:")
    for class_name, value in zip(CLASSES, overall_recall):
        print(f"  {class_name}: {value:.6f}")
    print("Clinically important recall flags:")
    if flagged:
        for item in flagged:
            print(
                f"  {item['occupation']} / {item['class']}: "
                f"subgroup={item['subgroup_recall']:.6f}, "
                f"overall={item['overall_recall']:.6f}, gap={item['gap']:.6f}"
            )
    else:
        print("  none")
    print(f"Saved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()