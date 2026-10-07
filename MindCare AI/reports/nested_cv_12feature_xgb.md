# Nested Cross-Validation — 12-Feature XGBoost Pipeline (3-Class Anxiety Level)

Script: `src/evaluation/nested_cv_12feature_xgb.py`. Estimates how the whole pipeline — preprocessing, tuning and threshold choice — performs on data it never saw, and compares that with the single validation-split figures in `reports/model_comparison_12feature.md`.

## Setup

- **Data:** the 9350 train + validation rows only, read from the raw CSV via the saved `train_original_idx` / `val_original_idx`. Labels rebuilt from `Anxiety Level (1-10)` and checked against the saved splits. **The test set was not loaded** (the 12-feature splits file has no test keys, and `test_original_idx` is never read).
- **Outer loop:** 5-fold stratified on the 3-class label (shuffled, seed 42).
- **Inside each outer training fold, rebuilt from scratch:**
  1. The preprocessor (StandardScaler + OneHotEncoder), inside a Pipeline with the model, so it is refit inside every inner split too.
  2. XGBoost tuning, as in `src/models/tune_models_12feature.py`: RandomizedSearchCV, inner cv=5, balanced-accuracy scoring, the same search space, **20 configurations unweighted + 20 with balanced sample weights**, keeping the better. (This matches what the real pipeline did; the request specified balanced weights only, but the deployed model came from the both-ways search, where unweighted won.)
  3. The review threshold, from the chosen configuration's inner out-of-fold P(High): the **highest** threshold that still flags at least 158/165 (95.76%) of High cases. That is the coverage the deployed 0.025 was chosen to match, with the fewest flags. (The *smallest* threshold meeting the target would be 0, which flags everyone.)
