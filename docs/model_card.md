# Model Card — MindCare Anxiety Level Classifier (3-Class)

**Model:** XGBoost (`xgboost.XGBClassifier`), canonical since 2026-09-28. It replaced a tuned
Random Forest; see "Performance — 12-Feature XGBoost" and `reports/model_comparison_12feature.md`.
Sections covering Phases 14-19 below describe the earlier Random Forest models unless they say
otherwise.
**Target:** 3-class Anxiety Level — Low / Medium / High (primary target as of 2026-09-14)
**Status:** Prototype / research model. Not clinically validated.

This card consolidates findings already established and documented in [`CLAUDE.md`](../CLAUDE.md)
and the reports under [`reports/`](../reports/). No number here is invented or re-rounded beyond
what those source files already report — each figure is cited to its source.

---

## Intended Use

This model produces a **decision-support suggestion only**. Per the project's critical workflow
constraint (`CLAUDE.md`, "What this is"):

> AI prediction → psychologist reviews → psychologist approves/modifies → patient sees it.

The model's output must never reach a patient directly and must never bypass psychologist review.
It is not an autonomous diagnostic tool, and nothing in this card should be read as clinical
validation of diagnostic accuracy. This is a research/prototype model (`CLAUDE.md` Engineering
Rule 7).

**Intended population: adults aged 18–49 (decided 2026-09-27).** The API refuses a prediction
for any other age. Platform rules (decided 2026-09-28):
- **Under 18: cannot register for MindCare at all.** The web app's registration must block
  them. The training data has no one under 18, and physiological norms and consent rules differ
  for minors. If a minor ever reaches this model, the API rejects them as "not eligible", with
  no referral.
- **50 and over: can register, and are redirected straight to a psychologist**, with no AI
  pre-assessment. The training data has almost no High-anxiety cases from age 50 on, so there
  is almost no evidence the model can recognise High anxiety at these ages.

See Known Limitations #12.

---

## Training Data

- **Source:** `data/raw/mindcare_dataset_final.csv` — ~11,000 rows, 23 columns.
- **This is very likely synthetic data**, not real patient data: near-uniform demographics, zero
  missing values/duplicates, templated recommendation text (`CLAUDE.md`, "Dataset"). All
  performance claims in this card should be read as prototype-level, not clinically validated,
  per that same caveat.
- **Split:** 7700 / 1650 / 1650 (train/val/test), stratified, seed=42. This split is shared
  between the 3-class target and the 5-class Severity (secondary/reference) target — the same
  `train_original_idx`/`val_original_idx`/`test_original_idx` row membership is reused for both,
  via `data/processed/mindcare_processed_splits_3class.npz` (`CLAUDE.md`, "Target change").
- **Test set:** the 3-class test set has been evaluated **twice** — 2026-09-15 for the original
  17-feature model, 2026-09-22 for the 11-feature model — and is now **fully spent** (see "Final
  Test-Set Evaluation" below for both). The current canonical 12-feature model (Age restored,
  see "Features" below) deliberately does **not** have a test-set evaluation — validation-only
  by design, since a third use was not justified as a genuinely new configuration requiring it.
  The 5-class Severity test set remains untouched.

### Target definition

