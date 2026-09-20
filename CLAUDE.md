---
# MindCare AI — Project Context for Claude Code

## What this is
The AI/ML component of MindCare, an FYP mental-health platform connecting patients and
psychologists. This repo trains a model to predict anxiety risk from patient
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

**The feature set is unchanged.** All 17 features (11 numeric + 6 categorical, listed
below) — including Stress Level — remain fully included in every model for the 3-class
target, identical to the 5-class setup. This change only swaps the target labels; it does
not add, drop, or otherwise touch any feature.

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
  bucket (primary, see "Target change" above) — the feature list below is identical
  for both; only the target label differs.
- **Numeric features (11):** Age, Sleep Hours, Physical Activity (hrs/week), Caffeine
  Intake (mg/day), Alcohol Consumption (drinks/week), Stress Level (1-10), Heart Rate
  (bpm), Breathing Rate (breaths/min), Sweating Level (1-5), Therapy Sessions (per
  month), Diet Quality (1-10)
- **Categorical features (6):** Occupation, Smoking, Family History of Anxiety,
  Dizziness, Medication, Recent Major Life Event
- **Dropped, and why:**
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

### TEST SET USED — 2026-09-15 (3-class target, one-time, final)
- [x] **The test set (X_test/y_test, 3-class) has now been used, on 2026-09-15 — this was a
      one-way door and must not be repeated.** (`src/evaluation/final_test_evaluation.py`,
      `reports/final_test_evaluation.md`.) Evaluated the saved final tuned Random Forest, exactly
      as-is, no retraining/tuning/model-selection change made in response to the results.
      Result: accuracy 0.7915, balanced accuracy 0.8193, macro-F1 0.8311, macro AUROC 0.9083,
      macro AUPRC 0.8691 — every metric within ~0.02 of the validation-set numbers in
      `reports/full_evaluation_3class.md` (no metric gapped by ≥0.03), and test performance was
      very slightly *better* than validation across the board — no evidence of overfitting to
      the validation split during Phases 11-19. **The 3-class test set must not be evaluated
      again** unless the model is retrained/retuned from scratch as a deliberate, explicit new
      final-model decision. The 5-class Severity test set remains untouched.

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
        `src/inference/input_validation.py` below.
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
- `src/inference/input_validation.py` — validates all 17 raw features before any prediction,
  wired into `src/inference/predict_single.py`. Two tiers per numeric feature: `observed_min`/
  `observed_max` (exact CSV min/max) vs `hard_min`/`hard_max` (physically/clinically plausible
  outer bounds — real physiological limits for open-ended quantities like Heart Rate (30-220 bpm)
  and Breathing Rate (5-60), literal unit ceilings for bounded counts like Physical Activity
  (≤168 hrs/week) and Therapy Sessions (≤31/month), and the rating scale plus a small margin for
  Stress Level/Diet Quality/Sweating Level so e.g. a half-point value like 10.5 warns rather than
  rejects). Outside `hard` bounds → rejected with a clear error, listing every violation found.
  Inside `hard` but outside `observed` → allowed through with a warning. Categorical features are
  closed sets (13 occupations; Yes/No for the 5 binary fields) — anything else is rejected, no
  warn tier. Verified against the exact Age=-5 / Stress Level=250 / Heart Rate=9000 style inputs
  that silently produced confident predictions in the Phase 19 robustness report — all three now
  correctly rejected.

### Saved final model artifact (3-class target)
- `data/processed/mindcare_final_model.pkl` — the tuned Random Forest (3-class Anxiety Level
  target), fit once on `X_train`/`y_train` and persisted via `src/models/save_final_model.py`.
  Verified two ways before being adopted anywhere: (1) metrics recomputed from this exact
  artifact on `X_val` match `reports/tuning_results_3class.json`'s `random_forest.tuned_validation`
  values exactly (accuracy, balanced accuracy, macro-F1, High recall); (2) reloading the `.pkl` in
  a separate, fresh Python subprocess and predicting on `X_val` gives predictions identical
  (`np.array_equal`) to predicting with the in-memory freshly-fit model. `src/inference/
  predict_single.py` loads this saved artifact rather than refitting the model on every run.

### Phase 16 — Uncertainty / abstention mechanism (3-class target)
- [x] Phase 16 — done for 3-class Anxiety Level target (`src/models/uncertainty_flagging.py`,
      `reports/uncertainty_flagging.md`). Final rule: flag "borderline — recommend review" when
      the tuned Random Forest's P(High) >= 0.10 (the ~10% marginal base rate of High), chosen
      because every prediction is already reviewed by a psychologist, so this reprioritizes
      review attention rather than gatekeeping access to review. Not yet done for 5-class Severity.

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
