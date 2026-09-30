# Trustworthiness Report — MindCare Anxiety Level Classifier (3-Class)

Answers to the 25 Phase 35 questions, pulled only from
[`docs/model_card.md`](model_card.md) and [`CLAUDE.md`](../CLAUDE.md), each verified against the
report file(s) those documents cite. Where something has not actually been done, this report says
so explicitly rather than skipping the question or implying otherwise.

> **Update 2026-09-28 — the canonical model is now XGBoost.** Both 12-feature models were
> re-tuned under one identical procedure, then put through the full analysis suite side by side
> on validation and training data (`reports/model_comparison_12feature.md`). The analyses were
> calibration, the review flag, SHAP, fairness by occupation, age band and gender, and robustness.
> - **Performance was a tie:** 5-fold CV balanced accuracy 0.8085 (XGBoost) vs 0.8093 (Random
>   Forest).
> - **XGBoost was adopted** because it is 3–5 times better calibrated, more robust to noise,
>   free of a "High needs high caffeine" shortcut the Random Forest had learned, barely affected
>   by the age-50 data artifact, and about 30 times faster.
> - **The review threshold changed from 0.10 to 0.025**, so the flag keeps the Random Forest's
>   validation coverage: 158 of 165 High cases, and 10 of the 17 hardest misses.
> - **Nothing touched the test set.**
>
> Answers below that describe "the tuned Random Forest" are the history up to this change. Q9,
> Q22 items 10–12, Q23 and Q25 items 6–7 carry update notes.
>
> **Update 2026-09-30 — nested cross-validation is now the primary performance estimate**
> (`reports/nested_cv_12feature_xgb.md`). The full XGBoost pipeline was rebuilt inside each of 5
> outer folds on the 9,350 train + validation rows: preprocessor, tuning and review threshold.
> The test set was not used.
> - **All ages:** balanced accuracy 0.8119 ± 0.0057, High recall 0.8771 ± 0.0111, flag catch
>   rate 0.9587 ± 0.0153.
> - **Validation vs nested:** the validation split was slightly pessimistic on the headline
>   metrics. Its High recall (0.897) is about 2 points above the nested figure, which is within
>   the sampling noise of 165 High cases.
> - **Threshold:** each fold's own threshold, 0.0268 ± 0.0026, supports the deployed 0.025.
> - **Not covered:** decisions made on the same data outside the nested loop (Q22 item 13).
>
> Q12, Q22, Q23 and Q24 carry update notes.

---

### 1. What clinical problem does the model solve?

It predicts an **anxiety risk level — Low / Medium / High** — from a patient's lifestyle and
physiological data, as a decision-support suggestion within the MindCare platform
(`model_card.md`, "Intended Use"; `CLAUDE.md`, "What this is"). It does not diagnose; it produces
a risk bucket for a psychologist to review.

### 2. Who is it intended for?