The 3-class target is derived **directly from the raw `Anxiety Level (1-10)` column**, not from
the 5-class Severity column (their boundaries don't align cleanly per earlier EDA):

- **Low:** Anxiety Level 1-3
- **Medium:** Anxiety Level 4-6
- **High:** Anxiety Level 7-10

Class balance (validation split, `reports/baseline_results_3class.json`): Low 778/1650 (47.2%),
Medium 707/1650 (42.8%), High 165/1650 (10.0%). This is an imbalanced target — accuracy alone is
insufficient; balanced accuracy, macro-F1, and per-class recall (especially High) are required
(`CLAUDE.md`, "Target change").

---

## Features

**12 features (10 numeric + 2 categorical), as of 2026-09-22** — the current canonical set,
reached via two changes to the original 17 the same day: first reduced to 11
(`reports/feature_reduction_3class.md`), then Age restored, bringing it to 12
(`reports/feature_addition_age_3class.md`). The 11-feature configuration is superseded and no
longer deployed. The 5-class Severity reference model is unaffected by either change and still
uses all 17.

- **Numeric (10):** Stress Level (1-10), Therapy Sessions (per month), Sleep Hours, Caffeine
  Intake (mg/day), Diet Quality (1-10), Physical Activity (hrs/week), Heart Rate (bpm),
  Breathing Rate (breaths/min), Sweating Level (1-5), **Age** (restored 2026-09-22, see below).
  **Caffeine Intake is no longer entered as a raw mg value.** The API
  (`src/api/main.py`) collects it as four everyday serving counts — `cups_of_coffee`,
  `cups_of_tea`, `energy_drinks`, `cans_of_soda` — and converts them server-side via
  `estimate_caffeine_mg()` using fixed average mg-per-serving figures (coffee ~95mg, tea
  ~47mg, energy drink ~80mg, soda ~35mg — commonly-cited USDA/Mayo-Clinic-style averages, an
  approximation not a measurement). The computed total is what the model actually receives,
  checked against the same plausibility bounds as before.
  **Stress Level is no longer entered as a raw 1-10 rating either.** The API collects the 4
  items of the Perceived Stress Scale (PSS-4) — `pss_uncontrollable`, `pss_confident`,
  `pss_going_your_way`, `pss_difficulties_piling_up`, each 0-4, with `pss_confident` and
  `pss_going_your_way` reverse-scored — and converts the 0-16 total to 1-10 server-side via
  `estimate_stress_level()` (`src/inference/stress_scale.py`):
  `round_half_up(1 + total × 9/16)`, clamped to [1, 10]. **Two different evidence levels apply
  here and should not be conflated:** the PSS-4 questionnaire itself is a validated instrument
  (Cohen, Kamarck & Mermelstein, 1983, *Journal of Health and Social Behavior* 24(4)), but the
  0-16 → 1-10 mapping is **this project's own invented convention and has not been
  independently validated**. The model was trained on the dataset's unanchored 1-10 self-rating,
  which was never measured with the PSS, so a PSS-derived value and a training-data value share
  only a direction and a range — not an established equivalence. Training and evaluation are
  unaffected: they still use the dataset's real `Stress Level (1-10)` column.
- **Categorical (2):** Occupation, Family History of Anxiety.
- **Removed entirely, 2026-09-22** (`reports/feature_reduction_3class.md`): Alcohol Consumption
  (drinks/week), Dizziness, Smoking, Recent Major Life Event, Medication — 5 of the original
  bottom-6 of 17 by SHAP importance (`reports/shap_full_ranking_3class.md`; Age was the 6th and
  has since been restored, see below), dropped after validation showed near-zero cost for the
  full group of 6. This was a **product/UX decision** (fewer required fields → less onboarding
  friction, and removes exposure to Phase 19's documented missing-data fragility for those
  specific fields — `reports/robustness_3class.md`), not a performance-driven one — though the
  weak performance case made it an easy call. See "Attempted Improvements" below for the
  companion finding: Caffeine Intake was evaluated for the same removal and *rejected* (real
  signal, ranked 4th by SHAP), with the input method changed instead of the feature being
  dropped.
- **Age restored, 2026-09-22** (`reports/feature_addition_age_3class.md`, `CLAUDE.md`
  "Finalized feature decisions"): unlike the removal above, this was a **clinical/UX decision,
  not a performance-driven one** — Age is a professional norm for a healthcare-adjacent
  platform (age-appropriate reference ranges, legal/consent handling that differs for minors vs.
  adults). The near-zero validation cost measured for this exact 12-feature combination
  (accuracy 0.7739 vs. the 11-feature baseline's 0.7770, a 0.31-point difference; full numbers
  below) is cited as **confirmation the restoration isn't harmful, not as the reason for making
  it** — this is an adopted product decision with a measured cost, not a rejected experiment, and
  is intentionally kept out of "Attempted Improvements" below for that reason.
- **Dropped, and why** (`CLAUDE.md`, "Finalized feature decisions"): Exercises, Sleep_Schedule,
  Nutrition (downstream recommendation outputs, leakage risk); Anxiety Level (1-10) (this is the
  3-class target's own source column, and is a near-duplicate of the 5-class target — 0.86
  correlation with Severity); Gender (no signal — ANOVA F=0.025, p=0.98, eta²≈0.0000045).

### Stress Level's role — reported honestly for both targets

Stress Level (1-10) is the single most important feature for **both** targets, but the degree of
dominance differs sharply (`CLAUDE.md`, "Known finding: Stress Level..."):

| Target | Correlation with target (ordinal) | Accuracy drop if removed (Logistic Regression) | Remaining accuracy without it |
|---|---:|---:|---:|
| 5-class Severity | 0.91 | ~49 points (≈80% → ≈30%) | ≈30% — near the ~27% majority-class baseline |
| 3-class Anxiety Level | 0.65 | 17.6 points (77.8% → 60.1%) | 60.1% — well above the 47.2% majority baseline |

For 5-class Severity, Stress Level is carrying almost the **entire** signal — the model is not
meaningfully using the other 16 features, and the ~80% accuracy figure must not be quoted without
this caveat. For the 3-class target, the remaining 16 features (as measured, Phase 11 — the
17-feature configuration at the time) carry real, independent predictive signal even without
Stress Level — the 3-class model is a meaningfully more broadly-supported model than the 5-class
one. Stress Level is retained for both targets (clinically plausible, realistically collectable),
but this distinction must be documented wherever either model's accuracy is reported. **This
analysis predates both 2026-09-22 feature-set changes (17→11, then 11→12 with Age restored) and
was not recomputed for the current 11-remaining-features-without-Stress-Level configuration** —
see "Known Limitations" #2 below.

---

## Model Selection Rationale

> **Superseded 2026-09-28.** This section records why the Random Forest was chosen originally,
> on the 17-feature data. The limitation it ends with (XGBoost never got the same depth of
> analysis) was closed by running the full suite on both 12-feature models. That comparison
> led to adopting XGBoost; see "Performance — 12-Feature XGBoost".

Both a tuned Random Forest and a tuned XGBoost were evaluated via `RandomizedSearchCV`
(`reports/tuning_results_3class.json`). On the validation set:

| Metric | Random Forest (tuned) | XGBoost (tuned) |
|---|---:|---:|
| Accuracy | 0.7733 | **0.7770** (higher) |
| Balanced accuracy | 0.8056 | **0.8074** (higher) |
| Macro-F1 | **0.8177** (higher) | 0.8175 |
| High recall | 0.8970 | 0.8970 (tied) |

**XGBoost scored marginally higher on accuracy and balanced accuracy; Random Forest scored
marginally higher on macro-F1.** Every metric is within ~0.4 points of the other model.

**Random Forest was selected as the primary model based on:**
1. **Comparable performance** — both tuned models sit within ~0.4 points of each other on every
   reported metric; neither is a clear quantitative winner.
2. **Greater interpretability for a psychologist-facing clinical tool** — Random Forest's
   feature-based splits are more directly inspectable than a gradient-boosted ensemble, which
   matters for a tool whose entire purpose is to support (not replace) a human reviewer's
   judgment.
3. **Continuity with the analysis already built** — Random Forest is the model already used for
   every downstream SHAP, calibration, uncertainty-flagging, and fairness analysis in this card;
   switching models at this point would mean redoing that entire analysis stack.

**This rationale was formalized after model selection, not before it.** Random Forest was carried
forward into Phases 15-18 as an implementation choice, and reasons (1)-(3) above were written up
retroactively rather than serving as the criteria that drove the original choice.

**Limitation:** the selection has **not** been validated against an equivalent depth of analysis
on the alternative — the full SHAP / calibration / uncertainty / fairness suite has not been
re-run on tuned XGBoost. It is possible XGBoost would show different (better or worse)
calibration, fairness, or feature-dependency characteristics; this has not been checked. Treat
the Random Forest selection as a reasonable but not rigorously defended choice between two
close alternatives, not as evidence that Random Forest is definitively the better model for this
task.

---

## Attempted Improvements (Not Adopted)

After the original 17-feature model was selected, four further approaches were tested against
it on validation data, none adopted. A fifth approach — dropping Caffeine Intake — was tested
later, against the already-adopted 11-feature model (see "Features" above for that reduction);
it was also rejected, but a related input-simplification change was adopted separately (see the
closing note below). None of the five touched the test set.

- **Feature engineering** (`HR_Activity_Ratio`, `Sleep_Therapy_Interaction`): essentially no
  change, slightly negative for both Random Forest and XGBoost
  (`reports/feature_engineering_3class.md`).
- **RF + XGBoost soft-voting ensemble**: +0.16 macro-F1 points over the better individual model —
  rejected because the interpretability cost (losing the cheap, exact `TreeExplainer` either
  model has alone) exceeds this marginal gain (`reports/ensemble_3class.md`).
- **Probability calibration** (Platt/isotonic, `CalibratedClassifierCV(cv=5)`): negligible
  classification impact (isotonic: accuracy 0.7733→0.7739, macro-F1 0.8177→0.8180; only
  21/1650 predictions changed), but a real, measured calibration-quality improvement — mean
  Brier score across the 3 classes dropped from 0.1098 (uncalibrated) to 0.1019 (isotonic, the
  better of the two methods tested), and isotonic corrects the documented over-confidence
  pattern for High down to a roughly-calibrated weighted gap (`reports/postprocessing_3class.md`).
  Not adopted as the deployed configuration — see below.
- **Calibration combined with the existing 0.10 uncertainty-flagging threshold, tested
  together**: **net negative.** Isotonic calibration cuts known-boundary-miss coverage from
  9/17 (0.5294) to 3/17 (0.1765) and roughly halves overall flagged volume (346/1650 → 171/1650),
  because the 0.10 threshold was tuned against the *uncalibrated* model's probabilities — the
  same shrinking of low-range P(High) values that improves calibration quality also pushes
  several of the known boundary-ambiguous misses below the flagging cutoff
  (`reports/calibrated_uncertainty_flagging_3class.md`). **This is a documented example of two
  independently-reasonable changes interacting badly when combined** — calibration alone looked
  like a plausible (if minor) improvement, and the flagging threshold alone was already
  validated, but composing them without re-testing would have silently gutted the flagging
  mechanism's coverage of exactly the cases it exists to catch. This is precisely why they were
  tested together rather than assumed to compose safely.
- **Dropping Caffeine Intake** (on top of the already-reduced 11-feature set, to simplify
  onboarding even further): **rejected — real cost.** Caffeine ranks 4th by SHAP importance
  (`reports/shap_full_ranking_3class.md`), unlike the bottom-6 features that were actually
  dropped. Removing it costs a real 1.56-point hit to Medium-class recall (aggregate metrics —
  accuracy, balanced accuracy, macro-F1 — move less, all under 1 point, but the per-class cost
  is real and consistent with the SHAP rank) (`reports/feature_reduction_caffeine_3class.md`).
  **Kept as a model input; the onboarding-simplification goal was served a different way
  instead** — the API collects it as four everyday serving counts and converts them
  server-side (`estimate_caffeine_mg()`), rather than dropping the feature. This is the one
  item on this list where the underlying *input* was still simplified, just not by removing
  the feature.

**Of the five experiments above, four (feature engineering, ensembling, calibration alone,
calibration+threshold combined) changed nothing — the model that resulted from them is
identical to the one before them.** The fifth (caffeine removal) was also rejected as a
feature-removal, but prompted the collection-method change described in "Features" above.
Neither the canonical 17→11 feature reduction nor the subsequent 11→12 restoration of Age was
one of these five "attempted improvement" experiments — both were separate, deliberate decisions
(product/UX for the reduction, clinical/UX for restoring Age;
`reports/feature_reduction_3class.md`, `reports/feature_addition_age_3class.md`, `CLAUDE.md`
"Finalized feature decisions"), not responses to an improvement experiment's evidence. The
17→11 change was confirmed on the test set in `reports/final_test_evaluation_11feature.md`; the
11→12 change deliberately was not (see "Final Test-Set Evaluation" below for why). **The model
actually deployed today (`src/api/main.py`) is the 12-feature model (Age restored), calibration
untouched (uncalibrated), with the original 0.10 flagging threshold** — see "Performance" above
for all three configurations' validation numbers, and "Final Test-Set Evaluation" below for the
17-feature and 11-feature test results only (the 12-feature model has no test-set entry, by
design — see that section's note on why).

---

## Performance — 17-Feature Model (Original, Phase 14 — `reports/full_evaluation_3class.md`)

**Historical reference — this is the original 17-feature model, superseded 2026-09-22.** See
"Performance — 11-Feature Model" below for the current canonical model.

Tuned Random Forest hyperparameters (`reports/tuning_results_3class.json`, `best_params`):
`n_estimators=200, max_depth=10, min_samples_split=10, min_samples_leaf=4, max_features='sqrt',
class_weight='balanced'`, `random_state=42`. Best CV balanced accuracy: 0.8105 (`cv=5, n_iter=20`,
scoring=`balanced_accuracy`, tuned on train only).

Baseline vs. tuned comparison, validation set (`reports/baseline_results_3class.json`,
`reports/tuning_results_3class.json`):

| | Majority dummy | Logistic Regression (baseline) | Random Forest (untuned) | Random Forest (tuned) |
|---|---:|---:|---:|---:|
| Accuracy | 0.4715 | 0.7776 | 0.7703 | 0.7733 |
| Balanced accuracy | 0.3333 | 0.8076 | 0.8024 | 0.8056 |
| Macro-F1 | 0.2136 | 0.8186 | 0.8150 | 0.8177 |
| High recall | 0.0000 | 0.8970 | 0.8970 | 0.8970 |

Full classification report, tuned Random Forest, validation set (n=1650):

```
              precision    recall  f1-score   support

         Low     0.7806    0.7545    0.7673       778
      Medium     0.7223    0.7652    0.7431       707
        High     0.9933    0.8970    0.9427       165

    accuracy                         0.7733      1650
   macro avg     0.8321    0.8056    0.8177      1650
weighted avg     0.7769    0.7733    0.7745      1650
```

Per-class AUROC / AUPRC (one-vs-rest):

| Class | AUROC | AUPRC |
|---|---:|---:|
| Low | 0.8745 | 0.8556 |
| Medium | 0.8517 | 0.7699 |
| High | 0.9850 | 0.9511 |
| **Macro average** | **0.9037** | **0.8589** |

High-class precision is essentially perfect (0.9933) — when this model predicts High, it is
almost never wrong. Low and Medium are the weaker classes on both precision and recall; nearly
all confusion is between Low and Medium, not involving High.

---

## Performance — 11-Feature Model (Superseded 2026-09-22, `reports/feature_reduction_3class.md`)

**Historical reference — this configuration was deployed only briefly on 2026-09-22 before Age
was restored the same day.** See "Performance — 12-Feature Model" below for the current
canonical model actually deployed via `src/api/main.py`. Same tuned Random Forest
hyperparameters as above (`n_estimators=200, max_depth=10, min_samples_split=10,
min_samples_leaf=4, max_features='sqrt', class_weight='balanced'`, `random_state=42`), retrained
from scratch on the 11-feature set (9 numeric + 2 categorical) after dropping the bottom-6
SHAP-ranked features. New `ColumnTransformer` fit on train rows only.

Validation-set comparison, 17-feature baseline vs. 11-feature reduced (`reports/feature_reduction_3class.md`):

| Feature set | Accuracy | Balanced acc. | Macro-F1 | Recall Low | Recall Medium | Recall High |
|---|---:|---:|---:|---:|---:|---:|
| 17-feature (baseline, documented above) | 0.7733 | 0.8056 | 0.8177 | 0.7545 | 0.7652 | 0.8970 |
| **11-feature (reduced)** | **0.7770** | **0.8084** | **0.8204** | 0.7545 | 0.7737 | 0.8970 |
| Delta (11 − 17) | +0.0036 | +0.0028 | +0.0027 | −0.0000 | +0.0085 | +0.0000 |

**On validation alone, no headline metric moved by as much as 1 point** — removing the 6
lowest-SHAP features cost essentially nothing there. Per-class precision and AUROC/AUPRC were
not separately computed for the 11-feature model on validation (`reports/feature_reduction_3class.md`
reports accuracy/balanced-accuracy/macro-F1/per-class recall only); the full picture, including
where this validation-only reading holds up and where it doesn't, is in "Final Test-Set
Evaluation" below.

---

## Performance — 12-Feature XGBoost (Current Canonical, since 2026-09-28 — `reports/model_comparison_12feature.md`)

**This is the model deployed via `src/api/main.py`** (`mindcare_final_model_12feature_xgb.pkl`,
built by `src/models/adopt_xgboost_12feature_model.py`). Same 12 features and preprocessor as the
Random Forest below.

### Primary performance estimate: nested cross-validation (`reports/nested_cv_12feature_xgb.md`)

The whole pipeline was rebuilt from scratch inside each of 5 outer folds, on the 9,350 train +
validation rows: preprocessor, XGBoost tuning (the same search as the real pipeline) and the review
threshold. Each fold was then scored on rows it had never seen. The test set was not used. Figures
are mean ± standard deviation across the 5 outer folds.

| | Nested CV, all ages | Nested CV, ages 18-49 | Validation split, all ages | Validation split, ages 18-49 |
|---|---:|---:|---:|---:|
| Accuracy | **0.7904 ± 0.0094** | 0.7996 ± 0.0100 | 0.7776 | 0.7861 |
| Balanced accuracy | **0.8119 ± 0.0057** | 0.8230 ± 0.0059 | 0.8078 | 0.8152 |
| Macro-F1 | **0.8244 ± 0.0064** | 0.8318 ± 0.0062 | 0.8171 | 0.8226 |
| High recall | **0.8771 ± 0.0111** | 0.9087 ± 0.0122 | 0.8970 | 0.9193 |
| High precision | **0.9759 ± 0.0065** | 0.9837 ± 0.0044 | 0.9673 | 0.9801 |
| Flag catch rate (share of High cases flagged) | **0.9587 ± 0.0153** | 0.9700 ± 0.0159 | 0.9576 | 0.9627 |
| Flag volume (share of all rows flagged) | 0.2448 ± 0.0217 | 0.2783 ± 0.0259 | 0.2485 | 0.2789 |

- **The nested figures are the primary estimate.** The validation columns come from one split of
  1,650 rows, and that split was also used, in part, to choose the model and its threshold.
- **Validation was slightly pessimistic** on the headline metrics: accuracy 1.3 points, balanced
  accuracy 0.4 points and macro-F1 0.7 points *below* the nested means.
- **Validation's High recall of 0.897 sits about 2 points above the nested 0.877.** That is within
  the sampling noise of 165 High cases: the standard error of a recall measured on 165 cases is
  about 0.026, and the gap is about 0.8 of that. (The nested report calls the same gap "1.8 fold
  standard deviations"; that compares it with the spread between the 5 fold means, a different
  yardstick.) The figure to quote for the model's own High predictions is about **0.88**.
- **Ages 18-49**, the population the API serves, score higher on every performance metric above
  (balanced accuracy 0.8230, High recall 0.9087). A larger share of rows is flagged, though:
  27.8% against 24.5%.
- **The deployed 0.025 threshold is supported.** Each outer fold chose its own threshold with the
  same rule (the highest threshold still flagging at least 158/165 of High cases in the inner
  out-of-fold predictions). They came out at **0.0268 ± 0.0026 (range 0.023–0.030)**, which brackets
  0.025. On the unseen outer folds, those thresholds flagged 95.9% of High cases against a 95.8%
  target. Every fold's tuning also picked the deployed settings (300 trees, depth 3, learning
  rate 0.03, unweighted).
- **What this does not cover** is in Known Limitations #13: several decisions were made on this
  same data, outside the nested loop.

**How it was chosen:**
- Both models were re-tuned on the 12 features under one identical procedure: 40 configurations
  each, 5-fold cross-validation on the training data, balanced-accuracy scoring
  (`src/models/tune_models_12feature.py`).
- XGBoost's search included balanced sample weights; unweighted won in cross-validation (0.8089
  vs 0.8077).
