"""Threshold sweep for a P(High)-only uncertainty-flagging trigger, tuned
Random Forest, 3-class Anxiety Level target. Flag rule at each threshold t:
flag row if P(High) >= t (unconditional on predicted class — this isolates
the P(High) component of the combined rule in uncertainty_flagging.py).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier


SEED = 42
THRESHOLDS = [0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25]
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
REPORT_PATH = ROOT / "reports" / "threshold_sweep_high.md"

CLASS_NAMES = ["Low", "Medium", "High"]
HIGH_INDEX = CLASS_NAMES.index("High")
MEDIUM_INDEX = CLASS_NAMES.index("Medium")

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


def build_baseline_models() -> dict[str, object]:
    """Same untuned baseline models used in train_baselines_3class.py,
    reproduced here only to re-identify the 17 known unanimous misses."""
    return {
        "logistic_regression": LogisticRegression(max_iter=2000, random_state=SEED),
        "random_forest": RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1),
        "xgboost": XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.1, subsample=0.8,
            colsample_bytree=0.8, objective="multi:softprob", eval_metric="mlogloss",
            random_state=SEED, n_jobs=-1,
        ),
    }


def main() -> None:
    splits = np.load(SPLITS_PATH)
    x_train, y_train = splits["X_train"], splits["y_train"]
    x_val, y_val = splits["X_val"], splits["y_val"]

    tuned_rf = RandomForestClassifier(**TUNED_RF_PARAMS)
    tuned_rf.fit(x_train, y_train)
    probabilities = tuned_rf.predict_proba(x_val)
    predictions = tuned_rf.predict(x_val)
    p_high = probabilities[:, HIGH_INDEX]

    correctly_classified = predictions == y_val
    true_high = y_val == HIGH_INDEX
    n_true_high = int(true_high.sum())

    # Re-identify the 17 known unanimous True-High/Predicted-Medium misses
    baseline_models = build_baseline_models()
    baseline_predictions = {}
    for name, model in baseline_models.items():
        model.fit(x_train, y_train)
        baseline_predictions[name] = model.predict(x_val)

    all_predicted_medium = (
        (baseline_predictions["logistic_regression"] == MEDIUM_INDEX)
        & (baseline_predictions["random_forest"] == MEDIUM_INDEX)
        & (baseline_predictions["xgboost"] == MEDIUM_INDEX)
    )
    miss_mask = true_high & all_predicted_medium
    miss_positions = np.where(miss_mask)[0]
    n_misses = len(miss_positions)
    print(f"Known unanimous True-High/Predicted-Medium misses: {n_misses}")
    print(f"True High rows in validation set: {n_true_high}")

    n_val = len(y_val)
    sweep_rows = []
    for threshold in THRESHOLDS:
        flagged = p_high >= threshold

        misses_flagged = int(flagged[miss_positions].sum())
        misses_flagged_pct = misses_flagged / n_misses

        n_flagged = int(flagged.sum())
        flagged_pct = n_flagged / n_val

        n_flagged_correct = int((flagged & correctly_classified).sum())
        false_flag_rate = n_flagged_correct / n_flagged if n_flagged else float("nan")

        true_high_flagged = int(flagged[true_high].sum())
        true_high_flagged_pct = true_high_flagged / n_true_high

        sweep_rows.append(
            {
                "threshold": threshold,
                "misses_flagged": misses_flagged,
                "misses_flagged_pct": misses_flagged_pct,
                "n_flagged": n_flagged,
                "flagged_pct": flagged_pct,
                "false_flag_rate": false_flag_rate,
                "true_high_flagged": true_high_flagged,
                "true_high_flagged_pct": true_high_flagged_pct,
            }
        )

    header = (
        f"{'threshold':>10} {'misses_flag':>13} {'val_flagged':>14} "
        f"{'false_flag_rate':>16} {'true_high_flagged':>18}"
    )
    print("\n" + header)
    for row in sweep_rows:
        print(
            f"{row['threshold']:>10.2f} "
            f"{row['misses_flagged']:>4}/{n_misses:<2} ({row['misses_flagged_pct']:.4f}) "
            f"{row['n_flagged']:>5}/{n_val} ({row['flagged_pct']:.4f}) "
            f"{row['false_flag_rate']:>16.4f} "
            f"{row['true_high_flagged']:>4}/{n_true_high} ({row['true_high_flagged_pct']:.4f})"
        )

    # --- Write report ---
    lines: list[str] = [
        "# P(High)-Only Threshold Sweep — Tuned Random Forest, 3-Class Target",
        "",
        "## Scope",
        "",
        "- Model: tuned Random Forest (n_estimators=200, max_depth=10, min_samples_split=10,"
        " min_samples_leaf=4, max_features='sqrt', class_weight='balanced') from"
        " `reports/tuning_results_3class.json`.",
        "- Evaluation: `X_val`/`y_val` from `mindcare_processed_splits_3class.npz`; test set untouched.",
        f"- Validation rows: {n_val}; seed: {SEED}.",
        "- Flag rule at each threshold t: flag row if P(High) >= t, **unconditional on predicted"
        " class** (isolates the P(High) component of the combined rule in"
        " `reports/uncertainty_flagging.md`).",
        f"- Known unanimous True-High/Predicted-Medium misses (baseline models): {n_misses} rows.",
        f"- True High rows in validation set overall: {n_true_high}.",
        "",
        "## Threshold Sweep",
        "",
        "| Threshold | Misses flagged (17) | Val rows flagged | Val flagged % |"
        " False-flag rate | True-High rows flagged |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sweep_rows:
        lines.append(
            f"| {row['threshold']:.2f} | {row['misses_flagged']}/{n_misses} ({row['misses_flagged_pct']:.4f}) |"
            f" {row['n_flagged']}/{n_val} | {row['flagged_pct']:.4f} |"
            f" {row['false_flag_rate']:.4f} |"
            f" {row['true_high_flagged']}/{n_true_high} ({row['true_high_flagged_pct']:.4f}) |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Prototype-model metrics on a very likely synthetic dataset (see CLAUDE.md); not"
            " clinical validation. False-flag rate here is the fraction of ALL flagged rows"
            " (any true class) that the tuned Random Forest already classified correctly —"
            " i.e. review workload spent on cases where flagging doesn't change the outcome.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
