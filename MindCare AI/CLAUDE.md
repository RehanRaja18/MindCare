---
# MindCare AI — Project Context for Claude Code

## What this is
The AI/ML component of MindCare, an FYP mental-health platform connecting patients and
psychologists. **Location:** the `MindCare AI/` folder of the MindCare monorepo (which also holds
`MindCare Backend/`, `MindCare App/` and `MindCare Web/`). It replaced a placeholder scaffold there
on the `ai/anxiety-model-into-mindcare-ai` branch, via `git subtree add`, keeping this project's
history. Paths in this file are relative to `MindCare AI/`, except `render.yaml` and
`.github/workflows/keep-alive.yml`, which must be at the repository root. This repo trains a model to predict anxiety risk from patient
lifestyle/physiological data. **As of 2026-09-14, the primary target is a 3-class
Low/Medium/High Anxiety Level bucket** (see "Target change" section below); the original
5-class Anxiety Severity target is kept as a secondary/reference target for comparison.

**Critical workflow constraint:** this model's output NEVER goes directly to patients.
AI prediction → psychologist reviews → psychologist approves/modifies → patient sees it.
Do not build or suggest anything that bypasses psychologist review.

## Reference Documents
- `docs/master_project_instructions.md` — the full phase-by-phase methodology this project
  follows (Phases 0-35). From now on, if a phase number is referenced that you can't find
  details for elsewhere, check this file before saying it doesn't exist.
- `docs/setup.md` — model artifacts (`data/processed/*.pkl`/`*.npz`) are not in git; this lists
  the exact scripts to regenerate them, in order. `mindcare_processed_splits.npz` is the one
  tracked exception (no script can recreate it from scratch) — never delete it.
- `reports/recommendation_mapping_investigation.md` — evidence base for `POST /patient-summary` (2026-09-30), which returns the prediction plus an **estimated** Severity tier (3-class prediction + PSS Stress Level → most common tier; 88.0% ceiling with the true label per this report, 78.3% measured with the current model's own predictions) and the matching dataset recommendation bundle, always under a fixed clinician-review caveat; `/predict` returns none of this.

## Dataset
data/raw/mindcare_dataset_final.csv — ~11,000 rows, 23 columns.
**This is very likely synthetic data**, not real patient data (near-uniform demographics,
zero missing values/duplicates, templated recommendation text). Treat all performance
claims as prototype-level, not clinically validated. Document this caveat in any report
or model card generated from this repo.

## Target change (2026-09-14): 3-class Anxiety Level is now primary
The primary target changed from 5-class Severity to a **3-class Low/Medium/High**
target, derived directly from the raw `Anxiety Level (1-10)` column (not from Severity):
- **Low:** Anxiety Level 1-3
- **Medium:** Anxiety Level 4-6
- **High:** Anxiety Level 7-10

Reason: per earlier EDA, Severity's 5 class boundaries don't align cleanly with this
binning, so the 3-class target is built independently from the raw scale rather than by
re-bucketing Severity.

**The feature set was unchanged at the time of this target switch (2026-09-14).** All 17
features (11 numeric + 6 categorical, listed below) — including Stress Level — remained fully
included in every model for the 3-class target, identical to the 5-class setup; this change
only swapped the target labels. **This is no longer current** — see "Finalized feature
decisions" below: as of 2026-09-22 the 3-class model uses 12 features (having briefly used 11,
now superseded), not 17. The 5-class model described in this section's original wording is
unaffected and still uses all 17.

No re-splitting or re-preprocessing was done: the 3-class target reuses the exact same
train/val/test row membership as the 5-class split (7700/1650/1650), via the
`train_original_idx`/`val_original_idx`/`test_original_idx` arrays.

**New artifacts (parallel to the existing 5-class ones, neither overwrites the other):**
- `data/processed/mindcare_processed_splits_3class.npz` — same `X_train`/`X_val`/`X_test`
  and index arrays as `mindcare_processed_splits.npz`; only `y_train`/`y_val`/`y_test`
  differ (3-class labels instead of 5-class).
- `data/processed/mindcare_label_encoder_3class.pkl` — classes ordered `Low`/`Medium`/`High`
  (indices 0/1/2).
- `src/build_3class_target.py` — builds the above from the raw CSV + existing split indices.
- `src/models/train_baselines_3class.py` — baseline models for the 3-class target
  (`reports/baseline_results_3class.json`).

The 3-class target is imbalanced: High is only ~10% of every split (Low ~47%, Medium ~42%,
High ~10%), so accuracy alone is even more misleading here than for 5-class Severity —
report balanced accuracy, macro-F1, and per-class recall (especially High) for this target.

## Finalized feature decisions (do not change without discussion)
- **Target:** Severity (5-class, secondary/reference) or the 3-class Anxiety Level
  bucket (primary, see "Target change" above).
- **As of 2026-09-22, the feature set DIFFERS between the two targets** — it is no longer
  identical. The 5-class Severity model still uses the original 17 features. The 3-class
  Anxiety Level model (primary, canonical, deployed via `src/api/main.py`; XGBoost since
  2026-09-28, see below) went through two
  changes the same day: first reduced from 17 to 11 features, then Age was restored, bringing
  it to **12**. The 11-feature configuration is superseded and kept only for history (see
  Pipeline Status below); it is not the current canonical model. **On 2026-10-02 Sweating Level
  was removed, giving the current canonical "11-feature v2" set** (with Age, without Sweating
  Level) — a different set from that superseded 11-feature one.

### 3-class Anxiety Level (canonical, 11 features — "11-feature v2", since 2026-10-02)
- **Numeric (9):** Stress Level (1-10) [now collected via the API as the 4 PSS-4
  questionnaire items and converted server-side — see "Stress Level input method changed"
  below, not entered as a raw 1-10 rating], Therapy Sessions (per month), Sleep Hours, Caffeine
  Intake (mg/day) [now collected via the API as 4 serving-count fields and estimated
  server-side — see below, not entered as raw mg], Diet Quality (1-10), Physical Activity
  (hrs/week), Heart Rate (bpm), Breathing Rate (breaths/min), Age
  [restored — see "Age restored" below]. Sweating Level (1-5) was removed on 2026-10-02 — see
  "Sweating Level removed" below.
