# Feature Engineering Experiment (Exploratory) — 3-Class Anxiety Level Target

**Scope note: this script works on TRAIN and VALIDATION only. It never loads or references X_test, y_test, or test_original_idx anywhere. The test set was not touched by this experiment. No artifact here replaces the saved final model, preprocessor, or any canonical pipeline file — this is exploratory only.**

## Engineered Features

1. `HR_Activity_Ratio = Heart Rate (bpm) / (Physical Activity (hrs/week) + 1)`
2. `Sleep_Therapy_Interaction = Sleep Hours * Therapy Sessions (per month)`

Computed directly from raw CSV columns (no leakage — no target or train-only statistic involved), added to the numeric feature list (13 numeric + 6 categorical = 19 raw features), and a new `ColumnTransformer` (`StandardScaler` + `OneHotEncoder`) fit on **train rows only** (`train_original_idx`), then applied to train and validation.

| Engineered feature | mean | std | min | max |
|---|---:|---:|---:|---:|
| HR_Activity_Ratio | 30.1763 | 19.2284 | 6.3830 | 119.0000 |
| Sleep_Therapy_Interaction | 15.3180 | 12.9872 | 0.0000 | 90.4000 |

## Sanity Check

Freshly-computed baseline metrics (original 11 numeric features, existing preprocessed `X_train`/`X_val`) match `reports/tuning_results_3class.json` exactly:

- RF accuracy: computed 0.7733 vs documented 0.7733
- RF balanced accuracy: computed 0.8056 vs documented 0.8056
- XGBoost accuracy: computed 0.7770 vs documented 0.7770
- XGBoost balanced accuracy: computed 0.8074 vs documented 0.8074

## Results: Baseline (11 Features) vs Engineered (13 Features)

| Model | Feature set | Accuracy | Balanced acc. | Macro-F1 | Recall Low | Recall Medium | Recall High |
|---|---|---:|---:|---:|---:|---:|---:|
| Random Forest | Baseline (11) | 0.7733 | 0.8056 | 0.8177 | 0.7545 | 0.7652 | 0.8970 |
| Random Forest | Engineered (13) | 0.7703 | 0.8032 | 0.8154 | 0.7532 | 0.7595 | 0.8970 |
| XGBoost | Baseline (11) | 0.7770 | 0.8074 | 0.8175 | 0.7828 | 0.7426 | 0.8970 |
| XGBoost | Engineered (13) | 0.7758 | 0.8064 | 0.8165 | 0.7853 | 0.7369 | 0.8970 |

## Deltas (Engineered − Baseline)

| Model | Δ Accuracy | Δ Balanced acc. | Δ Macro-F1 | Δ Recall Low | Δ Recall Medium | Δ Recall High |
|---|---:|---:|---:|---:|---:|---:|
| Random Forest | -0.0030 | -0.0023 | -0.0023 | -0.0013 | -0.0057 | +0.0000 |
| XGBoost | -0.0012 | -0.0010 | -0.0010 | +0.0026 | -0.0057 | +0.0000 |

## Honest Verdict

**No headline metric (accuracy, balanced accuracy, macro-F1) moved by as much as 1 point for either model** — the largest absolute change across both models on those three metrics was 0.0030 (0.30 points). This is within the range of run-to-run noise for a tree ensemble on ~7700 training rows, not a meaningful improvement. **`HR_Activity_Ratio` and `Sleep_Therapy_Interaction` do not measurably help either model on this target.** Stated plainly rather than framed as a win: this experiment is a negative result.

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation. This was an exploratory experiment only — no canonical artifact (preprocessor, saved model, or CLAUDE.md feature list) was changed as a result. The test set was never touched by this script.
