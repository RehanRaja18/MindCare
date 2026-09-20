# Post-Processing Experiments (Exploratory) — 3-Class Anxiety Level Target

**Scope note: this script works on TRAIN and VALIDATION only. It never loads or references X_test, y_test, or test_original_idx anywhere. The test set was not touched by this experiment. No artifact here replaces the saved final model, preprocessor, or any canonical pipeline file — this is exploratory only, same as the feature engineering and ensemble experiments.**

## Part 1: Calibration

Tuned Random Forest (`reports/tuning_results_3class.json` hyperparameters) wrapped in `CalibratedClassifierCV(cv=5)`, fit on `X_train`/`y_train` — both `method='sigmoid'` (Platt scaling) and `method='isotonic'` were tested. Evaluated on `X_val`.

### Sanity Check

A freshly-fit uncalibrated Random Forest's per-class Brier scores, computed in this script, closely match the previously documented values:

| Class | Fresh (this script) | Documented | Match |
|---|---:|---:|---|
| Low | 0.151839 | 0.151839 | Yes |
| Medium | 0.164572 | 0.164572 | Yes |
| High | 0.013128 | 0.013128 | Yes |

### Brier Score Comparison — Uncalibrated vs Platt vs Isotonic

| Class | Uncalibrated (documented) | Platt | Isotonic | Best |
|---|---:|---:|---:|---|
| Low | 0.151839 | 0.145719 | 0.143326 | isotonic |
| Medium | 0.164572 | 0.153885 | 0.151477 | isotonic |
| High | 0.013128 | 0.011054 | 0.010756 | isotonic |
| **Mean across classes** | **0.109846** | **0.103553** | **0.101853** | **isotonic** |

**Isotonic scaling has the lower mean Brier score across the 3 classes and is used as the "best calibrated model" for Part 2.**

### Weighted Calibration Gap (predicted − actual) — Uncalibrated vs Platt vs Isotonic

| Class | Uncalibrated (documented) | Platt | Isotonic |
|---|---:|---:|---:|
| Low | -0.0238 | -0.0012 | -0.0010 |
| Medium | -0.0095 | +0.0017 | -0.0025 |
| High | +0.0333 | -0.0005 | +0.0034 |

### Full Reliability Diagram Data (10 Bins) — Platt and Isotonic

#### Platt (sigmoid)

**Low** (Brier=0.145719, weighted_gap=-0.0012, verdict=ROUGHLY CALIBRATED)

| Bin range | Mean predicted | Actual frequency | n |
|---|---:|---:|---:|
| [0.0, 0.1) | 0.0432 | 0.0098 | 204 |
| [0.1, 0.2) | 0.1463 | 0.1164 | 318 |
| [0.2, 0.3) | 0.2440 | 0.3315 | 178 |
| [0.3, 0.4) | 0.3502 | 0.4312 | 109 |
| [0.4, 0.5) | 0.4477 | 0.5119 | 84 |
| [0.5, 0.6) | 0.5481 | 0.4902 | 51 |
| [0.6, 0.7) | 0.6487 | 0.5663 | 83 |
| [0.7, 0.8) | 0.7537 | 0.7079 | 178 |
| [0.8, 0.9) | 0.8523 | 0.8538 | 342 |
| [0.9, 1.0) | 0.9133 | 0.9709 | 103 |

**Medium** (Brier=0.153885, weighted_gap=+0.0017, verdict=ROUGHLY CALIBRATED)

| Bin range | Mean predicted | Actual frequency | n |
|---|---:|---:|---:|
| [0.0, 0.1) | 0.0516 | 0.0177 | 282 |
| [0.1, 0.2) | 0.1472 | 0.1692 | 331 |
| [0.2, 0.3) | 0.2451 | 0.2814 | 167 |
| [0.3, 0.4) | 0.3494 | 0.4634 | 82 |
| [0.4, 0.5) | 0.4526 | 0.5000 | 50 |
| [0.5, 0.6) | 0.5490 | 0.4828 | 87 |
| [0.6, 0.7) | 0.6459 | 0.5789 | 114 |
| [0.7, 0.8) | 0.7575 | 0.7118 | 229 |
| [0.8, 0.9) | 0.8423 | 0.8604 | 308 |
| [0.9, 1.0) | — | — | 0 |

**High** (Brier=0.011054, weighted_gap=-0.0005, verdict=ROUGHLY CALIBRATED)

| Bin range | Mean predicted | Actual frequency | n |
|---|---:|---:|---:|
| [0.0, 0.1) | 0.0138 | 0.0107 | 1490 |
| [0.1, 0.2) | 0.1313 | 0.1250 | 8 |
| [0.2, 0.3) | 0.2372 | 0.0000 | 1 |
| [0.3, 0.4) | 0.3790 | 0.0000 | 1 |
| [0.4, 0.5) | 0.4514 | 0.0000 | 1 |
| [0.5, 0.6) | — | — | 0 |
| [0.6, 0.7) | — | — | 0 |
| [0.7, 0.8) | 0.7065 | 1.0000 | 1 |
| [0.8, 0.9) | 0.8857 | 1.0000 | 1 |
| [0.9, 1.0) | 0.9512 | 0.9932 | 147 |

#### Isotonic

**Low** (Brier=0.143326, weighted_gap=-0.0010, verdict=ROUGHLY CALIBRATED)

