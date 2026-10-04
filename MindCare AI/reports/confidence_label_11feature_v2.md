# Confident / Borderline Label — Evidence (11-Feature v2 XGBoost, 3-Class Target)

**Scope: TRAIN and VALIDATION only.** The 11-feature v2 splits file has no test keys and the 3-class test set is spent. No model, API, test or documentation file was changed by this script (`src/experiments/confidence_label_analysis.py`). Raw numbers: `reports/confidence_label_11feature_v2.json`.

## What this is

Each prediction comes with three probabilities. Call the largest one the model's **confidence**. A prediction is labelled **confident** when that probability is at least the cut-off, otherwise **borderline**. The label changes no prediction. It tells the reviewing psychologist which predictions the model itself is unsure about.

**This does not make the model more accurate.** Overall accuracy is unchanged (0.7895 out-of-fold, 0.7745 on the validation split). It separates the predictions that are usually right from the ones that are close to a coin-flip.

## Method

- **Out-of-fold (primary):** 5-fold stratified CV over the 9,350 train + validation rows. Preprocessing and the model are refit in every fold with the deployed hyperparameters, so each row is scored by a model that never saw it.
- **Validation split:** the deployed model on its 1,650 validation rows.
- Confidence is the raw top-class probability. XGBoost's probabilities are reasonably calibrated (calibration error about 1–2 points on the 12-feature model), but they are still not a literal percentage to show a patient.

## Results — out-of-fold, all 9,350 rows

| Confidence cut-off | Labelled confident | Accuracy when confident | Accuracy when borderline | Errors that fall in borderline |
|---:|---:|---:|---:|---:|
| 0.50 | 99.7% | 0.7900 | 0.6000 | 10 of 1968 (0.5%) |
| 0.60 | 85.7% | 0.8267 | 0.5666 | 579 of 1968 (29.4%) |
| 0.65 | 78.6% | 0.8436 | 0.5908 | 818 of 1968 (41.6%) |
| 0.70 **(chosen)** | 71.1% | 0.8580 | 0.6210 | 1024 of 1968 (52.0%) |
| 0.75 | 62.1% | 0.8783 | 0.6440 | 1261 of 1968 (64.1%) |
| 0.80 | 51.2% | 0.8986 | 0.6751 | 1483 of 1968 (75.4%) |
| 0.90 | 23.5% | 0.9571 | 0.7382 | 1874 of 1968 (95.2%) |

## Results — validation split (deployed model)

| Confidence cut-off | Labelled confident | Accuracy when confident | Accuracy when borderline | Errors that fall in borderline |
|---:|---:|---:|---:|---:|
| 0.50 | 99.3% | 0.7755 | 0.6364 | 4 of 372 (1.1%) |
| 0.60 | 84.4% | 0.8212 | 0.5214 | 123 of 372 (33.1%) |
| 0.65 | 77.8% | 0.8402 | 0.5450 | 167 of 372 (44.9%) |
| 0.70 **(chosen)** | 69.5% | 0.8588 | 0.5825 | 210 of 372 (56.5%) |
| 0.75 | 60.6% | 0.8850 | 0.6046 | 257 of 372 (69.1%) |
| 0.80 | 50.5% | 0.9052 | 0.6414 | 293 of 372 (78.8%) |
| 0.90 | 23.9% | 0.9570 | 0.7171 | 355 of 372 (95.4%) |

## The chosen cut-off: 0.70

- **Out-of-fold:** 71.1% of predictions are labelled confident, and they are **85.8%** accurate. The borderline 28.9% are 62.1% accurate. 1024 of 1968 errors (52.0%) carry the borderline label.
- **Validation split:** 69.5% confident at 85.9%; borderline 58.3%. The two measurements agree.
- **Ages 18–49 (the API's range), out-of-fold:** 71.8% confident at 86.5%; borderline 62.7%.
- **Why 0.70:** below it, the confident group's accuracy falls towards the overall figure and the label says little. Above it, most predictions become borderline and the label stops discriminating. At 0.70 roughly two thirds of predictions are confident, at an accuracy clearly above the overall figure.

### What borderline predictions are borderline between (out-of-fold)

| Top two classes | Borderline predictions |
|---|---:|
| Low/Medium | 2628 |
| Medium/High | 74 |
| Low/High | 0 |

### Confident predictions, by predicted class (out-of-fold)

| Predicted class | Confident predictions | Accuracy |
|---|---:|---:|
| Low | 3171 | 0.8619 |
| Medium | 2636 | 0.8115 |
| High | 841 | 0.9893 |

## Safety check: High patients

A "confident" label must not hide High-risk patients. Out-of-fold, of 968 true-High patients: 832 are confidently labelled High; **108 are confidently labelled something else**; the rest are borderline. Of those 108, **33 are also missed by the priority-review flag** (P(High) ≥ 0.025). On the validation split the same counts are 143 / 16 / 7 of 165.

A plain confidence cut-off would therefore present some High patients as a confident Medium. **The shipped rule closes most of that gap.**

## The shipped rule

A prediction is **confident** only if its top probability is ≥ 0.70 **and** it is not a flagged non-High prediction (P(High) ≥ 0.025 while predicting Low or Medium). Everything else is **borderline**. So a patient the review flag marks as possibly High is never shown as a confident Low or Medium.

| | Out-of-fold, all rows | Out-of-fold, ages 18–49 | Validation split |
|---|---:|---:|---:|
| Labelled confident | 56.2% | 57.1% | 54.8% |
| Accuracy when confident | 0.8582 | 0.8703 | 0.8530 |
| Accuracy when borderline | 0.7015 | 0.7021 | 0.6792 |
| Moved to borderline by the flag | 1395 | 991 | 242 |
| True-High patients | 968 | 931 | 165 |
| … confident, labelled High | 832 | 830 | 143 |
| … borderline | 103 | 79 | 15 |
| … confident, labelled Low/Medium | 33 | 22 | 7 |

Out-of-fold, 1223 of 1968 errors (62.1%) carry the borderline label. Confident predictions by class (out-of-fold): Low 3171 at 0.8619; Medium 1241 at 0.7599; High 841 at 0.9893.

The 33 High patients still shown as a confident Low/Medium out-of-fold are the ones the priority-review flag also misses; no label built on this model's probabilities can catch them. "Confident" means the model is sure of its top class, not that the patient is safe. Every prediction still goes to a psychologist.

## Interpretation

Prototype-model evidence on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation. The cut-off was chosen on the same train + validation rows it is reported on, so the confident-group accuracy may be slightly optimistic. The test set was never touched.