**Psychologists**, as the reviewer/approver of the model's suggestion, not patients directly. Per
the project's critical workflow constraint: "AI prediction → psychologist reviews → psychologist
approves/modifies → patient sees it." The model's output must never reach a patient directly and
must never bypass psychologist review (`model_card.md`, "Intended Use"; `CLAUDE.md`, "What this
is").

### 3. What data was used?

`data/raw/mindcare_dataset_final.csv` — ~11,000 rows, 23 columns. **As of 2026-09-22, the two
targets use different feature sets, and the 3-class target's own feature set changed twice the
same day** (`model_card.md`, "Features"; `CLAUDE.md`, "Finalized feature decisions"):
- The **primary, deployed 3-class Anxiety Level model uses 12 features** — 10 numeric (Stress
  Level, Therapy Sessions, Sleep Hours, Caffeine Intake, Diet Quality, Physical Activity, Heart
  Rate, Breathing Rate, Sweating Level, **Age**) + 2 categorical (Occupation, Family History of
  Anxiety). Six columns that were previously features (Age, Alcohol Consumption, Dizziness,
  Smoking, Recent Major Life Event, Medication) were removed on 2026-09-22; Age was then restored
  the same day, leaving 5 removed (Alcohol Consumption, Dizziness, Smoking, Recent Major Life
  Event, Medication) — see Q9/Q10 for why both changes happened and why they differ in kind.
- The **secondary/reference 5-class Severity model still uses the original 17 columns** (11
  numeric + 6 categorical) — unchanged.

The rest of the 23 columns are the target columns (Severity, Anxiety Level) or columns dropped
for leakage reasons (`model_card.md`, "Training Data", "Features"). Unless a question below is
explicitly about the 5-class target, or explicitly about a superseded configuration, "the model"
in this report refers to the deployed 12-feature 3-class model.

### 4. How was the data collected?

**Not documented.** Neither `model_card.md` nor `CLAUDE.md` describes a collection methodology
(no survey design, recruitment process, or instrumentation is mentioned). What is documented is
forensic evidence pointing the other way: the dataset is flagged as **very likely synthetic**, on
the basis of near-uniform demographics, zero missing values or duplicates, and templated
recommendation text (`model_card.md`, "Training Data"; `CLAUDE.md`, "Dataset"). There is no
stated real-world collection process to describe.

### 5. How were labels created?

For the primary (3-class) target: labels are derived **directly from the raw `Anxiety Level
(1-10)` column** by fixed binning — Low = 1-3, Medium = 4-6, High = 7-10 (`model_card.md`,
"Target definition"; `CLAUDE.md`, "Target change"). This was a deliberate choice over re-bucketing
the 5-class Severity column, because Severity's boundaries don't align cleanly with these bins per
earlier EDA. How the underlying raw `Anxiety Level` and `Severity` values were originally assigned
in the source dataset itself is not documented — consistent with the dataset's likely-synthetic
origin (see Q4).

### 6. How was leakage prevented?

Documented leakage-prevention decisions (`model_card.md`, "Features"; `CLAUDE.md`, "Finalized
feature decisions"):
- `Exercises`, `Sleep_Schedule`, `Nutrition` are dropped as features — they are downstream
  recommendation outputs, not predictors.
- `Anxiety Level (1-10)` is never used as an input feature for either target: for 5-class
  Severity it was dropped for being a near-duplicate of the target (0.86 correlation); for the
  3-class target it **is** the target's own source column, so it is excluded from the feature set
  by construction.
- Preprocessing (`StandardScaler`/`OneHotEncoder`) is fit on the training split only, never on
  val/test/the full dataset (Engineering Rule 2), and hyperparameter tuning is restricted to the
  training split with validation-only evaluation (Engineering Rule 3) — the test set has never
  been touched by any fitting or selection step.

### 7. How was the dataset split?

**7700 / 1650 / 1650** rows (train/val/test), stratified, seed=42. This split is shared between
the 3-class and 5-class targets — the same `train_original_idx`/`val_original_idx`/
`test_original_idx` row membership is reused for both, so switching targets did not require
re-splitting (`model_card.md`, "Training Data"; `CLAUDE.md`, "Target change").

### 8. What baselines were evaluated?

Four models, on the validation set: a **majority-class dummy classifier**, **Logistic
Regression**, **Random Forest**, and **XGBoost** (`model_card.md`, "Performance", citing
`reports/baseline_results_3class.json`).

| | Majority dummy | Logistic Regression | Random Forest (untuned) |
|---|---:|---:|---:|
| Accuracy | 0.4715 | 0.7776 | 0.7703 |
| Balanced accuracy | 0.3333 | 0.8076 | 0.8024 |
| Macro-F1 | 0.2136 | 0.8186 | 0.8150 |
| High recall | 0.0000 | 0.8970 | 0.8970 |

(XGBoost's untuned baseline numbers are referenced in the tuning comparison but not reproduced
in `model_card.md`'s baseline table; see Q10 for the tuned XGBoost figures that are documented.)

### 9. What model was selected?

**Current (since 2026-09-28): XGBoost**, with 300 trees, max_depth 3, learning_rate 0.03,
subsample 0.8, colsample_bytree 1.0, min_child_weight 3, gamma 0, unweighted. It was re-tuned on
the 12 features (`reports/tuning_results_12feature.json`) and chosen after the side-by-side
comparison in `reports/model_comparison_12feature.md` (see the update note at the top). The
original selection follows.

**Original selection:** the **tuned Random Forest** — hyperparameters `n_estimators=200, max_depth=10,
min_samples_split=10, min_samples_leaf=4, max_features='sqrt', class_weight='balanced',
random_state=42` (`model_card.md`, "Performance", citing `reports/tuning_results_3class.json`).
This is the model used for every subsequent analysis in the model card: full evaluation,
calibration, uncertainty flagging, SHAP, and fairness.

**The algorithm and hyperparameters were never revisited across either of the two feature-set
changes on 2026-09-22** (see below) — the same tuned Random Forest configuration was simply
retrained from scratch first on the reduced 11-feature set, then again on the 12-feature set
with Age restored. What changed, twice, is the *input feature set*, not the model family or its
tuning.

### 10. Why was it selected?

Documented in `model_card.md`'s **"Model Selection Rationale"** section (added after this
report's first draft flagged the gap): both tuned Random Forest and tuned XGBoost were evaluated
(`reports/tuning_results_3class.json`), and XGBoost scored marginally higher on accuracy (0.7770
vs. 0.7733) and balanced accuracy (0.8074 vs. 0.8056), while Random Forest scored marginally
higher on macro-F1 (0.8177 vs. 0.8175) — every metric within ~0.4 points of the other model.
Random Forest was selected based on (1) comparable performance, (2) greater interpretability for
a psychologist-facing tool (feature-based splits vs. a gradient-boosted ensemble), and (3) it
being the model already carried through the SHAP/calibration/uncertainty/fairness analysis
stack.

**Important caveat, stated plainly in that same section:** this rationale was formalized *after*
model selection, not before it — reasons (1)-(3) were written up retroactively rather than having
driven the original choice — and the full analysis suite (SHAP, calibration, uncertainty,
fairness) has **not** been re-run on tuned XGBoost. So while a rationale now exists, it has not
been validated against an equivalent depth of analysis on the alternative; treat the selection as
reasonable but not rigorously defended. **This algorithm-selection question is distinct from, and
predates, both feature-set changes below** — Random Forest vs. XGBoost was decided while the
model still used all 17 features.

**Why the feature set was reduced from 17 to 11 (2026-09-22), and why that was a separate
decision from model selection:** after adoption, SHAP ranking (`reports/shap_full_ranking_3class.md`)
identified 6 features (Age, Alcohol Consumption, Dizziness, Smoking, Recent Major Life Event,
Medication) as the bottom of the importance ranking. Dropping them and retraining the same tuned
Random Forest cost essentially nothing on validation (`reports/feature_reduction_3class.md`, all
headline metrics within 0.36 points). **This was a product/UX decision, not a
performance-driven one** — fewer required onboarding fields and less exposure to missing-data
fragility (per the project's earlier Phase 19 robustness findings, Q16/Q18), justified because
the performance case *against* dropping them was already weak to begin with. Caffeine Intake was
separately evaluated for the same treatment and *rejected* — it ranks 4th by SHAP importance (a
real signal) and dropping it cost a real 1.56-point hit to Medium-class recall
(`reports/feature_reduction_caffeine_3class.md`) — so it was kept as a model input, with only its
*collection method* simplified (four serving counts converted server-side, `model_card.md`,
"Features"). See Q11/Q12 for how this reduction held up when checked on the held-out test set.

**Why Age was then restored, the same day (11→12 features), and why this THIRD change differs in
kind from the first two:** the first two feature-set decisions (17→11 features, and keeping vs.
dropping Caffeine Intake within that) were each grounded in a **performance or product/UX
tradeoff** — a SHAP ranking, a measured validation cost, an onboarding-friction argument. Age's
restoration is different: it is a **clinical necessity, not a performance or UX tradeoff at
all** — Age is a professional norm for a healthcare-adjacent intake form (age-appropriate
reference ranges for physiological features like Heart Rate and Breathing Rate, and
legal/consent handling that differs for minors vs. adults). The decision to restore it did not
depend on, and was not contingent on, what a validation check would show.
`reports/feature_addition_age_3class.md` was run anyway — accuracy 0.7739 vs. the 11-feature
baseline's 0.7770 (a 0.31-point difference, largest movement 0.39 points on any metric) — but
**that result is cited only as confirmation the restoration isn't harmful, explicitly not as the
reason for making it.** This is the project's clearest example yet of a feature-set decision
whose *justification* is entirely outside the performance metrics this report otherwise centers
on. **Unlike the 17→11 change, this one was not checked against the test set** — see Q11/Q12 and
Q22 for why, and for what evidentiary gap that leaves for the currently-deployed model.

### 11. What are its AUROC/AUPRC values?

**The model actually deployed via `src/api/main.py` today is the 12-feature model (Age
restored) — but no AUROC/AUPRC figures exist for it, on either validation or test, by design
(see Q9/Q10, Q22).** Figures for the 17-feature (original) and 11-feature (superseded 2026-09-22)
models are given below, kept explicitly distinct, per `model_card.md`'s "Performance" sections.
**Nothing below should be read as characterizing the currently-deployed 12-feature model's
AUROC/AUPRC** — that evidence does not exist.

17-feature model, per-class, one-vs-rest, validation set (`model_card.md`, "Performance —
17-Feature Model", citing `reports/full_evaluation_3class.md`):

| Class | AUROC | AUPRC |
|---|---:|---:|
| Low | 0.8745 | 0.8556 |
| Medium | 0.8517 | 0.7699 |
| High | 0.9850 | 0.9511 |
| **Macro average** | **0.9037** | **0.8589** |

17-feature model, real, one-time **test-set** values, first disclosed test-set use, 2026-09-15
(`model_card.md`, "Final Test-Set Evaluation", citing `reports/final_test_evaluation.md`):

| Class | AUROC (test) | AUPRC (test) | Gap vs. validation |
|---|---:|---:|---:|
| Low | 0.8798 | 0.8587 | AUROC +0.0053, AUPRC +0.0031 |
| Medium | 0.8607 | 0.7920 | AUROC +0.0090, AUPRC +0.0221 |
| High | 0.9843 | 0.9566 | AUROC −0.0007, AUPRC +0.0055 |
| **Macro average** | **0.9083** | **0.8691** | AUROC +0.0046, AUPRC +0.0102 |

Every gap is small (≤0.022) and mostly in the direction of test performing slightly *better*
than validation — evidence against overfitting during the tuning/analysis process, not evidence
of a problem.

**11-feature model (superseded 2026-09-22, same day), test-set values**, second and final
disclosed test-set use, 2026-09-22 (`model_card.md`, "Performance — 11-Feature Model", citing
`reports/final_test_evaluation_11feature.md`; per-class AUROC/AUPRC was not separately computed
for this model on validation):

| Class | AUROC (test) | AUPRC (test) |
|---|---:|---:|
| Low | 0.8789 | 0.8558 |
| Medium | 0.8587 | 0.7798 |
| High | 0.9856 | 0.9544 |
| **Macro average** | **0.9077** | **0.8633** |

Head-to-head against the 17-feature model's test result: every macro figure moved very slightly
negative (macro AUROC −0.0006, macro AUPRC −0.0058), and Medium-class AUPRC moved −0.0122 — the
one gap that crosses the 0.01 threshold used elsewhere in this project. See Q10 and Q25 for the
full honest verdict on this comparison.

**12-feature model (current, deployed): no AUROC/AUPRC exists, on validation or test.** Only
accuracy, balanced accuracy, macro-F1, and per-class recall were computed
(`reports/feature_addition_age_3class.md`) — see Q12 below for the recall figures, and Q22 for
why this evidentiary gap is a deliberate, disclosed scope decision rather than an oversight.

### 12. What are sensitivity and specificity?

**Sensitivity (= recall) is documented for all three model configurations on validation;
test-set recall exists only for the 17-feature and 11-feature (superseded) models, by design.
Specificity is not documented at all, for any configuration.**

> **Update 2026-09-30 — current model (12-feature XGBoost), nested cross-validation**
> (`reports/nested_cv_12feature_xgb.md`, mean ± std over 5 outer folds; primary estimate):
>
> | Class | Recall, all ages | Recall, ages 18-49 | Recall, validation split |
> |---|---:|---:|---:|
> | Low | 0.7978 ± 0.0150 | 0.8071 ± 0.0199 | 0.7866 |
> | Medium | 0.7609 ± 0.0098 | 0.7532 ± 0.0153 | 0.7397 |
> | High | 0.8771 ± 0.0111 | 0.9087 ± 0.0122 | 0.8970 |
>
> - **High precision:** 0.9759 ± 0.0065.
> - **The priority-review flag** (each fold's own threshold) catches 0.9587 ± 0.0153 of High cases.
> - **Validation's High recall (0.897)** is about 2 points above the nested estimate. That's within
>   the sampling noise of 165 High cases (standard error about 0.026), but the figure to quote is
>   about 0.88.
>
> Specificity is still not computed. The tables below are the Random Forest history.

17-feature model, per-class recall (`model_card.md`, "Performance — 17-Feature Model" and "Final
Test-Set Evaluation" classification reports):

| Class | Recall (validation) | Recall (test) |
|---|---:|---:|
| Low | 0.7545 | 0.7772 |
| Medium | 0.7652 | 0.7814 |
| High | 0.8970 | 0.8994 |
| Macro average | 0.8056 | 0.8193 |

**11-feature model (superseded 2026-09-22, same day)**, per-class recall
(`reports/feature_reduction_3class.md`, `reports/final_test_evaluation_11feature.md`):

| Class | Recall (validation) | Recall (test) |
|---|---:|---:|
| Low | 0.7545 | 0.7695 |
| Medium | 0.7737 | 0.7843 |
| High | 0.8970 | 0.8994 |
| Macro average | 0.8084 | 0.8177 |

**12-feature model (current, deployed) — validation only, no test-set column** (deliberate, see
Q9/Q10, Q22), per-class recall (`reports/feature_addition_age_3class.md`):

| Class | Recall (validation) | Recall (test) |
|---|---:|---:|
| Low | 0.7506 | *(not evaluated — by design)* |
| Medium | 0.7709 | *(not evaluated — by design)* |
| High | 0.8970 | *(not evaluated — by design)* |
| Macro average | 0.8062 | *(not evaluated — by design)* |

For the 17-feature and 11-feature models, test-set recall is slightly higher than validation for
every class — consistent with the no-overfitting finding elsewhere in this report. That
comparison cannot be made for the 12-feature model because no test-set recall exists for it.
Neither `model_card.md` nor `CLAUDE.md` reports a specificity (true-negative rate) figure for any
class, on either split, for any configuration — it is not computed or cited anywhere in either
document. This is an explicit gap rather than an omission on my part: it has not been documented,
so no number can honestly be given here.

### 13. Is it calibrated?

**No, not well, across most of the probability range — and this is explicitly documented rather
than assumed.** Phase 15 was completed for all 3 classes on this target (`model_card.md`,
"Calibration Status", citing `reports/calibration_3class.md` and
`reports/calibration_3class_full.md`):

| Class | Brier score | Count-weighted gap | Verdict |
|---|---:|---:|---|
| High | 0.013128 | +0.0333 | Over-confident overall, not uniformly |
| Low | 0.151839 | −0.0238 | Roughly calibrated on average, not uniformly |
| Medium | 0.164572 | −0.0095 | Roughly calibrated on average, not uniformly |

The weighted averages hide real per-bin miscalibration: High is over-confident below predicted
P≈0.3 (90.7% of the validation set sits there); Low and Medium are under-confident at high
predicted probabilities — most notably Medium's single most populated bin ([0.6,0.7), 436 of 1650
rows) predicts 65.0% but the actual rate is 78.7%, a 13.7-point gap on over a quarter of the
validation set. **Recommendation on record but not implemented:** Platt scaling or isotonic
regression per class. This has **not** been done for the 5-class Severity target at all.

### 14. How uncertain is it?

Uncertainty is handled via one specific, documented mechanism (Phase 16) — not via a general
uncertainty quantification method like ensembling or conformal prediction, neither of which has
been implemented. The production rule: flag a row **"borderline — recommend review"** if **P(High)
≥ 0.10** (the ~10% marginal base rate of High), regardless of the predicted class
(`model_card.md`, "Uncertainty / Abstention Mechanism", citing `reports/uncertainty_flagging.md`).
Measured effect on the validation set (n=1650):
- 346/1650 (20.97%) of rows flagged overall
- 9/17 (52.94%) of a known set of True-High/Predicted-Medium misses get caught by this flag
- 321/346 (92.77%) of flagged rows were already correctly classified (an accepted cost, since the
  rule's purpose is reprioritizing review attention, not gatekeeping it — every case is reviewed
  regardless of the flag)

This has **not** been done for the 5-class Severity target.

### 15. How does it perform across subgroups?

**Only one subgroup dimension — Occupation — has been evaluated. No age, gender, or other
demographic subgroup fairness analysis has been performed on model *outputs*** (Gender was
examined only as a candidate *input feature* and dropped for having no signal — that is a
feature-selection finding, not a subgroup-fairness evaluation, and the two should not be
conflated).

Occupation-subgroup results, validation set (`model_card.md`, "Fairness Findings", citing
`reports/fairness_report_3class.md`): overall recall by class is Low 0.7545, Medium 0.7652, High
0.8970. High-class precision is 1.00 in 12 of 13 occupations (only Doctor is lower, at 0.9167).
Two occupations were flagged for a High-class recall gap ≥0.10 below the overall average:

| Occupation | Support (High) | Subgroup recall | Gap | Confidence |
|---|---:|---:|---:|---|
| Scientist | 16 | 0.7500 | 0.1470 | Adequate sample |
| Engineer | 14 | 0.7857 | 0.1113 | **Low — n<15** |

The Scientist flag was investigated directly and **found not to replicate**: the feature
differences that would explain it (Stress Level, Sleep Hours, Therapy Sessions) are not
statistically significant on the validation set (Welch t-test p=0.36 for 3-class), and the full
dataset shows essentially no Occupation↔Stress Level relationship at all (ANOVA F=0.47, p=0.93).
The documented conclusion is that this gap is **likely validation-set sampling noise, not a real
fairness issue**, pending a larger sample. This is an honest, checked finding — not a dismissal
without evidence.

### 16. How robust is it?

**Tested for the 3-class target (Phase 19), and measurably fragile in specific, documented ways
— not "untested," and not "robust."** (`CLAUDE.md`, Pipeline Status; `reports/robustness_3class.md`,
run against the saved final model, validation split only.)

- **Missing-feature knockout** (each feature replaced with its train-set mean/mode in turn):
  losing Stress Level alone collapses balanced accuracy from 0.8056 to 0.4291 (a 0.3765-point
  drop); losing Therapy Sessions alone drops it to 0.5590 (a 0.2465-point drop). Every other
  feature's removal costs at most ~0.01 balanced-accuracy points. The model's two most important
  SHAP features are also its two biggest single points of failure.
- **Gaussian noise** (added to all numeric features simultaneously, scaled to each feature's
  train-set standard deviation): even a modest 0.25× noise level costs 0.0323 balanced-accuracy
  points; at 1× std, performance collapses to 0.5560 (from 0.8056); at 2×, to 0.4480.
- **Out-of-range/invalid inputs** (qualitative): no crashes on any tested case, but — as of when
  this test was run — the pipeline silently accepted and confidently predicted on physically
  impossible values (Age=-5, Stress Level=250, Heart Rate=9000) with no error or warning. **This
  specific gap has since been fixed**: `src/inference/input_validation.py` now rejects
  physically-implausible values before they reach the model, verified against these exact inputs
  (see Q18 and Q21). It is wired into `src/inference/predict_single.py` only — not into every
  conceivable entry point.
- **Distribution shift** (Stress Level shifted by a constant across all validation rows): shifting
  down 3 points nearly halves the predicted-High rate (0.0903 → 0.0418); shifting up 1-3 points
  changes nothing at all (stays at 0.0903) — an asymmetry `reports/robustness_3class.md` notes as
  "not yet root-caused."
- **Not testable with this dataset, and explicitly marked as such rather than skipped**: wording
  changes (no text fields), site changes (single data source, no site identifier), temporal
  changes (no timestamp column).

This has **not** been done for the 5-class Severity target.

### 17. What happens on OOD inputs?

**Unknown — not tested or documented anywhere.** Neither `model_card.md` nor `CLAUDE.md`
describes an out-of-distribution detection mechanism, an OOD evaluation, or any stated behavior
for inputs outside the training distribution (e.g., extreme feature values, unusual feature
combinations, or categorical values not seen during training). This question cannot be answered
from the documented evidence; it should be treated as an open risk, not a "should be fine"
assumption.

### 18. What are the major failure modes?

Documented, evidence-backed failure modes:
- **Low↔Medium confusion is the dominant error mode.** Nearly all misclassification happens
  between these two classes; High is rarely confused with either (`model_card.md`, "Performance").
- **Heavy single-feature dependency.** 17.6 of the model's ~30.6-point accuracy gain over the
  majority baseline comes from Stress Level alone; the model is not drawing on broad,
  independent multi-feature signal to the degree a clinical deployment would ideally require
  (`model_card.md`, "Known Limitations" #2).
- **Single-feature fragility under missing data (Phase 19, `reports/robustness_3class.md`) —
  open, not fixed.** Losing Stress Level alone (simulated via train-mean imputation) collapses
  balanced accuracy from 0.8056 to 0.4291; losing Therapy Sessions alone drops it to 0.5590.
  Directly follows from the dependency above, but is a distinct, separately-measured finding
  about what happens when that one feature is unavailable at inference time, not just about
  training-time importance.
- **Sensitivity to input noise (Phase 19)** — open, not fixed. Gaussian noise at just 0.25× each
  numeric feature's train std already costs 0.0323 balanced-accuracy points; at 1× std,
  performance collapses to 0.5560.
- **Unexplained asymmetric sensitivity to Stress Level distribution shift (Phase 19)** — open,
  not fixed, and not yet root-caused. Shifting Stress Level down 3 points nearly halves the
  predicted-High rate; shifting it up 1-3 points changes nothing at all.
- **Miscalibrated probabilities**, especially Medium's most populated probability bin
  under-stating true likelihood by 13.7 points (see Q13).
- **Small-sample subgroup instability** — occupation-level High-class recall figures are computed
  on samples as small as 9-18 rows, so subgroup metrics (including the two flags above) are
  inherently noisy (`model_card.md`, "Known Limitations" #3).
- **The uncertainty flag has a high false-flag rate by design (92.77%)** — most flagged rows were
  already correct, so the mechanism trades review workload for coverage of misses (see Q14).
- ~~No input validation~~ **— fixed.** Phase 19 originally found the pipeline silently accepted
  physically impossible values (Age=-5, Stress Level=250, Heart Rate=9000) and predicted on them
  anyway with no warning. `src/inference/input_validation.py` now rejects such values before they
  reach the model, verified against these exact inputs. This is the one Phase 19 finding that has
  been closed; the four items above it remain open.

### 19. Was external validation performed?

**No.** All reported evaluation — baselines, tuning, full evaluation, calibration, uncertainty
flagging, SHAP, fairness — is computed on an internal train/validation/test split of the single
`mindcare_dataset_final.csv` file, which is itself very likely synthetic. No external dataset,
no second data source, and no cross-institution or cross-population validation is mentioned
anywhere in `model_card.md` or `CLAUDE.md`.

### 20. Was clinical evaluation performed?

**No.** There is no documented prospective study, clinician-in-the-loop trial, comparison of
model-assisted vs. unassisted psychologist decisions, or any evaluation involving real patient
outcomes. `model_card.md`'s own status line states plainly: "Prototype / research model. Not
clinically validated," and Engineering Rule 7 in `CLAUDE.md` requires that this never be
represented otherwise.

### 21. What safety mechanisms exist?

- **Mandatory psychologist review is the core safety mechanism**, stated as a non-negotiable,
  critical workflow constraint: the model's output never reaches a patient directly and can never
  bypass psychologist review (`CLAUDE.md`, "What this is"; `model_card.md`, "Intended Use").
- **The Phase 16 uncertainty flag** reprioritizes (not gatekeeps) psychologist review attention
  toward rows the model considers plausibly High-risk even when it didn't predict High — an
  additional layer on top of, not a replacement for, universal review (see Q14).
- **Process-level safeguards documented in `CLAUDE.md`'s Engineering Rules**: no metric may be
  fabricated; preprocessing/tuning must never touch val/test data; every reported number must
  carry seed/hyperparameter/dataset-version provenance; and any push toward a specific accuracy
  target must be pushed back on and explained. These are documented practices, not technical
  safety mechanisms in the deployed model itself.
- **Input validation** (`src/inference/input_validation.py`) — added after Phase 19 robustness
  testing found the pipeline silently accepted physically impossible values (e.g. Age=-5, Stress
  Level=250, Heart Rate=9000) and predicted on them anyway with no warning. Two-tier bounds per
  numeric feature: physically-impossible values are rejected with a clear error; valid-but-
  outside-the-training-distribution values are allowed through with a warning. Verified against
  the exact inputs that exposed the original gap. Currently wired into
  `src/inference/predict_single.py` only — not a universal gate in front of every possible
  entry point to the model.
- No OOD detection and no confidence-based abstention beyond the Phase 16 uncertainty flag are
  documented.

### 22. What are the limitations?

Directly from `model_card.md`'s "Known Limitations" section, plus the gaps surfaced by this
report (Q16, Q17, Q19, Q20). **Scope note: unless stated otherwise, "the model" below is the
current, deployed 12-feature 3-class model (Age restored, as of 2026-09-22) — see Q3, Q9/Q10.**
1. Training data is very likely synthetic — no performance figure here is clinically validated.
2. Even for the 3-class target, over half (17.6 of ~30.6 points) of the model's improvement over
   the majority baseline comes from one feature, Stress Level. **This dependency figure was
   computed against the original 17-feature model (Phase 11) and was not recomputed after either
   2026-09-22 feature-set change (17→11, then 11→12 with Age restored); Stress Level was not
   affected by either change, so the dependency is expected to persist but is unverified for the
   current 12-feature model** (`model_card.md`, "Known Limitations" #2).
3. Imbalanced target with small per-occupation High-class samples (9-18 rows) — subgroup metrics
   are inherently noisy at this scale.
4. Predicted probabilities are not well-calibrated across the full range for any class. (This
   analysis, like most Phase 15-19 analyses below, was run against the 17-feature model and has
   not been separately re-run for the 11-feature or 12-feature models — see item 7.)
5. The uncertainty flag has a 92.77% false-flag rate by design.
6. **The 3-class test set has been evaluated twice, and is fully spent — for the 17-feature and
   11-feature configurations only.** First (2026-09-15, 17-feature model) — see Q11/Q12/Q25.
   Second (2026-09-22, 11-feature model, since superseded) — justified because it evaluated a
   genuinely new feature-set configuration, not a re-check of the same model. Both uses are
   disclosed and kept distinct from validation figures throughout. **No further test-set
   evaluation is permitted for the 17-feature or 11-feature configurations** (Q10, Q25). **The
   current, deployed 12-feature model (Age restored) deliberately has no test-set evaluation at
   all** — restoring Age was a clinical/UX decision, not a performance claim, so it was not
   treated as justifying a third one-way-door use. This is a genuine, disclosed evidentiary gap
   for the currently-deployed model, not an oversight (Q9/Q10).
7. Phase 12 (advanced models) and Phase 19 (robustness testing) are done for the 3-class target,
   but **only against the original 17-feature model** — see Q16 and Q18 for the Phase 19
   findings, several of which remain open (Stress Level/Therapy Sessions single-feature
   fragility, noise sensitivity, an unexplained distribution-shift asymmetry). **None of Phases
   15-19 (calibration, uncertainty flagging, SHAP, fairness, robustness) have been re-run
   end-to-end against the 11-feature or 12-feature models** — for the 12-feature model
   specifically, the currently-deployed one, only headline accuracy/balanced-accuracy/macro-F1/
   recall metrics exist, on validation only (Q9/Q10, Q11/Q12). Phase 15 (calibration) and Phase
   16 (uncertainty) are also still not done for the 5-class reference target, which remains on
   the original 17 features throughout.
8. This is a prototype/research model and must never be represented as having clinical
   diagnostic validity.
9. Phase 19 robustness testing has been performed for the 17-feature configuration of the 3-class
   target and found real, specific fragilities (Q16, Q18) — one of which (missing input
   validation) has since been fixed (Q21) and re-verified for the current 12-feature input set,
   including Age's restored bounds (`src/inference/input_validation.py`). The robustness findings
   themselves have not been re-tested against the 11-feature or 12-feature models. OOD handling,
   external validation, and clinical evaluation remain entirely unperformed (Q17, Q19, Q20).
10. *(Surfaced here.)* Subgroup fairness has only been checked along one dimension (Occupation),
    and only for the 17-feature model; no age, gender, or other demographic fairness evaluation
    of model outputs exists, and the fairness check has not been re-run for the 11-feature or
    12-feature models. **Updated 2026-09-28:** both 12-feature models now have occupation,
    age-band and gender fairness checks on validation data (`reports/model_comparison_12feature.md`).
    Most occupations still have too few High cases (under 15) for a reliable High-recall
    comparison.
11. The choice of Random Forest over XGBoost is now backed by a documented rationale
    (`model_card.md`, "Model Selection Rationale"), but that rationale was written up *after*
    the model was already selected, and the full SHAP/calibration/uncertainty/fairness analysis
    suite has not been re-run on XGBoost for comparison — the selection has not been validated
    against an equivalent depth of analysis on the alternative (Q10). This is a separate question
    from the two later feature-set changes (17→11, then 11→12 with Age restored), which each
    kept Random Forest and only changed the input columns (Q9/Q10). **Resolved 2026-09-28:**
    the full suite was run on both 12-feature models, and the evidence favoured XGBoost, which was
    adopted (update note at the top).
12. *(Surfaced here.)* **The current, deployed 12-feature model (Age restored) has strictly less
    evidentiary depth than either the 17-feature or 11-feature configurations that preceded it**
    — validation-only headline metrics exist and nothing else (items 4, 6, 7, 9, 10 above). This
    is a deliberate, disclosed scope decision tied to the clinical/UX nature of the Age-restoration
    decision (Q9/Q10), not an unnoticed gap — but it does mean the model actually running in
    production today has been evaluated less thoroughly than its two immediate predecessors.
    **Resolved 2026-09-28:** the deployed model (now XGBoost) has the full validation-set analysis
    suite. It still has no test-set number, by design.
13. *(Added 2026-09-30.)* **Nested cross-validation doesn't cover the decisions made outside it.**
    The nested CV (`reports/nested_cv_12feature_xgb.md`) redoes the preprocessing, tuning and
    threshold choice inside every fold, so those steps are estimated honestly. But these were all
    decided on the same train + validation data, outside the loop:
    - the 17 → 11 → 12 feature reduction;
    - choosing XGBoost over Random Forest;
    - the 158/165 flag-coverage target;
    - the Low/Medium/High label boundaries;
    - the 18–49 age limit.

    The nested figures describe **re-running this pipeline**, not the whole chain of decisions, and
    can still be optimistic about that chain. **No test-set number exists for the current model.**

### 23. What claims can we legitimately make?

- On an internal, held-out validation split of this specific (very likely synthetic) dataset, the
  tuned Random Forest — across its original 17-feature configuration, the superseded 11-feature
  configuration, and the current 12-feature configuration (Age restored) — meaningfully
  outperforms a majority-class baseline (17-feature: balanced accuracy 0.8056 vs. 0.3333,
  macro-F1 0.8177 vs. 0.2136; 11-feature: balanced accuracy 0.8084, macro-F1 0.8204; 12-feature:
  balanced accuracy 0.8062, macro-F1 0.8182). The current 12-feature **XGBoost** model does
  likewise on validation (balanced accuracy 0.8078, macro-F1 0.8171), statistically tied with the
  Random Forest in 5-fold CV. Its primary estimate is **nested cross-validation** (added
  2026-09-30): balanced accuracy 0.8119 ± 0.0057, macro-F1 0.8244 ± 0.0064, accuracy
  0.7904 ± 0.0094 and High recall 0.8771 ± 0.0111, with the whole pipeline rebuilt inside each
  fold. The legitimate claim is about **re-running this pipeline** on this dataset, not the full
  chain of decisions (Q22 item 13). The disclosed held-out **test** evaluations confirm
  this wasn't an artifact of validation-set overfitting for the 17-feature and 11-feature
  configurations — 17-feature test balanced accuracy 0.8193 (+0.0137 vs. validation), 11-feature
  test balanced accuracy 0.8177 (+0.0093 vs. validation) (Q11, Q12). **This confirmation does not
  exist for the current 12-feature model** — no test-set evaluation was performed for it, by
  design (Q9/Q10, Q22).
- When the model predicts High, it is very rarely wrong (0.9933 precision overall on 17-feature
  validation, 0.9935 on 17-feature test, 0.9870 on 11-feature test; 1.00 precision in 12 of 13
  occupation subgroups for the 17-feature model). Per-class precision has not been separately
  computed for the 12-feature model (Q11/Q12).
- **The 17→11 feature reduction was checked honestly against held-out test data, not just
  validation — and the check surfaced a real, if small, direction-reversal rather than confirming
  the validation-only result.** On validation, the 11-feature model looked marginally *better*
  than the 17-feature model. On test, that reverses: every 11-feature headline metric is very
  slightly *below* the 17-feature model's test result (deltas of −0.0006 to −0.0058), with
  Medium-class AUPRC the one metric crossing the 0.01 threshold (Q10, Q11/Q12, Q25). **This
  disagreement was reported plainly rather than resolved in the more favorable direction** — the
  honest net conclusion is "no meaningful cost either way," not "the reduction improved the
  model," even though that is what validation alone had suggested. This is itself evidence of
  the project's intellectual honesty: a result that could have been quietly left at the
  validation-only, more flattering reading was instead checked further and reported as found.
- Four post-selection improvement attempts against the 17-feature model (feature engineering, an
  RF+XGBoost ensemble, probability calibration, and calibration combined with the
  uncertainty-flagging threshold), plus a fifth against the 11-feature model (dropping Caffeine
  Intake), were tested honestly on validation data and none were adopted where the evidence
  didn't support adoption — including one case where combining two individually-reasonable
  changes was found to interact badly and was explicitly rejected on that basis, and one case
  where a real per-class cost (Medium-class recall −1.56 points) was surfaced even though
  aggregate metrics alone would have looked acceptable (`model_card.md`, "Attempted Improvements
  (Not Adopted)"). The deployed model is unmodified by any of these five experiments; the
  onboarding-simplification goal behind the caffeine experiment was instead served by changing
  *how* that one feature is collected, not by dropping it. Age's later restoration was a separate,
  sixth, adopted decision — not a rejected experiment — and is documented distinctly in
  `model_card.md`'s "Features" section, not "Attempted Improvements" (Q9/Q10).
- The model's behavior has been examined honestly and in reasonable depth for a prototype: full
  per-class AUROC/AUPRC, a 10-bin calibration analysis per class with documented over/under-
  confidence patterns, a threshold-justified uncertainty-flagging mechanism, SHAP-based feature
  attribution, and an occupation-subgroup fairness check with at least one flagged finding
  actively investigated (and found not to replicate) rather than left unexamined. **This full
  analysis depth exists only for the superseded 17-feature model. The 11-feature model (also
  superseded) has headline metrics plus two test evaluations. The current, deployed 12-feature
  model has the least depth of the three: headline validation metrics only, no test-set
  evaluation at all** (Q22 items 6, 7, 12).
- The project has an explicit, enforced workflow constraint requiring psychologist review of
  every prediction before it reaches a patient.

### 24. What claims can we NOT make?

- **No claim of clinical diagnostic validity** — explicitly prohibited by `CLAUDE.md` Engineering
  Rule 7.
- **No claim of external validity** — the model has never been evaluated on data outside this one
  (likely synthetic) source file (Q19).
- **No claim that the current model's High recall is 0.897** *(added 2026-09-30)*. That figure is
  from a single validation split. The nested cross-validation estimate is 0.8771 ± 0.0111, so
  quote about 0.88. Nor can the nested figures be presented as a test of the whole decision chain
  (Q22 item 13).
- **No claim of clinical effectiveness** — no clinical evaluation, trial, or real-outcome
  comparison has occurred (Q20).
- **No claim the model is calibrated** — it is measurably not, across most of the probability
  range for Low and Medium, and below P≈0.3 for High (Q13). (Calibration was measured against the
  17-feature model; not re-measured for the 11-feature or 12-feature models.)
- **No claim of robustness** to noisy or missing inputs — the opposite is documented for the
  17-feature model: it is measurably fragile to losing or corrupting its top 1-2 features, and to
  realistic-magnitude input noise (Q16, Q18). No claim of robustness to adversarial inputs
  specifically — that was not tested. **Robustness has not been separately re-tested for the
  12-feature model actually deployed** (or for the 11-feature model before it).
- **No claim about behavior on out-of-distribution inputs** — untested and undocumented (Q17).
- **No claim of fairness across patient subgroups in general** — only Occupation has been
  checked, only for the 17-feature model, and even that check surfaced one low-confidence flag
  that hasn't been resolved with more data, plus one flag investigated and attributed to sampling
  noise rather than confirmed absent (Q15).
- **No claim that dropping the 6 originally-removed features, or that the 11-feature model
  generally, was an *improvement*** — the honest, tested result on held-out data was a tiny,
  direction-reversing regression versus the 17-feature model, not a gain (Q10, Q11/Q12, Q25). The
  legitimate claim was narrower: "no meaningful cost," in exchange for a real product/UX benefit
  (fewer required fields). That configuration is now superseded.
- **No claim that restoring Age was a performance-driven decision, or that it was validated
  against held-out test data** — it was a clinical/UX decision, deliberately checked only on
  validation (near-zero cost measured, `reports/feature_addition_age_3class.md`), with no
  test-set confirmation performed or planned (Q9/Q10, Q22 item 6). The legitimate claim is
  narrower still than the 17→11 case: "measured not to be harmful on validation," not "confirmed
  on held-out data" and not "an improvement."
- **No claim that the reported accuracy reflects broad, robust multi-feature reasoning** for the
  5-class Severity target specifically — that model is, by the project's own ablation finding,
  overwhelmingly dependent on a single feature.
- **No claim of autonomous decision-making capability** — the model must never be deployed in a
  way that bypasses psychologist review.

### 25. What further evidence is required before clinical deployment?

Based strictly on the gaps this report surfaced:
1. **Resolution of the open Phase 19 robustness findings for the 3-class target** — Stress
   Level/Therapy Sessions single-feature fragility, sensitivity to input noise, and the
   unexplained asymmetric response to Stress Level distribution shift (Q16, Q18) — plus **Phase
   19 robustness testing for the 5-class target**, which has not been started at all.
2. **OOD detection and evaluation** — currently nonexistent.
3. **External validation** on a data source independent of `mindcare_dataset_final.csv`,
   ideally real (non-synthetic) patient data.
4. **Formal clinical evaluation** — a prospective, clinician-in-the-loop study comparing
   model-assisted to unassisted outcomes, before any deployment claim can be made.
5. **A resolved plan for probability calibration, not just a tested-and-shelved experiment.**
   Isotonic calibration was tested (`model_card.md`, "Attempted Improvements") and does measurably
   improve calibration quality (mean Brier 0.1098 → 0.1019) with negligible classification impact
   — but adopting it as-is was found to silently cut the uncertainty-flagging mechanism's coverage
   of known boundary-ambiguous cases from 9/17 to 3/17, because the 0.10 flagging threshold was
   tuned against the uncalibrated model. Before calibration can be adopted, the flagging threshold
   would need to be re-swept against calibrated probabilities and re-validated — this has not been
   done. Needed before any probability is shown to a psychologist as if it were a reliable
   confidence figure.
6. **Broader subgroup fairness analysis** — beyond Occupation, at minimum age and gender (gender
   was excluded as a predictive feature for lack of signal, which is a separate question from
   whether the model's *errors* are distributed fairly by gender). *Partly done 2026-09-28:* age
   and gender checks exist for both 12-feature models on validation data. Nothing has been
   checked on real data.
7. **A re-run of the full Phase 15-18 analysis stack (SHAP, calibration, uncertainty, fairness)
   on tuned XGBoost**, to validate the now-documented Random Forest selection rationale (Q10)
   against an equivalent depth of evidence on the alternative — the rationale exists, but was
   written retroactively and has not been tested against that alternative's actual behavior.
   **Done 2026-09-28** (`reports/model_comparison_12feature.md`). The evidence led to adopting
   XGBoost.
8. **Resolution of the Stress-Level single-feature dependency**, particularly for the 5-class
   Severity target, before that target (if retained at all) is used in any deployment context.
9. **Completion of Phase 15 (calibration) and Phase 16 (uncertainty) for the 5-class target**, if
   it continues to be maintained as a reference/secondary target.
10. ~~A final, one-time evaluation on the untouched test set~~ **— done, twice, for the
    17-feature and 11-feature configurations, both now fully spent.** First, 2026-09-15
    (`reports/final_test_evaluation.md`; Q11, Q12): the 17-feature model, results consistent with
    validation (no gap ≥0.03), no retraining or model change triggered. Second, 2026-09-22
    (`reports/final_test_evaluation_11feature.md`; Q10, Q11, Q12): the 11-feature model (since
    superseded) — justified as a genuinely new configuration, not a re-check of the same model —
    results showed a small, consistent regression versus the 17-feature model's test performance
    that validation alone had not predicted, again with no retraining or model change triggered
    in response. **Both uses are complete and disclosed; the 3-class test set must not be
    evaluated again for either of those two configurations.** The current, deployed 12-feature
    model (Age restored) was deliberately NOT given a third test-set evaluation — see item 12
    below, which is a distinct, still-open item, not resolved by this one. The remaining gap for
    this item specifically is the analogous evaluation for the 5-class target, if that target is
    ever finalized (it retains its own, never-touched test split — see Q7).
11. **Re-running the Phase 15-19 analysis stack (calibration, uncertainty flagging, SHAP,
    fairness, robustness) against the current 12-feature model.** All of that depth currently
    exists only for the superseded 17-feature model (Q22 item 7, Q23) — the model actually
    deployed today has only headline accuracy/balanced-accuracy/macro-F1/recall figures, on
    validation only, with no test-set evaluation at all. This is a gap in evidentiary depth for
    the currently-deployed configuration, separate from the earlier items in this list.
12. *(Surfaced here.)* **A deliberate decision on whether the 12-feature model's clinical/UX
    justification for Age is sufficient on its own, or whether a third, disclosed test-set use
    should eventually be authorized for it.** As documented (Q9/Q10, Q22 item 6), the current
    position is that Age's restoration did not require test-set confirmation because it was not
    a performance claim — but this report surfaces that position explicitly so it can be
    revisited by a human decision-maker rather than silently treated as settled by default.

---

## Source Traceability

Every answer above is drawn from [`docs/model_card.md`](model_card.md) and
[`CLAUDE.md`](../CLAUDE.md), cross-checked against the specific report files each of those
documents cites (`reports/baseline_results_3class.json`, `reports/tuning_results_3class.json`,
`reports/full_evaluation_3class.md`, `reports/calibration_3class.md`,
`reports/calibration_3class_full.md`, `reports/uncertainty_flagging.md`,
`reports/threshold_sweep_high.md`, `reports/shap_summary_3class.md`,
`reports/shap_full_ranking_3class.md`, `reports/fairness_report_3class.md`,
`reports/advanced_models_3class.md`, `reports/robustness_3class.md`,
`reports/feature_engineering_3class.md`, `reports/ensemble_3class.md`,
`reports/postprocessing_3class.md`, `reports/calibrated_uncertainty_flagging_3class.md`,
`reports/final_test_evaluation.md`, `reports/feature_reduction_3class.md`,
`reports/feature_reduction_caffeine_3class.md`, `reports/final_test_evaluation_11feature.md`,
`reports/feature_addition_age_3class.md`,
`src/inference/input_validation.py`). No number in this report was invented, estimated, or newly
computed — where a question cannot be answered from these sources (Q4, Q12's specificity half,
Q17, Q19, Q20), this report says so explicitly rather than filling the gap.
