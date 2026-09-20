# Trustworthiness Report — MindCare Anxiety Level Classifier (3-Class)

Answers to the 25 Phase 35 questions, pulled only from
[`docs/model_card.md`](model_card.md) and [`CLAUDE.md`](../CLAUDE.md), each verified against the
report file(s) those documents cite. Where something has not actually been done, this report says
so explicitly rather than skipping the question or implying otherwise.

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

`data/raw/mindcare_dataset_final.csv` — ~11,000 rows, 23 columns. 17 of those columns are used as
model features (11 numeric + 6 categorical); the rest are the target columns (Severity, Anxiety
Level) or columns dropped for leakage reasons (`model_card.md`, "Training Data", "Features").

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

The **tuned Random Forest** — hyperparameters `n_estimators=200, max_depth=10,
min_samples_split=10, min_samples_leaf=4, max_features='sqrt', class_weight='balanced',
random_state=42` (`model_card.md`, "Performance", citing `reports/tuning_results_3class.json`).
This is the model used for every subsequent analysis in the model card: full evaluation,
calibration, uncertainty flagging, SHAP, and fairness.

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
reasonable but not rigorously defended.

### 11. What are its AUROC/AUPRC values?

Per-class, one-vs-rest, validation set (`model_card.md`, "Performance", citing
`reports/full_evaluation_3class.md`):

| Class | AUROC | AUPRC |
|---|---:|---:|
| Low | 0.8745 | 0.8556 |
| Medium | 0.8517 | 0.7699 |
| High | 0.9850 | 0.9511 |
| **Macro average** | **0.9037** | **0.8589** |

