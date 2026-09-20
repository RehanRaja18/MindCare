# Model Card — MindCare Anxiety Level Classifier (3-Class)

**Model:** Tuned Random Forest (scikit-learn `RandomForestClassifier`)
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
- **Test set:** the 3-class test set was evaluated exactly once, on 2026-09-15, as the final,
  one-way-door check after model selection (`reports/final_test_evaluation.md`; see "Final
  Test-Set Evaluation" below) — it has not been touched since and must not be evaluated again
  without a deliberate new final-model decision. The 5-class Severity test set remains untouched.

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

**17 features total (11 numeric + 6 categorical), identical for both the 3-class and 5-class
targets** — this target change only swaps labels, it does not add, drop, or otherwise touch any
feature (`CLAUDE.md`, "Target change").

- **Numeric (11):** Age, Sleep Hours, Physical Activity (hrs/week), Caffeine Intake (mg/day),
  Alcohol Consumption (drinks/week), Stress Level (1-10), Heart Rate (bpm), Breathing Rate
  (breaths/min), Sweating Level (1-5), Therapy Sessions (per month), Diet Quality (1-10)
- **Categorical (6):** Occupation, Smoking, Family History of Anxiety, Dizziness, Medication,
  Recent Major Life Event
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
this caveat. For the 3-class target, the remaining 16 features carry real, independent predictive
signal even without Stress Level — the 3-class model is a meaningfully more broadly-supported
model than the 5-class one. Stress Level is retained for both targets (clinically plausible,
realistically collectable), but this distinction must be documented wherever either model's
accuracy is reported.

---

## Model Selection Rationale

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

After the final model was selected, four further approaches were tested on validation data —
none were adopted, and none touched the test set:

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

**The deployed model remains the original tuned Random Forest, unmodified, uncalibrated, with
the original 17-feature set and the original 0.10 flagging threshold.** The reported test
performance (accuracy 0.7915, see "Final Test-Set Evaluation" below) reflects exactly this
configuration — none of the four experiments above changed it in any way.

---

## Performance (Phase 14 — `reports/full_evaluation_3class.md`)

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

## Final Test-Set Evaluation (`reports/final_test_evaluation.md`)

Performed exactly once, on 2026-09-15, against the saved final model exactly as-is — no
retraining, tuning, or model-selection change was made in response to these results.

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

Full classification report — **test** (n=1650):

```
              precision    recall  f1-score   support

         Low     0.7987    0.7772    0.7878       781
      Medium     0.7422    0.7814    0.7613       700
        High     0.9935    0.8994    0.9441       169

    accuracy                         0.7915      1650
   macro avg     0.8448    0.8193    0.8311      1650
weighted avg     0.7947    0.7915    0.7926      1650
```

Confusion matrix — **test** (rows = true, columns = predicted, order Low/Medium/High):

```
[[607 174   0]
 [152 547   1]
 [  1  16 152]]
```

**No metric gapped by ≥0.03 between validation and test** — every one of the 20 metrics checked
(headline metrics, per-class AUROC/AUPRC, per-class precision/recall/F1) landed within 0.001–0.023
of its validation counterpart, and test performance was slightly *better* than validation on
nearly every metric except High's AUROC (−0.0007, negligible). This is a clean result: no
evidence of overfitting to the validation split across the tuning, calibration, SHAP, fairness,
and robustness work in Phases 11-19. These test-set figures are kept distinct from the
validation-set figures above throughout this card — both are reported, never conflated.

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
   require, even though this is a materially smaller dependency than the 5-class target's.
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
   now rejects physically impossible values (e.g. Age=-5, Stress Level=250, Heart Rate=9000)
   before they reach the model — added specifically because Phase 19 found the pipeline
   previously accepted such values silently and produced a confident-looking prediction anyway.
   Only wired into `src/inference/predict_single.py`; any other future entry point to this model
   must independently call it.
8. **Test set was evaluated once** (2026-09-15, `reports/final_test_evaluation.md`) — see
   "Final Test-Set Evaluation" above. Test performance matched validation closely (no metric
   gapped by ≥0.03), but this was a single one-way-door check on a single (likely synthetic)
   data source, not repeated or cross-validated evaluation.
9. **Not yet done for the 5-class Severity target:** Phase 15 (calibration), Phase 16
   (uncertainty/abstention). (Phase 12 and Phase 19 are now done for the 3-class target — see
   limitation 6 above and `reports/advanced_models_3class.md`.)
10. **This is a prototype/research model** (`CLAUDE.md` Engineering Rule 7) — it must never be
    represented as having clinical diagnostic validity, and its output must never bypass
    psychologist review per the project's critical workflow constraint.

---

## Source Traceability

All figures in this card are pulled directly from, and can be re-verified against:
`CLAUDE.md`; `reports/baseline_results_3class.json`; `reports/tuning_results_3class.json`;
`reports/full_evaluation_3class.md`; `reports/calibration_3class.md`;
`reports/calibration_3class_full.md`; `reports/uncertainty_flagging.md`;
`reports/threshold_sweep_high.md`; `reports/shap_summary_3class.md`;
`reports/fairness_report_3class.md`; `reports/advanced_models_3class.md`;
`reports/robustness_3class.md`; `reports/feature_engineering_3class.md`;
`reports/ensemble_3class.md`; `reports/postprocessing_3class.md`;
`reports/calibrated_uncertainty_flagging_3class.md`; `reports/final_test_evaluation.md`.
Seed=42 throughout. No number here was invented, estimated, or rounded beyond what these source
files already report.
