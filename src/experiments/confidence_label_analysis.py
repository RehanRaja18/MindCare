"""Evidence for a "confident" / "borderline" label on each prediction (canonical
11-feature v2 XGBoost, 3-class Anxiety Level target).

Idea: the model's top-class probability ("confidence") separates predictions it
tends to get right from ones it tends to get wrong. Most errors sit at the class
borders (Anxiety Level 3 vs 4, and 6 vs 7), where the inputs can't tell patients
apart. Labelling low-confidence predictions "borderline" tells the reviewing
psychologist which predictions need their own judgement most. It changes no
prediction and is not a way to raise overall accuracy.

Measured two ways, TRAIN + VALIDATION only (the 11-feature v2 splits file has no
test keys; the 3-class test set is spent):
  1. Out-of-fold: 5-fold stratified CV over the 9,350 rows, preprocessing and
     model refit in every fold with the deployed hyperparameters, so every row
     is scored by a model that never saw it. This is the primary evidence.
  2. The deployed model on the 1,650-row validation split.

Writes reports/confidence_label_11feature_v2.md and .json. Changes no model,
API, test or doc file.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from src.build_3class_target import bin_anxiety_level
from src.models.adopt_11feature_v2_model import CATEGORICAL_FEATURES, NUMERIC_FEATURES

SEED = 42
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_11feature_v2.npz"
MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model_11feature_v2_xgb.pkl"
PREPROCESSOR_PATH = ROOT / "data" / "processed" / "mindcare_preprocessor_11feature_v2.pkl"
TUNING_PATH = ROOT / "reports" / "tuning_results_12feature.json"
REPORT_PATH = ROOT / "reports" / "confidence_label_11feature_v2.md"
JSON_PATH = ROOT / "reports" / "confidence_label_11feature_v2.json"

CLASSES = ["Low", "Medium", "High"]
HIGH = 2
THRESHOLDS = [0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.90]
CHOSEN = 0.70
FLAG_THRESHOLD = 0.025
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def summarise(y: np.ndarray, prob: np.ndarray, threshold: float) -> dict:
    pred, conf = prob.argmax(axis=1), prob.max(axis=1)
    confident = conf >= threshold
    correct = pred == y
    top2 = np.sort(np.argsort(prob, axis=1)[:, -2:], axis=1)
    pairs = {}
    for a, b in [(0, 1), (1, 2), (0, 2)]:
        mask = ~confident & (top2[:, 0] == a) & (top2[:, 1] == b)
        pairs[f"{CLASSES[a]}/{CLASSES[b]}"] = int(mask.sum())
    is_high = y == HIGH
    flagged = prob[:, HIGH] >= FLAG_THRESHOLD
    return {
        "threshold": threshold,
        "confident_share": float(confident.mean()),
        "accuracy_confident": float(correct[confident].mean()) if confident.any() else None,
        "accuracy_borderline": float(correct[~confident].mean()) if (~confident).any() else None,
        "errors_total": int((~correct).sum()),
        "errors_in_borderline": int((~correct & ~confident).sum()),
        "confident_but_wrong": int((~correct & confident).sum()),
        "borderline_pairs": pairs,
        "per_class_confident_accuracy": {
            c: (float(correct[confident & (pred == k)].mean()) if (confident & (pred == k)).any() else None)
            for k, c in enumerate(CLASSES)},
        "per_class_confident_count": {c: int((confident & (pred == k)).sum()) for k, c in enumerate(CLASSES)},
        "true_high_total": int(is_high.sum()),
        "true_high_confident_and_labelled_high": int((is_high & confident & (pred == HIGH)).sum()),
        "true_high_confident_but_not_high": int((is_high & confident & (pred != HIGH)).sum()),
        "true_high_confident_not_high_and_unflagged": int((is_high & confident & (pred != HIGH) & ~flagged).sum()),
    }


def shipped_rule(y: np.ndarray, prob: np.ndarray) -> dict:
    """The rule the API ships: confident only if the top probability is >= CHOSEN and the
    prediction is not a flagged non-High one (P(High) >= FLAG_THRESHOLD while predicting Low or
    Medium). The second condition stops a possibly-High patient being presented as a confident
    Low/Medium."""
    pred, conf = prob.argmax(axis=1), prob.max(axis=1)
    flagged_not_high = (prob[:, HIGH] >= FLAG_THRESHOLD) & (pred != HIGH)
    confident = (conf >= CHOSEN) & ~flagged_not_high
    correct, is_high = pred == y, y == HIGH
    return {
        "confident_share": float(confident.mean()),
        "accuracy_confident": float(correct[confident].mean()),
        "accuracy_borderline": float(correct[~confident].mean()),
        "errors_total": int((~correct).sum()),
        "errors_in_borderline": int((~correct & ~confident).sum()),
        "moved_to_borderline_by_flag": int(((conf >= CHOSEN) & flagged_not_high).sum()),
        "true_high_total": int(is_high.sum()),
        "true_high_confident_high": int((is_high & confident & (pred == HIGH)).sum()),
        "true_high_borderline": int((is_high & ~confident).sum()),
        "true_high_confident_not_high": int((is_high & confident & (pred != HIGH)).sum()),
        "per_class_confident_accuracy": {c: float(correct[confident & (pred == k)].mean()) for k, c in enumerate(CLASSES)},
        "per_class_confident_count": {c: int((confident & (pred == k)).sum()) for k, c in enumerate(CLASSES)},
    }


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    with np.load(SPLITS_PATH) as s:
        assert "X_test" not in s.files and "test_original_idx" not in s.files
        train_idx, val_idx, y_val = s["train_original_idx"], s["val_original_idx"], s["y_val"]
    rows = df.iloc[np.concatenate([train_idx, val_idx])].reset_index(drop=True)
    y = bin_anxiety_level(rows["Anxiety Level (1-10)"].to_numpy())
    params = json.loads(TUNING_PATH.read_text(encoding="utf-8"))["models"]["xgboost"]["best_params"]

    pipeline = Pipeline([
        ("pre", ColumnTransformer([("num", StandardScaler(), NUMERIC_FEATURES),
                                   ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES)])),
        ("xgb", XGBClassifier(**params, objective="multi:softprob", eval_metric="mlogloss", random_state=SEED, n_jobs=-1)),
    ])
    oof = cross_val_predict(pipeline, rows[FEATURES], y, cv=StratifiedKFold(5, shuffle=True, random_state=SEED),
                            method="predict_proba")
    val_rows = df.iloc[val_idx]
    val_prob = joblib.load(MODEL_PATH).predict_proba(joblib.load(PREPROCESSOR_PATH).transform(val_rows[FEATURES]))
    eligible = (rows["Age"] <= 49).to_numpy()

    results = {
        "rows": {"out_of_fold": int(len(y)), "out_of_fold_ages_18_49": int(eligible.sum()), "validation": int(len(y_val))},
        "overall_accuracy": {"out_of_fold": float((oof.argmax(1) == y).mean()),
                             "validation": float((val_prob.argmax(1) == y_val).mean())},
        "chosen_threshold": CHOSEN,
        "out_of_fold": [summarise(y, oof, t) for t in THRESHOLDS],
        "out_of_fold_ages_18_49": [summarise(y[eligible], oof[eligible], t) for t in THRESHOLDS],
        "validation": [summarise(y_val, val_prob, t) for t in THRESHOLDS],
        "shipped_rule": {"out_of_fold": shipped_rule(y, oof), "out_of_fold_ages_18_49": shipped_rule(y[eligible], oof[eligible]),
                         "validation": shipped_rule(y_val, val_prob)},
    }
    JSON_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    sr = results["shipped_rule"]
    pick = lambda key: next(r for r in results[key] if r["threshold"] == CHOSEN)
    o, v, e = pick("out_of_fold"), pick("validation"), pick("out_of_fold_ages_18_49")

    def table(key: str) -> list[str]:
        out = ["| Confidence cut-off | Labelled confident | Accuracy when confident | Accuracy when borderline | Errors that fall in borderline |",
               "|---:|---:|---:|---:|---:|"]
        for r in results[key]:
            mark = " **(chosen)**" if r["threshold"] == CHOSEN else ""
            out.append(f"| {r['threshold']:.2f}{mark} | {r['confident_share']:.1%} | {r['accuracy_confident']:.4f} |"
                       f" {r['accuracy_borderline']:.4f} | {r['errors_in_borderline']} of {r['errors_total']}"
                       f" ({r['errors_in_borderline'] / r['errors_total']:.1%}) |")
        return out

    lines = [
        "# Confident / Borderline Label — Evidence (11-Feature v2 XGBoost, 3-Class Target)",
        "",
        "**Scope: TRAIN and VALIDATION only.** The 11-feature v2 splits file has no test keys and the 3-class test"
        " set is spent. No model, API, test or documentation file was changed by this script"
        " (`src/experiments/confidence_label_analysis.py`). Raw numbers: `reports/confidence_label_11feature_v2.json`.",
        "",
        "## What this is",
        "",
        "Each prediction comes with three probabilities. Call the largest one the model's **confidence**. A"
        " prediction is labelled **confident** when that probability is at least the cut-off, otherwise"
        " **borderline**. The label changes no prediction. It tells the reviewing psychologist which predictions"
        " the model itself is unsure about.",
        "",
        "**This does not make the model more accurate.** Overall accuracy is unchanged"
        f" ({results['overall_accuracy']['out_of_fold']:.4f} out-of-fold, {results['overall_accuracy']['validation']:.4f}"
        " on the validation split). It separates the predictions that are usually right from the ones that are"
        " close to a coin-flip.",
        "",
        "## Method",
        "",
        f"- **Out-of-fold (primary):** 5-fold stratified CV over the {results['rows']['out_of_fold']:,} train + validation"
        " rows. Preprocessing and the model are refit in every fold with the deployed hyperparameters, so each"
        " row is scored by a model that never saw it.",
        f"- **Validation split:** the deployed model on its {results['rows']['validation']:,} validation rows.",
        "- Confidence is the raw top-class probability. XGBoost's probabilities are reasonably calibrated"
        " (calibration error about 1–2 points on the 12-feature model), but they are still not a literal"
        " percentage to show a patient.",
        "",
        "## Results — out-of-fold, all 9,350 rows",
        "",
        *table("out_of_fold"),
        "",
        "## Results — validation split (deployed model)",
        "",
        *table("validation"),
        "",
        f"## The chosen cut-off: {CHOSEN:.2f}",
        "",
        f"- **Out-of-fold:** {o['confident_share']:.1%} of predictions are labelled confident, and they are"
        f" **{o['accuracy_confident']:.1%}** accurate. The borderline {1 - o['confident_share']:.1%} are"
        f" {o['accuracy_borderline']:.1%} accurate. {o['errors_in_borderline']} of {o['errors_total']} errors"
        f" ({o['errors_in_borderline'] / o['errors_total']:.1%}) carry the borderline label.",
        f"- **Validation split:** {v['confident_share']:.1%} confident at {v['accuracy_confident']:.1%};"
        f" borderline {v['accuracy_borderline']:.1%}. The two measurements agree.",
        f"- **Ages 18–49 (the API's range), out-of-fold:** {e['confident_share']:.1%} confident at"
        f" {e['accuracy_confident']:.1%}; borderline {e['accuracy_borderline']:.1%}.",
        "- **Why 0.70:** below it, the confident group's accuracy falls towards the overall figure and the label"
        " says little. Above it, most predictions become borderline and the label stops discriminating. At 0.70"
        " roughly two thirds of predictions are confident, at an accuracy clearly above the overall figure.",
        "",
        "### What borderline predictions are borderline between (out-of-fold)",
        "",
        "| Top two classes | Borderline predictions |",
        "|---|---:|",
        *[f"| {pair} | {n} |" for pair, n in o["borderline_pairs"].items()],
        "",
        "### Confident predictions, by predicted class (out-of-fold)",
        "",
        "| Predicted class | Confident predictions | Accuracy |",
        "|---|---:|---:|",
        *[f"| {c} | {o['per_class_confident_count'][c]} | {o['per_class_confident_accuracy'][c]:.4f} |" for c in CLASSES],
        "",
        "## Safety check: High patients",
        "",
        f"A \"confident\" label must not hide High-risk patients. Out-of-fold, of {o['true_high_total']} true-High"
        f" patients: {o['true_high_confident_and_labelled_high']} are confidently labelled High;"
        f" **{o['true_high_confident_but_not_high']} are confidently labelled something else**; the rest are"
        f" borderline. Of those {o['true_high_confident_but_not_high']}, **{o['true_high_confident_not_high_and_unflagged']}"
        f" are also missed by the priority-review flag** (P(High) ≥ {FLAG_THRESHOLD}). On the validation split the"
        f" same counts are {v['true_high_confident_and_labelled_high']} / {v['true_high_confident_but_not_high']} /"
        f" {v['true_high_confident_not_high_and_unflagged']} of {v['true_high_total']}.",
        "",
        "A plain confidence cut-off would therefore present some High patients as a confident Medium."
        " **The shipped rule closes most of that gap.**",
        "",
        "## The shipped rule",
        "",
        f"A prediction is **confident** only if its top probability is ≥ {CHOSEN:.2f} **and** it is not a flagged"
        f" non-High prediction (P(High) ≥ {FLAG_THRESHOLD} while predicting Low or Medium). Everything else is"
        " **borderline**. So a patient the review flag marks as possibly High is never shown as a confident"
        " Low or Medium.",
        "",
        "| | Out-of-fold, all rows | Out-of-fold, ages 18–49 | Validation split |",
        "|---|---:|---:|---:|",
        *[f"| {label} | {fmt(sr['out_of_fold'][key])} | {fmt(sr['out_of_fold_ages_18_49'][key])} | {fmt(sr['validation'][key])} |"
          for label, key, fmt in [
              ("Labelled confident", "confident_share", lambda x: f"{x:.1%}"),
              ("Accuracy when confident", "accuracy_confident", lambda x: f"{x:.4f}"),
              ("Accuracy when borderline", "accuracy_borderline", lambda x: f"{x:.4f}"),
              ("Moved to borderline by the flag", "moved_to_borderline_by_flag", str),
              ("True-High patients", "true_high_total", str),
              ("… confident, labelled High", "true_high_confident_high", str),
              ("… borderline", "true_high_borderline", str),
              ("… confident, labelled Low/Medium", "true_high_confident_not_high", str),
          ]],
        "",
        f"Out-of-fold, {sr['out_of_fold']['errors_in_borderline']} of {sr['out_of_fold']['errors_total']} errors"
        f" ({sr['out_of_fold']['errors_in_borderline'] / sr['out_of_fold']['errors_total']:.1%}) carry the borderline label."
        " Confident predictions by class (out-of-fold): "
        + "; ".join(f"{c} {sr['out_of_fold']['per_class_confident_count'][c]} at {sr['out_of_fold']['per_class_confident_accuracy'][c]:.4f}" for c in CLASSES)
        + ".",
        "",
        f"The {sr['out_of_fold']['true_high_confident_not_high']} High patients still shown as a confident Low/Medium"
        " out-of-fold are the ones the priority-review flag also misses; no label built on this model's"
        " probabilities can catch them. \"Confident\" means the model is sure of its top class, not that the"
        " patient is safe. Every prediction still goes to a psychologist.",
        "",
        "## Interpretation",
        "",
        "Prototype-model evidence on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation."
        " The cut-off was chosen on the same train + validation rows it is reported on, so the confident-group"
        " accuracy may be slightly optimistic. The test set was never touched.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"out-of-fold @ {CHOSEN}: confident {o['confident_share']:.3f}, acc {o['accuracy_confident']:.4f} / {o['accuracy_borderline']:.4f}")
    print(f"validation  @ {CHOSEN}: confident {v['confident_share']:.3f}, acc {v['accuracy_confident']:.4f} / {v['accuracy_borderline']:.4f}")
    for k, r in sr.items():
        print(f"shipped rule, {k}: confident {r['confident_share']:.3f}, acc {r['accuracy_confident']:.4f} / {r['accuracy_borderline']:.4f}, "
              f"true-High confident-not-High {r['true_high_confident_not_high']}/{r['true_high_total']}")
    print(f"Saved {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
