# Model Comparison — Random Forest vs XGBoost, 12-Feature Data (3-Class Anxiety Level)

Validation and training data only — the 12-feature splits contain no test arrays, and the 3-class test set is treated as spent. Script: `src/evaluation/compare_models_12feature.py`.

## Candidates

- `rf_current` — the model the API serves today (`mindcare_final_model_12feature.pkl`): 200 trees, max_depth 10, class_weight balanced (params tuned on the old 17 features).
- `rf_retuned` — Random Forest re-tuned on the 12 features: {'n_estimators': 500, 'min_samples_split': 10, 'min_samples_leaf': 4, 'max_features': 'sqrt', 'max_depth': 30, 'class_weight': 'balanced'}.
- `xgb_retuned` — XGBoost re-tuned on the 12 features: {'subsample': 0.8, 'n_estimators': 300, 'min_child_weight': 3, 'max_depth': 3, 'learning_rate': 0.03, 'gamma': 0, 'colsample_bytree': 1.0}; unweighted (beat balanced sample weights in CV, 0.8089 vs 0.8077).
- Re-tuning: identical procedure for both (`src/models/tune_models_12feature.py`) — 40 configurations each, 5-fold CV on train, balanced-accuracy scoring; validation never used to choose.

## 1. Performance (validation, n=1650)

| | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| Accuracy | 0.7739 | 0.7758 | 0.7776 |
| Balanced accuracy | 0.8062 | 0.8074 | 0.8078 |
| Macro-F1 | 0.8182 | 0.8195 | 0.8171 |
| High recall | 0.8970 | 0.8970 | 0.8970 |
| High precision | 0.9933 | 0.9933 | 0.9673 |
| Medium recall | 0.7709 | 0.7680 | 0.7397 |
| Low recall | 0.7506 | 0.7571 | 0.7866 |
| Macro AUROC | 0.9044 | 0.9052 | 0.9083 |
| Macro AUPRC | 0.8576 | 0.8599 | 0.8658 |

Confusion matrices (rows = true Low/Medium/High, columns = predicted):

- `rf_current`: [584, 194, 0] / [161, 545, 1] / [0, 17, 148]
- `rf_retuned`: [589, 189, 0] / [163, 543, 1] / [0, 17, 148]
- `xgb_retuned`: [612, 166, 0] / [179, 523, 5] / [0, 17, 148]

## 2. Stability

| | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| 5-fold CV balanced accuracy (train) | 0.8093 ± 0.0154 | 0.8093 ± 0.0151 | 0.8085 ± 0.0144 |
| 5-fold CV macro-F1 (train) | 0.8242 ± 0.0128 | 0.8242 ± 0.0125 | 0.8216 ± 0.0126 |
| 5-fold CV High recall (train) | 0.8718 ± 0.0242 | 0.8718 ± 0.0242 | 0.8718 ± 0.0222 |
| Validation balanced accuracy over 5 seeds | 0.8071 ± 0.0011 | 0.8072 ± 0.0011 | 0.8067 ± 0.0007 |

## 3. Calibration (validation; lower is better)

| | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| Log loss | 0.5202 | 0.5096 | 0.4836 |
| Brier — Low | 0.1470 | 0.1444 | 0.1408 |
| Brier — Medium | 0.1598 | 0.1567 | 0.1514 |
| Brier — High | 0.0132 | 0.0133 | 0.0124 |
| ECE (10-bin) — Low | 0.0608 | 0.0443 | 0.0161 |
| ECE (10-bin) — Medium | 0.0603 | 0.0549 | 0.0199 |
| ECE (10-bin) — High | 0.0332 | 0.0302 | 0.0069 |

## 4. Uncertainty Flag (production rule P(High) ≥ 0.10)

| | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| Rows flagged | 363 | 352 | 199 |
| True-High caught | 158 / 165 | 156 / 165 | 152 / 165 |
| False-flag rate | 0.5647 | 0.5568 | 0.2362 |
| Own True-High→Medium misses caught | 10 / 17 | 8 / 17 | 4 / 17 |
| Union of all models' True-High→Medium misses caught | 10 / 17 | 8 / 17 | 4 / 17 |

Rows each model must flag to catch N of the 165 true-High cases (its own best threshold; fewer = less review work):

| High cases caught | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| 150 | 169 | 176 | 170 |
| 155 | 236 | 301 | 326 |
| 158 | 360 | 373 | 384 |
| 160 | 400 | 423 | 442 |
| 163 | 527 | 548 | 523 |
| 165 | 772 | 780 | 619 |

## 5. SHAP Feature Importance (share of mean |SHAP|, 300 validation rows)

