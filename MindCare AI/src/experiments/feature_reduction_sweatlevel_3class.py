"""EXPLORATORY feature-reduction experiment - can Sweating Level (1-5) be
removed from the canonical 12-feature XGBoost model? 3-class Anxiety Level
target.

Works on TRAIN and VALIDATION only. Reads rows through the 12-feature splits
file's train_original_idx / val_original_idx; that file has no test keys and
test_original_idx is never loaded - the 3-class test set is fully spent (see
CLAUDE.md, "TEST SET USED" entries).

Does not touch: the deployed model (mindcare_final_model_12feature_xgb.pkl, only
read to confirm the baseline reproduces it), the 12-feature preprocessor, the
API, input validation, tests or docs. Purely evidence-gathering.

Steps:
  1. Baseline: refit the deployed 12-feature XGBoost (same preprocessing, same
     hyperparameters from reports/tuning_results_12feature.json) and confirm it
     reproduces the saved model's validation probabilities exactly.
  2. Reduced: the same pipeline with Sweating Level removed (11 features), same
     hyperparameters, new ColumnTransformer fit on train rows only.
  3. Validation-split comparison: accuracy, balanced accuracy, macro-F1,
     per-class precision/recall/F1, and the review flag at 0.025 (plus the
     threshold the 11-feature model needs to match the 12-feature catch rate).
  4. Paired 5-fold CV on train + validation (identical folds for both versions,
     preprocessing refit inside each fold), so each delta can be judged against
     fold-to-fold noise.
  5. Re-tuning check: re-run the deployed tuning procedure (as in
     src/models/tune_models_12feature.py: 20 unweighted + 20 balanced-weight
     configurations, 5-fold CV on train) on the 11 features, to see whether the
     deployed hyperparameters are still the right ones without Sweating Level.
  6. Shortcut stress test: true-High validation patients, Sweating Level forced
     to a constant (3, the train median, plus a 1-5 sweep), 12-feature model vs
     the 11-feature model that never sees it.

Writes reports/feature_reduction_sweatlevel_3class.md and .json.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score, precision_score,
                             recall_score)
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from src.build_3class_target import bin_anxiety_level
from src.models.tune_models_12feature import XGB_SPACE

SEED = 42
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_12feature.npz"
TUNING_PATH = ROOT / "reports" / "tuning_results_12feature.json"
DEPLOYED_MODEL = ROOT / "data" / "processed" / "mindcare_final_model_12feature_xgb.pkl"
DEPLOYED_PREPROCESSOR = ROOT / "data" / "processed" / "mindcare_preprocessor_12feature.pkl"
REPORT_PATH = ROOT / "reports" / "feature_reduction_sweatlevel_3class.md"
JSON_PATH = ROOT / "reports" / "feature_reduction_sweatlevel_3class.json"

FEATURE = "Sweating Level (1-5)"
CONSTANT = 3  # train median (train mean 3.08); mid-point of the 1-5 scale
THRESHOLD = 0.025
CLASSES = ["Low", "Medium", "High"]
HIGH = 2
NUMERIC_12 = [
    "Sleep Hours", "Physical Activity (hrs/week)", "Caffeine Intake (mg/day)", "Stress Level (1-10)",
    "Heart Rate (bpm)", "Breathing Rate (breaths/min)", "Sweating Level (1-5)",
    "Therapy Sessions (per month)", "Diet Quality (1-10)", "Age",
]
CATEGORICAL = ["Occupation", "Family History of Anxiety"]
NUMERIC_11 = [f for f in NUMERIC_12 if f != FEATURE]


def pipeline(numeric: list[str], params: dict, n_jobs: int = -1) -> Pipeline:
    pre = ColumnTransformer([("num", StandardScaler(), numeric),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)])
    xgb = XGBClassifier(**params, objective="multi:softprob", eval_metric="mlogloss", random_state=SEED, n_jobs=n_jobs)
    return Pipeline([("pre", pre), ("xgb", xgb)])


def metrics(y: np.ndarray, prob: np.ndarray, threshold: float = THRESHOLD) -> dict[str, float]:
    pred = prob.argmax(axis=1)
    p = precision_score(y, pred, labels=[0, 1, 2], average=None, zero_division=0)
    r = recall_score(y, pred, labels=[0, 1, 2], average=None, zero_division=0)
    f = f1_score(y, pred, labels=[0, 1, 2], average=None, zero_division=0)
    flagged = prob[:, HIGH] >= threshold
    out = {"accuracy": accuracy_score(y, pred), "balanced_accuracy": balanced_accuracy_score(y, pred),
           "macro_f1": f1_score(y, pred, average="macro")}
    for k, c in enumerate(CLASSES):
        out |= {f"precision_{c}": p[k], f"recall_{c}": r[k], f"f1_{c}": f[k]}
    out |= {"flag_catch_rate": float(flagged[y == HIGH].mean()), "flag_volume": float(flagged.mean()),
            "high_caught_as_label": int(((pred == HIGH) & (y == HIGH)).sum()),
            "high_caught_by_flag": int((flagged & (y == HIGH)).sum())}
    return {k: float(v) for k, v in out.items()}


def threshold_for(p_high: np.ndarray, is_high: np.ndarray, n_caught: int) -> float:
    """Highest threshold that still flags at least n_caught true-High rows."""
    return float(np.sort(p_high[is_high])[::-1][n_caught - 1])


def main() -> None:
    t0 = time.time()
    df = pd.read_csv(DATA_PATH)
    with np.load(SPLITS_PATH) as s:
        assert "X_test" not in s.files and "test_original_idx" not in s.files
        tr_idx, va_idx, y_tr_saved, y_va_saved = s["train_original_idx"], s["val_original_idx"], s["y_train"], s["y_val"]
    train, val = df.iloc[tr_idx].reset_index(drop=True), df.iloc[va_idx].reset_index(drop=True)
    y_tr, y_va = bin_anxiety_level(train["Anxiety Level (1-10)"].to_numpy()), bin_anxiety_level(val["Anxiety Level (1-10)"].to_numpy())
    assert np.array_equal(y_tr, y_tr_saved) and np.array_equal(y_va, y_va_saved)
    tuning = json.loads(TUNING_PATH.read_text(encoding="utf-8"))["models"]["xgboost"]
    assert tuning["sample_weighting"] == "none"
    params = tuning["best_params"]

    # ---- 1-2. Fit both versions ----
    full = pipeline(NUMERIC_12, params).fit(train[NUMERIC_12 + CATEGORICAL], y_tr)
    reduced = pipeline(NUMERIC_11, params).fit(train[NUMERIC_11 + CATEGORICAL], y_tr)
    prob_full = full.predict_proba(val[NUMERIC_12 + CATEGORICAL])
    prob_red = reduced.predict_proba(val[NUMERIC_11 + CATEGORICAL])
    deployed = joblib.load(DEPLOYED_MODEL).predict_proba(joblib.load(DEPLOYED_PREPROCESSOR).transform(val[NUMERIC_12 + CATEGORICAL]))
    baseline_max_diff = float(np.abs(prob_full - deployed).max())
    assert baseline_max_diff < 1e-6, f"baseline does not reproduce the deployed model ({baseline_max_diff})"

    # ---- 3. Validation comparison ----
    m_full, m_red = metrics(y_va, prob_full), metrics(y_va, prob_red)
    is_high = y_va == HIGH
    target_catch = int(m_full["high_caught_by_flag"])
    t_match = threshold_for(prob_red[:, HIGH], is_high, target_catch)
    m_red_matched = metrics(y_va, prob_red, t_match)

    # ---- 4. Paired 5-fold CV on train + validation ----
    both = pd.concat([train, val], ignore_index=True)
    y_both = np.concatenate([y_tr, y_va])
    folds = StratifiedKFold(5, shuffle=True, random_state=SEED)
    cv = {"full": [], "reduced": []}
    for tr, te in folds.split(both, y_both):
        for name, numeric in (("full", NUMERIC_12), ("reduced", NUMERIC_11)):
            cols = numeric + CATEGORICAL
            model = pipeline(numeric, params).fit(both.iloc[tr][cols], y_both[tr])
            cv[name].append(metrics(y_both[te], model.predict_proba(both.iloc[te][cols])))
    cv_delta = {k: [r[k] - f[k] for f, r in zip(cv["full"], cv["reduced"])] for k in cv["full"][0]}

    # ---- 5. Re-tuning check on 11 features (training rows only, as the deployed tuning did) ----
    retune = {}
    weights = compute_sample_weight("balanced", y_tr)
    for weighting in ("none", "balanced"):
        search = RandomizedSearchCV(pipeline(NUMERIC_11, {}, n_jobs=1), {f"xgb__{k}": v for k, v in XGB_SPACE.items()},
                                    n_iter=20, scoring="balanced_accuracy", cv=5, random_state=SEED, n_jobs=-1, refit=True)
        search.fit(train[NUMERIC_11 + CATEGORICAL], y_tr, **({"xgb__sample_weight": weights} if weighting == "balanced" else {}))
        retune[weighting] = search
    best_w = max(retune, key=lambda w: retune[w].best_score_)
    best_params_11 = {k.removeprefix("xgb__"): v for k, v in retune[best_w].best_params_.items()}
    retuned_same = best_w == "none" and best_params_11 == params
    m_retuned = metrics(y_va, retune[best_w].best_estimator_.predict_proba(val[NUMERIC_11 + CATEGORICAL]))

    # ---- 6. Shortcut stress test on true-High validation patients ----
    high_rows = val[is_high]
    stress = {}
    for v in [1, 2, 3, 4, 5]:
        pr = full.predict_proba(high_rows.assign(**{FEATURE: v})[NUMERIC_12 + CATEGORICAL])
        stress[v] = {"label_high": int((pr.argmax(1) == HIGH).sum()), "flagged": int((pr[:, HIGH] >= THRESHOLD).sum()),
                     "mean_p_high": float(pr[:, HIGH].mean())}
    pr_real = prob_full[is_high]
    stress_real = {"label_high": int((pr_real.argmax(1) == HIGH).sum()), "flagged": int((pr_real[:, HIGH] >= THRESHOLD).sum()),
                   "mean_p_high": float(pr_real[:, HIGH].mean())}
    pr_red_h = prob_red[is_high]
    stress_removed = {"label_high": int((pr_red_h.argmax(1) == HIGH).sum()), "flagged": int((pr_red_h[:, HIGH] >= THRESHOLD).sum()),
                      "mean_p_high": float(pr_red_h[:, HIGH].mean())}
    # Who changes: High patients whose label or flag differs between real sweating and the constant.
    pr_const = full.predict_proba(high_rows.assign(**{FEATURE: CONSTANT})[NUMERIC_12 + CATEGORICAL])
    lost_label = int(((pr_real.argmax(1) == HIGH) & (pr_const.argmax(1) != HIGH)).sum())
    gained_label = int(((pr_real.argmax(1) != HIGH) & (pr_const.argmax(1) == HIGH)).sum())
    lost_flag = int(((pr_real[:, HIGH] >= THRESHOLD) & (pr_const[:, HIGH] < THRESHOLD)).sum())

    results = {
        "data": {"train_rows": int(len(train)), "validation_rows": int(len(val)), "validation_high": int(is_high.sum()),
                 "test_set": "not loaded (12-feature splits file has no test keys)"},
        "hyperparameters": params, "baseline_reproduces_deployed_max_abs_prob_diff": baseline_max_diff,
        "validation": {"full_12": m_full, "reduced_11": m_red,
                       "reduced_11_at_matched_threshold": {"threshold": t_match, **m_red_matched},
                       "reduced_11_retuned": m_retuned},
        "paired_cv": {"full_12": cv["full"], "reduced_11": cv["reduced"]},
        "retune_11": {"chosen_weighting": best_w, "cv_scores": {w: float(s.best_score_) for w, s in retune.items()},
                      "best_params": best_params_11, "same_as_deployed": retuned_same},
        "stress_test": {"constant": CONSTANT, "real_sweating": stress_real, "forced": stress, "sweating_removed": stress_removed,
                        "lost_label_at_constant": lost_label, "gained_label_at_constant": gained_label,
                        "lost_flag_at_constant": lost_flag},
    }
    JSON_PATH.write_text(json.dumps(results, indent=2, default=float) + "\n", encoding="utf-8")
    write_report(results, cv_delta)
    print(f"done in {time.time() - t0:.0f}s; saved {REPORT_PATH.relative_to(ROOT)} and {JSON_PATH.relative_to(ROOT)}")


KEY_METRICS = ["accuracy", "balanced_accuracy", "macro_f1", "precision_Low", "recall_Low", "precision_Medium",
               "recall_Medium", "precision_High", "recall_High", "flag_catch_rate"]
LABELS = {"accuracy": "Accuracy", "balanced_accuracy": "Balanced accuracy", "macro_f1": "Macro-F1",
          "precision_Low": "Precision Low", "recall_Low": "Recall Low", "precision_Medium": "Precision Medium",
          "recall_Medium": "Recall Medium", "precision_High": "Precision High", "recall_High": "Recall High",
          "f1_Low": "F1 Low", "f1_Medium": "F1 Medium", "f1_High": "F1 High",
          "flag_catch_rate": "Flag catch rate (0.025)", "flag_volume": "Flag volume (0.025)"}


def write_report(r: dict, cv_delta: dict) -> None:
    v12, v11 = r["validation"]["full_12"], r["validation"]["reduced_11"]
    matched = r["validation"]["reduced_11_at_matched_threshold"]
    st = r["stress_test"]
    n_val, n_high = r["data"]["validation_rows"], r["data"]["validation_high"]

    # Verdict rules, applied per metric on the validation split (11 minus 12):
    #   meaningful cost  - any drop of >= 0.02 on a headline, per-class or flag metric
    #   small real cost  - any drop of >= 0.01, OR fewer true-High patients caught (as label or by flag)
    #   no meaningful    - otherwise
    # A validation drop only counts as "real" if the paired CV mean moves the same way by more than
    # one fold-std; otherwise it is reported as within noise and the raw numbers are shown.
    rows = []
    for k in KEY_METRICS:
        d_val = v11[k] - v12[k]
        cv_mean, cv_std = float(np.mean(cv_delta[k])), float(np.std(cv_delta[k]))
        rows.append((k, v12[k], v11[k], d_val, cv_mean, cv_std))
    drops_2 = [k for k, _, _, d, *_ in rows if d <= -0.02]
    drops_1 = [k for k, _, _, d, *_ in rows if d <= -0.01]
    fewer_high = (v11["high_caught_as_label"] < v12["high_caught_as_label"]) or (v11["high_caught_by_flag"] < v12["high_caught_by_flag"])
    confirmed = [k for k, _, _, d, m, sd in rows if d <= -0.01 and m < 0 and abs(m) > sd]
    if drops_2:
        verdict = "meaningful cost"
    elif drops_1 or fewer_high:
        verdict = "small but real cost"
    else:
        verdict = "no meaningful cost"

    L = [
        "# Feature Reduction Experiment: Sweating Level Removal (Exploratory) — 3-Class Target",
        "",
        "**Scope note: this experiment uses TRAIN and VALIDATION only. It never loads or references X_test, y_test or"
        " test_original_idx — the 12-feature splits file has no test keys, and the 3-class test set is fully spent"
        " (see `CLAUDE.md`, \"TEST SET USED\" entries). No canonical artifact, API, validation, test or documentation"
        " file was changed — purely exploratory.** Script: `src/experiments/feature_reduction_sweatlevel_3class.py`;"
        " raw numbers: `reports/feature_reduction_sweatlevel_3class.json`.",
        "",
        "## Motivation",
        "",
        "Could the onboarding form drop `Sweating Level (1-5)`? It is one of the 12 canonical inputs. In the"
        " original 17-feature Random Forest SHAP ranking (`reports/shap_full_ranking_3class.md`) it ranked **10th of 17**"
        " (mean |SHAP| 0.0103). In the current 12-feature XGBoost (`reports/model_comparison_12feature.md`) it ranks"
        " **12th of 12** (0.4% of total mean |SHAP|). In the training data, High patients average 3.85 on it,"
        " against 2.98 (Low) and 3.01 (Medium), so it may carry High-specific signal despite its low overall rank.",
        "",
        "## Method",
        "",
        f"- **Data:** {r['data']['train_rows']:,} train rows to fit; {n_val:,} validation rows ({n_high} High) to score."
        " Rows come from the 12-feature splits' saved indices; labels rebuilt from the raw CSV and checked against them.",
        f"- **Baseline (12 features):** the deployed XGBoost pipeline refit with its own hyperparameters"
        f" ({r['hyperparameters']}). It reproduces the saved deployed model's validation probabilities"
        f" (max difference {r['baseline_reproduces_deployed_max_abs_prob_diff']:.1e}).",
        "- **Reduced (11 features):** the same pipeline without Sweating Level, same hyperparameters, new"
        " ColumnTransformer fit on train rows only.",
        "- **Paired 5-fold CV** on train + validation (9,350 rows): both versions on identical folds, preprocessing"
        " refit inside each fold, so every delta has a fold-to-fold spread.",
        "- **Re-tuning check:** the deployed tuning procedure re-run on the 11 features (see below).",
        f"- **Shortcut stress test:** the {n_high} true-High validation patients, Sweating Level forced to {st['constant']}"
        " (the train median) and swept 1–5, scored by the 12-feature model; compared with the 11-feature model.",
        "",
        "## Results (validation split)",
        "",
        "| Metric | 12 features (deployed) | 11 features (no Sweating Level) | Δ (11 − 12) | Paired 5-fold CV Δ (mean ± std) |",
        "|---|---:|---:|---:|---:|",
    ]
    for k, a, b, d, m, sd in rows:
        L.append(f"| {LABELS[k]} | {a:.4f} | {b:.4f} | {d:+.4f} | {m:+.4f} ± {sd:.4f} |")
    L += [
        f"| F1 Low / Medium / High | {v12['f1_Low']:.4f} / {v12['f1_Medium']:.4f} / {v12['f1_High']:.4f} |"
        f" {v11['f1_Low']:.4f} / {v11['f1_Medium']:.4f} / {v11['f1_High']:.4f} |"
        f" {v11['f1_Low'] - v12['f1_Low']:+.4f} / {v11['f1_Medium'] - v12['f1_Medium']:+.4f} / {v11['f1_High'] - v12['f1_High']:+.4f} | |",
        f"| Flag volume (0.025) | {v12['flag_volume']:.4f} | {v11['flag_volume']:.4f} | {v11['flag_volume'] - v12['flag_volume']:+.4f} |"
        f" {np.mean(cv_delta['flag_volume']):+.4f} ± {np.std(cv_delta['flag_volume']):.4f} |",
        "",
        f"True-High patients ({n_high}) caught on validation: **as a High label** {int(v12['high_caught_as_label'])} → "
        f"{int(v11['high_caught_as_label'])}; **by the 0.025 flag** {int(v12['high_caught_by_flag'])} → {int(v11['high_caught_by_flag'])}"
        f" (flagging {round(v12['flag_volume'] * n_val)} → {round(v11['flag_volume'] * n_val)} of {n_val} rows).",
        "",
        "### Review threshold",
        "",
        f"To catch the same {int(v12['high_caught_by_flag'])}/{n_high} High patients as the 12-feature model at 0.025, the"
        f" 11-feature model needs a threshold of **{matched['threshold']:.4f}**, which flags"
        f" **{round(matched['flag_volume'] * n_val)}** of {n_val} rows (12-feature at 0.025: {round(v12['flag_volume'] * n_val)})."
        f" At that threshold its flag catches {int(matched['high_caught_by_flag'])}/{n_high} High patients.",
        "",
        "### Re-tuning check",
        "",
        f"The deployed tuning procedure was re-run on the 11 features (20 unweighted + 20 balanced-weight"
        f" configurations, 5-fold CV on train rows). Best: **{r['retune_11']['chosen_weighting']}** weighting, CV"
        f" balanced accuracy {r['retune_11']['cv_scores'][r['retune_11']['chosen_weighting']]:.4f}, parameters"
        f" {r['retune_11']['best_params']}. "
        + ("**These are the same hyperparameters as the deployed model, so re-tuning is not needed** and the"
           " same-hyperparameter comparison above is the right one."
           if r["retune_11"]["same_as_deployed"] else
           "**Re-tuning chose different hyperparameters.** The re-tuned 11-feature model scores, on validation:"
           f" balanced accuracy {r['validation']['reduced_11_retuned']['balanced_accuracy']:.4f}, macro-F1"
           f" {r['validation']['reduced_11_retuned']['macro_f1']:.4f}, High recall"
           f" {r['validation']['reduced_11_retuned']['recall_High']:.4f}, flag catch rate"
           f" {r['validation']['reduced_11_retuned']['flag_catch_rate']:.4f}."),
        "",
        "## Shortcut Stress Test (true-High validation patients)",
        "",
        f"| Sweating Level given to the {n_high} High patients | Labelled High | Flagged at 0.025 | Mean P(High) |",
        "|---|---:|---:|---:|",
        f"| Their real values (12-feature model) | {st['real_sweating']['label_high']} | {st['real_sweating']['flagged']} | {st['real_sweating']['mean_p_high']:.4f} |",
    ]
    for v, s in st["forced"].items():
        mark = " (median)" if int(v) == st["constant"] else ""
        L.append(f"| Forced to {v}{mark} (12-feature model) | {s['label_high']} | {s['flagged']} | {s['mean_p_high']:.4f} |")
    L += [
        f"| Feature removed (11-feature model) | {st['sweating_removed']['label_high']} | {st['sweating_removed']['flagged']} | {st['sweating_removed']['mean_p_high']:.4f} |",
        "",
        f"At the median ({st['constant']}), {st['lost_label_at_constant']} High patients lose their High label and"
        f" {st['gained_label_at_constant']} gain it; {st['lost_flag_at_constant']} lose the review flag.",
        "",
        "## Verdict",
        "",
        "Rules, applied to the validation deltas above (11 − 12): **meaningful cost** if any headline, per-class or"
        " flag metric drops by ≥ 0.02; **small but real cost** if any drops by ≥ 0.01, or fewer true-High patients"
        " are caught as a label or by the flag; otherwise **no meaningful cost**. Each validation drop is also"
        " checked against the paired CV: it is called consistent only if the CV mean moves the same way by more"
        " than one fold standard deviation.",
        "",
        f"**Rule outcome: {verdict}.**",
        "",
        f"- Drops of ≥ 0.02 on validation: {', '.join(LABELS[k] for k in drops_2) or 'none'}.",
        f"- Drops of ≥ 0.01 on validation: {', '.join(LABELS[k] for k in drops_1) or 'none'}.",
        f"- Fewer true-High patients caught: {'yes' if fewer_high else 'no'}"
        f" (label {int(v12['high_caught_as_label'])} → {int(v11['high_caught_as_label'])},"
        f" flag {int(v12['high_caught_by_flag'])} → {int(v11['high_caught_by_flag'])}).",
        f"- Validation drops of ≥ 0.01 that the paired CV confirms: {', '.join(LABELS[k] for k in confirmed) or 'none'}.",
        "",
        "Where the validation split and the paired CV disagree, the raw numbers above are the evidence; this report"
        " does not resolve that disagreement for the reader.",
        "",
        "## Interpretation",
        "",
        "Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation."
        " Exploratory only: no canonical artifact, API, validation rule, test or document changed. The test set was"
        " never touched.",
    ]
    REPORT_PATH.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