The model card also reports the real, one-time **test-set** values (`model_card.md`, "Final
Test-Set Evaluation", citing `reports/final_test_evaluation.md`) — kept explicitly distinct from
the validation numbers above, not conflated with them:

| Class | AUROC (test) | AUPRC (test) | Gap vs. validation |
|---|---:|---:|---:|
| Low | 0.8798 | 0.8587 | AUROC +0.0053, AUPRC +0.0031 |
| Medium | 0.8607 | 0.7920 | AUROC +0.0090, AUPRC +0.0221 |
| High | 0.9843 | 0.9566 | AUROC −0.0007, AUPRC +0.0055 |
| **Macro average** | **0.9083** | **0.8691** | AUROC +0.0046, AUPRC +0.0102 |

Every gap is small (≤0.022) and mostly in the direction of test performing slightly *better*
than validation — evidence against overfitting during the tuning/analysis process, not evidence
of a problem.

### 12. What are sensitivity and specificity?

**Sensitivity (= recall) is documented for both validation and test; specificity is not
documented at all.** Per-class recall (`model_card.md`, "Performance" and "Final Test-Set
Evaluation" classification reports):

| Class | Recall (validation) | Recall (test) |
|---|---:|---:|
| Low | 0.7545 | 0.7772 |
| Medium | 0.7652 | 0.7814 |
| High | 0.8970 | 0.8994 |
| Macro average | 0.8056 | 0.8193 |

Test-set recall is slightly higher than validation for every class — consistent with the
no-overfitting finding elsewhere in this report. Neither `model_card.md` nor `CLAUDE.md` reports
a specificity (true-negative rate) figure for any class, on either split — it is not computed or
cited anywhere in either document. This is an explicit gap rather than an omission on my part: it
has not been documented, so no number can honestly be given here.

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
report (Q16, Q17, Q19, Q20):
1. Training data is very likely synthetic — no performance figure here is clinically validated.
2. Even for the 3-class target, over half (17.6 of ~30.6 points) of the model's improvement over
   the majority baseline comes from one feature, Stress Level.
3. Imbalanced target with small per-occupation High-class samples (9-18 rows) — subgroup metrics
   are inherently noisy at this scale.
4. Predicted probabilities are not well-calibrated across the full range for any class.
5. The uncertainty flag has a 92.77% false-flag rate by design.
6. The test set was evaluated exactly once (2026-09-15) — see Q11/Q12/Q25. Test figures are
   reported and kept distinct from validation figures throughout; this was a single one-way-door
   check, not repeated or cross-validated evaluation, and it must not be repeated.
7. Phase 12 (advanced models) and Phase 19 (robustness testing) are now done for the 3-class
   target — see Q16 and Q18 for the Phase 19 findings, several of which remain open (Stress
   Level/Therapy Sessions single-feature fragility, noise sensitivity, an unexplained
   distribution-shift asymmetry). Phase 15 (calibration) and Phase 16 (uncertainty) are still not
   done for the 5-class reference target.
8. This is a prototype/research model and must never be represented as having clinical
   diagnostic validity.
9. Phase 19 robustness testing has been performed for the 3-class target and found real,
   specific fragilities (Q16, Q18) — one of which (missing input validation) has since been
   fixed (Q21). OOD handling, external validation, and clinical evaluation remain entirely
   unperformed (Q17, Q19, Q20).
10. *(Surfaced here.)* Subgroup fairness has only been checked along one dimension (Occupation);
    no age, gender, or other demographic fairness evaluation of model outputs exists.
11. The choice of Random Forest over XGBoost is now backed by a documented rationale
    (`model_card.md`, "Model Selection Rationale"), but that rationale was written up *after*
    the model was already selected, and the full SHAP/calibration/uncertainty/fairness analysis
    suite has not been re-run on XGBoost for comparison — the selection has not been validated
    against an equivalent depth of analysis on the alternative (Q10).

### 23. What claims can we legitimately make?

- On an internal, held-out validation split of this specific (very likely synthetic) dataset, the
  tuned Random Forest meaningfully outperforms a majority-class baseline (balanced accuracy 0.8056
  vs. 0.3333; macro-F1 0.8177 vs. 0.2136). The one-time held-out **test** split confirms this
  wasn't an artifact of validation-set overfitting — test balanced accuracy is 0.8193, macro-F1
  0.8311, both slightly *higher* than validation (Q11, Q12).
- When the model predicts High, it is very rarely wrong (0.9933 precision overall on validation,
  0.9935 on test; 1.00 precision in 12 of 13 occupation subgroups).
- Four post-selection improvement attempts (feature engineering, an RF+XGBoost ensemble,
  probability calibration, and calibration combined with the uncertainty-flagging threshold) were
  tested honestly on validation data and none were adopted where the evidence didn't support
  adoption — including one case where combining two individually-reasonable changes was found to
  interact badly and was explicitly rejected on that basis (`model_card.md`, "Attempted
  Improvements (Not Adopted)"). The deployed model is unmodified by any of them.
- The model's behavior has been examined honestly and in reasonable depth for a prototype: full
  per-class AUROC/AUPRC, a 10-bin calibration analysis per class with documented over/under-
  confidence patterns, a threshold-justified uncertainty-flagging mechanism, SHAP-based feature
  attribution, and an occupation-subgroup fairness check with at least one flagged finding
  actively investigated (and found not to replicate) rather than left unexamined.
- The project has an explicit, enforced workflow constraint requiring psychologist review of
  every prediction before it reaches a patient.

### 24. What claims can we NOT make?

- **No claim of clinical diagnostic validity** — explicitly prohibited by `CLAUDE.md` Engineering
  Rule 7.
- **No claim of external validity** — the model has never been evaluated on data outside this one
  (likely synthetic) source file (Q19).
- **No claim of clinical effectiveness** — no clinical evaluation, trial, or real-outcome
  comparison has occurred (Q20).
- **No claim the model is calibrated** — it is measurably not, across most of the probability
  range for Low and Medium, and below P≈0.3 for High (Q13).
- **No claim of robustness** to noisy or missing inputs — the opposite is documented: the model
  is measurably fragile to losing or corrupting its top 1-2 features, and to realistic-magnitude
  input noise (Q16, Q18). No claim of robustness to adversarial inputs specifically — that was
  not tested.
- **No claim about behavior on out-of-distribution inputs** — untested and undocumented (Q17).
- **No claim of fairness across patient subgroups in general** — only Occupation has been
  checked, and even that check surfaced one low-confidence flag that hasn't been resolved with
  more data, plus one flag investigated and attributed to sampling noise rather than confirmed
  absent (Q15).
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
   whether the model's *errors* are distributed fairly by gender).
7. **A re-run of the full Phase 15-18 analysis stack (SHAP, calibration, uncertainty, fairness)
   on tuned XGBoost**, to validate the now-documented Random Forest selection rationale (Q10)
   against an equivalent depth of evidence on the alternative — the rationale exists, but was
   written retroactively and has not been tested against that alternative's actual behavior.
8. **Resolution of the Stress-Level single-feature dependency**, particularly for the 5-class
   Severity target, before that target (if retained at all) is used in any deployment context.
9. **Completion of Phase 15 (calibration) and Phase 16 (uncertainty) for the 5-class target**, if
   it continues to be maintained as a reference/secondary target.
10. ~~A final, one-time evaluation on the untouched test set~~ **— done, 2026-09-15**
    (`reports/final_test_evaluation.md`; Q11, Q12). Results were consistent with validation (no
    gap ≥0.03) and did not trigger any retraining or model change. This item is complete; the
    3-class test set must not be evaluated again. The remaining gap is the analogous evaluation
    for the 5-class target, if that target is ever finalized.

---

## Source Traceability

Every answer above is drawn from [`docs/model_card.md`](model_card.md) and
[`CLAUDE.md`](../CLAUDE.md), cross-checked against the specific report files each of those
documents cites (`reports/baseline_results_3class.json`, `reports/tuning_results_3class.json`,
`reports/full_evaluation_3class.md`, `reports/calibration_3class.md`,
`reports/calibration_3class_full.md`, `reports/uncertainty_flagging.md`,
`reports/threshold_sweep_high.md`, `reports/shap_summary_3class.md`,
`reports/fairness_report_3class.md`, `reports/advanced_models_3class.md`,
`reports/robustness_3class.md`, `reports/feature_engineering_3class.md`,
`reports/ensemble_3class.md`, `reports/postprocessing_3class.md`,
`reports/calibrated_uncertainty_flagging_3class.md`, `reports/final_test_evaluation.md`,
`src/inference/input_validation.py`). No number in this report was invented, estimated, or newly
computed — where a question cannot be answered from these sources (Q4, Q12's specificity half,
Q17, Q19, Q20), this report says so explicitly rather than filling the gap.