- Final settings: 300 trees, max_depth 3, learning_rate 0.03, subsample 0.8, min_child_weight 3.
- The full analysis suite was then run on the current Random Forest, a re-tuned Random Forest and
  XGBoost side by side (`src/evaluation/compare_models_12feature.py`).
- **Validation and training data only.** No candidate has a test-set number.

The comparison below uses the **single validation split** (1,650 rows), the same split used partly to
choose between the models. For XGBoost's primary performance estimate, see the nested
cross-validation above.

| | RF (previous canonical) | XGBoost (current) |
|---|---:|---:|
| Validation accuracy | 0.7739 | 0.7776 |
| Validation balanced accuracy | 0.8062 | 0.8078 |
| Validation macro-F1 | 0.8182 | 0.8171 |
| High recall / High precision | 0.8970 / 0.9933 | 0.8970 / 0.9673 |
| 5-fold CV balanced accuracy (train) | 0.8093 ± 0.0154 | 0.8085 ± 0.0144 |
| Macro AUROC / AUPRC | 0.9044 / 0.8576 | 0.9083 / 0.8658 |
| Calibration error (ECE) Low / Medium / High | 0.061 / 0.060 / 0.033 | 0.016 / 0.020 / 0.007 |
| Balanced accuracy under 1× std noise | 0.5558 | 0.6151 |
| Balanced accuracy with Caffeine replaced by its mean | 0.5232 | 0.7879 |
| Single prediction / model size | 37 ms / 9.2 MB | 1.1 ms / 1.0 MB |

