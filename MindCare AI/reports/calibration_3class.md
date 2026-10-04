# Calibration Report — Tuned Random Forest, 3-Class Target (High class)

## Scope

- Model: tuned Random Forest (n_estimators=200, max_depth=10, min_samples_split=10, min_samples_leaf=4, max_features='sqrt', class_weight='balanced') from `reports/tuning_results_3class.json`.
- Evaluation: `X_val`/`y_val` from `mindcare_processed_splits_3class.npz`; test set untouched.
- Validation rows: 1650; seed: 42.
- Calibration target: High vs rest (one-vs-rest), 10 uniform-width probability bins.

## Brier Score

**Brier score (High vs rest): 0.013128**

(0 = perfect; 0.25 = always predicting 0.5; lower is better. This is a strictly proper scoring rule combining calibration and sharpness.)

## Reliability Diagram Data

| Bin range | Mean predicted P(High) | Actual frequency of High | n in bin |
|---|---:|---:|---:|
| [0.0, 0.1) | 0.0339 | 0.0061 | 1304 |
| [0.1, 0.2) | 0.1356 | 0.0364 | 165 |
| [0.2, 0.3) | 0.2360 | 0.1071 | 28 |
| [0.3, 0.4) | 0.3469 | 0.0000 | 3 |
| [0.4, 0.5) | 0.4069 | 0.0000 | 1 |
| [0.5, 0.6) | 0.5740 | 1.0000 | 1 |
| [0.6, 0.7) | — | — | 0 |
| [0.7, 0.8) | 0.7726 | 1.0000 | 1 |
| [0.8, 0.9) | 0.8599 | 1.0000 | 8 |
| [0.9, 1.0) | 0.9854 | 0.9928 | 139 |

Count-weighted mean gap (predicted − actual): **+0.0333**
Count-weighted mean absolute gap: 0.0367

**Verdict: OVER-CONFIDENT (predicted probabilities skew higher than actual outcome frequency)**

![Reliability diagram](calibration_high_3class.png)

## The 17 Unanimous True-High / Predicted-Medium Misses

These are the validation rows where true label is High and the three untuned baseline models (Logistic Regression, Random Forest, XGBoost) all predicted Medium (`reports/baseline_results_3class.json`). Shown here: this tuned Random Forest's full predicted-probability vector on each of those same 17 rows.

| Original row | Anxiety Level | P(Low) | P(Medium) | P(High) |
|---:|---:|---:|---:|---:|
| 10691 | 7 | 0.2233 | 0.6858 | 0.0909 |
| 3617 | 7 | 0.2321 | 0.6744 | 0.0935 |
| 7745 | 7 | 0.2421 | 0.6849 | 0.0730 |
| 8451 | 7 | 0.1425 | 0.6044 | 0.2530 |
| 5963 | 7 | 0.2036 | 0.5416 | 0.2547 |
| 6420 | 7 | 0.3577 | 0.6002 | 0.0421 |
| 7929 | 7 | 0.2564 | 0.6321 | 0.1115 |
| 3628 | 8 | 0.1953 | 0.7117 | 0.0929 |
| 1819 | 8 | 0.1575 | 0.6133 | 0.2292 |
| 1432 | 7 | 0.1991 | 0.6636 | 0.1373 |
| 7312 | 7 | 0.1662 | 0.7262 | 0.1076 |
| 10199 | 7 | 0.3269 | 0.6329 | 0.0402 |
| 5237 | 9 | 0.1971 | 0.6119 | 0.1910 |
| 6275 | 7 | 0.2194 | 0.7104 | 0.0702 |
| 22 | 7 | 0.1701 | 0.6823 | 0.1476 |
| 2318 | 7 | 0.2050 | 0.6764 | 0.1186 |
| 9746 | 7 | 0.3811 | 0.5540 | 0.0650 |

Mean P(High) on these 17 rows: **0.1246** (range [0.0402, 0.2547])
Rows with P(High) >= 0.10: 9/17
Rows with P(High) >= 0.20: 3/17

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see CLAUDE.md); not clinical validation.