- **Categorical (2):** Occupation, Family History of Anxiety
- **Removed entirely (not just deprioritized), 2026-09-22:** Alcohol Consumption
  (drinks/week), Dizziness, Smoking, Recent Major Life Event, Medication — 5 of the original
  bottom-6 of 17 by SHAP importance (`reports/shap_full_ranking_3class.md`; Age was the 6th
  and has since been restored, see below), dropped after `reports/feature_reduction_3class.md`
  found near-zero validation cost for the full group of 6 (later confirmed on the second,
  disclosed test-set use — `reports/final_test_evaluation_11feature.md` — with only a tiny,
  honestly-reported regression; see Pipeline Status below).
  - **Decision log — why removed:** this was a **product/UX decision, not a
    performance-driven one**. Fewer required fields reduces onboarding friction for a
    patient-facing form, and removes exposure to Phase 19's documented missing-data
    fragility risk for those specific fields (`reports/robustness_3class.md`). The
    performance case for keeping them was already weak (bottom-6 SHAP rank, near-zero
    validation cost), so once a product reason to drop them existed, there was no strong
    performance reason not to.
  - **Caffeine Intake (mg/day) was separately evaluated for the same treatment and
    REJECTED.** It ranks **4th** by SHAP importance — real signal, not a bottom-of-the-list
    feature — and `reports/feature_reduction_caffeine_3class.md` found dropping it costs a
    real 1.56-point hit to Medium-class recall (aggregate metrics move less, under 1 point,
    but the per-class cost is real and consistent with its SHAP rank). **Kept as a model
    input; only the collection method changed.** The API now asks for four everyday serving
    counts (cups of coffee/tea, energy drinks, cans of soda) and converts them server-side to
    the mg/day figure the model needs (`src/api/main.py`, `estimate_caffeine_mg()`), rather
    than dropping the feature outright.
- **Age restored, 2026-09-22 (subsequent to the removal above):** Age moves from "removed" back
  to a model input — 10 numeric + 2 categorical = **12 features**, the canonical set until
  2026-10-02 (when Sweating Level was removed, giving the current 11-feature v2 set).
  - **Decision log — why restored:** this was a **clinical/UX decision, not a
    performance-driven one** — the mirror image of the removal decision above. Age is a
    professional norm for a healthcare-adjacent platform (age-appropriate reference ranges for
    physiological features like Heart Rate and Breathing Rate, and legal/consent handling
    differs for minors vs. adults), independent of what the model's validation metrics show.
    `reports/feature_addition_age_3class.md`'s near-zero validation cost (largest movement
    0.39 points, recall_low: 0.7545 → 0.7506) is cited here as **confirmation the restoration
    isn't harmful, not as the reason for making it** — the decision would have been made
    regardless of that result, and the report says so explicitly.
  - **This exact 12-feature combination (11-feature set + Age) had never been tested before
    that run** — the earlier near-zero-cost finding for dropping the full bottom-6 group
    (`reports/feature_reduction_3class.md`) does not, by itself, establish the cost of adding
    back just one of those six in isolation. It was measured for real rather than assumed.
  - **Validation-only, by design — no test-set evaluation for this configuration.** The
    3-class test set has already been used twice (17-feature, 11-feature) and is being treated
    as fully spent; per explicit instruction, `src/models/adopt_12feature_model.py` never
    loads, transforms, or references `X_test`/`y_test`/`test_original_idx`. This is a
    deliberate scope difference from the 11-feature adoption script, which did pre-transform
    (but not evaluate) the test set. **No test-set number exists for the 12-feature model, and
    none should be quoted or implied anywhere in this project's documentation.**
