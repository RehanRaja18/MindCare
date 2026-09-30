"""Nested cross-validation of the full 12-feature XGBoost pipeline (3-class
Anxiety Level target), to estimate how optimistic the single validation-split
figures in reports/model_comparison_12feature.md are.

Data: the train + validation rows only (9,350), read from the raw CSV via the
saved train_original_idx / val_original_idx. The 12-feature splits file has
no test keys; test_original_idx is never loaded from anywhere.

Outer loop: 5-fold stratified on the 3-class label (shuffle, seed 42). Inside
each outer training fold, the whole pipeline is rebuilt from scratch:
  1. Preprocessor (StandardScaler + OneHotEncoder, as in
     src/models/adopt_12feature_model.py) - wrapped in a Pipeline with the
     model, so it is refit inside every INNER split too.
  2. XGBoost tuning exactly as src/models/tune_models_12feature.py does it:
     RandomizedSearchCV, cv=5, balanced-accuracy scoring, the same search
     space, 20 configurations unweighted + 20 with balanced sample weights,
     keeping whichever variant has the better inner CV score.
  3. Review threshold from the inner out-of-fold P(High) of the chosen
     configuration: the HIGHEST threshold that still flags at least 158/165
     (95.76%) of the fold's High cases - the coverage the deployed 0.025 was
     chosen to match. (The highest such threshold = fewest flags; the
     smallest would be 0, which flags everyone.)
The untouched outer fold is then scored, for all rows and for ages 18-49
(the API's supported range).

Writes reports/nested_cv_12feature_xgb.md. Modifies no model, API or doc file.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from src.build_3class_target import bin_anxiety_level
from src.models.tune_models_12feature import XGB_SPACE

SEED = 42
OUTER_FOLDS = 5
INNER_CV = 5
ITER_PER_WEIGHTING = 20
TARGET_COVERAGE = 158 / 165
DEPLOYED_THRESHOLD = 0.025
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_12feature.npz"
COMPARISON_JSON = ROOT / "reports" / "model_comparison_12feature.json"
DEPLOYED_MODEL = ROOT / "data" / "processed" / "mindcare_final_model_12feature_xgb.pkl"
DEPLOYED_PREPROCESSOR = ROOT / "data" / "processed" / "mindcare_preprocessor_12feature.pkl"
REPORT_PATH = ROOT / "reports" / "nested_cv_12feature_xgb.md"
RESULTS_JSON = ROOT / "reports" / "nested_cv_12feature_xgb.json"

NUMERIC = [
    "Sleep Hours", "Physical Activity (hrs/week)", "Caffeine Intake (mg/day)", "Stress Level (1-10)",
    "Heart Rate (bpm)", "Breathing Rate (breaths/min)", "Sweating Level (1-5)",
    "Therapy Sessions (per month)", "Diet Quality (1-10)", "Age",
]
CATEGORICAL = ["Occupation", "Family History of Anxiety"]
FEATURES = NUMERIC + CATEGORICAL
CLASSES = ["Low", "Medium", "High"]
HIGH = 2
METRICS = [
    "accuracy", "balanced_accuracy", "macro_f1", "recall_Low", "recall_Medium", "recall_High",
    "precision_High", "flag_catch_rate", "flag_volume", "brier_Low", "brier_Medium", "brier_High",
]


def make_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])
    model = XGBClassifier(objective="multi:softprob", eval_metric="mlogloss", random_state=SEED, n_jobs=1)
    return Pipeline([("pre", preprocessor), ("xgb", model)])


def coverage_threshold(p_high: np.ndarray, is_high: np.ndarray) -> float:
    """Highest threshold that flags at least TARGET_COVERAGE of the High rows."""
    needed = math.ceil(TARGET_COVERAGE * is_high.sum())
    return float(np.sort(p_high[is_high])[::-1][needed - 1])


def score(y: np.ndarray, prob: np.ndarray, threshold: float) -> dict[str, float]:
    pred = prob.argmax(axis=1)
    recalls = recall_score(y, pred, labels=[0, 1, 2], average=None, zero_division=0)
    flagged = prob[:, HIGH] >= threshold
    return {
        "accuracy": accuracy_score(y, pred),
        "balanced_accuracy": balanced_accuracy_score(y, pred),
        "macro_f1": f1_score(y, pred, average="macro"),
        **{f"recall_{c}": recalls[k] for k, c in enumerate(CLASSES)},
        "precision_High": precision_score(y, pred, labels=[HIGH], average=None, zero_division=0)[0],
        "flag_catch_rate": float(flagged[y == HIGH].mean()),
        "flag_volume": float(flagged.mean()),
        **{f"brier_{c}": brier_score_loss((y == k).astype(int), prob[:, k]) for k, c in enumerate(CLASSES)},
    }


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    with np.load(SPLITS_PATH) as splits:
        assert "X_test" not in splits.files and "test_original_idx" not in splits.files
        rows = np.concatenate([splits["train_original_idx"], splits["val_original_idx"]])
        y_saved = np.concatenate([splits["y_train"], splits["y_val"]])
    data = df.iloc[rows].reset_index(drop=True)
    y = bin_anxiety_level(data["Anxiety Level (1-10)"].to_numpy())
    assert np.array_equal(y, y_saved), "labels rebuilt from the CSV must match the saved splits"
    X = data[FEATURES]
    eligible = (data["Age"] <= 49).to_numpy()
    print(f"Rows: {len(data)} (train + validation), of which ages 18-49: {int(eligible.sum())}")

    outer = StratifiedKFold(OUTER_FOLDS, shuffle=True, random_state=SEED)
    folds = []
    for fold, (tr, te) in enumerate(outer.split(X, y), start=1):
        start = time.time()
        X_tr, y_tr = X.iloc[tr], y[tr]
        weights = compute_sample_weight("balanced", y_tr)

        searches = {}
        for weighting in ("none", "balanced"):
            search = RandomizedSearchCV(
                make_pipeline(),
                {f"xgb__{k}": v for k, v in XGB_SPACE.items()},
                n_iter=ITER_PER_WEIGHTING, scoring="balanced_accuracy", cv=INNER_CV,
                random_state=SEED, n_jobs=-1, refit=True,
            )
            search.fit(X_tr, y_tr, **({"xgb__sample_weight": weights} if weighting == "balanced" else {}))
            searches[weighting] = search
        chosen = max(searches, key=lambda w: searches[w].best_score_)
        best = searches[chosen]

        # Threshold from the chosen configuration's INNER out-of-fold predictions.
        oof = cross_val_predict(
            make_pipeline().set_params(**best.best_params_), X_tr, y_tr, cv=INNER_CV, method="predict_proba",
            params={"xgb__sample_weight": weights} if chosen == "balanced" else None,
        )
        threshold = coverage_threshold(oof[:, HIGH], y_tr == HIGH)

        prob = best.best_estimator_.predict_proba(X.iloc[te])
        y_te, elig_te = y[te], eligible[te]
        folds.append({
            "fold": fold,
            "weighting": chosen,
            "inner_cv": {w: float(s.best_score_) for w, s in searches.items()},
            "params": {k.removeprefix("xgb__"): v for k, v in best.best_params_.items()},
            "threshold": threshold,
            "n_test": int(len(te)), "n_test_eligible": int(elig_te.sum()),
            "all": score(y_te, prob, threshold),
            "eligible": score(y_te[elig_te], prob[elig_te], threshold),
            "all_at_0025": score(y_te, prob, DEPLOYED_THRESHOLD),
            "eligible_at_0025": score(y_te[elig_te], prob[elig_te], DEPLOYED_THRESHOLD),
        })
        f = folds[-1]
        print(f"fold {fold}: {chosen} weights, threshold {threshold:.4f}, bal_acc {f['all']['balanced_accuracy']:.4f}, "
              f"flag catch {f['all']['flag_catch_rate']:.3f} ({time.time() - start:.0f}s)")

    # Validation-split reference: the deployed XGBoost on X_val (all rows and ages 18-49).
    comparison = json.loads(COMPARISON_JSON.read_text(encoding="utf-8"))["xgb_retuned"]
    with np.load(SPLITS_PATH) as splits:
        val_rows, y_val = df.iloc[splits["val_original_idx"]].reset_index(drop=True), splits["y_val"]
    prob_val = joblib.load(DEPLOYED_MODEL).predict_proba(joblib.load(DEPLOYED_PREPROCESSOR).transform(val_rows[FEATURES]))
    val_elig = (val_rows["Age"] <= 49).to_numpy()
    reference = {"all": score(y_val, prob_val, DEPLOYED_THRESHOLD),
                 "eligible": score(y_val[val_elig], prob_val[val_elig], DEPLOYED_THRESHOLD)}
    assert round(reference["all"]["balanced_accuracy"], 4) == round(comparison["validation"]["balanced_accuracy"], 4), \
        "validation reference must match reports/model_comparison_12feature.json"
    RESULTS_JSON.write_text(json.dumps(
        {"folds": folds, "reference": reference, "n_rows": int(len(data)), "n_eligible": int(eligible.sum())},
        indent=2, default=float) + "\n", encoding="utf-8")
    write_report(folds, reference, int(len(data)), int(eligible.sum()))
    print(f"Saved {REPORT_PATH.relative_to(ROOT)} and {RESULTS_JSON.relative_to(ROOT)}")


def write_report(folds: list[dict], reference: dict, n_rows: int, n_eligible: int) -> None:
    def summary(key: str) -> dict[str, tuple[float, float]]:
        return {m: (float(np.mean([f[key][m] for f in folds])), float(np.std([f[key][m] for f in folds])))
                for m in METRICS}

    nested = {k: summary(k) for k in ("all", "eligible", "all_at_0025", "eligible_at_0025")}
    labels = {
        "accuracy": "Accuracy", "balanced_accuracy": "Balanced accuracy", "macro_f1": "Macro-F1",
        "recall_Low": "Recall Low", "recall_Medium": "Recall Medium", "recall_High": "Recall High",
        "precision_High": "Precision High", "flag_catch_rate": "Flag catch rate (High caught)",
        "flag_volume": "Flag volume (share of rows flagged)", "brier_Low": "Brier Low",
        "brier_Medium": "Brier Medium", "brier_High": "Brier High",
    }

    def table(scope: str, flag_note: str) -> list[str]:
        out = [
            "| Metric | Nested CV (mean ± std, 5 folds) | Validation split | Validation − nested mean | In fold-std units |",
            "|---|---:|---:|---:|---:|",
        ]
        for m in METRICS:
            mean, std = nested[scope][m]
            ref = reference[scope][m]
            gap = ref - mean
            out.append(f"| {labels[m]} | {mean:.4f} ± {std:.4f} | {ref:.4f} | {gap:+.4f} | "
                       f"{(gap / std if std > 0 else float('nan')):+.1f} |")
        out.append("")
        out.append(flag_note + " For every metric except Brier and flag volume, a positive difference means"
                   " the validation split looked better than nested CV. For Brier and flag volume (lower is"
                   " better), a negative difference means that. \"Fold-std units\" divide the difference by the"
                   " spread between the 5 outer folds.")
        return out

    lower_is_better = {"flag_volume", "brier_Low", "brier_Medium", "brier_High"}

    def verdict(scope: str) -> str:
        # "Advantage" = how much better the validation split looked than nested CV (sign-adjusted).
        advantage = {
            m: (nested[scope][m][0] - reference[scope][m]) if m in lower_is_better
            else (reference[scope][m] - nested[scope][m][0])
            for m in METRICS
        }
        optimistic = [m for m in METRICS if advantage[m] > nested[scope][m][1]]
        pessimistic = [m for m in METRICS if -advantage[m] > nested[scope][m][1]]
        headline = ("accuracy", "balanced_accuracy", "macro_f1")
        direction = "optimistic" if np.mean([advantage[m] for m in headline]) > 0 else "pessimistic"
        text = (
            f"**Headline metrics: the validation split was {direction}.** Relative to nested CV, validation"
            f" looked {'better' if direction == 'optimistic' else 'worse'} on accuracy"
            f" ({advantage['accuracy']:+.4f}), balanced accuracy ({advantage['balanced_accuracy']:+.4f}) and"
            f" macro-F1 ({advantage['macro_f1']:+.4f}); positive = validation looked better."
        )

        def describe(ms: list[str]) -> str:
            return ", ".join(f"{labels[m]} ({advantage[m]:+.4f})" for m in ms)

        text += (
            f" Beyond one fold-std, validation was **optimistic** on: {describe(optimistic)}."
            if optimistic else " Validation was not optimistic beyond one fold-std on any metric."
        )
        text += (
            f" It was **pessimistic** beyond one fold-std on: {describe(pessimistic)}."
            if pessimistic else ""
        )
        return text

    flag_all = nested["all"]
    lines = [
        "# Nested Cross-Validation — 12-Feature XGBoost Pipeline (3-Class Anxiety Level)",
        "",
        "Script: `src/evaluation/nested_cv_12feature_xgb.py`. Estimates how the whole pipeline — preprocessing,"
        " tuning and threshold choice — performs on data it never saw, and compares that with the single"
        " validation-split figures in `reports/model_comparison_12feature.md`.",
        "",
        "## Setup",
        "",
        f"- **Data:** the {n_rows} train + validation rows only, read from the raw CSV via the saved"
        " `train_original_idx` / `val_original_idx`. Labels rebuilt from `Anxiety Level (1-10)` and checked"
        " against the saved splits. **The test set was not loaded** (the 12-feature splits file has no test"
        " keys, and `test_original_idx` is never read).",
        f"- **Outer loop:** 5-fold stratified on the 3-class label (shuffled, seed {SEED}).",
        "- **Inside each outer training fold, rebuilt from scratch:**",
        "  1. The preprocessor (StandardScaler + OneHotEncoder), inside a Pipeline with the model, so it is"
        " refit inside every inner split too.",
        "  2. XGBoost tuning, as in `src/models/tune_models_12feature.py`: RandomizedSearchCV, inner cv=5,"
        " balanced-accuracy scoring, the same search space, **20 configurations unweighted + 20 with balanced"
        " sample weights**, keeping the better. (This matches what the real pipeline did; the request specified"
        " balanced weights only, but the deployed model came from the both-ways search, where unweighted won.)",
        "  3. The review threshold, from the chosen configuration's inner out-of-fold P(High): the **highest**"
        " threshold that still flags at least 158/165 (95.76%) of High cases. That is the coverage the deployed"
        " 0.025 was chosen to match, with the fewest flags. (The *smallest* threshold meeting the target would"
        " be 0, which flags everyone.)",
        "- **Scored on the untouched outer fold:** all rows, and ages 18-49 only (the API's supported range).",
        "- **Validation-split reference:** the deployed model (`mindcare_final_model_12feature_xgb.pkl`) on"
        " `X_val` at its 0.025 threshold. The all-rows headline figures match `reports/model_comparison_12feature.md`"
        " (checked in the script); the 18-49 figures are computed the same way on that subset.",
        "",
        "## Per-Fold Choices",
        "",
        "| Fold | Test rows (18-49) | Weighting chosen | Inner CV bal. acc. (none / balanced) | Threshold | Key params |",
        "|---:|---:|---|---|---:|---|",
    ]
    for f in folds:
        p = f["params"]
        lines.append(
            f"| {f['fold']} | {f['n_test']} ({f['n_test_eligible']}) | {f['weighting']} |"
            f" {f['inner_cv']['none']:.4f} / {f['inner_cv']['balanced']:.4f} | {f['threshold']:.4f} |"
            f" {p['n_estimators']} trees, depth {p['max_depth']}, lr {p['learning_rate']} |"
        )
    thresholds = [f["threshold"] for f in folds]
    lines += [
        "",
        f"Chosen threshold: mean {np.mean(thresholds):.4f} ± {np.std(thresholds):.4f}"
        f" (range {min(thresholds):.4f}-{max(thresholds):.4f}); the deployed threshold is {DEPLOYED_THRESHOLD}.",
        "",
        "## Results — All Rows",
        "",
        *table("all", "Flag rows use each fold's own threshold (above); the validation column uses the deployed 0.025."),
        "",
        verdict("all"),
        "",
        "## Results — Ages 18-49 (the API's supported range)",
        "",
        *table("eligible", "Same thresholds as above; only the scored rows are restricted to ages 18-49."),
        "",
        verdict("eligible"),
        "",
        "## The Flag at the Deployed 0.025 (for reference)",
        "",
        "The same outer-fold models, flagged at the fixed deployed threshold instead of each fold's own:",
        "",
        "| Scope | Flag catch rate | Flag volume |",
        "|---|---:|---:|",
        f"| All rows | {nested['all_at_0025']['flag_catch_rate'][0]:.4f} ± {nested['all_at_0025']['flag_catch_rate'][1]:.4f}"
        f" | {nested['all_at_0025']['flag_volume'][0]:.4f} ± {nested['all_at_0025']['flag_volume'][1]:.4f} |",
        f"| Ages 18-49 | {nested['eligible_at_0025']['flag_catch_rate'][0]:.4f} ± {nested['eligible_at_0025']['flag_catch_rate'][1]:.4f}"
        f" | {nested['eligible_at_0025']['flag_volume'][0]:.4f} ± {nested['eligible_at_0025']['flag_volume'][1]:.4f} |",
        "",
        f"With each fold's own threshold, the flag caught {flag_all['flag_catch_rate'][0]:.1%} of High cases on"
        f" average against a {TARGET_COVERAGE:.1%} target set on inner out-of-fold data.",
        "",
        "## What This Does NOT Cover",
        "",
        "Nested CV only makes the steps **inside** the loop honest. Several decisions were made **outside** it,"
        " using this same train + validation data, so their optimism is not measured here:",
        "",
        "- **The 17 → 11 → 12 feature reduction.** The features were chosen from SHAP rankings and validation"
        " results on these rows (`reports/feature_reduction_3class.md`, `reports/feature_addition_age_3class.md`).",
        "- **Choosing XGBoost over Random Forest** (`reports/model_comparison_12feature.md`), made on validation"
        " and cross-validation results from these rows.",
        "- **The coverage target itself (158/165)**, which was copied from the Random Forest's validation result.",
        "- **The search space, the Low/Medium/High label boundaries and the 18-49 age limit**, all set after"
        " looking at this data.",
        "",
        "So these numbers are an honest estimate for *re-running this pipeline*, not for the whole path of"
        " decisions that led to it. Only fresh data can check that. The 3-class test set is already spent (used"
        " twice), and the dataset is very likely synthetic (see CLAUDE.md) — none of this is clinical validation.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
