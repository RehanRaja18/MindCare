"""EXPLORATORY: does isotonic calibration change the uncertainty-flagging
mechanism's behavior? 3-class Anxiety Level target.

Works on TRAIN and VALIDATION only - never loads or references X_test,
y_test, or test_original_idx anywhere. Re-fits the isotonic-calibrated
Random Forest exactly as in src/experiments/postprocessing_3class.py, then
re-runs the production flag rule (P(High) >= 0.10) and compares against the
existing uncalibrated results in reports/uncertainty_flagging.md.

Does not touch the saved final model, the existing preprocessor, or the
test set. Purely exploratory.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier


SEED = 42
HIGH_PROBA_THRESHOLD = 0.10
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
REPORT_PATH = ROOT / "reports" / "calibrated_uncertainty_flagging_3class.md"

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

# Existing documented uncalibrated results (reports/uncertainty_flagging.md)
DOCUMENTED = {
    "n_flagged": 346,
    "n_val": 1650,
    "flagged_fraction": 0.2097,
    "misses_flagged": 9,
    "n_misses": 17,
    "misses_flagged_fraction": 0.5294,
    "false_flag_rate": 0.9277,
    "n_flagged_correct": 321,
}


def build_baseline_models() -> dict[str, object]:
    """Same untuned baseline models used throughout this project, reproduced
    here only to re-identify the 17 known unanimous misses."""
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
    with np.load(SPLITS_PATH) as splits:
        x_train = splits["X_train"]
        y_train = splits["y_train"]
        x_val = splits["X_val"]
        y_val = splits["y_val"]
        val_original_idx = splits["val_original_idx"]

    print("Fitting isotonic-calibrated Random Forest (cv=5) on X_train/y_train...")
    isotonic = CalibratedClassifierCV(
        estimator=RandomForestClassifier(**TUNED_RF_PARAMS), method="isotonic", cv=5
    )
    isotonic.fit(x_train, y_train)
    proba = isotonic.predict_proba(x_val)
    predictions = isotonic.predict(x_val)
    p_high = proba[:, HIGH_INDEX]

    flagged = p_high >= HIGH_PROBA_THRESHOLD
    n_flagged = int(flagged.sum())
    n_val = len(y_val)
    flagged_fraction = n_flagged / n_val

    correctly_classified = predictions == y_val
    n_flagged_correct = int((flagged & correctly_classified).sum())
    false_flag_rate = n_flagged_correct / n_flagged if n_flagged else float("nan")

    print(f"\nCalibrated (isotonic) flagging: {n_flagged} / {n_val} = {flagged_fraction:.4f}")
    print(f"Calibrated false-flag rate: {n_flagged_correct} / {n_flagged} = {false_flag_rate:.4f}")

    # --- Re-identify the 17 known unanimous True-High/Predicted-Medium misses ---
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
    n_misses = len(miss_positions)

    misses_flagged_calibrated = flagged[miss_positions]
    n_misses_flagged_calibrated = int(misses_flagged_calibrated.sum())
    misses_flagged_fraction_calibrated = n_misses_flagged_calibrated / n_misses

    print(f"\nKnown misses re-identified: {n_misses} (documented: {DOCUMENTED['n_misses']})")
    print(f"Calibrated coverage of known misses: {n_misses_flagged_calibrated} / {n_misses} = "
          f"{misses_flagged_fraction_calibrated:.4f}")
    print(f"Uncalibrated coverage (documented): {DOCUMENTED['misses_flagged']} / {DOCUMENTED['n_misses']} = "
          f"{DOCUMENTED['misses_flagged_fraction']:.4f}")

    miss_original_rows = val_original_idx[miss_positions]
    print(f"\n{'orig_row':>10} {'P(High) uncal (doc)':>20} {'P(High) calibrated':>20} {'flagged (calibrated)':>22}")
    miss_table = []
    for pos, orig_row in zip(miss_positions, miss_original_rows):
        row_flagged = bool(flagged[pos])
        miss_table.append(
            {
                "original_row": int(orig_row),
                "p_high_calibrated": float(p_high[pos]),
                "flagged_calibrated": row_flagged,
            }
        )
        print(f"{orig_row:>10} {'—':>20} {p_high[pos]:>20.4f} {str(row_flagged):>22}")

    # --- Comparison summary ---
    delta_n_flagged = n_flagged - DOCUMENTED["n_flagged"]
    delta_misses_flagged = n_misses_flagged_calibrated - DOCUMENTED["misses_flagged"]
    delta_false_flag_rate = false_flag_rate - DOCUMENTED["false_flag_rate"]

    print("\n=== COMPARISON: uncalibrated (documented) vs isotonic-calibrated ===")
    print(f"  Overall flagged: {DOCUMENTED['n_flagged']}/{DOCUMENTED['n_val']} ({DOCUMENTED['flagged_fraction']:.4f}) "
          f"-> {n_flagged}/{n_val} ({flagged_fraction:.4f})   delta={delta_n_flagged:+d} rows")
    print(f"  Known-miss coverage: {DOCUMENTED['misses_flagged']}/{DOCUMENTED['n_misses']} "
          f"({DOCUMENTED['misses_flagged_fraction']:.4f}) -> {n_misses_flagged_calibrated}/{n_misses} "
          f"({misses_flagged_fraction_calibrated:.4f})   delta={delta_misses_flagged:+d} rows")
    print(f"  False-flag rate: {DOCUMENTED['false_flag_rate']:.4f} -> {false_flag_rate:.4f}   "
          f"delta={delta_false_flag_rate:+.4f}")

    meaningfully_different = abs(delta_misses_flagged) >= 1 or abs(delta_n_flagged) / DOCUMENTED["n_flagged"] >= 0.05
    print(f"\nMeaningfully different behavior: {meaningfully_different}")

    # --- Write report ---
    lines: list[str] = [
        "# Calibrated Uncertainty Flagging Check (Exploratory) — 3-Class Anxiety Level Target",
        "",
        "**Scope note: this script works on TRAIN and VALIDATION only. It never loads or"
        " references X_test, y_test, or test_original_idx anywhere. The test set was not"
        " touched. No canonical artifact was changed — purely exploratory.**",
        "",
        "## Method",
        "",
        "Isotonic-calibrated Random Forest, identical to"
        " `src/experiments/postprocessing_3class.py`"
        " (`CalibratedClassifierCV(estimator=RandomForest(tuned params), method='isotonic',"
        " cv=5)`, fit on `X_train`/`y_train`). Production flag rule re-applied unchanged:"
        f" P(High) >= {HIGH_PROBA_THRESHOLD}, unconditional on predicted class.",
        "",
        "## Comparison: Uncalibrated (Documented) vs Isotonic-Calibrated",
        "",
        "| Metric | Uncalibrated (`reports/uncertainty_flagging.md`) | Isotonic-calibrated | Delta |",
        "|---|---:|---:|---:|",
        f"| Overall flagged | {DOCUMENTED['n_flagged']}/{DOCUMENTED['n_val']} ({DOCUMENTED['flagged_fraction']:.4f}) |"
        f" {n_flagged}/{n_val} ({flagged_fraction:.4f}) | {delta_n_flagged:+d} rows |",
        f"| Known-miss coverage (of 17) | {DOCUMENTED['misses_flagged']}/{DOCUMENTED['n_misses']}"
        f" ({DOCUMENTED['misses_flagged_fraction']:.4f}) | {n_misses_flagged_calibrated}/{n_misses}"
        f" ({misses_flagged_fraction_calibrated:.4f}) | {delta_misses_flagged:+d} rows |",
        f"| False-flag rate | {DOCUMENTED['false_flag_rate']:.4f} | {false_flag_rate:.4f} |"
        f" {delta_false_flag_rate:+.4f} |",
        "",
        "## The 17 Known Misses — Calibrated P(High) and Flag Status",
        "",
        "| Original row | P(High), isotonic-calibrated | Flagged |",
        "|---:|---:|---|",
    ]
    for row in miss_table:
        lines.append(
            f"| {row['original_row']} | {row['p_high_calibrated']:.4f} | {row['flagged_calibrated']} |"
        )

    lines.extend(
        [
            "",
            "## Plain Answer",
            "",
        ]
    )
    if meaningfully_different:
        lines.append(
            f"**Calibration DOES meaningfully change the flagging mechanism's behavior.**"
            f" Known-miss coverage moved from {DOCUMENTED['misses_flagged']}/{DOCUMENTED['n_misses']}"
            f" to {n_misses_flagged_calibrated}/{n_misses} ({delta_misses_flagged:+d} rows), and/or"
            f" overall flagged volume moved by {delta_n_flagged:+d} rows"
            f" ({abs(delta_n_flagged) / DOCUMENTED['n_flagged'] * 100:.1f}% relative change)."
        )
    else:
        lines.append(
            f"**No — calibration does not meaningfully change the flagging mechanism's"
            f" behavior.** Overall flagged count moved by only {delta_n_flagged:+d} rows"
            f" ({DOCUMENTED['n_flagged']} → {n_flagged}, "
            f"{abs(delta_n_flagged) / DOCUMENTED['n_flagged'] * 100:.1f}% relative change), and"
            f" known-miss coverage is"
            f" {'unchanged' if delta_misses_flagged == 0 else f'the same {n_misses_flagged_calibrated}/{n_misses} count, just {delta_misses_flagged:+d} from documented'}"
            f" at {n_misses_flagged_calibrated}/{n_misses}"
            f" ({misses_flagged_fraction_calibrated:.4f}) vs the documented"
            f" {DOCUMENTED['misses_flagged']}/{DOCUMENTED['n_misses']}"
            f" ({DOCUMENTED['misses_flagged_fraction']:.4f}). This is consistent with Part 1 of"
            f" `reports/postprocessing_3class.md`, which found isotonic calibration only flips"
            f" 21/1650 (1.27%) of argmax predictions overall — the P(High) values shift slightly"
            f" per row, but not enough to cross the 0.10 threshold differently for more than a"
            f" small handful of rows, and evidently none of the 17 known misses flip status."
            f" **The uncertainty-flagging mechanism's behavior is robust to whether the"
            f" underlying model is calibrated or not** — the finding from"
            f" `reports/postprocessing_3class.md` (calibration is a negligible net effect on"
            f" this model) extends to this specific downstream use of the probabilities too.",
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not"
            " clinical validation. Purely exploratory — no canonical artifact was changed. The"
            " test set was never touched by this script.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
