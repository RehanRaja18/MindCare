# Nested Cross-Validation — 11-Feature v2 XGBoost Pipeline (Sweating Level removed) (3-Class Anxiety Level)

Script: `src/evaluation/nested_cv_12feature_xgb.py`. Estimates how the whole pipeline — preprocessing, tuning and threshold choice — performs on data it never saw, and compares that with the single validation-split figures in `reports/feature_reduction_sweatlevel_3class.md`.

## Setup

- **Data:** the 9350 train + validation rows only, read from the raw CSV via the saved `train_original_idx` / `val_original_idx`. Labels rebuilt from `Anxiety Level (1-10)` and checked against the saved splits. **The test set was not loaded** (the 12-feature splits file has no test keys, and `test_original_idx` is never read).
- **Outer loop:** 5-fold stratified on the 3-class label (shuffled, seed 42).
- **Inside each outer training fold, rebuilt from scratch:**
  1. The preprocessor (StandardScaler + OneHotEncoder), inside a Pipeline with the model, so it is refit inside every inner split too.
  2. XGBoost tuning, as in `src/models/tune_models_12feature.py`: RandomizedSearchCV, inner cv=5, balanced-accuracy scoring, the same search space, **20 configurations unweighted + 20 with balanced sample weights**, keeping the better. (This matches what the real pipeline did; the request specified balanced weights only, but the deployed model came from the both-ways search, where unweighted won.)
  3. The review threshold, from the chosen configuration's inner out-of-fold P(High): the **highest** threshold that still flags at least 158/165 (95.76%) of High cases. That is the coverage the deployed 0.025 was chosen to match, with the fewest flags. (The *smallest* threshold meeting the target would be 0, which flags everyone.)
