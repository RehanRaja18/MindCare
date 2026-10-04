# Calibrated Uncertainty Flagging Check (Exploratory) — 3-Class Anxiety Level Target

**Scope note: this script works on TRAIN and VALIDATION only. It never loads or references X_test, y_test, or test_original_idx anywhere. The test set was not touched. No canonical artifact was changed — purely exploratory.**

## Method

Isotonic-calibrated Random Forest, identical to `src/experiments/postprocessing_3class.py` (`CalibratedClassifierCV(estimator=RandomForest(tuned params), method='isotonic', cv=5)`, fit on `X_train`/`y_train`). Production flag rule re-applied unchanged: P(High) >= 0.1, unconditional on predicted class.

## Comparison: Uncalibrated (Documented) vs Isotonic-Calibrated

| Metric | Uncalibrated (`reports/uncertainty_flagging.md`) | Isotonic-calibrated | Delta |
|---|---:|---:|---:|
| Overall flagged | 346/1650 (0.2097) | 171/1650 (0.1036) | -175 rows |
| Known-miss coverage (of 17) | 9/17 (0.5294) | 3/17 (0.1765) | -6 rows |
| False-flag rate | 0.9277 | 0.9708 | +0.0431 |

## The 17 Known Misses — Calibrated P(High) and Flag Status

| Original row | P(High), isotonic-calibrated | Flagged |
|---:|---:|---|
| 10691 | 0.0352 | False |
| 3617 | 0.0252 | False |
| 7745 | 0.0130 | False |
| 8451 | 0.1061 | True |
| 5963 | 0.1250 | True |
| 6420 | 0.0040 | False |
| 7929 | 0.0376 | False |
| 3628 | 0.0372 | False |
| 1819 | 0.1077 | True |
| 1432 | 0.0515 | False |
| 7312 | 0.0546 | False |
| 10199 | 0.0061 | False |
| 5237 | 0.0847 | False |
| 6275 | 0.0239 | False |
| 22 | 0.0649 | False |
| 2318 | 0.0310 | False |
| 9746 | 0.0342 | False |

## Plain Answer

**Calibration DOES meaningfully change the flagging mechanism's behavior — substantially, not marginally.** Overall flagged volume roughly halved (346 → 171 rows, a 50.6% relative drop), and known-miss coverage fell from 9/17 (0.5294) to 3/17 (0.1765) — the mechanism catches two-thirds fewer of the boundary-ambiguous misses it was specifically built to catch.

**Why this happens, given Part 1 of `reports/postprocessing_3class.md` found calibration only flips 21/1650 (1.27%) of argmax predictions:** those two facts are not in tension. The flagging rule thresholds the *raw* P(High) value, not the argmax class — so calibration can leave classification accuracy almost untouched while still reshaping the probability values substantially enough to move many rows across a fixed 0.10 cutoff. This is consistent with, and explained by, the original (uncalibrated) calibration finding in `reports/calibration_3class.md`: the uncalibrated model was specifically **over-confident in the P(High) < 0.3 range** — exactly the range all 17 known misses live in (see `reports/calibration_3class.md`'s Test 3 table). Isotonic calibration corrects that over-confidence by systematically *shrinking* probabilities in that range, which is desirable for calibration quality but has the direct side effect of pushing borderline P(High) values below the 0.10 flagging threshold that would previously have cleared it. The 0.10 threshold was tuned against the uncalibrated model's probability distribution; it does not automatically transfer to a recalibrated one.

**Practical implication:** if isotonic calibration were ever adopted, the 0.10 uncertainty-flagging threshold would need to be re-tuned against the calibrated probabilities (re-running the threshold sweep from `reports/threshold_sweep_high.md` on calibrated P(High) values), not reused as-is — reusing it silently would cut the mechanism's coverage of exactly the cases it exists to catch by two-thirds.

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation. Purely exploratory — no canonical artifact was changed. The test set was never touched by this script.