| Bin range | Mean predicted | Actual frequency | n |
|---|---:|---:|---:|
| [0.0, 0.1) | 0.0262 | 0.0244 | 287 |
| [0.1, 0.2) | 0.1464 | 0.1250 | 200 |
| [0.2, 0.3) | 0.2523 | 0.2611 | 157 |
| [0.3, 0.4) | 0.3414 | 0.4622 | 119 |
| [0.4, 0.5) | 0.4476 | 0.4677 | 124 |
| [0.5, 0.6) | 0.5483 | 0.4306 | 72 |
| [0.6, 0.7) | 0.6502 | 0.6667 | 99 |
| [0.7, 0.8) | 0.7537 | 0.7077 | 195 |
| [0.8, 0.9) | 0.8551 | 0.8472 | 229 |
| [0.9, 1.0) | 0.9357 | 0.9702 | 168 |

**Medium** (Brier=0.151477, weighted_gap=-0.0025, verdict=ROUGHLY CALIBRATED)

| Bin range | Mean predicted | Actual frequency | n |
|---|---:|---:|---:|
| [0.0, 0.1) | 0.0348 | 0.0190 | 316 |
| [0.1, 0.2) | 0.1453 | 0.1638 | 232 |
| [0.2, 0.3) | 0.2470 | 0.2843 | 197 |
| [0.3, 0.4) | 0.3492 | 0.3434 | 99 |
| [0.4, 0.5) | 0.4503 | 0.5417 | 72 |
| [0.5, 0.6) | 0.5524 | 0.5303 | 132 |
| [0.6, 0.7) | 0.6613 | 0.5672 | 134 |
| [0.7, 0.8) | 0.7519 | 0.7709 | 179 |
| [0.8, 0.9) | 0.8464 | 0.8544 | 261 |
| [0.9, 1.0) | 0.9131 | 0.9643 | 28 |

**High** (Brier=0.010756, weighted_gap=+0.0034, verdict=ROUGHLY CALIBRATED)

| Bin range | Mean predicted | Actual frequency | n |
|---|---:|---:|---:|
| [0.0, 0.1) | 0.0130 | 0.0095 | 1479 |
| [0.1, 0.2) | 0.1156 | 0.1500 | 20 |
| [0.2, 0.3) | 0.2779 | 0.0000 | 1 |
| [0.3, 0.4) | 0.3401 | 0.0000 | 1 |
| [0.4, 0.5) | — | — | 0 |
| [0.5, 0.6) | — | — | 0 |
| [0.6, 0.7) | — | — | 0 |
| [0.7, 0.8) | 0.7063 | 1.0000 | 1 |
| [0.8, 0.9) | — | — | 0 |
| [0.9, 1.0) | 0.9988 | 0.9932 | 148 |

### Does Calibration Change Predictions?

- Predictions changed by Platt calibration: **19 / 1650** (1.15%)
- Predictions changed by isotonic calibration: **21 / 1650** (1.27%)

| Variant | Accuracy | Balanced accuracy | Macro-F1 |
|---|---:|---:|---:|
| Uncalibrated | 0.7733 | 0.8056 | 0.8177 |
| Platt | 0.7752 | 0.8067 | 0.8190 |
| Isotonic | 0.7739 | 0.8057 | 0.8180 |

## Part 2: Threshold Adjustment

Custom rule using isotonic calibrated probabilities: predict High if P(High) >= threshold, else predict argmax(Low, Medium).

| Threshold | Accuracy | Balanced acc. | Macro-F1 | High Precision | High Recall | Low Precision | Low Recall | Medium Precision | Medium Recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| default argmax | 0.7739 | 0.8057 | 0.8180 | 0.9933 | 0.8970 | 0.7757 | 0.7648 | 0.7275 | 0.7553 |
| 0.15 | 0.7721 | 0.8043 | 0.8142 | 0.9737 | 0.8970 | 0.7757 | 0.7648 | 0.7264 | 0.7511 |
| 0.20 | 0.7727 | 0.8047 | 0.8154 | 0.9801 | 0.8970 | 0.7757 | 0.7648 | 0.7268 | 0.7525 |
| 0.25 | 0.7727 | 0.8047 | 0.8154 | 0.9801 | 0.8970 | 0.7757 | 0.7648 | 0.7268 | 0.7525 |
| 0.30 | 0.7733 | 0.8052 | 0.8167 | 0.9867 | 0.8970 | 0.7757 | 0.7648 | 0.7271 | 0.7539 |
| 0.35 | 0.7739 | 0.8057 | 0.8180 | 0.9933 | 0.8970 | 0.7757 | 0.7648 | 0.7275 | 0.7553 |
| 0.40 | 0.7739 | 0.8057 | 0.8180 | 0.9933 | 0.8970 | 0.7757 | 0.7648 | 0.7275 | 0.7553 |

**Best threshold by macro-F1: 0.35** (macro_f1=0.8180 vs default 0.8180, gain=+0.0000). High precision at that threshold: 0.9933 (default 0.9933, cost=+0.0000).

## FINAL VERDICT

**Calibration (isotonic):** 
negligible — mean Brier improved by only 0.0080 (under 0.01), and argmax-based metrics moved by at most 0.0013. Calibration measurably reduces the documented over/under-confidence *pattern* (see weighted-gap table above) even where the aggregate Brier change is small — worth adopting if calibrated probabilities are ever surfaced directly, but not a headline accuracy win.

**Threshold adjustment:** 
negligible / net negative — the best threshold found (0.35) only changes macro-F1 by +0.0000 vs default argmax, under the 1-point bar. **Not worth adopting**; default argmax remains the better choice.

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation. This was an exploratory experiment only — no canonical artifact (preprocessor, saved model, or CLAUDE.md feature list) was changed as a result. The test set was never touched by this script. No new plot images were generated in this pass — reliability diagram data is reported in tabular form only, matching the numeric content (not the images) of the earlier calibration reports.