- **Scored on the untouched outer fold:** all rows, and ages 18-49 only (the API's supported range).
- **Validation-split reference:** the saved model (`mindcare_final_model_11feature_v2_xgb.pkl`) on `X_val` at its 0.025 threshold. The all-rows headline figures match `reports/feature_reduction_sweatlevel_3class.md` (checked in the script); the 18-49 figures are computed the same way on that subset.

## Per-Fold Choices

| Fold | Test rows (18-49) | Weighting chosen | Inner CV bal. acc. (none / balanced) | Threshold | Key params |
|---:|---:|---|---|---:|---|
| 1 | 1870 (1358) | none | 0.8124 / 0.8083 | 0.0234 | 300 trees, depth 3, lr 0.03 |
| 2 | 1870 (1362) | balanced | 0.8077 / 0.8078 | 0.0814 | 300 trees, depth 3, lr 0.03 |
| 3 | 1870 (1312) | none | 0.8113 / 0.8086 | 0.0263 | 300 trees, depth 3, lr 0.03 |
| 4 | 1870 (1333) | none | 0.8112 / 0.8088 | 0.0288 | 300 trees, depth 3, lr 0.03 |
| 5 | 1870 (1351) | none | 0.8065 / 0.8063 | 0.0311 | 300 trees, depth 3, lr 0.03 |

Chosen threshold: mean 0.0382 ± 0.0217 (range 0.0234-0.0814); the deployed threshold is 0.025.

## Results — All Rows

| Metric | Nested CV (mean ± std, 5 folds) | Validation split | Validation − nested mean | In fold-std units |
|---|---:|---:|---:|---:|
| Accuracy | 0.7891 ± 0.0081 | 0.7745 | -0.0145 | -1.8 |
| Balanced accuracy | 0.8121 ± 0.0060 | 0.8055 | -0.0066 | -1.1 |
| Macro-F1 | 0.8225 ± 0.0052 | 0.8148 | -0.0077 | -1.5 |
| Recall Low | 0.7946 ± 0.0133 | 0.7841 | -0.0106 | -0.8 |
| Recall Medium | 0.7604 ± 0.0101 | 0.7355 | -0.0249 | -2.5 |
| Recall High | 0.8812 ± 0.0092 | 0.8970 | +0.0158 | +1.7 |
| Precision High | 0.9632 ± 0.0231 | 0.9673 | +0.0041 | +0.2 |
| Flag catch rate (High caught) | 0.9546 ± 0.0143 | 0.9576 | +0.0030 | +0.2 |
| Flag volume (share of rows flagged) | 0.2425 ± 0.0219 | 0.2491 | +0.0066 | +0.3 |
| Brier Low | 0.1369 ± 0.0050 | 0.1409 | +0.0040 | +0.8 |
| Brier Medium | 0.1496 ± 0.0031 | 0.1515 | +0.0019 | +0.6 |
| Brier High | 0.0148 ± 0.0020 | 0.0124 | -0.0024 | -1.2 |

Flag rows use each fold's own threshold (above); the validation column uses the deployed 0.025. For every metric except Brier and flag volume, a positive difference means the validation split looked better than nested CV. For Brier and flag volume (lower is better), a negative difference means that. "Fold-std units" divide the difference by the spread between the 5 outer folds.

**Headline metrics: the validation split was pessimistic.** Relative to nested CV, validation looked worse on accuracy (-0.0145), balanced accuracy (-0.0066) and macro-F1 (-0.0077); positive = validation looked better. Beyond one fold-std, validation was **optimistic** on: Recall High (+0.0158), Brier High (+0.0024). It was **pessimistic** beyond one fold-std on: Accuracy (-0.0145), Balanced accuracy (-0.0066), Macro-F1 (-0.0077), Recall Medium (-0.0249).

## Results — Ages 18-49 (the API's supported range)

| Metric | Nested CV (mean ± std, 5 folds) | Validation split | Validation − nested mean | In fold-std units |
|---|---:|---:|---:|---:|
| Accuracy | 0.7978 ± 0.0084 | 0.7853 | -0.0126 | -1.5 |
| Balanced accuracy | 0.8226 ± 0.0053 | 0.8144 | -0.0082 | -1.5 |
| Macro-F1 | 0.8297 ± 0.0043 | 0.8219 | -0.0078 | -1.8 |
| Recall Low | 0.8042 ± 0.0179 | 0.7970 | -0.0072 | -0.4 |
| Recall Medium | 0.7506 ± 0.0152 | 0.7269 | -0.0237 | -1.6 |
| Recall High | 0.9130 ± 0.0089 | 0.9193 | +0.0062 | +0.7 |
| Precision High | 0.9729 ± 0.0230 | 0.9801 | +0.0073 | +0.3 |
| Flag catch rate (High caught) | 0.9658 ± 0.0166 | 0.9627 | -0.0030 | -0.2 |
| Flag volume (share of rows flagged) | 0.2769 ± 0.0254 | 0.2789 | +0.0019 | +0.1 |
| Brier Low | 0.1308 ± 0.0060 | 0.1319 | +0.0012 | +0.2 |
| Brier Medium | 0.1436 ± 0.0036 | 0.1435 | -0.0001 | -0.0 |
| Brier High | 0.0150 ± 0.0021 | 0.0133 | -0.0017 | -0.8 |

Same thresholds as above; only the scored rows are restricted to ages 18-49. For every metric except Brier and flag volume, a positive difference means the validation split looked better than nested CV. For Brier and flag volume (lower is better), a negative difference means that. "Fold-std units" divide the difference by the spread between the 5 outer folds.

**Headline metrics: the validation split was pessimistic.** Relative to nested CV, validation looked worse on accuracy (-0.0126), balanced accuracy (-0.0082) and macro-F1 (-0.0078); positive = validation looked better. Validation was not optimistic beyond one fold-std on any metric. It was **pessimistic** beyond one fold-std on: Accuracy (-0.0126), Balanced accuracy (-0.0082), Macro-F1 (-0.0078), Recall Medium (-0.0237).

## The Flag at the Deployed 0.025 (for reference)

The same outer-fold models, flagged at the fixed deployed threshold instead of each fold's own:

| Scope | Flag catch rate | Flag volume |
|---|---:|---:|
| All rows | 0.9670 ± 0.0200 | 0.2839 ± 0.0675 |
| Ages 18-49 | 0.9754 ± 0.0177 | 0.3157 ± 0.0645 |

With each fold's own threshold, the flag caught 95.5% of High cases on average against a 95.8% target set on inner out-of-fold data.

## What This Does NOT Cover

Nested CV only makes the steps **inside** the loop honest. Several decisions were made **outside** it, using this same train + validation data, so their optimism is not measured here:

- **The 17 → 11 → 12 feature reduction.** The features were chosen from SHAP rankings and validation results on these rows (`reports/feature_reduction_3class.md`, `reports/feature_addition_age_3class.md`).
- **Removing Sweating Level** (`reports/feature_reduction_sweatlevel_3class.md`), decided on validation and paired cross-validation results from these rows.
- **Choosing XGBoost over Random Forest** (`reports/model_comparison_12feature.md`), made on validation and cross-validation results from these rows.
- **The coverage target itself (158/165)**, which was copied from the Random Forest's validation result.
- **The search space, the Low/Medium/High label boundaries and the 18-49 age limit**, all set after looking at this data.

So these numbers are an honest estimate for *re-running this pipeline*, not for the whole path of decisions that led to it. Only fresh data can check that. The 3-class test set is already spent (used twice), and the dataset is very likely synthetic (see CLAUDE.md) — none of this is clinical validation.