**Why XGBoost:**
- **Performance is a tie.** The cross-validation gap (0.0008) is about 20 times smaller than the
  variation between folds. Both models predict High for the same 148 of 165 High cases and miss
  the same 17.
- **Calibration:** XGBoost's probabilities are 3–5 times better calibrated.
- **Robustness:** it holds up better under input noise.
- **No caffeine shortcut.** The Random Forest learned "High needs high caffeine". With a truly
  High patient's caffeine at or below 200 mg a day, it predicted High for 0 of 165, against
  127–129 for XGBoost. That matters because the API only *estimates* caffeine from serving counts.
- **Age:** it is barely affected by the dataset's age-50 artifact (mean P(High) 0.885 → 0.863
  from age 49 to 55, against 0.903 → 0.628 for the Random Forest).
- **Practical:** about 30 times faster and 9 times smaller.

**Trade-offs accepted:**
- **High precision is lower** (0.967 vs 0.993): XGBoost labels 5 true-Medium rows High,
  against 1 for the Random Forest.
- **More sensitive to a missing Sleep Hours value** (0.715 vs 0.786).
- **Needed a lower review threshold** (see "Uncertainty / Abstention Mechanism").

The re-tuned Random Forest (500 trees, depth 30) was also compared. It was no better than the
previous one, and five times larger and slower, so it was not adopted.

