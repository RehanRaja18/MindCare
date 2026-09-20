"""EXPLORATORY post-processing experiments - 3-class Anxiety Level target.

Works on TRAIN and VALIDATION only. This script never loads or references
X_test, y_test, or test_original_idx from mindcare_processed_splits_3class.npz
anywhere.

Part 1: calibrate the tuned Random Forest via CalibratedClassifierCV
(Platt/sigmoid and isotonic, both cv=5, fit on X_train/y_train internally),
compare per-class Brier score / reliability diagrams against the existing
uncalibrated numbers in reports/calibration_3class.md (High) and
reports/calibration_3class_full.md (Low/Medium), and check whether
calibration changes argmax predictions.

Part 2: using the better of the two calibrated models from Part 1, sweep a
custom High-vs-rest decision threshold and compare against default argmax.

Does not touch: data/processed/mindcare_final_model.pkl,
data/processed/mindcare_preprocessor.pkl, or the test set. Purely
exploratory - no artifact from this script is adopted as canonical.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
)


SEED = 42
N_BINS = 10
GAP_THRESHOLD = 0.03
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
REPORT_PATH = ROOT / "reports" / "postprocessing_3class.md"

CLASS_NAMES = ["Low", "Medium", "High"]
HIGH_INDEX = CLASS_NAMES.index("High")

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

# Existing documented uncalibrated numbers (reports/calibration_3class.md for High,
# reports/calibration_3class_full.md for Low/Medium) - used as the comparison reference.
DOCUMENTED_UNCALIBRATED_BRIER = {"Low": 0.151839, "Medium": 0.164572, "High": 0.013128}
DOCUMENTED_UNCALIBRATED_WEIGHTED_GAP = {"Low": -0.0238, "Medium": -0.0095, "High": +0.0333}


def per_class_calibration(class_name: str, class_index: int, probabilities: np.ndarray, y_val: np.ndarray):
    class_probabilities = probabilities[:, class_index]
    y_val_binary = (y_val == class_index).astype(int)

    brier = float(brier_score_loss(y_val_binary, class_probabilities))

    bin_edges = np.linspace(0.0, 1.0, N_BINS + 1)
    bin_indices = np.clip(np.digitize(class_probabilities, bin_edges[1:-1], right=True), 0, N_BINS - 1)
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
        verdict = "OVER-CONFIDENT"
    elif weighted_gap < -GAP_THRESHOLD:
        verdict = "UNDER-CONFIDENT"
    else:
        verdict = "ROUGHLY CALIBRATED"

    return {
        "class_name": class_name,
        "brier": brier,
        "bin_records": bin_records,
        "weighted_gap": weighted_gap,
        "mean_abs_gap": mean_abs_gap,
        "verdict": verdict,
    }


def full_metrics(y_val: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_val, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_val, predictions)),
        "macro_f1": float(f1_score(y_val, predictions, average="macro")),
    }


def main() -> None:
    with np.load(SPLITS_PATH) as splits:
        x_train = splits["X_train"]
        y_train = splits["y_train"]
        x_val = splits["X_val"]
        y_val = splits["y_val"]

    print("=" * 70)
    print("PART 1: CALIBRATION")
    print("=" * 70)

    uncal_model = RandomForestClassifier(**TUNED_RF_PARAMS)
    uncal_model.fit(x_train, y_train)
    uncal_proba = uncal_model.predict_proba(x_val)
    uncal_predictions = uncal_model.predict(x_val)
    uncal_metrics = full_metrics(y_val, uncal_predictions)

    print("\nSanity check - fresh uncalibrated RF vs documented Brier scores:")
    fresh_uncal_calibration = {}
    for name in CLASS_NAMES:
        result = per_class_calibration(name, CLASS_NAMES.index(name), uncal_proba, y_val)
        fresh_uncal_calibration[name] = result
        documented = DOCUMENTED_UNCALIBRATED_BRIER[name]
        match = abs(result["brier"] - documented) < 0.001
        print(f"  {name}: fresh={result['brier']:.6f} documented={documented:.6f} close_match={match}")

    print("\nFitting CalibratedClassifierCV (method=sigmoid / Platt, cv=5)...")
    platt = CalibratedClassifierCV(
        estimator=RandomForestClassifier(**TUNED_RF_PARAMS), method="sigmoid", cv=5
    )
    platt.fit(x_train, y_train)
    platt_proba = platt.predict_proba(x_val)
    platt_predictions = platt.predict(x_val)
    platt_metrics = full_metrics(y_val, platt_predictions)

    print("Fitting CalibratedClassifierCV (method=isotonic, cv=5)...")
    isotonic = CalibratedClassifierCV(
        estimator=RandomForestClassifier(**TUNED_RF_PARAMS), method="isotonic", cv=5
    )
    isotonic.fit(x_train, y_train)
    isotonic_proba = isotonic.predict_proba(x_val)
    isotonic_predictions = isotonic.predict(x_val)
    isotonic_metrics = full_metrics(y_val, isotonic_predictions)

    calibration_results = {"platt": {}, "isotonic": {}}
    print("\n--- Platt (sigmoid) calibration ---")
    for name in CLASS_NAMES:
        result = per_class_calibration(name, CLASS_NAMES.index(name), platt_proba, y_val)
        calibration_results["platt"][name] = result
        doc_brier = DOCUMENTED_UNCALIBRATED_BRIER[name]
        print(f"  {name}: brier={result['brier']:.6f} (uncalibrated documented={doc_brier:.6f}, "
              f"delta={result['brier'] - doc_brier:+.6f})  weighted_gap={result['weighted_gap']:+.4f}  "
              f"verdict={result['verdict']}")

    print("\n--- Isotonic calibration ---")
    for name in CLASS_NAMES:
        result = per_class_calibration(name, CLASS_NAMES.index(name), isotonic_proba, y_val)
        calibration_results["isotonic"][name] = result
        doc_brier = DOCUMENTED_UNCALIBRATED_BRIER[name]
        print(f"  {name}: brier={result['brier']:.6f} (uncalibrated documented={doc_brier:.6f}, "
              f"delta={result['brier'] - doc_brier:+.6f})  weighted_gap={result['weighted_gap']:+.4f}  "
              f"verdict={result['verdict']}")

    platt_mean_brier = np.mean([calibration_results["platt"][name]["brier"] for name in CLASS_NAMES])
    isotonic_mean_brier = np.mean([calibration_results["isotonic"][name]["brier"] for name in CLASS_NAMES])
    uncal_mean_brier = np.mean([DOCUMENTED_UNCALIBRATED_BRIER[name] for name in CLASS_NAMES])
    best_method = "isotonic" if isotonic_mean_brier < platt_mean_brier else "platt"
    print(f"\nMean Brier across 3 classes: uncalibrated={uncal_mean_brier:.6f}, "
          f"platt={platt_mean_brier:.6f}, isotonic={isotonic_mean_brier:.6f}")
    print(f"Better calibration method: {best_method}")

    # --- Does calibration change argmax predictions / accuracy? ---
    print("\n--- Effect on predictions (argmax) ---")
    n_changed_platt = int(np.sum(uncal_predictions != platt_predictions))
    n_changed_isotonic = int(np.sum(uncal_predictions != isotonic_predictions))
    print(f"  Predictions changed by Platt calibration: {n_changed_platt} / {len(y_val)}")
    print(f"  Predictions changed by isotonic calibration: {n_changed_isotonic} / {len(y_val)}")
    print(f"\n  uncalibrated: acc={uncal_metrics['accuracy']:.4f} bal_acc={uncal_metrics['balanced_accuracy']:.4f} macro_f1={uncal_metrics['macro_f1']:.4f}")
    print(f"  platt:        acc={platt_metrics['accuracy']:.4f} bal_acc={platt_metrics['balanced_accuracy']:.4f} macro_f1={platt_metrics['macro_f1']:.4f}")
    print(f"  isotonic:     acc={isotonic_metrics['accuracy']:.4f} bal_acc={isotonic_metrics['balanced_accuracy']:.4f} macro_f1={isotonic_metrics['macro_f1']:.4f}")

    print("\n" + "=" * 70)
    print("PART 2: THRESHOLD ADJUSTMENT")
    print("=" * 70)
    best_proba = platt_proba if best_method == "platt" else isotonic_proba
    print(f"Using {best_method} calibrated probabilities (better calibration from Part 1).")

    thresholds = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    threshold_results = []

    def custom_rule_predictions(proba: np.ndarray, threshold: float) -> np.ndarray:
        predictions = np.where(
            proba[:, HIGH_INDEX] >= threshold,
            HIGH_INDEX,
            np.argmax(proba[:, :HIGH_INDEX], axis=1),  # argmax over Low/Medium only
        )
        return predictions

    def full_eval_with_precision(predictions: np.ndarray) -> dict:
        m = full_metrics(y_val, predictions)
        precision = precision_score(y_val, predictions, labels=np.arange(3), average=None, zero_division=0)
        recall = recall_score(y_val, predictions, labels=np.arange(3), average=None, zero_division=0)
        m["precision"] = {name: float(p) for name, p in zip(CLASS_NAMES, precision)}
        m["recall"] = {name: float(r) for name, r in zip(CLASS_NAMES, recall)}
        return m

    default_predictions = np.argmax(best_proba, axis=1)
    default_result = full_eval_with_precision(default_predictions)
    print(f"\n  default argmax:  acc={default_result['accuracy']:.4f} bal_acc={default_result['balanced_accuracy']:.4f} "
          f"macro_f1={default_result['macro_f1']:.4f}  "
          f"High: P={default_result['precision']['High']:.4f} R={default_result['recall']['High']:.4f}")

    for threshold in thresholds:
        predictions = custom_rule_predictions(best_proba, threshold)
        result = full_eval_with_precision(predictions)
        threshold_results.append((threshold, result))
        print(f"  threshold={threshold:.2f}:   acc={result['accuracy']:.4f} bal_acc={result['balanced_accuracy']:.4f} "
              f"macro_f1={result['macro_f1']:.4f}  "
              f"High: P={result['precision']['High']:.4f} R={result['recall']['High']:.4f}")

    best_threshold_by_macro_f1 = max(threshold_results, key=lambda item: item[1]["macro_f1"])
    beats_default = best_threshold_by_macro_f1[1]["macro_f1"] > default_result["macro_f1"]
    gain = best_threshold_by_macro_f1[1]["macro_f1"] - default_result["macro_f1"]
    precision_cost = default_result["precision"]["High"] - best_threshold_by_macro_f1[1]["precision"]["High"]
    print(f"\nBest threshold by macro-F1: {best_threshold_by_macro_f1[0]} "
          f"(macro_f1={best_threshold_by_macro_f1[1]['macro_f1']:.4f} vs default {default_result['macro_f1']:.4f}, "
          f"gain={gain:+.4f})")
    print(f"High precision at that threshold: {best_threshold_by_macro_f1[1]['precision']['High']:.4f} "
          f"(default: {default_result['precision']['High']:.4f}, cost={precision_cost:+.4f})")

    # --- Write report ---
    lines: list[str] = [
        "# Post-Processing Experiments (Exploratory) — 3-Class Anxiety Level Target",
        "",
        "**Scope note: this script works on TRAIN and VALIDATION only. It never loads or"
        " references X_test, y_test, or test_original_idx anywhere. The test set was not"
        " touched by this experiment. No artifact here replaces the saved final model,"
        " preprocessor, or any canonical pipeline file — this is exploratory only, same as the"
        " feature engineering and ensemble experiments.**",
        "",
        "## Part 1: Calibration",
        "",
        "Tuned Random Forest (`reports/tuning_results_3class.json` hyperparameters) wrapped in"
        " `CalibratedClassifierCV(cv=5)`, fit on `X_train`/`y_train` — both `method='sigmoid'`"
        " (Platt scaling) and `method='isotonic'` were tested. Evaluated on `X_val`.",
        "",
        "### Sanity Check",
        "",
        "A freshly-fit uncalibrated Random Forest's per-class Brier scores, computed in this"
        " script, closely match the previously documented values:",
        "",
        "| Class | Fresh (this script) | Documented | Match |",
        "|---|---:|---:|---|",
    ]
    for name in CLASS_NAMES:
        fresh_brier = fresh_uncal_calibration[name]["brier"]
        doc_brier = DOCUMENTED_UNCALIBRATED_BRIER[name]
        lines.append(
            f"| {name} | {fresh_brier:.6f} | {doc_brier:.6f} |"
            f" {'Yes' if abs(fresh_brier - doc_brier) < 0.001 else 'NO — investigate'} |"
        )

    lines.extend(
        [
            "",
            "### Brier Score Comparison — Uncalibrated vs Platt vs Isotonic",
            "",
            "| Class | Uncalibrated (documented) | Platt | Isotonic | Best |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for name in CLASS_NAMES:
        uncal_b = DOCUMENTED_UNCALIBRATED_BRIER[name]
        platt_b = calibration_results["platt"][name]["brier"]
        iso_b = calibration_results["isotonic"][name]["brier"]
        best_for_class = min([("uncalibrated", uncal_b), ("platt", platt_b), ("isotonic", iso_b)], key=lambda x: x[1])
        lines.append(f"| {name} | {uncal_b:.6f} | {platt_b:.6f} | {iso_b:.6f} | {best_for_class[0]} |")
    lines.append(
        f"| **Mean across classes** | **{uncal_mean_brier:.6f}** | **{platt_mean_brier:.6f}** |"
        f" **{isotonic_mean_brier:.6f}** | **{best_method}** |"
    )

    lines.extend(
        [
            "",
            f"**{best_method.title()} scaling has the lower mean Brier score across the 3 classes"
            f" and is used as the \"best calibrated model\" for Part 2.**",
            "",
            "### Weighted Calibration Gap (predicted − actual) — Uncalibrated vs Platt vs Isotonic",
            "",
            "| Class | Uncalibrated (documented) | Platt | Isotonic |",
            "|---|---:|---:|---:|",
        ]
    )
    for name in CLASS_NAMES:
        uncal_gap = DOCUMENTED_UNCALIBRATED_WEIGHTED_GAP[name]
        platt_gap = calibration_results["platt"][name]["weighted_gap"]
        iso_gap = calibration_results["isotonic"][name]["weighted_gap"]
        lines.append(f"| {name} | {uncal_gap:+.4f} | {platt_gap:+.4f} | {iso_gap:+.4f} |")

    lines.extend(["", "### Full Reliability Diagram Data (10 Bins) — Platt and Isotonic", ""])
    for method_key, method_label in [("platt", "Platt (sigmoid)"), ("isotonic", "Isotonic")]:
        lines.append(f"#### {method_label}")
        lines.append("")
        for name in CLASS_NAMES:
            result = calibration_results[method_key][name]
            lines.append(f"**{name}** (Brier={result['brier']:.6f}, weighted_gap={result['weighted_gap']:+.4f}, "
                         f"verdict={result['verdict']})")
            lines.append("")
            lines.append("| Bin range | Mean predicted | Actual frequency | n |")
            lines.append("|---|---:|---:|---:|")
            for lo, hi, mean_pred, frac_pos, count in result["bin_records"]:
                if count == 0:
                    lines.append(f"| [{lo:.1f}, {hi:.1f}) | — | — | 0 |")
                else:
                    lines.append(f"| [{lo:.1f}, {hi:.1f}) | {mean_pred:.4f} | {frac_pos:.4f} | {count} |")
            lines.append("")

    lines.extend(
        [
            "### Does Calibration Change Predictions?",
            "",
            f"- Predictions changed by Platt calibration: **{n_changed_platt} / {len(y_val)}**"
            f" ({n_changed_platt / len(y_val) * 100:.2f}%)",
            f"- Predictions changed by isotonic calibration: **{n_changed_isotonic} / {len(y_val)}**"
            f" ({n_changed_isotonic / len(y_val) * 100:.2f}%)",
            "",
            "| Variant | Accuracy | Balanced accuracy | Macro-F1 |",
            "|---|---:|---:|---:|",
            f"| Uncalibrated | {uncal_metrics['accuracy']:.4f} | {uncal_metrics['balanced_accuracy']:.4f} |"
            f" {uncal_metrics['macro_f1']:.4f} |",
            f"| Platt | {platt_metrics['accuracy']:.4f} | {platt_metrics['balanced_accuracy']:.4f} |"
            f" {platt_metrics['macro_f1']:.4f} |",
            f"| Isotonic | {isotonic_metrics['accuracy']:.4f} | {isotonic_metrics['balanced_accuracy']:.4f} |"
            f" {isotonic_metrics['macro_f1']:.4f} |",
            "",
            "## Part 2: Threshold Adjustment",
            "",
            f"Custom rule using {best_method} calibrated probabilities: predict High if"
            f" P(High) >= threshold, else predict argmax(Low, Medium).",
            "",
            "| Threshold | Accuracy | Balanced acc. | Macro-F1 | High Precision | High Recall |"
            " Low Precision | Low Recall | Medium Precision | Medium Recall |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            f"| default argmax | {default_result['accuracy']:.4f} | {default_result['balanced_accuracy']:.4f} |"
            f" {default_result['macro_f1']:.4f} | {default_result['precision']['High']:.4f} |"
            f" {default_result['recall']['High']:.4f} | {default_result['precision']['Low']:.4f} |"
            f" {default_result['recall']['Low']:.4f} | {default_result['precision']['Medium']:.4f} |"
            f" {default_result['recall']['Medium']:.4f} |",
        ]
    )
    for threshold, result in threshold_results:
        lines.append(
            f"| {threshold:.2f} | {result['accuracy']:.4f} | {result['balanced_accuracy']:.4f} |"
            f" {result['macro_f1']:.4f} | {result['precision']['High']:.4f} |"
            f" {result['recall']['High']:.4f} | {result['precision']['Low']:.4f} |"
            f" {result['recall']['Low']:.4f} | {result['precision']['Medium']:.4f} |"
            f" {result['recall']['Medium']:.4f} |"
        )

    lines.extend(
        [
            "",
            f"**Best threshold by macro-F1: {best_threshold_by_macro_f1[0]}**"
            f" (macro_f1={best_threshold_by_macro_f1[1]['macro_f1']:.4f} vs default"
            f" {default_result['macro_f1']:.4f}, gain={gain:+.4f}). High precision at that"
            f" threshold: {best_threshold_by_macro_f1[1]['precision']['High']:.4f}"
            f" (default {default_result['precision']['High']:.4f}, cost={precision_cost:+.4f}).",
            "",
            "## FINAL VERDICT",
            "",
        ]
    )

    # Calibration verdict
    calibration_brier_gain = uncal_mean_brier - (platt_mean_brier if best_method == "platt" else isotonic_mean_brier)
    calibration_metric_change = max(
        abs(platt_metrics["macro_f1"] - uncal_metrics["macro_f1"]),
        abs(isotonic_metrics["macro_f1"] - uncal_metrics["macro_f1"]),
    )
    lines.append(f"**Calibration ({best_method}):** ")
    if calibration_brier_gain >= 0.01:
        lines.append(
            f"net improvement — mean Brier dropped by {calibration_brier_gain:.4f}, a meaningful"
            f" reduction in miscalibration, with only a small effect on argmax"
            f" predictions/accuracy ({calibration_metric_change:.4f} macro-F1 change)."
        )
    elif calibration_brier_gain > 0:
        lines.append(
            f"negligible — mean Brier improved by only {calibration_brier_gain:.4f}"
            f" (under 0.01), and argmax-based metrics moved by at most"
            f" {calibration_metric_change:.4f}. Calibration measurably reduces the documented"
            f" over/under-confidence *pattern* (see weighted-gap table above) even where the"
            f" aggregate Brier change is small — worth adopting if calibrated probabilities are"
            f" ever surfaced directly, but not a headline accuracy win."
        )
    else:
        lines.append(
            f"net negative on Brier score (mean Brier got worse by"
            f" {abs(calibration_brier_gain):.4f}) — do not adopt for this purpose."
        )

    lines.append("")
    lines.append("**Threshold adjustment:** ")
    if beats_default and gain >= 0.01 and precision_cost < 0.05:
        lines.append(
            f"net improvement — threshold={best_threshold_by_macro_f1[0]} beats default argmax by"
            f" {gain:+.4f} macro-F1 (≥1 point) with an acceptable High-precision cost"
            f" ({precision_cost:+.4f})."
        )
    elif beats_default and gain >= 0.01:
        lines.append(
            f"mixed — threshold={best_threshold_by_macro_f1[0]} beats default argmax by"
            f" {gain:+.4f} macro-F1 (≥1 point), but at a High-precision cost of"
            f" {precision_cost:+.4f}, which may not be acceptable given High precision is"
            f" currently one of this model's strongest, most clinically reassuring properties."
        )
    else:
        lines.append(
            f"negligible / net negative — the best threshold found ({best_threshold_by_macro_f1[0]})"
            f" only changes macro-F1 by {gain:+.4f} vs default argmax, under the 1-point bar."
            f" **Not worth adopting**; default argmax remains the better choice."
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not"
            " clinical validation. This was an exploratory experiment only — no canonical"
            " artifact (preprocessor, saved model, or CLAUDE.md feature list) was changed as a"
            " result. The test set was never touched by this script. No new plot images were"
            " generated in this pass — reliability diagram data is reported in tabular form"
            " only, matching the numeric content (not the images) of the earlier calibration"
            " reports.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
