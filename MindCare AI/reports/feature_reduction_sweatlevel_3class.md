# Feature Reduction Experiment: Sweating Level Removal (Exploratory) — 3-Class Target

**Scope note: this experiment uses TRAIN and VALIDATION only. It never loads or references X_test, y_test or test_original_idx — the 12-feature splits file has no test keys, and the 3-class test set is fully spent (see `CLAUDE.md`, "TEST SET USED" entries). No canonical artifact, API, validation, test or documentation file was changed — purely exploratory.** Script: `src/experiments/feature_reduction_sweatlevel_3class.py`; raw numbers: `reports/feature_reduction_sweatlevel_3class.json`.

## Motivation

Could the onboarding form drop `Sweating Level (1-5)`? It is one of the 12 canonical inputs. In the original 17-feature Random Forest SHAP ranking (`reports/shap_full_ranking_3class.md`) it ranked **10th of 17** (mean |SHAP| 0.0103). In the current 12-feature XGBoost (`reports/model_comparison_12feature.md`) it ranks **12th of 12** (0.4% of total mean |SHAP|). In the training data, High patients average 3.85 on it, against 2.98 (Low) and 3.01 (Medium), so it may carry High-specific signal despite its low overall rank.

## Method

- **Data:** 7,700 train rows to fit; 1,650 validation rows (165 High) to score. Rows come from the 12-feature splits' saved indices; labels rebuilt from the raw CSV and checked against them.
- **Baseline (12 features):** the deployed XGBoost pipeline refit with its own hyperparameters ({'subsample': 0.8, 'n_estimators': 300, 'min_child_weight': 3, 'max_depth': 3, 'learning_rate': 0.03, 'gamma': 0, 'colsample_bytree': 1.0}). It reproduces the saved deployed model's validation probabilities (max difference 0.0e+00).
- **Reduced (11 features):** the same pipeline without Sweating Level, same hyperparameters, new ColumnTransformer fit on train rows only.
- **Paired 5-fold CV** on train + validation (9,350 rows): both versions on identical folds, preprocessing refit inside each fold, so every delta has a fold-to-fold spread.
- **Re-tuning check:** the deployed tuning procedure re-run on the 11 features (see below).
- **Shortcut stress test:** the 165 true-High validation patients, Sweating Level forced to 3 (the train median) and swept 1–5, scored by the 12-feature model; compared with the 11-feature model.

## Results (validation split)

| Metric | 12 features (deployed) | 11 features (no Sweating Level) | Δ (11 − 12) | Paired 5-fold CV Δ (mean ± std) |
|---|---:|---:|---:|---:|
| Accuracy | 0.7776 | 0.7745 | -0.0030 | +0.0000 ± 0.0009 |
| Balanced accuracy | 0.8078 | 0.8055 | -0.0023 | +0.0000 ± 0.0007 |
| Macro-F1 | 0.8171 | 0.8148 | -0.0023 | +0.0001 ± 0.0007 |
| Precision Low | 0.7737 | 0.7702 | -0.0035 | +0.0001 ± 0.0011 |
| Recall Low | 0.7866 | 0.7841 | -0.0026 | -0.0002 ± 0.0013 |
| Precision Medium | 0.7408 | 0.7376 | -0.0032 | -0.0003 ± 0.0012 |
| Recall Medium | 0.7397 | 0.7355 | -0.0042 | +0.0003 ± 0.0019 |
| Precision High | 0.9673 | 0.9673 | +0.0000 | +0.0011 ± 0.0022 |
| Recall High | 0.8970 | 0.8970 | +0.0000 | +0.0000 ± 0.0000 |
| Flag catch rate (0.025) | 0.9576 | 0.9576 | +0.0000 | +0.0000 ± 0.0033 |
| F1 Low / Medium / High | 0.7801 / 0.7403 / 0.9308 | 0.7771 / 0.7365 / 0.9308 | -0.0030 / -0.0037 / +0.0000 | |
| Flag volume (0.025) | 0.2485 | 0.2491 | +0.0006 | +0.0007 ± 0.0018 |

True-High patients (165) caught on validation: **as a High label** 148 → 148; **by the 0.025 flag** 158 → 158 (flagging 410 → 411 of 1650 rows).

### Review threshold

To catch the same 158/165 High patients as the 12-feature model at 0.025, the 11-feature model needs a threshold of **0.0302**, which flags **370** of 1650 rows (12-feature at 0.025: 410). At that threshold its flag catches 158/165 High patients.

### Re-tuning check

The deployed tuning procedure was re-run on the 11 features (20 unweighted + 20 balanced-weight configurations, 5-fold CV on train rows). Best: **none** weighting, CV balanced accuracy 0.8097, parameters {'subsample': 0.8, 'n_estimators': 300, 'min_child_weight': 3, 'max_depth': 3, 'learning_rate': 0.03, 'gamma': 0, 'colsample_bytree': 1.0}. **These are the same hyperparameters as the deployed model, so re-tuning is not needed** and the same-hyperparameter comparison above is the right one.

## Shortcut Stress Test (true-High validation patients)

| Sweating Level given to the 165 High patients | Labelled High | Flagged at 0.025 | Mean P(High) |
|---|---:|---:|---:|
| Their real values (12-feature model) | 148 | 158 | 0.8670 |
| Forced to 1 (12-feature model) | 147 | 158 | 0.8615 |
| Forced to 2 (12-feature model) | 148 | 158 | 0.8657 |
| Forced to 3 (median) (12-feature model) | 148 | 158 | 0.8669 |
| Forced to 4 (12-feature model) | 148 | 158 | 0.8669 |
| Forced to 5 (12-feature model) | 148 | 158 | 0.8669 |
| Feature removed (11-feature model) | 148 | 158 | 0.8668 |

At the median (3), 0 High patients lose their High label and 0 gain it; 0 lose the review flag.

## Verdict

Rules, applied to the validation deltas above (11 − 12): **meaningful cost** if any headline, per-class or flag metric drops by ≥ 0.02; **small but real cost** if any drops by ≥ 0.01, or fewer true-High patients are caught as a label or by the flag; otherwise **no meaningful cost**. Each validation drop is also checked against the paired CV: it is called consistent only if the CV mean moves the same way by more than one fold standard deviation.

**Rule outcome: no meaningful cost.**

- Drops of ≥ 0.02 on validation: none.
- Drops of ≥ 0.01 on validation: none.
- Fewer true-High patients caught: no (label 148 → 148, flag 158 → 158).
- Validation drops of ≥ 0.01 that the paired CV confirms: none.

Where the validation split and the paired CV disagree, the raw numbers above are the evidence; this report does not resolve that disagreement for the reader.

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation. Exploratory only: no canonical artifact, API, validation rule, test or document changed. The test set was never touched.