**SHAP:** Stress Level is still #1, and more dominant (44.3% of mean |SHAP|, against 37.6% for
the Random Forest). It's followed by Sleep Hours (16.2%), Therapy Sessions (14.7%) and Caffeine
(10.2%).

**Fairness:** the gaps across occupation, age band and gender are similar to the Random Forest's.
Balanced accuracy varies by 0.120 across occupations (0.108 for the Random Forest) and by 0.029
across genders (0.036).

---

## Performance — 12-Feature Random Forest (Superseded 2026-09-28, `reports/feature_addition_age_3class.md`)

**This model was deployed via `src/api/main.py` from 2026-09-22 to 2026-09-28**, when XGBoost
replaced it (above). The file `mindcare_final_model_12feature.pkl` is kept for history. Same tuned
Random Forest hyperparameters as above, retrained from scratch on the 11-feature set plus Age
restored (10 numeric + 2 categorical — see "Features" above). New `ColumnTransformer` fit on
train rows only.

**Validation only — this configuration has no test-set evaluation, by design (see "Final
Test-Set Evaluation" below).** Restoring Age was a clinical/UX decision, not a
performance-driven one, so the numbers below are reported to confirm the restoration isn't
harmful — not as justification for making it, and not as grounds for a third test-set use.

Validation-set comparison, 11-feature baseline vs. 12-feature (Age restored)
(`reports/feature_addition_age_3class.md`):

| Feature set | Accuracy | Balanced acc. | Macro-F1 | Recall Low | Recall Medium | Recall High |
|---|---:|---:|---:|---:|---:|---:|
| 11-feature (baseline, documented above) | 0.7770 | 0.8084 | 0.8204 | 0.7545 | 0.7737 | 0.8970 |
| **12-feature (with Age)** | **0.7739** | **0.8062** | **0.8182** | 0.7506 | 0.7709 | 0.8970 |
| Delta (12 − 11) | −0.0031 | −0.0022 | −0.0022 | −0.0039 | −0.0028 | −0.0000 |

**No headline or per-class metric moved by as much as 1 point** (largest movement: recall Low,
−0.0039, 0.39 points). This exact 12-feature combination (11-feature set + Age) had never been
tested before this run — the near-zero result is a measured finding, not an assumption carried
over from Age's earlier bottom-6 SHAP ranking. Per-class precision and AUROC/AUPRC were not
separately computed for this configuration (`reports/feature_addition_age_3class.md` reports
accuracy/balanced-accuracy/macro-F1/per-class recall only, matching the 11-feature report's
scope).

---

## Final Test-Set Evaluation — 17- and 11-Feature Models (Two Disclosed Uses)

The test set has now been used **twice**, both disclosed and justified in `CLAUDE.md` ("TEST SET
USED" entries), and is **fully spent** as of 2026-09-22 — no further evaluation is permitted for
the 17-feature or 11-feature model configurations below.

**The current canonical 12-feature model (Age restored) deliberately has no entry here and none
is planned.** Restoring Age was a clinical/UX decision, not a performance claim, so it was not
treated as justifying a third test-set use — see `reports/feature_addition_age_3class.md` and
"Performance — 12-Feature Model" above for its validation-only evidence. Do not read the
"fully spent" statement above as implying a gap for the 12-feature model; the absence of a
test-set number for it is intentional, not outstanding work.

### First use, 2026-09-15 — 17-feature model (`reports/final_test_evaluation.md`)

Performed exactly once against the saved 17-feature final model exactly as-is — no retraining,
tuning, or model-selection change was made in response to these results.

| Metric | Validation | Test | Gap (test − val) |
|---|---:|---:|---:|
| Accuracy | 0.7733 | **0.7915** | +0.0182 |
| Balanced accuracy | 0.8056 | **0.8193** | +0.0137 |
| Macro-F1 | 0.8177 | **0.8311** | +0.0134 |
| Macro AUROC | 0.9037 | 0.9083 | +0.0046 |
| Macro AUPRC | 0.8589 | 0.8691 | +0.0102 |

Per-class AUROC/AUPRC, validation vs. test:

| Class | AUROC (val) | AUROC (test) | Gap | AUPRC (val) | AUPRC (test) | Gap |
|---|---:|---:|---:|---:|---:|---:|
| Low | 0.8745 | 0.8798 | +0.0053 | 0.8556 | 0.8587 | +0.0031 |
| Medium | 0.8517 | 0.8607 | +0.0090 | 0.7699 | 0.7920 | +0.0221 |
| High | 0.9850 | 0.9843 | −0.0007 | 0.9511 | 0.9566 | +0.0055 |

Full classification report — **17-feature test** (n=1650):

```
              precision    recall  f1-score   support

         Low     0.7987    0.7772    0.7878       781
      Medium     0.7422    0.7814    0.7613       700
        High     0.9935    0.8994    0.9441       169

    accuracy                         0.7915      1650
   macro avg     0.8448    0.8193    0.8311      1650
weighted avg     0.7947    0.7915    0.7926      1650
```

Confusion matrix — **17-feature test** (rows = true, columns = predicted, order Low/Medium/High):

```
[[607 174   0]
 [152 547   1]
 [  1  16 152]]
```

No metric gapped by ≥0.03 between validation and test — a clean result, no evidence of
overfitting to the validation split across the tuning, calibration, SHAP, fairness, and
robustness work in Phases 11-19.

### Second and final use, 2026-09-22 — 11-feature model (`reports/final_test_evaluation_11feature.md`)

Justified because this evaluates a genuinely new model configuration (11 features replacing the
original 17), not iterative re-evaluation of the same model. Performed exactly once against
`mindcare_final_model_11feature.pkl` exactly as-is.

| Metric | Validation | Test | Gap (test − val) |
|---|---:|---:|---:|
| Accuracy | 0.7770 | **0.7891** | +0.0121 |
| Balanced accuracy | 0.8084 | **0.8177** | +0.0093 |
| Macro-F1 | 0.8204 | **0.8285** | +0.0081 |
| Macro AUROC | — | 0.9077 | — |
| Macro AUPRC | — | 0.8633 | — |

Per-class AUROC/AUPRC — **11-feature test**:

| Class | AUROC | AUPRC |
|---|---:|---:|
| Low | 0.8789 | 0.8558 |
| Medium | 0.8587 | 0.7798 |
| High | 0.9856 | 0.9544 |

Full classification report — **11-feature test** (n=1650):

```
              precision    recall  f1-score   support

         Low     0.8013    0.7695    0.7851       781
      Medium     0.7359    0.7843    0.7593       700
        High     0.9870    0.8994    0.9412       169

    accuracy                         0.7891      1650
   macro avg     0.8414    0.8177    0.8285      1650
weighted avg     0.7926    0.7891    0.7902      1650
```

Confusion matrix — **11-feature test** (rows = true, columns = predicted, order Low/Medium/High):

```
[[601 180   0]
 [149 549   2]
 [  0  17 152]]
```

No metric gapped by ≥0.03 between the 11-feature model's own validation and test performance —
no evidence of overfitting to the validation split during feature selection.

### The honest finding: validation and test disagree on direction

**On validation, the 11-feature model looked marginally *better* than the 17-feature model**
(+0.0036 accuracy, +0.0028 balanced accuracy, +0.0027 macro-F1 — `reports/feature_reduction_3class.md`).
**On the held-out test set, that reverses: the 11-feature model is very slightly, but
consistently, worse than the 17-feature model:**

| Metric | 17-feature (test) | 11-feature (test) | Delta (11 − 17) |
|---|---:|---:|---:|
| Accuracy | 0.7915 | 0.7891 | −0.0024 |
| Balanced accuracy | 0.8193 | 0.8177 | −0.0016 |
| Macro-F1 | 0.8311 | 0.8285 | −0.0026 |
| Macro AUROC | 0.9083 | 0.9077 | −0.0006 |
| Macro AUPRC | 0.8691 | 0.8633 | −0.0058 |

Of the 20 metrics compared (headline + per-class precision/recall/F1/AUROC/AUPRC), 19 are within
±0.01 (effectively noise at this sample size, n=1650), but **every single headline metric moved
in the negative direction**, and one — Medium-class AUPRC (−0.0122) — crosses the 0.01 threshold.
A small, one-directional effect, not noise scattered in both directions, and not the
wash-or-improvement picture the validation-only result suggested.

**Net conclusion: no meaningful cost either way.** The core decision to drop those 6 features
remains reasonable — even by this stricter test-set read, the cost is tiny (≤0.003 on every
headline metric, ≤0.012 on any single per-class metric) — but the accurate claim is "no
*meaningful* cost," not "a slight improvement." The validation-only finding did not fully
replicate on test; this is exactly why validation-only results must eventually be checked
against held-out test data (`reports/final_test_evaluation_11feature.md`, "Honest Verdict").

These test-set figures are kept distinct from validation-set figures throughout this card, and
the 17-feature and 11-feature test results are kept distinct from each other — none are
conflated.

---

## Calibration Status (Phase 15 — `reports/calibration_3class.md`, `reports/calibration_3class_full.md`)

10-bin reliability diagrams and Brier scores were computed for all 3 classes (one-vs-rest, tuned
Random Forest, validation set):

| Class | Brier score | Count-weighted gap (predicted − actual) | Verdict |
|---|---:|---:|---|
| High | 0.013128 | +0.0333 | Over-confident overall, but not uniformly — see nuance below |
| Low | 0.151839 | −0.0238 | Roughly calibrated on weighted average, but not uniformly |
| Medium | 0.164572 | −0.0095 | Roughly calibrated on weighted average, but not uniformly |

**The weighted-average verdicts understate real per-bin miscalibration:**

- **High:** over-confident below predicted P≈0.3 (90.7% of the validation set falls in this range —
  1497 of 1650 rows across the [0.0,0.1), [0.1,0.2), [0.2,0.3) bins;
  e.g. mean predicted 3.4% vs actual 0.6% in the [0.0,0.1) bin), but well-calibrated to slightly
  under-confident above P≈0.8 (mean predicted 98.5% vs actual 99.3% in the [0.9,1.0) bin, n=139).
- **Low:** over-confident at low-mid predicted probabilities (e.g. predicts 25.1% at [0.2,0.3),
  actual 14.1%), but under-confident at high probabilities (predicts 75.0% at [0.7,0.8), actual
  89.6%; predicts 82.5% at [0.8,0.9), actual 96.1%).
- **Medium:** over-confident at low probabilities, but notably under-confident in the single
  most heavily-populated bin — [0.6,0.7) holds 436 of 1650 validation rows (26%), predicts 65.0%
  Medium, actual rate is 78.7% (a 13.7-point gap affecting over a quarter of the validation set).

**Cross-class pattern:** High is over-confident at low probabilities; Low and Medium are
under-confident at high probabilities. The model's raw probability outputs compress less than
they should toward the extremes for Low/Medium, while over-extending slightly toward zero for
High.

**Recommendation (tested since this section was first written — see "Attempted Improvements"
above):** Platt scaling and isotonic regression per class were both tried. Isotonic measurably
improved calibration quality (mean Brier 0.1098 → 0.1019) with negligible effect on
classification metrics, exactly as predicted here — but it was **not adopted**, because it
silently breaks the uncertainty-flagging mechanism below (coverage of known boundary-ambiguous
misses drops from 9/17 to 3/17 when the two are combined without re-tuning the flagging
threshold). The deployed model remains uncalibrated.

Not yet done for the 5-class Severity target (`CLAUDE.md`, Pipeline Status).

---

## Uncertainty / Abstention Mechanism (Phase 16 — `src/models/uncertainty_flagging.py`, `reports/uncertainty_flagging.md`)

> **Current rule (since 2026-09-28): P(High) ≥ 0.025 on the XGBoost model.** The 0.10 rule
> described below was set for the Random Forest, as the ~10% base rate of High cases. XGBoost's
> better-calibrated probabilities put most borderline High cases below 0.10. At 0.10 it would
> catch 152 of 165 High cases and 4 of the 17 hardest misses (true High predicted Medium).
> At **0.025** it matches the Random Forest's validation coverage exactly: **158 of 165 High
> cases and 10 of 17 hard misses**. That costs 410 flagged rows instead of 363 (about 13% more
> review work), with a false-flag rate of 0.615. This is validation-only evidence, like the
> rest of this section. The analysis below is kept as the Random Forest history.

**Production rule:** flag a validation row **"borderline — recommend review"** if
**P(High) ≥ 0.10**, unconditional on the predicted class.

**Threshold reasoning:** 0.10 is the ~10% marginal base rate of the High class in this dataset —
not an arbitrary cutoff. It flags any row where the model assigns High at least its unconditional
prior likelihood. It is intentionally **not** gated on High being the model's top prediction: the
flag does not decide who gets reviewed — every prediction is already reviewed by a psychologist
per this project's approval workflow — it exists to **reprioritize** review attention toward rows
the model considers plausibly High-risk even when it predicted Medium or Low. Gatekeeping access
to review is explicitly out of scope.

A margin-based trigger (flag when the top-2 predicted-class probabilities are close) was
evaluated via a threshold sweep (`reports/threshold_sweep_high.md`) and **dropped**: it caught 0
of 17 known True-High/Predicted-Medium validation misses while driving most of the flagged
volume, because on those rows P(Medium) dominates so strongly that the top-1/top-2 gap looks
decisive even though the top prediction is wrong.

**Results at the production threshold (validation set, n=1650):**

- Overall flagged: **346 / 1650 = 20.97%**
- Coverage of the 17 known True-High/Predicted-Medium misses: **9 / 17 = 52.94%**
- True-High rows overall flagged (context): 157 / 165 = 95.15% (most correctly-classified High
  predictions also cross this threshold, since P(High) is naturally high when High is the top
  prediction — this is intended, not a defect)
- False-flag rate (flagged rows already correctly classified): **321 / 346 = 92.77%** — high
  mainly because the rule is unconditional; correctly-classified True-High rows are expected to
  be flagged too, since they should also receive priority attention.

**This threshold is specifically tuned to the uncalibrated model's probability distribution** —
see "Attempted Improvements" above for what happens (coverage of known misses drops from 9/17 to
3/17) if isotonic calibration is ever adopted without re-tuning this threshold to match.

Not yet done for the 5-class Severity target.

---

## SHAP Feature Importance (Phase 17 — `reports/shap_summary_3class.md`)

Computed on a 500-row sample of `X_val`, tuned Random Forest, mean absolute SHAP value across all
3 classes:

| Rank | Feature | Mean \|SHAP\| |
|---:|---|---:|
| 1 | Stress Level (1-10) | 0.13161728 |
| 2 | Therapy Sessions (per month) | 0.05513000 |
| 3 | Sleep Hours | 0.05060564 |
| 4 | Caffeine Intake (mg/day) | 0.03547575 |
| 5 | Diet Quality (1-10) | 0.02443511 |
| 6 | Physical Activity (hrs/week) | 0.01726092 |
| 7 | Heart Rate (bpm) | 0.01560360 |
| 8 | Breathing Rate (breaths/min) | 0.01046683 |
| 9 | Sweating Level (1-5) | 0.01027403 |
| 10 | Age | 0.00944933 |

**Stress Level still ranks #1 (1/34 transformed features)**, but at a reduced margin over 2nd
place (Therapy Sessions): 2.39x, vs. the much larger dominance implied for the 5-class target by
the ablation numbers above. This is consistent with the 0.65-vs-0.91 correlation finding: still
the top feature, but not singularly dominant the way it is for 5-class Severity.

Not yet done for the 5-class Severity target.

---

## Fairness Findings (Phase 18 — `reports/fairness_report_3class.md`)

Occupation-subgroup precision/recall evaluated on the validation set, joined via
`val_original_idx` (saved directly by `rebuild_preprocessor.py`; no index reconstruction needed).

Overall validation recall: Low 0.7545, Medium 0.7652, **High 0.8970**.

**Flag rule:** subgroup recall on the High class at least 0.10 below overall High recall.

| Occupation | Support (High) | Subgroup recall | Overall recall | Gap | Low confidence (<15 rows)? |
|---|---:|---:|---:|---:|---|
| Scientist | 16 | 0.7500 | 0.8970 | 0.1470 | No |
| Engineer | 14 | 0.7857 | 0.8970 | 0.1113 | **Yes — n<15** |

High-class precision is 1.00 in 12 of 13 occupations — only Doctor is lower, at 0.9167 — when
the model predicts High, it is almost never wrong, regardless of occupation.

### Scientist flag: investigated and found not to replicate

The Scientist gap above (and the analogous flag in the 5-class fairness report,
`reports/fairness_report.md`) was investigated directly by comparing Scientist vs. non-Scientist
feature distributions (Stress Level, Sleep Hours, Therapy Sessions — the top SHAP features) among
True-High(/Severe) validation rows (`CLAUDE.md`, "Known finding: Scientist occupation fairness
flag..."):

- On the validation set itself, none of these feature differences are statistically significant
  (Stress Level Welch t-test p=0.36 for 3-class, n=16; p=0.16 for 5-class, n=39) — sample sizes
  this small make a 10-15 point recall swing from one or two misclassified rows expected noise,
  not signal.
- The dataset shows **no real Occupation↔Stress Level relationship at all**: ANOVA of Stress
  Level across all 13 occupations, full dataset, gives **F=0.47, p=0.93**.

**Conclusion: the Scientist recall gap should be treated as likely validation-set sampling
noise, not a validated fairness issue**, pending a larger sample (e.g. cross-validated fairness
evaluation) before treating it as something to correct for. It should not be cited as evidence of
occupational bias without this caveat. The Engineer gap is additionally marked low-confidence
(n=14 High-class validation rows for that occupation) and should not be read as a finding at all
without more data.

Not yet done for the 5-class Severity target beyond what's already in `reports/fairness_report.md`.

---

## Known Limitations

1. **Synthetic data.** The training data is very likely synthetic (near-uniform demographics,
   zero missing values/duplicates, templated recommendation text). No performance figure in this
   card should be read as clinically validated.
2. **Stress Level dependency.** Even for the 3-class target (less dependent than 5-class), the
   model's total Logistic Regression accuracy gain over the majority baseline is ~30.6 points
   (77.8% − 47.2%), and 17.6 of those points (more than half) come from Stress Level alone
   (removing it still leaves 60.1%, vs. 47.2% majority baseline). The model is not drawing on
   broad, independent multi-feature signal to the degree a clinical deployment would ideally
   require, even though this is a materially smaller dependency than the 5-class target's. **This
   analysis (Phase 11) predates both 2026-09-22 feature-set changes (17→11, then 11→12 with Age
   restored) and was not recomputed for either** — Stress Level was not removed or affected by
   either change, so the dependency is expected to persist, but the exact percentages above are
   unverified for the current canonical (12-feature) model.
3. **Imbalanced target, small High-class subgroup samples.** High is ~10% of the data; per-
   occupation High-class validation samples are as small as 9-18 rows, making subgroup fairness
   metrics (and the two flags above) inherently noisy at this sample size.
4. **Miscalibrated raw probabilities, and calibration is tested but not deployed.** Predicted
   probabilities are not well-calibrated across the full range for any class (see Calibration
   Status) — raw `predict_proba` output should not be presented to a psychologist as a
   calibrated confidence figure. Post-hoc calibration (isotonic) was tested and does improve
   calibration quality, but was not adopted because it interacts badly with the existing
   uncertainty-flagging threshold (see "Attempted Improvements" above) — a fix requires
   re-tuning that threshold, not just applying calibration.
5. **Uncertainty flag has a high false-flag rate by design (92.77%).** This is an accepted
   tradeoff given the flag's reprioritization-not-gatekeeping purpose, but it means roughly 1 in
   5 validation rows (20.97%) get flagged, and the large majority of that review volume confirms
   correct predictions rather than catching errors.
6. **Robustness is measurably weak on the model's two most important features.** Per Phase 19
   (`reports/robustness_3class.md`): losing Stress Level alone (simulated via train-mean
   imputation) collapses balanced accuracy from 0.806 to 0.429; losing Therapy Sessions alone
   drops it to 0.559. Modest Gaussian noise (0.25× each numeric feature's train std, applied to
   all numeric features at once) already costs 3.2 balanced-accuracy points; at 1× std,
   performance collapses to 0.556. The same two features driving most of the model's accuracy
   (see limitation 2) are also its two biggest single points of failure.
7. **Input validation exists but is a recent addition.** `src/inference/input_validation.py`
   now rejects physically impossible values (e.g. Stress Level=250, Heart Rate=9000, Age=-5)
   before they reach the model — added specifically because Phase 19 found the pipeline
   previously accepted such values silently and produced a confident-looking prediction anyway.
   Bounds now cover the 12 currently-collected features; the 5 still-removed features (Alcohol
   Consumption, Dizziness, Smoking, Recent Major Life Event, Medication) have no validation
   bounds because they are no longer model inputs. Only wired into
   `src/inference/predict_single.py` and `src/api/main.py`; any other future entry point to this
   model must independently call it.
8. **Test set has been evaluated twice, and is now fully spent for the 3-class target — for the
   17-feature and 11-feature configurations only.** First (2026-09-15,
   `reports/final_test_evaluation.md`): the original 17-feature model, test matched validation
   closely (no metric gapped by ≥0.03). Second (2026-09-22,
   `reports/final_test_evaluation_11feature.md`): the 11-feature model (since superseded),
   evaluated because it was a genuinely new configuration, not a re-check of the same model. See
   "Final Test-Set Evaluation" above for both, including the honest finding that the 11-feature
   model's validation-set improvement over the 17-feature model did not replicate on test (test
   showed a tiny, consistent regression instead — net conclusion: no meaningful cost either way).
   **No further test-set evaluation is permitted for the 17-feature or 11-feature
   configurations** — both uses were one-way doors, each disclosed and justified once. See
   limitation 11 below for the current 12-feature model's deliberately different evidentiary
   status.
9. **Not yet done for the 5-class Severity target:** Phase 15 (calibration), Phase 16
   (uncertainty/abstention). (Phase 12 and Phase 19 are now done for the 3-class target — see
   limitation 6 above and `reports/advanced_models_3class.md`.)
10. **This is a prototype/research model** (`CLAUDE.md` Engineering Rule 7) — it must never be
    represented as having clinical diagnostic validity, and its output must never bypass
    psychologist review per the project's critical workflow constraint.
11. **The current canonical model (12-feature XGBoost) has validation-only evidence, and
    always will unless a future decision explicitly justifies a third test-set use.** This is
    true of both 12-feature models. Unlike the 17-feature and 11-feature configurations above, no
    test-set number exists for either, by design — `src/models/adopt_12feature_model.py` never loads, transforms, or
    references `X_test`/`y_test`/`test_original_idx` (`reports/feature_addition_age_3class.md`,
    `CLAUDE.md` "FEATURE SET CHANGE — 2026-09-22 (THIRD change)"). This is not an oversight to
    close later: restoring Age was a clinical/UX decision, not a performance claim, so a
    validation-only check (confirming it isn't harmful) was judged sufficient and a third
    one-way-door test-set use was not. Switching from Random Forest to XGBoost was likewise
    decided on validation and cross-validation evidence only. Both 12-feature models have the
    full analysis suite on validation data: calibration, the review flag, SHAP, fairness and
    robustness (`reports/model_comparison_12feature.md`). The Random Forest also has
    `reports/full_evaluation_12feature.md`.
12. **Supported age range is 18–49 (decided 2026-09-27).** The API rejects any other age. Under
    18 is rejected as not eligible (minors can't register), and 50+ is rejected with a
    psychologist referral; see "Intended Use".
    Evidence behind the upper bound, all on validation data:
    - The dataset's High rate falls from 12–15% below age 50 to about 1% from 50 on.
    - Random Forest (the model at the time): for identical people, mean P(High) dropped from
      0.90 at 49 to 0.63 at 55. The 53–64 band had only 3 true-High cases, and it missed all 3.
      Moving under-50 validation rows to age 55 turned off its review flag for 17 of 282.
    - XGBoost (current) barely shows the effect (0.885 → 0.863). The limit stands anyway,
      because the data gap does: with almost no High cases at 50+, nothing shows either model
      can recognise High anxiety at those ages.

    This is a data-coverage limit, not a clinical judgement about older adults.
13. **Nested cross-validation doesn't cover the decisions made outside it**
    (`reports/nested_cv_12feature_xgb.md`). It makes the preprocessing, tuning and threshold steps
    honest, because they are redone inside every fold. But these were all decided on the same
    train + validation data, before or outside the nested loop:
    - the 17 → 11 → 12 feature reduction;
    - choosing XGBoost over Random Forest;
    - the 158/165 flag-coverage target (copied from the Random Forest's validation result);
    - the Low/Medium/High label boundaries;
    - the 18–49 age limit.

    So the nested figures estimate how **re-running this pipeline** performs, not how the whole
    chain of decisions that produced it would perform on new data. They can still be optimistic
    about that chain. **No test-set number exists for the current model** (the 3-class test set was
    used twice, on earlier models, and is treated as spent), so only fresh data can check it.

---

## Source Traceability

All figures in this card are pulled directly from, and can be re-verified against:
`CLAUDE.md`; `reports/baseline_results_3class.json`; `reports/tuning_results_3class.json`;
`reports/full_evaluation_3class.md`; `reports/calibration_3class.md`;
`reports/calibration_3class_full.md`; `reports/uncertainty_flagging.md`;
`reports/threshold_sweep_high.md`; `reports/shap_summary_3class.md`;
`reports/shap_full_ranking_3class.md`; `reports/fairness_report_3class.md`;
`reports/advanced_models_3class.md`; `reports/robustness_3class.md`;
`reports/feature_engineering_3class.md`; `reports/ensemble_3class.md`;
`reports/postprocessing_3class.md`; `reports/calibrated_uncertainty_flagging_3class.md`;
`reports/final_test_evaluation.md`; `reports/feature_reduction_3class.md`;
`reports/feature_reduction_caffeine_3class.md`; `reports/final_test_evaluation_11feature.md`;
`reports/feature_addition_age_3class.md`.
Seed=42 throughout. No number here was invented, estimated, or rounded beyond what these source
files already report.