- **Stress Level input method changed, 2026-09-24:** Stress Level (1-10) stays a model input
  (still 12 features, no retraining); only how a live API caller supplies it changed — the same
  pattern as caffeine above.
  - **What changed:** the API's raw `Stress Level (1-10)` field was removed. It now takes the 4
    PSS-4 items — `pss_uncontrollable`, `pss_confident`, `pss_going_your_way`,
    `pss_difficulties_piling_up`, each an integer 0-4 (0 = Never ... 4 = Very often, "in the
    last month"), with `pss_confident` and `pss_going_your_way` reverse-scored (`4 - answer`).
    `estimate_stress_level()` (`src/inference/stress_scale.py`, shared by `src/api/main.py` and
    `src/inference/predict_single.py`) sums them to a 0-16 total and maps it to
    `round_half_up(1 + total * 9/16)`, clamped to [1, 10]. The computed value is what
    `input_validation.py` checks (same Stress Level bounds as before) and what the model
    receives; the API returns it as `estimated_stress_level`. A raw `Stress Level (1-10)` key
    sent by an old caller is silently ignored.
  - **Decision log — why:** the dataset's Stress Level is an unanchored 1-10 self-rating with no
    defined meaning per point, and it is the model's #1 SHAP feature — the input the model
    leans on most was the one with the least grounding for a patient to answer consistently. A
    published questionnaire gives the patient concrete, standard questions instead.
  - **Evidence levels — do not conflate them:** the PSS-4 questionnaire itself is a validated
    instrument (Cohen, Kamarck & Mermelstein, 1983, *Journal of Health and Social Behavior*
    24(4), 385-396). The **0-16 → 1-10 rescale is this project's own invented convention and
    has not been independently validated.** The dataset's Stress Level was never measured with
    the PSS, so a PSS-derived value and a training-data value share only a direction and a
    range, not an established equivalence. Any doc or report that mentions this conversion must
    keep that distinction (`docs/api_usage.md` and `docs/model_card.md` already do).
  - **Training and evaluation are unaffected.** The model still learns from the dataset's real
    `Stress Level (1-10)` column; `src/rebuild_preprocessor.py`,
    `src/evaluation/robustness_3class.py`, `src/fairness/occupation_fairness.py` and every other
    training/evaluation script are unchanged, and no model artifact was rebuilt. Verified live:
    for a fixed patient, PSS answers producing Stress Level N give exactly the same
    probabilities as feeding N directly, and P(High) went from 0.010 (least-stressed answers)
    to 0.130 (most-stressed) for the `ambiguous_moderate` example patient. The test set was not
    used.
  - **Pitfall to remember:** because of the reverse-scored items, all-0 and all-4 answers both
    map to 6 (total 8), not to the extremes; the extremes are `0,4,4,0` → 1 and `4,0,0,4` → 10.
    Covered in `tests/test_api.py` (`test_estimate_stress_level_arithmetic`).
- **Model switched from Random Forest to XGBoost, 2026-09-28:** same 12 features and preprocessor;
  the canonical model is now `data/processed/mindcare_final_model_12feature_xgb.pkl`, built by
  `src/models/adopt_xgboost_12feature_model.py`. The 12-feature Random Forest is kept for history.
  - **How:** both models were re-tuned on the 12 features under one identical procedure
    (`src/models/tune_models_12feature.py` → `reports/tuning_results_12feature.json`):
    - 40 configurations each, 5-fold CV on train, balanced-accuracy scoring.
    - XGBoost got the class-balancing freedom Random Forest always had (balanced sample
      weights); unweighted won (CV 0.8089 vs 0.8077).
    - XGBoost settings: 300 trees, max_depth 3, learning_rate 0.03, subsample 0.8,
      min_child_weight 3.
    - The full analysis suite then ran on the current RF, a re-tuned RF and XGBoost side by
      side (`src/evaluation/compare_models_12feature.py` → `reports/model_comparison_12feature.md`).
    - Validation and train only — the test set was not used and remains spent.
  - **Decision log — why:** performance is a statistical tie (5-fold CV balanced accuracy 0.8085
    vs 0.8093, a gap about 20 times smaller than the fold-to-fold std of ~0.015; both miss the
    same 17 High cases). XGBoost wins on everything else that matters:
    - **Calibration:** ECE Low/Medium/High 0.016/0.020/0.007, against 0.061/0.060/0.033.
    - **Noise:** balanced accuracy 0.615 against 0.556 at 1× std.
    - **No caffeine shortcut:** the RF learned "High needs high caffeine". With a true-High
      patient's caffeine at or below 200 mg a day, it predicted High for 0 of 165, against
      127-129 for XGBoost. That matters because the API only estimates caffeine from serving
      counts.
    - **Age artifact:** mean P(High) 0.885 → 0.863 from age 49 to 55, against 0.903 → 0.628
      for the RF.
    - **Practical:** about 30 times faster (1 ms vs 37 ms) and 9 times smaller.
    - Trade-offs accepted: lower High precision (0.967 vs 0.993 — 5 Medium rows labelled High,
      against 1), and more sensitivity to a missing Sleep Hours value (0.715 vs 0.786).
    - The re-tuned RF (500 trees, depth 30) was no better and 5 times larger, so it was not
      adopted.
  - **Review threshold changed from 0.10 to 0.025** (`HIGH_PROBA_THRESHOLD` in `src/api/main.py`
    and `src/inference/predict_single.py`). At 0.10, XGBoost's better-calibrated probabilities
    caught only 152/165 true-High rows and 4/17 of the true-High rows predicted Medium. 0.025
    matches the RF's validation coverage exactly (158/165, 10/17), for 410 flagged rows instead
    of 363. The 0.10 "base rate" rationale in `src/models/uncertainty_flagging.py` is RF
    history.
  - **Verification:** the adoption script reproduces the comparison's numbers exactly, or deletes
    its output. `test_serves_xgboost_with_its_review_threshold` pins the model file, type and
    threshold. `xgboost` is pinned in `requirements.txt` (==3.4.1) for pickle compatibility.
  - **Performance estimate — nested CV (2026-09-30, `src/evaluation/nested_cv_12feature_xgb.py` →
    `reports/nested_cv_12feature_xgb.md`/`.json`). This is the primary figure; quote it rather than
    the validation split.** 5 outer folds, stratified, on the 9,350 train + validation rows (test
    never loaded). The preprocessor, the tuning (same both-ways search as
    `tune_models_12feature.py`) and the threshold (highest one flagging >= 158/165 of High cases in
    the inner out-of-fold predictions) are all redone inside each fold. Mean ± std across folds:
    - **All ages:** accuracy 0.7904 ± 0.0094, balanced accuracy 0.8119 ± 0.0057, macro-F1
      0.8244 ± 0.0064, High recall 0.8771 ± 0.0111, High precision 0.9759 ± 0.0065, flag catch
      rate 0.9587 ± 0.0153.
    - **Ages 18-49:** accuracy 0.7996 ± 0.0100, balanced accuracy 0.8230 ± 0.0059, macro-F1
      0.8318 ± 0.0062, High recall 0.9087 ± 0.0122, High precision 0.9837 ± 0.0044, flag catch
      rate 0.9700 ± 0.0159.
    - **The validation split (single split, used partly to choose the model)** was slightly
      *pessimistic* on accuracy (0.7776), balanced accuracy (0.8078) and macro-F1 (0.8171). Its
      High recall of 0.897 sits about 2 points above the nested 0.877, which is within the sampling
      noise of 165 High cases (standard error about 0.026; the gap is about 0.8 SE). Quote about
      0.88 for High recall.
    - **Threshold support:** each fold's own threshold came out at 0.0268 ± 0.0026 (range
      0.023-0.030), bracketing the deployed 0.025. Every fold's tuning picked the deployed
      settings (300 trees, depth 3, lr 0.03, unweighted).
    - **Not covered:** the 17 → 12 feature reduction, XGBoost over Random Forest, the 158/165
      coverage target, the label boundaries and the 18-49 age limit were all decided on this same
      data, outside the nested loop. The figures describe re-running this pipeline, not the whole
      chain of decisions. No test-set number exists for the current model.
- **Confident / borderline label added, 2026-10-02:** every prediction (`/predict`, `/patient-summary`,
  `predict_single.py`) now returns `confidence`, `confidence_label`, `borderline_reasons` and
  `borderline_between`. The model and its predictions are unchanged, and **overall accuracy is
  unchanged** — this is not an accuracy improvement and must not be described as one.
  - **Rule** (`src/inference/confidence.py`): confident only if the top probability is >= 0.70 AND
    it is not a flagged non-High prediction (P(High) >= 0.025 while predicting Low or Medium).
  - **Decision log — why:** the user asked how to improve accuracy. Analysis showed a data ceiling:
    75% of validation errors sit at the class borders (Anxiety Level 3/4 and 6/7), accuracy away
    from the borders is 88.9%, and every model family tried lands at about 77-79%. Rather than
    chase the number (Engineering rule 6), the system now says which predictions it is unsure of.
  - **Evidence** (`src/experiments/confidence_label_analysis.py` →
    `reports/confidence_label_11feature_v2.md`; out-of-fold over the 9,350 train + validation rows,
    test set not used): 56.2% confident at 85.8% accuracy; borderline 70.2%. Validation split:
    54.8% confident at 85.3%.
  - **Why the flag condition:** a plain 0.70 cut-off labelled 108 of 968 true-High patients a
    confident Medium; with the flag condition 33 remain (the ones the review flag also misses).
    "Confident" means sure of the top class, not that the patient is safe.
  - Tests: `test_confidence_label_rule`, `test_predict_and_summary_return_consistent_confidence_fields`,
    `test_confidence_label_matches_report_on_validation`.