- **Scored on the untouched outer fold:** all rows, and ages 18-49 only (the API's supported range).
- **Validation-split reference:** the deployed model (`mindcare_final_model_12feature_xgb.pkl`) on `X_val` at its 0.025 threshold. The all-rows headline figures match `reports/model_comparison_12feature.md` (checked in the script); the 18-49 figures are computed the same way on that subset.

## Per-Fold Choices

| Fold | Test rows (18-49) | Weighting chosen | Inner CV bal. acc. (none / balanced) | Threshold | Key params |
|---:|---:|---|---|---:|---|
| 1 | 1870 (1358) | none | 0.8117 / 0.8088 | 0.0232 | 300 trees, depth 3, lr 0.03 |
| 2 | 1870 (1362) | none | 0.8084 / 0.8081 | 0.0253 | 300 trees, depth 3, lr 0.03 |
| 3 | 1870 (1312) | none | 0.8109 / 0.8093 | 0.0263 | 300 trees, depth 3, lr 0.03 |
| 4 | 1870 (1333) | none | 0.8121 / 0.8085 | 0.0300 | 300 trees, depth 3, lr 0.03 |
| 5 | 1870 (1351) | none | 0.8072 / 0.8062 | 0.0295 | 300 trees, depth 3, lr 0.03 |

Chosen threshold: mean 0.0268 ± 0.0026 (range 0.0232-0.0300); the deployed threshold is 0.025.

## Results — All Rows

| Metric | Nested CV (mean ± std, 5 folds) | Validation split | Validation − nested mean | In fold-std units |
|---|---:|---:|---:|---:|
| Accuracy | 0.7904 ± 0.0094 | 0.7776 | -0.0128 | -1.4 |
| Balanced accuracy | 0.8119 ± 0.0057 | 0.8078 | -0.0041 | -0.7 |
| Macro-F1 | 0.8244 ± 0.0064 | 0.8171 | -0.0074 | -1.2 |
| Recall Low | 0.7978 ± 0.0150 | 0.7866 | -0.0111 | -0.7 |
| Recall Medium | 0.7609 ± 0.0098 | 0.7397 | -0.0212 | -2.2 |
| Recall High | 0.8771 ± 0.0111 | 0.8970 | +0.0199 | +1.8 |
| Precision High | 0.9759 ± 0.0065 | 0.9673 | -0.0086 | -1.3 |
| Flag catch rate (High caught) | 0.9587 ± 0.0153 | 0.9576 | -0.0011 | -0.1 |
| Flag volume (share of rows flagged) | 0.2448 ± 0.0217 | 0.2485 | +0.0037 | +0.2 |
| Brier Low | 0.1368 ± 0.0051 | 0.1408 | +0.0040 | +0.8 |
| Brier Medium | 0.1486 ± 0.0042 | 0.1514 | +0.0028 | +0.7 |
| Brier High | 0.0140 ± 0.0011 | 0.0124 | -0.0017 | -1.6 |

Flag rows use each fold's own threshold (above); the validation column uses the deployed 0.025. For every metric except Brier and flag volume, a positive difference means the validation split looked better than nested CV. For Brier and flag volume (lower is better), a negative difference means that. "Fold-std units" divide the difference by the spread between the 5 outer folds.

**Headline metrics: the validation split was pessimistic.** Relative to nested CV, validation looked worse on accuracy (-0.0128), balanced accuracy (-0.0041) and macro-F1 (-0.0074); positive = validation looked better. Beyond one fold-std, validation was **optimistic** on: Recall High (+0.0199), Brier High (+0.0017). It was **pessimistic** beyond one fold-std on: Accuracy (-0.0128), Macro-F1 (-0.0074), Recall Medium (-0.0212), Precision High (-0.0086).

## Results — Ages 18-49 (the API's supported range)

| Metric | Nested CV (mean ± std, 5 folds) | Validation split | Validation − nested mean | In fold-std units |
|---|---:|---:|---:|---:|
| Accuracy | 0.7996 ± 0.0100 | 0.7861 | -0.0135 | -1.4 |
| Balanced accuracy | 0.8230 ± 0.0059 | 0.8152 | -0.0078 | -1.3 |
| Macro-F1 | 0.8318 ± 0.0062 | 0.8226 | -0.0092 | -1.5 |
| Recall Low | 0.8071 ± 0.0199 | 0.7951 | -0.0120 | -0.6 |
| Recall Medium | 0.7532 ± 0.0153 | 0.7311 | -0.0221 | -1.4 |
| Recall High | 0.9087 ± 0.0122 | 0.9193 | +0.0105 | +0.9 |
| Precision High | 0.9837 ± 0.0044 | 0.9801 | -0.0036 | -0.8 |
| Flag catch rate (High caught) | 0.9700 ± 0.0159 | 0.9627 | -0.0073 | -0.5 |
| Flag volume (share of rows flagged) | 0.2783 ± 0.0259 | 0.2789 | +0.0006 | +0.0 |
| Brier Low | 0.1309 ± 0.0058 | 0.1319 | +0.0010 | +0.2 |
| Brier Medium | 0.1428 ± 0.0047 | 0.1435 | +0.0007 | +0.1 |
| Brier High | 0.0142 ± 0.0011 | 0.0132 | -0.0010 | -0.9 |

Same thresholds as above; only the scored rows are restricted to ages 18-49. For every metric except Brier and flag volume, a positive difference means the validation split looked better than nested CV. For Brier and flag volume (lower is better), a negative difference means that. "Fold-std units" divide the difference by the spread between the 5 outer folds.

**Headline metrics: the validation split was pessimistic.** Relative to nested CV, validation looked worse on accuracy (-0.0135), balanced accuracy (-0.0078) and macro-F1 (-0.0092); positive = validation looked better. Validation was not optimistic beyond one fold-std on any metric. It was **pessimistic** beyond one fold-std on: Accuracy (-0.0135), Balanced accuracy (-0.0078), Macro-F1 (-0.0092), Recall Medium (-0.0221).

## The Flag at the Deployed 0.025 (for reference)

The same outer-fold models, flagged at the fixed deployed threshold instead of each fold's own:

| Scope | Flag catch rate | Flag volume |
|---|---:|---:|
| All rows | 0.9628 ± 0.0180 | 0.2538 ± 0.0121 |
| Ages 18-49 | 0.9742 ± 0.0159 | 0.2874 ± 0.0156 |

With each fold's own threshold, the flag caught 95.9% of High cases on average against a 95.8% target set on inner out-of-fold data.

## What This Does NOT Cover

Nested CV only makes the steps **inside** the loop honest. Several decisions were made **outside** it, using this same train + validation data, so their optimism is not measured here:

- **The 17 → 11 → 12 feature reduction.** The features were chosen from SHAP rankings and validation results on these rows (`reports/feature_reduction_3class.md`, `reports/feature_addition_age_3class.md`).
- **Choosing XGBoost over Random Forest** (`reports/model_comparison_12feature.md`), made on validation and cross-validation results from these rows.
- **The coverage target itself (158/165)**, which was copied from the Random Forest's validation result.
- **The search space, the Low/Medium/High label boundaries and the 18-49 age limit**, all set after looking at this data.

So these numbers are an honest estimate for *re-running this pipeline*, not for the whole path of decisions that led to it. Only fresh data can check that. The 3-class test set is already spent (used twice), and the dataset is very likely synthetic (see CLAUDE.md) — none of this is clinical validation.
