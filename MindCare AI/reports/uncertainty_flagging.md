# Uncertainty Flagging Report (Phase 16, FINAL) — Tuned Random Forest, 3-Class Target

## Scope

- Model: tuned Random Forest (n_estimators=200, max_depth=10, min_samples_split=10, min_samples_leaf=4, max_features='sqrt', class_weight='balanced') from `reports/tuning_results_3class.json`.
- Evaluation: `X_val`/`y_val` from `mindcare_processed_splits_3class.npz`; test set untouched.
- Validation rows: 1650; seed: 42.

## Flag Rule (Production, Finalized)

A row is flagged **"borderline — recommend review"** if P(High) >= 0.1 (the ~10% marginal base rate of High), unconditional on the predicted class.

This does not gate access to review — every prediction is already reviewed by a psychologist per this project's approval workflow — it reprioritizes review attention toward rows the model considers plausibly High-risk even when it did not predict High.

A margin-based trigger was evaluated and dropped: it caught 0 of the 17 known True-High/Predicted-Medium misses while driving most of the flagged volume (see `reports/threshold_sweep_high.md`), so only the P(High) trigger is kept.

## Overall Flagging Rate

**Flagged: 346 / 1650 = 0.2097**

## Key Number: Coverage of the 17 Known True-High/Predicted-Medium Misses

These are the validation rows where the true label is High and the three untuned baseline models (Logistic Regression, Random Forest, XGBoost) all predicted Medium (`reports/baseline_results_3class.json`, `reports/calibration_3class.md`).

**Flagged: 9 / 17 = 0.5294**

For context, True-High rows overall flagged: 157 / 165 = 0.9515 (most already-correct High predictions also cross this threshold, since P(High) is naturally high when High is the top prediction).

| Original row | P(High) | Tuned-RF predicted | Flagged |
|---:|---:|---|---|
| 10691 | 0.0909 | Medium | False |
| 3617 | 0.0935 | Medium | False |
| 7745 | 0.0730 | Medium | False |
| 8451 | 0.2530 | Medium | True |
| 5963 | 0.2547 | Medium | True |
| 6420 | 0.0421 | Medium | False |
| 7929 | 0.1115 | Medium | True |
| 3628 | 0.0929 | Medium | False |
| 1819 | 0.2292 | Medium | True |
| 1432 | 0.1373 | Medium | True |
| 7312 | 0.1076 | Medium | True |
| 10199 | 0.0402 | Medium | False |
| 5237 | 0.1910 | Medium | True |
| 6275 | 0.0702 | Medium | False |
| 22 | 0.1476 | Medium | True |
| 2318 | 0.1186 | Medium | True |
| 9746 | 0.0650 | Medium | False |

## False-Flag Rate (Cost of Extra Review)

Of the 346 rows flagged, 321 were already correctly classified by the tuned Random Forest.

**False-flag rate: 321 / 346 = 0.9277**

This is high mainly because the rule is unconditional: correctly-classified True-High rows also cross the threshold and get flagged, which is intended (they should also get priority attention), not a defect of the rule.

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see CLAUDE.md); not clinical validation. This flagging mechanism does not change any prediction — it only marks rows for prioritized psychologist review, consistent with the project's AI-prediction-then-psychologist-review workflow constraint.
