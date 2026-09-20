"""Calibration analysis for the tuned Random Forest (3-class Anxiety Level),
High class specifically: reliability diagram, Brier score, and per-row
predicted probability for the 17 unanimous True-High/Predicted-Medium
misses identified from the untuned baseline models.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from xgboost import XGBClassifier


SEED = 42
N_BINS = 10
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
PLOT_PATH = ROOT / "reports" / "calibration_high_3class.png"
REPORT_PATH = ROOT / "reports" / "calibration_3class.md"

CLASS_NAMES = ["Low", "Medium", "High"]
HIGH_INDEX = CLASS_NAMES.index("High")
MEDIUM_INDEX = CLASS_NAMES.index("Medium")

# Tuned Random Forest best params from reports/tuning_results_3class.json
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
    """Same baseline (untuned) models used in train_baselines_3class.py,
    reproduced here to re-identify the 17 unanimous High->Medium misses."""
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
    dataframe = pd.read_csv(DATA_PATH)
    splits = np.load(SPLITS_PATH)
    x_train, y_train = splits["X_train"], splits["y_train"]
    x_val, y_val = splits["X_val"], splits["y_val"]
    val_original_idx = splits["val_original_idx"]

    tuned_rf = RandomForestClassifier(**TUNED_RF_PARAMS)
    tuned_rf.fit(x_train, y_train)
    val_probabilities = tuned_rf.predict_proba(x_val)
    high_probabilities = val_probabilities[:, HIGH_INDEX]

    y_val_high_binary = (y_val == HIGH_INDEX).astype(int)

    fraction_of_positives, mean_predicted_value = calibration_curve(
        y_val_high_binary, high_probabilities, n_bins=N_BINS, strategy="uniform"
    )
    # also get per-bin counts for context
    bin_edges = np.linspace(0.0, 1.0, N_BINS + 1)
    bin_indices = np.clip(np.digitize(high_probabilities, bin_edges[1:-1], right=True), 0, N_BINS - 1)

    brier = brier_score_loss(y_val_high_binary, high_probabilities)

    print(f"Tuned Random Forest (3-class) — High-vs-rest calibration on X_val (n={len(y_val)})")
    print(f"\nBrier score (High vs rest): {brier:.6f}")

    print("\nReliability diagram data (uniform bins, n_bins=10):")
    # calibration_curve silently drops empty bins, so recompute per-bin stats explicitly
    # to report all 10 bins (including empty ones) with counts.
    bin_records = []
    for bin_i in range(N_BINS):
        mask = bin_indices == bin_i
        count = int(mask.sum())
        if count == 0:
            bin_records.append((bin_edges[bin_i], bin_edges[bin_i + 1], None, None, 0))
            continue
        mean_pred = float(high_probabilities[mask].mean())
        frac_pos = float(y_val_high_binary[mask].mean())
        bin_records.append((bin_edges[bin_i], bin_edges[bin_i + 1], mean_pred, frac_pos, count))

    for lo, hi, mean_pred, frac_pos, count in bin_records:
        if count == 0:
            print(f"  [{lo:.1f}, {hi:.1f}): empty (n=0)")
        else:
            print(f"  [{lo:.1f}, {hi:.1f}): mean_predicted={mean_pred:.4f}  actual_frequency={frac_pos:.4f}  n={count}")

    # Calibration verdict: compare mean predicted vs actual across populated bins,
    # weighted by count, using signed gap (predicted - actual).
    populated = [r for r in bin_records if r[4] > 0]
    total_n = sum(r[4] for r in populated)
    weighted_gap = sum((r[2] - r[3]) * r[4] for r in populated) / total_n
    mean_abs_gap = sum(abs(r[2] - r[3]) * r[4] for r in populated) / total_n

    if weighted_gap > 0.03:
        verdict = "OVER-CONFIDENT (predicted probabilities skew higher than actual outcome frequency)"
    elif weighted_gap < -0.03:
        verdict = "UNDER-CONFIDENT (predicted probabilities skew lower than actual outcome frequency)"
    else:
        verdict = "ROUGHLY CALIBRATED (predicted vs actual frequency close on average)"

    print(f"\nWeighted mean gap (predicted - actual), count-weighted: {weighted_gap:+.4f}")
    print(f"Weighted mean absolute gap: {mean_abs_gap:.4f}")
    print(f"Verdict: {verdict}")

    # Reliability diagram plot
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfectly calibrated")
    ax.plot(mean_predicted_value, fraction_of_positives, marker="o", color="C0", label="Tuned RF (High vs rest)")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed frequency of High")
    ax.set_title(f"Reliability diagram — High class (3-class Random Forest)\nBrier score = {brier:.4f}")
    ax.legend(loc="upper left")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(PLOT_PATH, dpi=150)
    plt.close(fig)
    print(f"\nSaved plot to {PLOT_PATH.relative_to(ROOT)}")

    # --- Identify the 17 unanimous True-High / Predicted-Medium misses from baseline models ---
    baseline_models = build_baseline_models()
    baseline_predictions = {}
    for name, model in baseline_models.items():
        model.fit(x_train, y_train)
        baseline_predictions[name] = model.predict(x_val)

    true_high = y_val == HIGH_INDEX
    all_predicted_medium = (
        (baseline_predictions["logistic_regression"] == MEDIUM_INDEX)
        & (baseline_predictions["random_forest"] == MEDIUM_INDEX)
        & (baseline_predictions["xgboost"] == MEDIUM_INDEX)
    )
    miss_mask = true_high & all_predicted_medium
    miss_positions = np.where(miss_mask)[0]
    print(f"\nUnanimous True-High/Predicted-Medium misses (baseline models): {len(miss_positions)} rows")

    miss_original_rows = val_original_idx[miss_positions]
    miss_anxiety = dataframe.iloc[miss_original_rows]["Anxiety Level (1-10)"].to_numpy()
    miss_tuned_rf_high_proba = high_probabilities[miss_positions]
    miss_tuned_rf_full_proba = val_probabilities[miss_positions]

    print(f"\n{'orig_row':>10} {'Anxiety':>8} {'P(Low)':>8} {'P(Medium)':>10} {'P(High)':>8}")
    miss_rows_table = []
    for orig_row, anxiety, proba_row in zip(miss_original_rows, miss_anxiety, miss_tuned_rf_full_proba):
        print(f"{orig_row:>10} {anxiety:>8} {proba_row[0]:>8.4f} {proba_row[1]:>10.4f} {proba_row[2]:>8.4f}")
        miss_rows_table.append(
            {
                "original_row": int(orig_row),
                "anxiety_level": int(anxiety),
                "p_low": float(proba_row[0]),
                "p_medium": float(proba_row[1]),
                "p_high": float(proba_row[2]),
            }
        )

    mean_high_proba_on_misses = float(miss_tuned_rf_high_proba.mean())
    print(f"\nMean tuned-RF P(High) on these 17 misses: {mean_high_proba_on_misses:.4f}")
    print(f"Range: [{miss_tuned_rf_high_proba.min():.4f}, {miss_tuned_rf_high_proba.max():.4f}]")
    n_above_10pct = int(np.sum(miss_tuned_rf_high_proba >= 0.10))
    n_above_20pct = int(np.sum(miss_tuned_rf_high_proba >= 0.20))
    print(f"Rows with P(High) >= 0.10: {n_above_10pct}/17")
    print(f"Rows with P(High) >= 0.20: {n_above_20pct}/17")

    # --- Write report ---
    lines: list[str] = [
        "# Calibration Report — Tuned Random Forest, 3-Class Target (High class)",
        "",
        "## Scope",
        "",
        "- Model: tuned Random Forest (n_estimators=200, max_depth=10, min_samples_split=10,"
        " min_samples_leaf=4, max_features='sqrt', class_weight='balanced') from"
        " `reports/tuning_results_3class.json`.",
        "- Evaluation: `X_val`/`y_val` from `mindcare_processed_splits_3class.npz`; test set untouched.",
        f"- Validation rows: {len(y_val)}; seed: {SEED}.",
        "- Calibration target: High vs rest (one-vs-rest), 10 uniform-width probability bins.",
        "",
        "## Brier Score",
        "",
        f"**Brier score (High vs rest): {brier:.6f}**",
        "",
        "(0 = perfect; 0.25 = always predicting 0.5; lower is better. This is a strictly proper"
        " scoring rule combining calibration and sharpness.)",
        "",
        "## Reliability Diagram Data",
        "",
        "| Bin range | Mean predicted P(High) | Actual frequency of High | n in bin |",
        "|---|---:|---:|---:|",
    ]
    for lo, hi, mean_pred, frac_pos, count in bin_records:
        if count == 0:
            lines.append(f"| [{lo:.1f}, {hi:.1f}) | — | — | 0 |")
        else:
            lines.append(f"| [{lo:.1f}, {hi:.1f}) | {mean_pred:.4f} | {frac_pos:.4f} | {count} |")
    lines.extend(
        [
            "",
            f"Count-weighted mean gap (predicted − actual): **{weighted_gap:+.4f}**",
            f"Count-weighted mean absolute gap: {mean_abs_gap:.4f}",
            "",
            f"**Verdict: {verdict}**",
            "",
            f"![Reliability diagram]({PLOT_PATH.name})",
            "",
            "## The 17 Unanimous True-High / Predicted-Medium Misses",
            "",
            "These are the validation rows where true label is High and the three untuned baseline"
            " models (Logistic Regression, Random Forest, XGBoost) all predicted Medium"
            " (`reports/baseline_results_3class.json`). Shown here: this tuned Random Forest's"
            " full predicted-probability vector on each of those same 17 rows.",
            "",
            "| Original row | Anxiety Level | P(Low) | P(Medium) | P(High) |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for row in miss_rows_table:
        lines.append(
            f"| {row['original_row']} | {row['anxiety_level']} | {row['p_low']:.4f} |"
            f" {row['p_medium']:.4f} | {row['p_high']:.4f} |"
        )
    lines.extend(
        [
            "",
            f"Mean P(High) on these 17 rows: **{mean_high_proba_on_misses:.4f}**"
            f" (range [{miss_tuned_rf_high_proba.min():.4f}, {miss_tuned_rf_high_proba.max():.4f}])",
            f"Rows with P(High) >= 0.10: {n_above_10pct}/17",
            f"Rows with P(High) >= 0.20: {n_above_20pct}/17",
            "",
            "## Interpretation",
            "",
            "Prototype-model metrics on a very likely synthetic dataset (see CLAUDE.md);"
            " not clinical validation.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
