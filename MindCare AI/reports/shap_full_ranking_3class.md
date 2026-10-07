# Complete SHAP Feature Importance Ranking — 3-Class Anxiety Level Target

## Scope

- Model: tuned Random Forest from `reports/tuning_results_3class.json` (n_estimators=200, max_depth=10, min_samples_split=10, min_samples_leaf=4, max_features='sqrt', class_weight='balanced').
- Training: existing `X_train`/`y_train` only.
- SHAP computed on the same 500-row sample of `X_val` as `reports/shap_summary_3class.md`, for direct consistency; test set untouched.
- Seed: 42.
- Importance = mean absolute SHAP value across all 3 classes and sampled rows.

## Grouped Ranking — 17 Original Features (Primary Result)

The 23 one-hot categorical columns (13 for Occupation, 2 each for the 5 binary features) are summed back to their original raw feature. Numeric features are unchanged (1 column each, no grouping needed).

| Rank | Feature | Mean \|SHAP\| | Type | Columns summed |
|---:|---|---:|---|---:|
| 1 | Stress Level (1-10) | 0.13161728 | Numeric | 1 |
| 2 | Therapy Sessions (per month) | 0.05513000 | Numeric | 1 |
| 3 | Sleep Hours | 0.05060564 | Numeric | 1 |
| 4 | Caffeine Intake (mg/day) | 0.03547575 | Numeric | 1 |
| 5 | Diet Quality (1-10) | 0.02443511 | Numeric | 1 |
| 6 | Physical Activity (hrs/week) | 0.01726092 | Numeric | 1 |
| 7 | Heart Rate (bpm) | 0.01560360 | Numeric | 1 |
| 8 | Family History of Anxiety | 0.01364324 | Categorical | 2 |
| 9 | Breathing Rate (breaths/min) | 0.01046683 | Numeric | 1 |
| 10 | Sweating Level (1-5) | 0.01027403 | Numeric | 1 |
| 11 | Occupation | 0.01006922 | Categorical | 13 |
| 12 | Age | 0.00944933 | Numeric | 1 |
| 13 | Alcohol Consumption (drinks/week) | 0.00529885 | Numeric | 1 |
| 14 | Dizziness | 0.00364129 | Categorical | 2 |
| 15 | Smoking | 0.00299399 | Categorical | 2 |
| 16 | Recent Major Life Event | 0.00228479 | Categorical | 2 |
| 17 | Medication | 0.00178400 | Categorical | 2 |

## Full 34-Column Ranking (Transformed / One-Hot-Encoded Features)

Shown for transparency — this is the raw basis the grouped table above was computed from. Top 10 here reproduce `reports/shap_summary_3class.md` exactly.

| Rank | Transformed column | Mean \|SHAP\| | Original feature |
|---:|---|---:|---|
| 1 | Stress Level (1-10) | 0.13161728 | Stress Level (1-10) |
| 2 | Therapy Sessions (per month) | 0.05513000 | Therapy Sessions (per month) |
| 3 | Sleep Hours | 0.05060564 | Sleep Hours |
| 4 | Caffeine Intake (mg/day) | 0.03547575 | Caffeine Intake (mg/day) |
| 5 | Diet Quality (1-10) | 0.02443511 | Diet Quality (1-10) |
| 6 | Physical Activity (hrs/week) | 0.01726092 | Physical Activity (hrs/week) |
| 7 | Heart Rate (bpm) | 0.01560360 | Heart Rate (bpm) |
| 8 | Breathing Rate (breaths/min) | 0.01046683 | Breathing Rate (breaths/min) |
| 9 | Sweating Level (1-5) | 0.01027403 | Sweating Level (1-5) |
| 10 | Age | 0.00944933 | Age |
| 11 | Family History of Anxiety=No | 0.00740978 | Family History of Anxiety |
| 12 | Family History of Anxiety=Yes | 0.00623346 | Family History of Anxiety |
| 13 | Alcohol Consumption (drinks/week) | 0.00529885 | Alcohol Consumption (drinks/week) |
| 14 | Dizziness=Yes | 0.00194872 | Dizziness |
| 15 | Smoking=No | 0.00177824 | Smoking |
| 16 | Dizziness=No | 0.00169257 | Dizziness |
| 17 | Occupation=Lawyer | 0.00167205 | Occupation |
| 18 | Occupation=Other | 0.00129314 | Occupation |
| 19 | Occupation=Engineer | 0.00126363 | Occupation |
| 20 | Smoking=Yes | 0.00121574 | Smoking |
| 21 | Recent Major Life Event=No | 0.00119167 | Recent Major Life Event |
| 22 | Recent Major Life Event=Yes | 0.00109313 | Recent Major Life Event |
| 23 | Occupation=Doctor | 0.00099837 | Occupation |
| 24 | Medication=No | 0.00097803 | Medication |
| 25 | Occupation=Scientist | 0.00093986 | Occupation |
| 26 | Occupation=Teacher | 0.00082763 | Occupation |
| 27 | Medication=Yes | 0.00080597 | Medication |
| 28 | Occupation=Musician | 0.00074518 | Occupation |
| 29 | Occupation=Athlete | 0.00044548 | Occupation |
| 30 | Occupation=Freelancer | 0.00042705 | Occupation |
| 31 | Occupation=Chef | 0.00041971 | Occupation |
| 32 | Occupation=Artist | 0.00037956 | Occupation |
| 33 | Occupation=Student | 0.00035006 | Occupation |
| 34 | Occupation=Nurse | 0.00030748 | Occupation |

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation. Grouping by summing dummy-column importances is a standard, if approximate, convention for one-hot-encoded categorical features — it can overstate a high-cardinality feature's importance relative to a max-based grouping, since Occupation's importance here is a sum over 13 columns while each binary feature's is a sum over only 2. This is worth keeping in mind when comparing Occupation's rank directly against the binary categoricals.