- **Sweating Level removed, 2026-10-02 — canonical model is now "11-feature v2" XGBoost:** 9 numeric
  + 2 categorical. Same hyperparameters and 0.025 threshold as the 12-feature XGBoost; new
  preprocessor. Built by `src/models/adopt_11feature_v2_model.py`. The API, `input_validation.py`,
  `predict_single.py` and the test form no longer take the field; a caller that still sends it gets
  the same prediction (it is ignored).
  - **Naming:** "v2" because `data/processed/*_11feature.*` is the superseded 2026-09-22 Random
    Forest set (no Age, WITH Sweating Level). The current files are `*_11feature_v2*`. Never mix
    the two.
  - **Decision log — why:** a product/UX decision (one fewer question on the patient form), taken
    only after testing showed no meaningful cost (`reports/feature_reduction_sweatlevel_3class.md`,
    train + validation only):
    - It was the least important of the 12 inputs (0.4% of mean |SHAP| in the 12-feature XGBoost).
    - High patients unchanged: 148/165 labelled High and 158/165 flagged at 0.025, before and
      after; High recall identical in all 5 folds of a paired CV.
    - Largest validation-split drop 0.4 points (Medium recall); every paired-CV change about zero.
    - Shortcut test: forcing all High patients' Sweating Level to the median (3) changed no label
      and no flag.
    - Re-running the tuning procedure on the 11 features chose the same hyperparameters.
  - **Primary performance estimate is now `reports/nested_cv_11feature_v2_xgb.md`** (run with
    `python -m src.evaluation.nested_cv_12feature_xgb 11feature_v2`); quote it, not the
    12-feature figures below. Mean ± std over 5 outer folds:
    - **All ages:** accuracy 0.7891 ± 0.0081, balanced accuracy 0.8121 ± 0.0060, macro-F1
      0.8225 ± 0.0052, High recall 0.8812 ± 0.0092, High precision 0.9632 ± 0.0231, flag catch
      rate 0.9546 ± 0.0143.
    - **Ages 18-49:** accuracy 0.7978 ± 0.0084, balanced accuracy 0.8226 ± 0.0053, macro-F1
      0.8297 ± 0.0043, High recall 0.9130 ± 0.0089, High precision 0.9729 ± 0.0230, flag catch
      rate 0.9658 ± 0.0166.
    - **Validation split:** accuracy 0.7745, balanced accuracy 0.8055, macro-F1 0.8148, High
      recall 0.8970; 411 flagged, 158/165 High caught at 0.025.
  - **Caveat — tuning near-tie:** in one of five folds the tuning step chose balanced class
    weights over unweighted (inner CV 0.8078 vs 0.8077). That fold needed a threshold of 0.081 and
    had High precision 0.919; the four unweighted folds chose 0.0234-0.0311. The deployed model
    is unweighted with 0.025. **If the model is ever re-tuned and balanced weights win, re-derive
    the threshold** — do not reuse 0.025.
  - **Not re-run for this model:** calibration, SHAP, fairness and robustness
    (`reports/model_comparison_12feature.md`) describe the 12-feature XGBoost. Validation and
    train only; the test set was not used.
  - Tests: `test_sweating_level_is_no_longer_an_input`, `test_serves_xgboost_with_its_review_threshold`.
