"""Calibration analysis for the tuned Random Forest (3-class Anxiety Level),
Low and Medium classes — completes Phase 15 (High was already done in
calibration_3class.py / reports/calibration_3class.md).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss


SEED = 42
N_BINS = 10
GAP_THRESHOLD = 0.03  # same convention as the High-class report
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
REPORT_PATH = ROOT / "reports" / "calibration_3class_full.md"
HIGH_PLOT_PATH = ROOT / "reports" / "calibration_high_3class.png"

CLASS_NAMES = ["Low", "Medium", "High"]

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


def analyze_class(class_name: str, class_index: int, probabilities: np.ndarray, y_val: np.ndarray, root: Path):
    class_probabilities = probabilities[:, class_index]
    y_val_binary = (y_val == class_index).astype(int)

    fraction_of_positives, mean_predicted_value = calibration_curve(
        y_val_binary, class_probabilities, n_bins=N_BINS, strategy="uniform"
    )
    bin_edges = np.linspace(0.0, 1.0, N_BINS + 1)
    bin_indices = np.clip(np.digitize(class_probabilities, bin_edges[1:-1], right=True), 0, N_BINS - 1)

    brier = brier_score_loss(y_val_binary, class_probabilities)

    bin_records = []
    for bin_i in range(N_BINS):
        mask = bin_indices == bin_i
        count = int(mask.sum())
        if count == 0:
            bin_records.append((bin_edges[bin_i], bin_edges[bin_i + 1], None, None, 0))
            continue
        mean_pred = float(class_probabilities[mask].mean())
        frac_pos = float(y_val_binary[mask].mean())
        bin_records.append((bin_edges[bin_i], bin_edges[bin_i + 1], mean_pred, frac_pos, count))

    populated = [r for r in bin_records if r[4] > 0]
    total_n = sum(r[4] for r in populated)
    weighted_gap = sum((r[2] - r[3]) * r[4] for r in populated) / total_n
    mean_abs_gap = sum(abs(r[2] - r[3]) * r[4] for r in populated) / total_n

    if weighted_gap > GAP_THRESHOLD:
        verdict = "OVER-CONFIDENT (predicted probabilities skew higher than actual outcome frequency)"
    elif weighted_gap < -GAP_THRESHOLD:
        verdict = "UNDER-CONFIDENT (predicted probabilities skew lower than actual outcome frequency)"
    else:
        verdict = "ROUGHLY CALIBRATED (predicted vs actual frequency close on average)"

    print(f"\n=== {class_name} vs rest ===")
    print(f"Brier score: {brier:.6f}")
    print("Reliability diagram data (uniform bins, n_bins=10):")
    for lo, hi, mean_pred, frac_pos, count in bin_records:
        if count == 0:
            print(f"  [{lo:.1f}, {hi:.1f}): empty (n=0)")
        else:
            print(f"  [{lo:.1f}, {hi:.1f}): mean_predicted={mean_pred:.4f}  actual_frequency={frac_pos:.4f}  n={count}")
    print(f"Weighted mean gap (predicted - actual): {weighted_gap:+.4f}")
    print(f"Weighted mean absolute gap: {mean_abs_gap:.4f}")
    print(f"Verdict: {verdict}")

    plot_path = root / "reports" / f"calibration_{class_name.lower()}_3class.png"
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfectly calibrated")
    ax.plot(mean_predicted_value, fraction_of_positives, marker="o", color="C0", label=f"Tuned RF ({class_name} vs rest)")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel(f"Observed frequency of {class_name}")
    ax.set_title(f"Reliability diagram — {class_name} class (3-class Random Forest)\nBrier score = {brier:.4f}")
    ax.legend(loc="upper left")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
    print(f"Saved plot to {plot_path.relative_to(root)}")

    return {
        "class_name": class_name,
        "brier": brier,
        "bin_records": bin_records,
        "weighted_gap": weighted_gap,
        "mean_abs_gap": mean_abs_gap,
        "verdict": verdict,
        "plot_path": plot_path,
    }


def main() -> None:
    splits = np.load(SPLITS_PATH)
    x_train, y_train = splits["X_train"], splits["y_train"]
    x_val, y_val = splits["X_val"], splits["y_val"]

    tuned_rf = RandomForestClassifier(**TUNED_RF_PARAMS)
    tuned_rf.fit(x_train, y_train)
    probabilities = tuned_rf.predict_proba(x_val)

    print(f"Tuned Random Forest (3-class) — Low/Medium calibration on X_val (n={len(y_val)})")

    results = []
    for class_name in ["Low", "Medium"]:
        class_index = CLASS_NAMES.index(class_name)
        result = analyze_class(class_name, class_index, probabilities, y_val, ROOT)
        results.append(result)

    # --- Write report ---
    lines: list[str] = [
        "# Calibration Report (Phase 15, completing) — Tuned Random Forest, 3-Class Target",
        "## Low and Medium Classes",
        "",
        "## Scope",
        "",
        "- Model: tuned Random Forest (n_estimators=200, max_depth=10, min_samples_split=10,"
        " min_samples_leaf=4, max_features='sqrt', class_weight='balanced') from"
        " `reports/tuning_results_3class.json`.",
        "- Evaluation: `X_val`/`y_val` from `mindcare_processed_splits_3class.npz`; test set untouched.",
        f"- Validation rows: {len(y_val)}; seed: {SEED}.",
        "- 10 uniform-width probability bins per class, one-vs-rest.",
        "- High class already covered in `reports/calibration_3class.md`"
        f" (![High reliability diagram]({HIGH_PLOT_PATH.name})); this report completes Low and Medium.",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"## {result['class_name']} vs Rest",
                "",
                f"**Brier score: {result['brier']:.6f}**",
                "",
                "| Bin range | Mean predicted P | Actual frequency | n in bin |",
                "|---|---:|---:|---:|",
            ]
        )
        for lo, hi, mean_pred, frac_pos, count in result["bin_records"]:
            if count == 0:
                lines.append(f"| [{lo:.1f}, {hi:.1f}) | — | — | 0 |")
            else:
                lines.append(f"| [{lo:.1f}, {hi:.1f}) | {mean_pred:.4f} | {frac_pos:.4f} | {count} |")
        lines.extend(
            [
                "",
                f"Count-weighted mean gap (predicted − actual): **{result['weighted_gap']:+.4f}**",
                f"Count-weighted mean absolute gap: {result['mean_abs_gap']:.4f}",
                "",
                f"**Verdict: {result['verdict']}**",
                "",
                f"![Reliability diagram]({result['plot_path'].name})",
                "",
            ]
        )

    lines.extend(
        [
            "## Summary Across All 3 Classes",
            "",
            "| Class | Brier score | Weighted gap (pred − actual) | Verdict |",
            "|---|---:|---:|---|",
        ]
    )
    for result in results:
        lines.append(
            f"| {result['class_name']} | {result['brier']:.6f} | {result['weighted_gap']:+.4f} |"
            f" {result['verdict'].split(' (')[0]} |"
        )
    lines.append(
        "| High | 0.013128 | +0.0333 | OVER-CONFIDENT (see `reports/calibration_3class.md`"
        " for the nuance: over-confident below P=0.3, well-calibrated above P=0.8) |"
    )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Prototype-model metrics on a very likely synthetic dataset (see CLAUDE.md); not"
            " clinical validation.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