| Rank | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| 1 | Stress Level (1-10) (37.6%) | Stress Level (1-10) (36.8%) | Stress Level (1-10) (44.3%) |
| 2 | Therapy Sessions (per month) (13.2%) | Therapy Sessions (per month) (13.5%) | Sleep Hours (16.2%) |
| 3 | Sleep Hours (12.5%) | Sleep Hours (13.4%) | Therapy Sessions (per month) (14.7%) |
| 4 | Caffeine Intake (mg/day) (11.0%) | Caffeine Intake (mg/day) (10.1%) | Caffeine Intake (mg/day) (10.2%) |
| 5 | Diet Quality (1-10) (5.9%) | Diet Quality (1-10) (6.1%) | Physical Activity (hrs/week) (4.9%) |
| 6 | Physical Activity (hrs/week) (3.9%) | Physical Activity (hrs/week) (4.1%) | Diet Quality (1-10) (2.2%) |
| 7 | Heart Rate (bpm) (3.8%) | Heart Rate (bpm) (3.6%) | Heart Rate (bpm) (1.8%) |
| 8 | Family History of Anxiety (2.8%) | Occupation (2.9%) | Age (1.7%) |
| 9 | Breathing Rate (breaths/min) (2.5%) | Family History of Anxiety (2.7%) | Occupation (1.4%) |
| 10 | Occupation (2.5%) | Breathing Rate (breaths/min) (2.3%) | Family History of Anxiety (1.1%) |
| 11 | Age (2.3%) | Age (2.3%) | Breathing Rate (breaths/min) (1.0%) |
| 12 | Sweating Level (1-5) (2.0%) | Sweating Level (1-5) (2.2%) | Sweating Level (1-5) (0.4%) |

## 6. Fairness (validation)

**occupation** — balanced-accuracy range across groups, and High-recall range across groups with ≥15 true-High rows:

| | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| Balanced-accuracy range | 0.1079 | 0.0898 | 0.1202 |
| High-recall range (reliable groups) | 0.1944 | 0.1944 | 0.1944 |

**age_band** — balanced-accuracy range across groups, and High-recall range across groups with ≥15 true-High rows:

| | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| Balanced-accuracy range | 0.3121 | 0.3144 | 0.3105 |
| High-recall range (reliable groups) | 0.0664 | 0.0664 | 0.0664 |

**gender** — balanced-accuracy range across groups, and High-recall range across groups with ≥15 true-High rows:

| | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| Balanced-accuracy range | 0.0359 | 0.0463 | 0.0287 |
| High-recall range (reliable groups) | 0.0351 | 0.0351 | 0.0351 |

Per-group detail is in `reports/model_comparison_12feature.json`. Most occupations have fewer than 15 true-High validation rows, so their High recall is not comparable.

## 7. Robustness (validation)

Single-feature knockout (feature replaced by its train mean/mode) — balanced accuracy:

| | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| No knockout | 0.8062 | 0.8074 | 0.8078 |
| Age | 0.8036 | 0.8075 | 0.8079 |
| Sleep Hours | 0.7860 | 0.7775 | 0.7151 |
| Physical Activity (hrs/week) | 0.8044 | 0.8080 | 0.7965 |
| Caffeine Intake (mg/day) | 0.5232 | 0.7044 | 0.7879 |
| Stress Level (1-10) | 0.3570 | 0.3611 | 0.3766 |
| Heart Rate (bpm) | 0.8066 | 0.8086 | 0.8041 |
| Breathing Rate (breaths/min) | 0.8065 | 0.8091 | 0.8062 |
| Sweating Level (1-5) | 0.8065 | 0.8077 | 0.8078 |
| Therapy Sessions (per month) | 0.5068 | 0.5089 | 0.5485 |
| Diet Quality (1-10) | 0.7477 | 0.6745 | 0.8027 |
| Occupation | 0.8058 | 0.8041 | 0.8077 |
| Family History of Anxiety | 0.8020 | 0.8045 | 0.8109 |

Gaussian noise on all numeric features (multiples of each feature's train std; identical noise for every model) — balanced accuracy:

| | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| 0.25× std | 0.7608 | 0.7609 | 0.7729 |
| 0.5× std | 0.6887 | 0.6861 | 0.7148 |
| 1.0× std | 0.5558 | 0.5521 | 0.6151 |

Stress Level shifted for every row (clipped to 1-10) — fraction predicted High:

| | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| shift -3 | 0.0000 | 0.0000 | 0.0248 |
| shift -2 | 0.0309 | 0.0309 | 0.0558 |
| shift -1 | 0.0655 | 0.0655 | 0.0836 |
| shift 0 | 0.0903 | 0.0903 | 0.0927 |
| shift 1 | 0.0903 | 0.0903 | 0.0933 |
| shift 2 | 0.0903 | 0.0903 | 0.0933 |
| shift 3 | 0.0903 | 0.0903 | 0.0945 |

Age sensitivity — mean P(High) for the true-High validation rows under 50, with only Age changed (the API accepts 18-49 only; 55 shows the dataset's age artifact):

| | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| Age 18 | 0.9095 | 0.9012 | 0.8885 |
| Age 30 | 0.9157 | 0.9140 | 0.8862 |
| Age 40 | 0.9168 | 0.9152 | 0.8866 |
| Age 49 | 0.9035 | 0.9048 | 0.8845 |
| Age 55 | 0.6281 | 0.6152 | 0.8628 |

## 8. Practical

| | `rf_current` | `rf_retuned` | `xgb_retuned` |
|---|---:|---:|---:|
| Single prediction (ms) | 37.2 | 82.9 | 1.1 |
| Pickled size (MB) | 9.2 | 44.9 | 1.0 |

## Caveats

- Validation/train evidence only; no candidate has a test-set number.
- The dataset is very likely synthetic (see CLAUDE.md) — these are prototype comparisons, not clinical validation.
- Latency depends on the machine; compare the ratio, not the absolute numbers.
