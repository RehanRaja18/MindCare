# Phase 19 — Robustness Testing (3-Class Anxiety Level Target)

## Scope

- Model: saved final tuned Random Forest (`data/processed/mindcare_final_model.pkl`).
- All perturbation applied to raw feature values on the **validation split only** (via `val_original_idx`); the test set was never touched.
- Any imputation statistic (mean/mode) is computed from the **train split only**.
- Validation rows: 1650; seed: 42.

## Baseline (Sanity Check)

Predictions on unmodified validation rows, run through this script's own preprocessor+model pipeline, reproduce the documented tuned Random Forest metrics:

| Metric | Value |
|---|---:|
| accuracy | 0.7733 |
| balanced_accuracy | 0.8056 |
| macro_f1 | 0.8177 |
| high_class_recall | 0.8970 |

## Test 1: Missing Features (Single-Feature Knockout)

Each feature in turn is replaced with its train-set mean (numeric) or mode (categorical) across all validation rows, simulating that feature being unavailable at inference time. Sorted worst-impact first.

| Feature | Balanced accuracy | Δ vs baseline | High recall |
|---|---:|---:|---:|
| Stress Level (1-10) | 0.4291 | -0.3765 | 0.2242 |
| Therapy Sessions (per month) | 0.5590 | -0.2465 | 0.1515 |
| Sleep Hours | 0.7922 | -0.0134 | 0.8545 |
| Caffeine Intake (mg/day) | 0.7972 | -0.0084 | 0.8727 |
| Diet Quality (1-10) | 0.7995 | -0.0060 | 0.8788 |
| Family History of Anxiety | 0.8029 | -0.0026 | 0.8970 |
| Heart Rate (bpm) | 0.8055 | -0.0001 | 0.8970 |
| Sweating Level (1-5) | 0.8056 | +0.0000 | 0.8970 |
| Age | 0.8057 | +0.0001 | 0.8970 |
| Recent Major Life Event | 0.8059 | +0.0003 | 0.8970 |
| Physical Activity (hrs/week) | 0.8065 | +0.0009 | 0.8970 |
| Breathing Rate (breaths/min) | 0.8068 | +0.0012 | 0.8970 |
| Medication | 0.8068 | +0.0013 | 0.8970 |
| Occupation | 0.8070 | +0.0014 | 0.8970 |
| Dizziness | 0.8070 | +0.0014 | 0.8970 |
| Alcohol Consumption (drinks/week) | 0.8070 | +0.0015 | 0.8970 |
| Smoking | 0.8079 | +0.0023 | 0.8970 |

**Most damaging single-feature loss: Stress Level (1-10)** (balanced accuracy drops 0.3765). This is consistent with the Phase 17 SHAP ranking and the documented Stress Level ablation finding — the model's single largest dependency shows up again here as its single largest robustness weakness.

## Test 2: Noisy Data (Gaussian Noise, All Numeric Features)

Gaussian noise scaled to each feature's train-set standard deviation is added to all 11 numeric features simultaneously, at increasing intensity.

| Noise level | Balanced accuracy | Δ vs baseline | High recall |
|---|---:|---:|---:|
| 0.25x std | 0.7732 | -0.0323 | 0.8000 |
| 0.5x std | 0.6837 | -0.1219 | 0.6121 |
| 1.0x std | 0.5560 | -0.2496 | 0.3273 |
| 2.0x std | 0.4480 | -0.3576 | 0.1576 |

## Test 3: Incorrect / Out-of-Range Inputs (Qualitative)

These have no ground-truth label - the question is whether the pipeline behaves safely (no crash, no silently absurd output) rather than whether it's "correct".

| Case | Crashed? | Predicted class | Probabilities |
|---|---|---|---|
| negative_age | No | Medium | Low=0.2887, Medium=0.6191, High=0.0922 |
| impossible_stress | No | Medium | Low=0.1556, Medium=0.7001, High=0.1443 |
| impossible_heart_rate | No | Medium | Low=0.2860, Medium=0.5848, High=0.1292 |
| negative_alcohol | No | Medium | Low=0.2541, Medium=0.6560, High=0.0900 |
| all_fields_extreme_max | No | Medium | Low=0.1605, Medium=0.5140, High=0.3255 |

**Any crashes: No.** `StandardScaler` does not clip or validate range, so out-of-range numeric inputs are silently transformed and passed to the model, which still produces a confident-looking prediction. There is **no input validation layer** in this pipeline — clearly out-of-range values (e.g., Age=-5, Heart Rate=9000) do not raise an error or a warning anywhere before reaching the model.

## Test 4: Distribution Shift (Stress Level)

Stress Level (the top SHAP feature) is shifted by a constant across every validation row (clipped to the valid 1-10 range), simulating a population-level drift in this one feature, and the resulting change in the fraction of rows predicted High is measured.

| Stress Level shift | Predicted High fraction | Baseline | Δ |
|---:|---:|---:|---:|
| -3 | 0.0418 | 0.0903 | -0.0485 |
| -1 | 0.0879 | 0.0903 | -0.0024 |
| +1 | 0.0903 | 0.0903 | +0.0000 |
| +3 | 0.0903 | 0.0903 | +0.0000 |

## Not Applicable to This Dataset

Per `docs/master_project_instructions.md` PHASE 19's checklist, these items cannot be tested with the data available, and are noted explicitly rather than skipped:

- **Wording Changes:** No text/NLP input fields exist in this dataset - all features are numeric or fixed-category; there is no wording to vary.
- **Site Changes:** The dataset has no site/institution identifier column - it is a single source file, so cross-site robustness cannot be tested with the data available.
- **Temporal Changes:** The dataset has no timestamp/date column - temporal drift cannot be tested with the data available.

## Documented Failure Modes

1. **Single-feature fragility.** Losing Stress Level (1-10) alone costs 0.3765 balanced-accuracy points — the model is not robust to its most important feature being missing or corrupted.
2. **No input validation.** The pipeline accepts and silently processes physically impossible values (negative ages, triple-digit stress scores, heart rates in the thousands) without any error, warning, or rejection.
3. **Sensitivity to noise scales with the amount added** (see Test 2) - expected, but the specific degradation curve is now measured rather than assumed.
4. **Distribution shift in Stress Level directly moves the predicted High rate** (see Test 4) - if the real-world population's stress reporting drifts from this training distribution, the model's High-flag rate would drift with it, silently.

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation. These tests were run against the validation split only - the test set remains untouched.
