# SECOND AND FINAL Test-Set Evaluation — 11-Feature Model, 3-Class Anxiety Level Target

**This is the SECOND and FINAL time the test set is used in this project, disclosed explicitly. It is justified because this evaluates a genuinely new model configuration (11 features, replacing the original 17-feature model per `reports/feature_reduction_3class.md` and `src/models/adopt_11feature_model.py`) — not iterative tuning or re-evaluation of the same model. After this report, the test set is fully spent for BOTH the 17-feature and 11-feature models. No further evaluation on X_test/y_test is permitted for either model.**

## Scope

- Model: `data/processed/mindcare_final_model_11feature.pkl` — used exactly as-is, no refitting.
- Test rows: 1650; seed: 42.
- AUROC/AUPRC computed one-vs-rest per class via `label_binarize`.

## Headline Metrics (11-Feature Model)

| Metric | Value |
|---|---:|
| Accuracy | 0.7891 |
| Balanced accuracy | 0.8177 |
| Macro-F1 | 0.8285 |
| Macro AUROC | 0.9077 |
| Macro AUPRC | 0.8633 |

## Per-Class AUROC / AUPRC — 11-Feature Test

| Class | AUROC | AUPRC |
|---|---:|---:|
| Low | 0.8789 | 0.8558 |
| Medium | 0.8587 | 0.7798 |
| High | 0.9856 | 0.9544 |

## Classification Report — 11-Feature Test

```
              precision    recall  f1-score   support

         Low     0.8013    0.7695    0.7851       781
      Medium     0.7359    0.7843    0.7593       700
        High     0.9870    0.8994    0.9412       169

    accuracy                         0.7891      1650
   macro avg     0.8414    0.8177    0.8285      1650
weighted avg     0.7926    0.7891    0.7902      1650
```

## Confusion Matrix — 11-Feature Test (rows = true, columns = predicted, order Low/Medium/High)

```
[[601 180   0]
 [149 549   2]
 [  0  17 152]]
```

## Comparison A: 11-Feature Test vs. 11-Feature's Own Validation

| Metric | Validation | Test | Gap (test − val) |
|---|---:|---:|---:|
| Accuracy | 0.7770 | 0.7891 | +0.0121 |
| Balanced accuracy | 0.8084 | 0.8177 | +0.0093 |
| Macro-F1 | 0.8204 | 0.8285 | +0.0081 |

**No metric shows a gap of 0.03 or more between this model's validation and test performance** — no evidence of overfitting to the validation split during feature selection.

## Comparison B: 11-Feature Test vs. 17-Feature Test (Honest Head-to-Head)

The original 17-feature model's test performance, for direct comparison (`reports/final_test_evaluation.md` — the first, disclosed use of the test set):

| Metric | 17-feature (test) | 11-feature (test) | Delta (11 − 17) |
|---|---:|---:|---:|
| Accuracy | 0.7915 | 0.7891 | -0.0024 |
| Balanced accuracy | 0.8193 | 0.8177 | -0.0016 |
| Macro-F1 | 0.8311 | 0.8285 | -0.0026 |
| Macro AUROC | 0.9083 | 0.9077 | -0.0006 |
| Macro AUPRC | 0.8691 | 0.8633 | -0.0058 |

| Class | Precision Δ | Recall Δ | F1 Δ | AUROC Δ | AUPRC Δ |
|---|---:|---:|---:|---:|---:|
| Low | +0.0026 | -0.0077 | -0.0027 | -0.0009 | -0.0029 |
| Medium | -0.0063 | +0.0029 | -0.0020 | -0.0020 | -0.0122 |
| High | -0.0065 | +0.0000 | -0.0029 | +0.0013 | -0.0022 |

## Honest Verdict

**The 11-feature model's test performance is very slightly, but consistently, worse than the 17-feature model's — not the wash-or-improvement picture validation data suggested.** Of the 20 metrics compared in Comparison B above, 19 are within ±0.01 (effectively noise at this sample size), but **every single headline metric moved in the negative direction** (accuracy −0.0024, balanced accuracy −0.0016, macro-F1 −0.0026, macro AUROC −0.0006, macro AUPRC −0.0058), and one metric — **Medium-class AUPRC (−0.0122)** — crosses the 0.01 threshold. This is a small effect, not a dramatic one, but it is a real, one-directional pattern, not noise scattered in both directions.

This matters because `reports/feature_reduction_3class.md` (validation-only) found the *opposite* direction — the 11-feature model looked marginally *better* than the 17-feature baseline on validation (+0.0036 accuracy, +0.0028 balanced accuracy, +0.0027 macro-F1). **That validation-only finding does not fully replicate on the held-out test set.** The likely explanation: the small validation-set gain was itself noise (removing 6 low-signal features doesn't meaningfully change what the model learns, so small differences in either direction are within normal run-to-run variance), and this test-set result is a more reliable read on the two models' true relative performance — which is "statistically indistinguishable, with a slight edge to the 17-feature model" rather than "the 11-feature model is better."

**Practical takeaway:** the core decision to drop those 6 features remains reasonable — the cost, even by this stricter test-set read, is tiny (≤0.003 on every headline metric, ≤0.012 on any single per-class metric) — but the claim should now be "no *meaningful* cost" rather than "a slight improvement." This is exactly why validation-only findings must eventually be checked against test data, and why this second, disclosed test-set use was worth spending.

## Interpretation

This is a prototype-model result on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation. This was the second and final disclosed use of the test set in this project. No retraining, tuning, or model-selection change was made in response to these numbers. The test set must not be evaluated again for either the 17-feature or 11-feature model.
