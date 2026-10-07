# Feature Addition Experiment: Re-adding Age — 3-Class Target

**Scope note: this script (`src/models/adopt_12feature_model.py`) works on TRAIN and VALIDATION
only. Per explicit instruction, it does not load, transform, or reference X_test, y_test, or
test_original_idx anywhere — the 3-class test set has been used twice already (17-feature,
11-feature) and is being treated as fully spent going forward. This Age re-addition is a
clinical/UX decision, not a performance claim requiring test-set verification, so no test-set
check was performed or is planned for this configuration.**

## Motivation

Age was one of the 6 lowest-SHAP-ranked features dropped when the 11-feature model was adopted
(`reports/feature_reduction_3class.md`) — a product/UX decision to shorten onboarding, not a
performance-driven one. This experiment re-adds Age on top of the current 11-feature set (a
clinical/UX decision to restore it), producing a genuinely new 12-feature configuration that has
never been tested before. The near-zero cost found for the original 6-feature group drop does not
by itself establish the cost of adding back just one of those six in isolation — measured here
for real rather than assumed.

## Method

Starting from the currently-adopted 11-feature set (Sleep Hours, Physical Activity (hrs/week),
Caffeine Intake (mg/day), Stress Level (1-10), Heart Rate (bpm), Breathing Rate (breaths/min),
Sweating Level (1-5), Therapy Sessions (per month), Diet Quality (1-10), Occupation, Family
History of Anxiety), added back `Age`, producing 12 features (10 numeric + 2 categorical). New
`ColumnTransformer` fit on train rows only; tuned Random Forest (same hyperparameters as
`reports/tuning_results_3class.json` / the 11-feature model) retrained from scratch.

## Results

| Feature set | Accuracy | Balanced acc. | Macro-F1 | Recall Low | Recall Medium | Recall High |
|---|---:|---:|---:|---:|---:|---:|
| Current 11-feature (baseline) | 0.7770 | 0.8084 | 0.8204 | 0.7545 | 0.7737 | 0.8970 |
| **With Age (12 features)** | **0.7739** | **0.8062** | **0.8182** | 0.7506 | 0.7709 | 0.8970 |

## Deltas (With Age − 11-Feature Baseline)

| Metric | Δ |
|---|---:|
| Accuracy | -0.0031 |
| Balanced accuracy | -0.0022 |
| Macro-F1 | -0.0022 |
| Recall Low | -0.0039 |
| Recall Medium | -0.0028 |
| Recall High | -0.0000 |

## Honest Verdict

**No headline or per-class metric moved by as much as 1 point in either direction** (largest absolute change: recall_low at -0.0039, 0.39 points). Re-adding Age on top of the current 11-feature set costs/gains essentially nothing on this validation split. This is consistent with Age's bottom-6 SHAP ranking in the original 17-feature analysis (`reports/shap_full_ranking_3class.md`), but this exact 12-feature combination had never actually been tested before this run - this is a measured result, not an assumption carried over from that ranking.

## Decision

**Age is re-added as a model input regardless of this validation result** — this was explicitly a
clinical/UX decision (restoring a field product/clinical stakeholders want collected), not
something contingent on a performance finding. This report exists so that decision is made with
real numbers in hand rather than an assumption, and so that if the result had shown a real cost,
that cost would be visible and disclosed rather than hidden. See `CLAUDE.md` and
`docs/model_card.md` for how this decision and its measured cost/benefit are documented going
forward.

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not clinical
validation. Validation-set result only — this configuration has not been, and per explicit
instruction will not be, evaluated against the test set (X_test/y_test), which is being treated
as fully spent for the 3-class target after its two prior uses (17-feature, 11-feature).
