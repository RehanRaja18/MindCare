# Feature Reduction Experiment (Exploratory) — 3-Class Anxiety Level Target

**Scope note: this script works on TRAIN and VALIDATION only. It never loads or references X_test, y_test, or test_original_idx anywhere. The test set was not touched. No canonical artifact (saved model, preprocessor, or CLAUDE.md feature list) was changed — purely exploratory, same protocol as the feature engineering, ensemble, and calibration experiments.**

## Method

Removed the 6 lowest-SHAP-ranked features (`reports/shap_full_ranking_3class.md`, grouped ranking, ranks 12-17): Age, Alcohol Consumption (drinks/week), Dizziness, Smoking, Recent Major Life Event, Medication.

Remaining 11 features — 9 numeric (Sleep Hours, Physical Activity (hrs/week), Caffeine Intake (mg/day), Stress Level (1-10), Heart Rate (bpm), Breathing Rate (breaths/min), Sweating Level (1-5), Therapy Sessions (per month), Diet Quality (1-10)) + 2 categorical (Occupation, Family History of Anxiety).

New `ColumnTransformer` (`StandardScaler` + `OneHotEncoder`) fit on **train rows only** (`train_original_idx`), applied to train and validation. Tuned Random Forest (same hyperparameters as `reports/tuning_results_3class.json`) retrained on this reduced feature set.

## Results

| Feature set | Accuracy | Balanced acc. | Macro-F1 | Recall Low | Recall Medium | Recall High |
|---|---:|---:|---:|---:|---:|---:|
| Baseline (17 features, documented) | 0.7733 | 0.8056 | 0.8177 | 0.7545 | 0.7652 | 0.8970 |
| **Reduced (11 features)** | **0.7770** | **0.8084** | **0.8204** | 0.7545 | 0.7737 | 0.8970 |

## Deltas (Reduced − Baseline)

| Metric | Δ |
|---|---:|
| Accuracy | +0.0036 |
| Balanced accuracy | +0.0028 |
| Macro-F1 | +0.0027 |
| Recall Low | -0.0000 |
| Recall Medium | +0.0085 |
| Recall High | +0.0000 |

## Honest Verdict

**No headline metric moved by as much as 1 point in either direction** (largest absolute change: 0.0036, 0.36 points). Removing Age, Alcohol Consumption, Dizziness, Smoking, Recent Major Life Event, and Medication costs essentially nothing — performance is statistically indistinguishable from the full 17-feature model. Stated plainly: **these 6 features are not pulling meaningful weight for this model**, consistent with their bottom-6 SHAP ranking. This is not evidence they should definitely be dropped from production (a smaller feature set has real operational value — less data to collect, validate, and maintain — but that's a product decision, not just a performance one), but the performance case against keeping them is weak to none.

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation. This was an exploratory experiment only — no canonical artifact (preprocessor, saved model, or CLAUDE.md feature list) was changed as a result. The test set was never touched by this script.
