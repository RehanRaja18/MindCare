# Feature Reduction Experiment: Caffeine Intake Removal (Exploratory) — 3-Class Target

**Scope note: this script works on TRAIN and VALIDATION only. It never loads or references X_test, y_test, or test_original_idx anywhere — the 3-class test set is fully spent (see `CLAUDE.md`, "TEST SET USED" entries) and must not be touched again. No canonical artifact was changed — purely exploratory.**

## Motivation

After adopting the 11-feature model (dropping the bottom-6 SHAP-ranked features — `reports/feature_reduction_3class.md`), a further product-UX question was raised: could the onboarding form be simplified even more by also dropping Caffeine Intake? Caffeine ranks **4th** by SHAP importance in the full ranking (`reports/shap_full_ranking_3class.md`) — a real signal, unlike the bottom-6 features that were actually dropped — so this is a genuinely separate, higher-stakes question, tested explicitly rather than assumed.

## Method

Starting from the currently-adopted 11-feature set (Sleep Hours, Physical Activity (hrs/week), Caffeine Intake (mg/day), Stress Level (1-10), Heart Rate (bpm), Breathing Rate (breaths/min), Sweating Level (1-5), Therapy Sessions (per month), Diet Quality (1-10), Occupation, Family History of Anxiety), additionally removed `Caffeine Intake (mg/day)`, leaving 10 features (8 numeric + 2 categorical). New `ColumnTransformer` fit on train rows only; tuned Random Forest (same hyperparameters as `reports/tuning_results_3class.json`) retrained from scratch.

## Results

| Feature set | Accuracy | Balanced acc. | Macro-F1 | Recall Low | Recall Medium | Recall High |
|---|---:|---:|---:|---:|---:|---:|
| Current 11-feature (baseline) | 0.7770 | 0.8084 | 0.8204 | 0.7545 | 0.7737 | 0.8970 |
| **Without Caffeine Intake (10 features)** | **0.7703** | **0.8032** | **0.8130** | 0.7545 | 0.7581 | 0.8970 |

## Deltas (Without Caffeine − 11-Feature Baseline)

| Metric | Δ |
|---|---:|
| Accuracy | -0.0067 |
| Balanced accuracy | -0.0052 |
| Macro-F1 | -0.0074 |
| Recall Low | -0.0000 |
| Recall Medium | -0.0156 |
| Recall High | -0.0000 |

## Honest Verdict

**Dropping Caffeine Intake carries a real, non-trivial cost, concentrated almost entirely in the Medium class.** The top-level aggregate metrics move modestly — accuracy −0.0067, balanced accuracy −0.0052, macro-F1 −0.0074, all under the 1-point bar used elsewhere in this project — but **Medium-class recall drops 1.56 points (−0.0156), the single largest movement of any metric in this experiment**, while Low and High recall are essentially untouched (both ~0.0000). This is not a case that should be rounded down to "no cost" just because the aggregate headline numbers stay under 1 point: a 1.5-point hit concentrated in one class is a real finding, consistent with Caffeine Intake's 4th-place SHAP rank (a genuine signal, unlike the bottom-6 features that were actually dropped with near-zero cost across every metric including per-class recall).

**Decision: KEEP Caffeine Intake as a model input.** The onboarding-simplification goal is instead served by changing *how* it's collected — four everyday serving counts (cups of coffee/tea, energy drinks, cans of soda) converted server-side to the mg/day figure the model needs (`src/api/main.py`, `estimate_caffeine_mg()`) — rather than dropping the feature outright.

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation. This was an exploratory experiment only — no canonical artifact (preprocessor, saved model, or CLAUDE.md feature list) was changed as a result. The test set was never touched by this script.