- **Supported age range restricted to 18-49, 2026-09-27:** the model makes predictions only for
  ages 18-49 inclusive. Any other age gets HTTP 422, with a different message per side (see the
  platform rules below). Enforced in `validate_patient()` (`ELIGIBLE_AGE_MIN`/`ELIGIBLE_AGE_MAX` in
  `src/inference/input_validation.py`), so the API and `predict_single.py` both apply it. The
  Pydantic Age bound stays 0-120 (impossible values only), and the model is unchanged — no
  retraining, and the test set was not used.
  - **Decision log — why 18 as the floor:** the dataset has no one under 18 (Age 18-64);
    physiological norms (heart and breathing rate) and consent rules differ for minors.
  - **Decision log — why 49 as the ceiling (not 40, not 55):** in the dataset the High rate is
    12-15% at every age up to 49, then drops to about 1% from 50 on (49: 15.5%, 50: 1.4%). This is
    almost certainly a synthetic-data artifact, and the model at the time (the 12-feature RF)
    had learned it. Evidence, all on validation data for that RF:
    - For the 161 true-High validation rows under 50, changing only Age drops mean P(High) from
      0.903 at 49 to 0.773 at 50 and 0.628 at 55.
    - Across all 1169 validation rows under 50, moving them to age 55 turns off the
      priority-review flag (P(High) >= 0.10) for 17 of 282 flagged rows. No High predictions
      flipped.
    - The 53-64 band had 3 true-High validation cases, and all 3 were missed.
    - **Update 2026-09-28:** XGBoost, the model since then, barely shows the effect (0.885 →
      0.863). The limit stands anyway: the reason is the data gap, since almost no High cases
      at 50+ means no evidence either model recognises High anxiety there. The API's rejection
      message was reworded to say that, rather than claiming the model lowers P(High).

    Under-calling High is the most dangerous error for this system. 40 was rejected because
    30-40 and 41-52 perform alike (balanced acc. 0.807 vs 0.815), so a lower cap would exclude
    well-served users without evidence. 55 was considered with a forced review flag for 50-55,
    and rejected in favour of the cleaner cut.
  - **This is a data-coverage limit, not a clinical judgement about older adults** — revisit if
    real data covering 50+ becomes available. Docs: `docs/api_usage.md` ("Supported age range"),
    `docs/model_card.md` (Intended Use; Known Limitations #12). Tests:
    `test_age_supported_range_boundaries_are_accepted` (plus the two per-side tests below).
  - **Platform rules, decided 2026-09-28** (these close the question left open on 2026-09-27):
    - **Under 18: cannot register for MindCare at all.** The block belongs in the web app's
      registration, which is not in this repo. `validate_patient()` is only a backstop. A minor
      reaching the model means the registration check failed, so the 422 says "not eligible for
      MindCare" and deliberately does NOT suggest a psychologist referral.
    - **50 and over: can register, and are redirected straight to a psychologist**, with no AI
      pre-assessment. The 422 says "refer this person directly to a psychologist" — the calling
      backend should act on that.
    - Tests: `test_under_18_is_rejected_as_not_eligible`,
      `test_over_49_is_rejected_with_psychologist_referral`.

### 5-class Severity (secondary/reference, unchanged — still 17 features)
- **Numeric (11):** Age, Sleep Hours, Physical Activity (hrs/week), Caffeine Intake
  (mg/day), Alcohol Consumption (drinks/week), Stress Level (1-10), Heart Rate (bpm),
  Breathing Rate (breaths/min), Sweating Level (1-5), Therapy Sessions (per month), Diet
  Quality (1-10)
- **Categorical (6):** Occupation, Smoking, Family History of Anxiety, Dizziness,
  Medication, Recent Major Life Event

### Dropped from both targets, and why
- Exercises, Sleep_Schedule, Nutrition — downstream recommendation outputs,
  not predictors (leakage risk)
- Anxiety Level (1-10) — near-duplicate of target (0.86 correlation with Severity)
- Gender — no signal (ANOVA F=0.025, p=0.98, eta²≈0.0000045)

## Known finding: Stress Level is the top feature for BOTH targets, but to different degrees
Stress Level (1-10) is the single most important feature for both the 5-class Severity
target and the new 3-class Anxiety Level target — by far the largest single-feature
effect in either case. **Decision: KEEP Stress Level for both targets** — it's a
clinically plausible, realistically collectable feature. But how much it dominates differs
sharply between the two targets, and this must be documented as a limitation wherever
either model's accuracy is reported:

- **5-class Severity:** Stress Level correlates 0.91 with Severity (ordinal, clinical
  order Minimal→Severe). Removing it (Logistic Regression) drops accuracy by ~49 points,
  from ~80% down to ~30% — i.e. down to near the ~27% majority-class baseline. Stress
  Level is carrying almost the **entire** signal here; the model is not meaningfully using
  the other 16 features. Do not represent the ~80% accuracy figure without this caveat.
- **3-class Anxiety Level (Low/Medium/High):** Stress Level correlates 0.65 with the
  3-class ordinal target (Low=0/Medium=1/High=2) — still the strongest single-feature
  relationship, but visibly weaker than 0.91. Removing it (Logistic Regression) drops
  accuracy by 17.6 points, from 77.8% down to 60.1% — well above the 47.2% majority
  baseline. So for this target, **the remaining 16 features carry real, independent
  predictive signal** even without Stress Level; the model is not singularly dependent
  on one feature the way the Severity model is.

Net takeaway: Stress Level is important and retained for both targets, but the 3-class
model is a meaningfully more broadly-supported model than the 5-class Severity model —
worth noting as a point in the 3-class target's favor when comparing the two, not just as
a caveat.

## Known finding: Scientist occupation fairness flag is likely noise, not a real gap
Both fairness reports (`reports/fairness_report.md` for 5-class, `reports/fairness_report_3class.md`
for 3-class) flag **Scientist** as having meaningfully weaker recall on the top-severity class
(High/Severe for 5-class, High for 3-class). Investigated this by comparing Scientist vs
non-Scientist feature distributions (Stress Level, Sleep Hours, Therapy Sessions — the top SHAP
features) among True-High(/Severe) rows. **It does not replicate:**
- On the validation set itself (the data the flag was computed from), none of these feature
  differences are statistically significant (Stress Level Welch t-test p=0.36 for 3-class n=16,
  p=0.16 for 5-class n=39) — the sample sizes are small enough that recall swinging by ~10-15
  points from one or two misclassified rows is expected noise, not a signal.
- The dataset shows **no real Occupation↔Stress Level relationship at all**: ANOVA of Stress
  Level across all 13 occupations, full dataset, gives F=0.47, **p=0.93**. There is nothing in
  how this (very likely synthetic) dataset was generated that would make Scientists'
  physiological/lifestyle profile systematically different in a way that should degrade model
  performance for this occupation.

**Conclusion: treat the Scientist recall gap as likely validation-set sampling noise, not a
validated fairness issue**, pending a larger sample (e.g. cross-validated fairness evaluation
instead of a single validation split) before treating it as something to correct for. Do not
cite this as evidence of occupational bias without that caveat.

## Pipeline status (update this section as phases complete)
Phases below are now tracked per target, since switching the primary target to 3-class
Anxiety Level does not carry over model training/tuning/evaluation work — only
preprocessing (Phase 10) is shared between the two targets.

### TEST SET USED — 2026-09-15 (FIRST use, 3-class target, 17-feature model)
- [x] **The test set (X_test/y_test, 3-class) was used on 2026-09-15 — the first of two total,
      now both spent (see SECOND TIME entry below).** (`src/evaluation/final_test_evaluation.py`,
      `reports/final_test_evaluation.md`.) Evaluated the saved final tuned Random Forest (17
      features), exactly as-is, no retraining/tuning/model-selection change made in response to
      the results. Result: accuracy 0.7915, balanced accuracy 0.8193, macro-F1 0.8311, macro
      AUROC 0.9083, macro AUPRC 0.8691 — every metric within ~0.02 of the validation-set numbers
      in `reports/full_evaluation_3class.md` (no metric gapped by ≥0.03), and test performance
      was very slightly *better* than validation across the board — no evidence of overfitting
      to the validation split during Phases 11-19. The 5-class Severity test set remains
      untouched.

### TEST SET USED — 2026-09-22 (SECOND AND FINAL use, 3-class target, 11-feature model)
- [x] **The test set (X_test/y_test, 3-class) was used a second time, on 2026-09-22 — this is
      now fully spent for the 3-class target. No further evaluation on it is permitted for
      either the 17-feature or the 11-feature model.**
      (`src/evaluation/final_test_evaluation_11feature.py`,
      `reports/final_test_evaluation_11feature.md`.)
      **Why a second use is disclosed and justified rather than tuning-driven reuse:** this
      evaluates a genuinely new, different model configuration — the 11-feature model adopted in
      `reports/feature_reduction_3class.md` / `src/models/adopt_11feature_model.py` to replace
      the original 17-feature model, dropping 6 SHAP-lowest features (Age, Alcohol Consumption,
      Dizziness, Smoking, Recent Major Life Event, Medication). It is not a re-run, re-tune, or
      iterative refinement of the model already evaluated on 2026-09-15 — reusing the test set
      for that would have been the exact tuning-driven misuse the one-way-door rule exists to
      prevent. A second disclosed evaluation for a materially different model is the legitimate
      exception.
      **Result:** accuracy 0.7891, balanced accuracy 0.8177, macro-F1 0.8285 — consistent with
      this model's own validation numbers (no gap ≥0.03), but **measurably, consistently
      (if slightly) worse than the 17-feature model's test performance**: every headline metric
      moved in the negative direction (accuracy −0.0024, balanced accuracy −0.0016, macro-F1
      −0.0026, macro AUROC −0.0006, macro AUPRC −0.0058), with Medium-class AUPRC the one metric
      crossing −0.01 (−0.0122). This **reverses** the validation-only finding in
      `reports/feature_reduction_3class.md`, which had shown the 11-feature model slightly
      *ahead* on validation — that gain did not replicate on held-out test data. Net effect is
      still small (≤0.003 on every headline metric), so the decision to drop those 6 features
      remains reasonable, but the honest claim is now "no *meaningful* cost" rather than "a
      slight improvement." **This is exactly the kind of finding a disclosed second test-set use
      is for** — checking whether a validation-only result holds up, not chasing a better number.

### FEATURE SET CHANGE — 2026-09-22 (THIRD change, 3-class target, Age restored, 12-feature model — VALIDATION ONLY, test set NOT used)
- [x] **Age was restored as a model input, on top of the 11-feature set, producing the
      12-feature model (canonical until 2026-10-02).** (`src/models/adopt_12feature_model.py`,
      `reports/feature_addition_age_3class.md`.) **Unlike the first two feature-set changes
      above, this one is explicitly NOT test-set-verified, by design.** The 3-class test set was
      already used twice (17-feature, then 11-feature) and is being treated as fully spent —
      `src/models/adopt_12feature_model.py` never loads, transforms, or references
      `X_test`/`y_test`/`test_original_idx` anywhere, unlike the 11-feature adoption script
      (which pre-transformed but did not evaluate the test set). **This configuration has
      validation-only evidence and always will, unless a future decision explicitly justifies a
      third test-set use.**
      **Why this change differs in kind from the first two:** this is a **clinical/UX decision,
      not a performance or product-friction tradeoff** — Age is a professional norm for a
      healthcare-adjacent platform (age-appropriate reference ranges for physiological features,
      legal/consent handling that differs for minors vs. adults). It was not made because
      validation metrics favored it, and would have been made even if they hadn't.
      **Result (validation only, vs. the 11-feature baseline 0.7770/0.8084/0.8204):** accuracy
      0.7739 (−0.0031), balanced accuracy 0.8062 (−0.0022), macro-F1 0.8182 (−0.0022), recall Low
      0.7506 (−0.0039), recall Medium 0.7709 (−0.0028), recall High 0.8970 (−0.0000) — largest
      movement 0.39 points, well under the 1-point bar used elsewhere in this project. This exact
      12-feature combination had never been tested before this run; the near-zero result is
      **cited as confirmation the restoration isn't harmful, not as the reason for making it.**

- [x] Phase 9 — EDA complete
- [x] Phase 10 — Preprocessing complete (ColumnTransformer: StandardScaler +
      OneHotEncoder, fit on train only; artifacts in data/processed/). Shared by both
      targets — the 3-class split file reuses the same X_train/X_val/X_test.

### 5-class Severity (secondary / reference target, kept for comparison)
- [x] Phase 11 — Baseline models
- [x] Phase 13 — Hyperparameter tuning (validation set only, never touch test set)
- [x] Phase 14 — Full evaluation (AUROC/AUPRC, per-class metrics — reports/full_evaluation.md)
- [x] Phase 17 — Explainability (SHAP)
- [x] Phase 18 — Fairness / subgroup analysis (Occupation subgroup performance — reports/fairness_report.md)

### 3-class Anxiety Level (primary target, as of 2026-09-14)
- [x] Phase 11 — Baseline models (src/models/train_baselines_3class.py,
      reports/baseline_results_3class.json — NOTE: this one is actually already done,
      not reset to "not started"; see caveat below)
- [x] Phase 13 — Hyperparameter tuning (`src/models/tune_models_3class.py`,
      `reports/tuning_results_3class.json`) — NOTE: also already done, not "not started"
- [x] Phase 14 — Full evaluation (AUROC/AUPRC, per-class metrics —
      `src/evaluation/full_evaluation_3class.py`, `reports/full_evaluation_3class.md`)
- [x] Phase 17 — Explainability (SHAP) (`src/explainability/shap_analysis_3class.py`,
      `reports/shap_summary_3class.md`, `reports/shap_summary_3class.png`) — NOTE: also
      already done, not "not started"
- [x] Phase 18 — Fairness / subgroup analysis (`src/fairness/occupation_fairness_3class.py`,
      `reports/fairness_report_3class.md`) — NOTE: also already done, not "not started"

### Phase 12 — Advanced models (3-class target)
- [x] Phase 12 — done for 3-class Anxiety Level target (`src/models/train_advanced_3class.py`,
      `reports/advanced_models_3class.json`, `reports/advanced_models_3class.md`). Per
      `docs/master_project_instructions.md` PHASE 12, evaluated a shallow MLP (neural network)
      as the advanced-model candidate appropriate to this small tabular dataset. Result: MLP
      (tuned) scores accuracy 0.7733 / balanced accuracy 0.8041 / macro-F1 0.8160 / High recall
      0.8970 — ties or slightly trails both Random Forest and XGBoost on every metric, while
      being worse on interpretability and computational cost. **Decision: MLP not adopted;
      Random Forest remains selected.** Not yet done for 5-class Severity.

### Phase 19 — Robustness testing (3-class target)
- [x] Phase 19 — done for 3-class Anxiety Level target, saved final model
      (`src/evaluation/robustness_3class.py`, `reports/robustness_3class.md`,
      `reports/robustness_3class.json`). Tested missing features (single-feature knockout),
      noisy data (Gaussian noise at 4 intensities), invalid/out-of-range inputs, and Stress
      Level distribution shift; wording/site/temporal-change tests are explicitly marked N/A
      (no text fields, single data source, no timestamp column). **Key findings — real
      fragilities, not reassurance:**
      - Losing Stress Level alone collapses balanced accuracy from 0.8056 to 0.4291 (High
        recall 0.8970 → 0.2242); losing Therapy Sessions alone drops it to 0.5590 (High recall
        → 0.1515). The model's two most important SHAP features are also its two biggest
        single points of failure.
      - Modest Gaussian noise (0.25x each feature's train std, all numeric features at once)
        already costs 0.0323 balanced-accuracy points; at 1x std it collapses to 0.5560 (from
        0.8056).
      - **No input validation exists anywhere in the pipeline** — physically impossible values
        (Age=-5, Stress Level=250, Heart Rate=9000) are silently transformed and produce a
        confident-looking prediction with no error or warning. **Fixed:** see
        `src/inference/input_validation.py` below. (Note, 2026-09-24: the Stress Level=250 case
        describes the pipeline and the historical raw-field API. Since the PSS-4 conversion, a
        live API caller can no longer send a raw Stress Level at all — it is computed from 4
        answers of 0-4 and is always 1-10. `validate_patient()`'s Stress Level check itself is
        unchanged and still rejects 250 if called directly.)
      - Predicted-High rate is asymmetric under Stress Level shift: shifting it down 3 points
        nearly halves the predicted-High fraction (0.0903 → 0.0418), but shifting it up 1-3
        points changes nothing (stays at 0.0903) — not yet root-caused.
      Not yet done for 5-class Severity.

### Phase 15 — Calibration (3-class target)
- [x] Phase 15 — done for 3-class Anxiety Level target, all 3 classes. High:
      `src/evaluation/calibration_3class.py` / `reports/calibration_3class.md` (Brier 0.0131,
      over-confident below P=0.3, well-calibrated above P=0.8). Low and Medium:
      `src/evaluation/calibration_3class_full.py` / `reports/calibration_3class_full.md`
      (Brier 0.1518 and 0.1646 respectively, both roughly calibrated on a count-weighted
      average but with real per-bin over/under-confidence patterns — see report). Not yet
      done for 5-class Severity.

### Input validation (fixes a Phase 19 finding, 3-class target)
- `src/inference/input_validation.py` — validates the (now 12, originally 17, briefly 11) raw
  features before any prediction, wired into `src/inference/predict_single.py` and
  `src/api/main.py`. Bounds for 5 of the 6 originally-removed features (Alcohol Consumption,
  Dizziness, Smoking, Recent Major Life Event, Medication) were deleted when those features were
  dropped, 2026-09-22. Age's bounds were deleted at the same time, then restored later the same
  day when Age was re-added (reusing the original justification: observed 18-64, hard 0-120,
  outer bound of recorded human lifespan). Two tiers per numeric feature: `observed_min`/
  `observed_max` (exact CSV min/max) vs `hard_min`/`hard_max` (physically/clinically plausible
  outer bounds — real physiological limits for open-ended quantities like Heart Rate (30-220 bpm)
  and Breathing Rate (5-60), literal unit ceilings for bounded counts like Physical Activity
  (≤168 hrs/week) and Therapy Sessions (≤31/month), and the rating scale plus a small margin for
  Stress Level/Diet Quality (and Sweating Level, until it was removed as a feature on 2026-10-02;
  its bounds were deleted with it) so e.g. a half-point value like 10.5 warns rather than
  rejects). Outside `hard` bounds → rejected with a clear error, listing every violation found.
  Inside `hard` but outside `observed` → allowed through with a warning. Categorical features are
  closed sets (13 occupations; Yes/No for the 5 binary fields) — anything else is rejected, no
  warn tier. Verified against the exact Age=-5 / Stress Level=250 / Heart Rate=9000 style inputs
  that silently produced confident predictions in the Phase 19 robustness report — all three now
  correctly rejected.
  - **Note, 2026-09-24 (PSS-4 conversion):** the Stress Level examples above (10.5 warns, 250
    rejected) describe `validate_patient()` called directly, and the historical raw-field API. A
    live API caller can no longer send either value: Stress Level is now computed from the 4
    PSS-4 answers (`src/inference/stress_scale.py`) and is always an integer 1-10, so through
    the API it can never trip the Stress Level warn or reject tier. The validation logic itself
    is unchanged — the bounds are still checked, now on the computed value. The equivalent
    API-level guard is Pydantic's 0-4 limit on each PSS answer.
  - **Age scope rule, 2026-09-27:** besides the plausibility tiers, `validate_patient()` rejects
    any Age outside 18-49 (the supported range; see "Supported age range restricted to 18-49"
    above). Under 18 gets "not eligible for MindCare", and 50+ gets "refer directly to a
    psychologist". Ages 50-64 were previously accepted without a warning, since they're inside
    the observed range; they are now rejected.

### Saved final model artifact (3-class target) — SUPERSEDED 2026-09-22, kept for history
- `data/processed/mindcare_final_model.pkl` — the original 17-feature tuned Random Forest
  (3-class Anxiety Level target), fit once on `X_train`/`y_train` and persisted via
  `src/models/save_final_model.py`. Verified two ways before being adopted anywhere: (1)
  metrics recomputed from this exact artifact on `X_val` match
  `reports/tuning_results_3class.json`'s `random_forest.tuned_validation` values exactly
  (accuracy, balanced accuracy, macro-F1, High recall); (2) reloading the `.pkl` in a separate,
  fresh Python subprocess and predicting on `X_val` gives predictions identical
  (`np.array_equal`) to predicting with the in-memory freshly-fit model.
  **No longer the canonical/deployed model** — replaced 2026-09-22, first by the 11-feature
  model below (also since superseded), then the same day by the 12-feature model
  (further below; itself superseded, see the current 11-feature v2 XGBoost). File left on disk, untouched, for historical reference and reproducibility of
  `reports/final_test_evaluation.md`; not used by `predict_single.py` or `src/api/main.py`
  anymore.

### Saved final model artifact (3-class target) — SUPERSEDED 2026-09-22 (same day), kept for history, 11 features
- `data/processed/mindcare_final_model_11feature.pkl` — the tuned Random Forest on the reduced
  11-feature set, fit on the 11-feature `X_train`, persisted via
  `src/models/adopt_11feature_model.py`. Verified the same way as the artifact above: reloaded
  from disk and confirmed to reproduce `reports/feature_reduction_3class.md`'s documented
  validation metrics exactly (accuracy 0.7770, balanced accuracy 0.8084, macro-F1 0.8204).
  **No longer the canonical/deployed model** — superseded the same day, 2026-09-22, when Age was
  restored (see below). File left on disk, untouched, for historical reference and reproducibility
  of `reports/final_test_evaluation_11feature.md`; not used by `predict_single.py` or
  `src/api/main.py` anymore.

### Saved final model artifact (3-class target) — CURRENT canonical, 11-feature v2 XGBoost
- `data/processed/mindcare_final_model_11feature_v2_xgb.pkl` — XGBoost on the 11-feature v2 set
  (12 features minus Sweating Level), with `mindcare_preprocessor_11feature_v2.pkl` and
  `mindcare_processed_splits_11feature_v2.npz` (train + validation only; no test keys). Built by
  `src/models/adopt_11feature_v2_model.py`, hyperparameters from
  `reports/tuning_results_12feature.json`.
  - The script checks the saved model against `reports/feature_reduction_sweatlevel_3class.md`
    and deletes its outputs on any mismatch: accuracy 0.7745, balanced accuracy 0.8055, macro-F1
    0.8148, High recall 0.8970, and 411 flagged / 158 true-High flagged / 148 labelled High at 0.025.
  - This is what `src/api/main.py` and `src/inference/predict_single.py` load. No test-set number
    exists or is planned.

### Saved final model artifact (3-class target) — SUPERSEDED 2026-10-02, kept for history, 12-feature XGBoost
- `data/processed/mindcare_final_model_12feature_xgb.pkl` — XGBoost on the same 12 features and
  preprocessor (`mindcare_preprocessor_12feature.pkl`), fit on the 12-feature `X_train` by
  `src/models/adopt_xgboost_12feature_model.py`, with hyperparameters read from
  `reports/tuning_results_12feature.json`.
  - The script checks it against `reports/model_comparison_12feature.md` and stops, deleting
    the file, on any mismatch: accuracy 0.7776, balanced accuracy 0.8078, macro-F1 0.8171, High
    recall 0.8970, and 410 flagged / 158 true-High / 10 of 17 hard misses at the 0.025 threshold.
  - It was the deployed model from 2026-09-28 to 2026-10-02. Validation-only evidence; no
    test-set number exists.

### Saved final model artifact (3-class target) — SUPERSEDED 2026-09-28, kept for history, 12-feature Random Forest
- `data/processed/mindcare_final_model_12feature.pkl` — the tuned Random Forest on the
  11-feature set plus Age restored, fit on the 12-feature `X_train`, persisted via
  `src/models/adopt_12feature_model.py`. Unlike the two artifacts above, this one's validation
  metrics are **not verified against a pre-documented expected value** (this exact configuration
  had never been run before) — instead its own run's numbers ARE the documented source of truth,
  written to `reports/feature_addition_age_3class.md` (accuracy 0.7739, balanced accuracy 0.8062,
  macro-F1 0.8182, recall Low/Medium/High 0.7506/0.7709/0.8970). **No test-set number exists or
  is planned for this configuration** — see "FEATURE SET CHANGE — 2026-09-22 (THIRD change)"
  above. Paired with `data/processed/mindcare_preprocessor_12feature.pkl` and
  `data/processed/mindcare_processed_splits_12feature.npz` (the latter has no
  `X_test`/`y_test`/`test_original_idx` keys — the test set was never loaded). It was the
  deployed model from 2026-09-22 to 2026-09-28; the preprocessor and splits are still in use by
  the XGBoost model above.

### Phase 16 — Uncertainty / abstention mechanism (3-class target)
- [x] Phase 16 — done for 3-class Anxiety Level target (`src/models/uncertainty_flagging.py`,
      `reports/uncertainty_flagging.md`). Final rule: flag "borderline — recommend review" when
      the tuned Random Forest's P(High) >= 0.10 (the ~10% marginal base rate of High), chosen
      because every prediction is already reviewed by a psychologist, so this reprioritizes
      review attention rather than gatekeeping access to review. Not yet done for 5-class Severity.
      **Superseded 2026-09-28:** the production threshold is now 0.025 on XGBoost; see "Model
      switched from Random Forest to XGBoost" above.

### Phase 21/22 — Clinical validation comparison tool (built, no data yet)
- [x] Clinical scoring scales and agreement metrics built in `src/evaluation/clinical_scales.py` and `src/evaluation/clinical_agreement.py`
- [x] Unit tests in `tests/test_clinical_scales.py` (arithmetic verification only)
- [ ] **No Hamilton score data exists in this project** — `clinical_agreement.py` has no real data to run against; do NOT fabricate or use synthetic paired data
- [x] Tooling built, but genuinely no data to run on yet; do NOT claim these phases are "done"

## Engineering rules (non-negotiable)
1. Never fabricate metrics — only report numbers actually computed by running code.
2. Fit any preprocessing/scaling only on train data, never on val/test/full dataset.
3. Never tune hyperparameters against the test set.
4. Every experiment needs: dataset version, model, hyperparameters, metrics, seed
   (use SEED=42 throughout for reproducibility).
5. Accuracy alone is insufficient — report macro-F1, balanced accuracy, and per-class
   metrics for this imbalanced 5-class problem.
6. If asked to push toward a specific accuracy target, push back and explain why.
7. This is a research/prototype model. Never claim clinical diagnostic validity.

## When implementing a new phase
1. State which phase this is and what its objective is.
2. Check this file for relevant prior decisions before proposing new ones.
3. Write code to src/, not directly in notebooks.
4. Run it and show real output — don't just generate code and stop.
5. Update the Pipeline Status checklist above when a phase completes.
6. Flag anything that contradicts an existing decision instead of silently changing it.
---
