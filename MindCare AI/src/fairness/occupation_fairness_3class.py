"""Evaluate tuned Random Forest (3-class Anxiety Level target) precision
and recall by occupation. Uses val_original_idx directly from
mindcare_processed_splits_3class.npz — no index reconstruction needed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score


SEED = 42
RECALL_GAP_THRESHOLD = 0.10
LOW_CONFIDENCE_SUPPORT_THRESHOLD = 15
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
REPORT_PATH = ROOT / "reports" / "fairness_report_3class.md"

CLASS_NAMES = ["Low", "Medium", "High"]
HIGH_INDEX = CLASS_NAMES.index("High")

# Tuned Random Forest best params from reports/tuning_results_3class.json
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
    dataframe = pd.read_csv(DATA_PATH)
    splits = np.load(SPLITS_PATH)
    x_train, y_train = splits["X_train"], splits["y_train"]
    x_val, y_val = splits["X_val"], splits["y_val"]
    validation_indices = splits["val_original_idx"]
    occupations = dataframe.iloc[validation_indices]["Occupation"].to_numpy()

    model = RandomForestClassifier(**RF_PARAMS)
    model.fit(x_train, y_train)
    predictions = model.predict(x_val)

    overall_recall = recall_score(
        y_val, predictions, labels=np.arange(len(CLASS_NAMES)), average=None, zero_division=0
    )
    overall_precision = precision_score(
        y_val, predictions, labels=np.arange(len(CLASS_NAMES)), average=None, zero_division=0
    )

    occupations_sorted = sorted(np.unique(occupations))
    subgroup_metrics: dict[str, dict[str, dict[str, float | int]]] = {}
    flagged: list[dict[str, object]] = []
    for occupation in occupations_sorted:
        mask = occupations == occupation
        subgroup_recall = recall_score(
            y_val[mask],
            predictions[mask],
            labels=np.arange(len(CLASS_NAMES)),
            average=None,
            zero_division=0,
        )
        subgroup_precision = precision_score(
            y_val[mask],
            predictions[mask],
            labels=np.arange(len(CLASS_NAMES)),
            average=None,
            zero_division=0,
        )
        subgroup_metrics[occupation] = {}
        for class_index, class_name in enumerate(CLASS_NAMES):
            support = int(np.sum(y_val[mask] == class_index))
            subgroup_metrics[occupation][class_name] = {
                "support": support,
                "precision": float(subgroup_precision[class_index]),
                "recall": float(subgroup_recall[class_index]),
            }
            if class_name == "High":
                gap = float(overall_recall[class_index] - subgroup_recall[class_index])
                if gap >= RECALL_GAP_THRESHOLD:
                    flagged.append(
                        {
                            "occupation": occupation,
                            "class": class_name,
                            "subgroup_recall": float(subgroup_recall[class_index]),
                            "overall_recall": float(overall_recall[class_index]),
                            "gap": gap,
                            "support": support,
                            "low_confidence": support < LOW_CONFIDENCE_SUPPORT_THRESHOLD,
                        }
                    )

    report: list[str] = [
        "# Occupation Fairness Report — 3-Class Anxiety Level Target",
        "",
        "## Scope",
        "",
        "- Model: tuned Random Forest from `reports/tuning_results_3class.json`.",
        "- Training: existing `X_train`/`y_train` only; no refitting of preprocessing.",
        "- Evaluation: existing `X_val`/`y_val` only.",
        "- Occupation: original unencoded CSV column joined via `val_original_idx`"
        " (saved directly by `rebuild_preprocessor.py` — no reconstruction needed).",
        f"- Validation rows: {len(y_val)}; seed: {SEED}.",
        f"- Meaningful recall gap: subgroup recall at least {RECALL_GAP_THRESHOLD:.2f} below"
        " overall validation recall, for the High class only.",
        f"- Low-confidence flag: fewer than {LOW_CONFIDENCE_SUPPORT_THRESHOLD} validation rows"
        " for that occupation/class cell (same convention as the 5-class fairness report).",
        "",
        "## Overall Validation Precision and Recall",
        "",
        "| Class | Support | Precision | Recall |",
        "|---|---:|---:|---:|",
    ]
    for index, class_name in enumerate(CLASS_NAMES):
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
        for class_name in CLASS_NAMES:
            metrics = subgroup_metrics[occupation][class_name]
            report.append(
                f"| {class_name} | {metrics['support']} | "
                f"{format_metric(metrics['precision'])} | {format_metric(metrics['recall'])} |"
            )
        report.append("")

    report.extend(["## Clinically Important Recall Flags (High class)", ""])
    if flagged:
        report.extend(
            [
                "The following occupations meet the predefined meaningful-gap rule for the"
                " High class:",
                "",
                "| Occupation | Support (High) | Subgroup Recall | Overall Recall | Gap |"
                " Low confidence (<15 rows)? |",
                "|---|---:|---:|---:|---:|---|",
            ]
        )
        for item in sorted(flagged, key=lambda x: -x["gap"]):
            report.append(
                f"| {item['occupation']} | {item['support']} | "
                f"{format_metric(item['subgroup_recall'])} | "
                f"{format_metric(item['overall_recall'])} | {format_metric(item['gap'])} | "
                f"{'YES — low confidence' if item['low_confidence'] else 'no'} |"
            )
    else:
        report.append("No occupation had High recall at least 0.10 below the overall validation recall.")

    report.extend(
        [
            "",
            "## Interpretation",
            "",
            "These are prototype subgroup estimates on a synthetic dataset and should not be"
            " interpreted as clinical validation.",
            "High-class support per occupation is small (~10% of an already-small"
            " per-occupation validation sample), so any flagged cell with fewer than"
            f" {LOW_CONFIDENCE_SUPPORT_THRESHOLD} rows is explicitly marked low-confidence:"
            " a single misclassified row can swing recall by a large margin at that sample size,"
            " and these should not be treated as reliable evidence of a real subgroup gap without"
            " a larger sample.",
        ]
    )
    REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"Validation rows: {len(y_val)}")
    print("\nOverall validation recall:")
    for class_name, value in zip(CLASS_NAMES, overall_recall):
        print(f"  {class_name}: {value:.6f}")

    print("\nClinically important recall flags (High class):")
    if flagged:
        for item in sorted(flagged, key=lambda x: -x["gap"]):
            confidence_note = " [LOW CONFIDENCE, n<15]" if item["low_confidence"] else ""
            print(
                f"  {item['occupation']}: support={item['support']}, "
                f"subgroup_recall={item['subgroup_recall']:.6f}, "
                f"overall_recall={item['overall_recall']:.6f}, gap={item['gap']:.6f}"
                f"{confidence_note}"
            )
    else:
        print("  none")

    print(f"\nSaved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
