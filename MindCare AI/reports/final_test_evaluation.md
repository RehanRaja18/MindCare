# FINAL Test-Set Evaluation (One-Time) — 3-Class Anxiety Level Target

**This is the only evaluation in this project that uses X_test/y_test. The test set was untouched until this report. No retraining, tuning, or model-selection decision may be made based on these results — this was a one-way door.**

## Scope

- Model: the saved final tuned Random Forest (`data/processed/mindcare_final_model.pkl`), hyperparameters from `reports/tuning_results_3class.json` — used exactly as-is, no refitting.
- Test rows: 1650; seed: 42.
- AUROC/AUPRC computed one-vs-rest per class via `label_binarize`.

## Headline Metrics

| Metric | Validation (reports/full_evaluation_3class.md) | Test | Gap (test − val) |
|---|---:|---:|---:|
| Accuracy | 0.7733 | 0.7915 | +0.0182 |
| Balanced accuracy | 0.8056 | 0.8193 | +0.0137 |
| Macro-F1 | 0.8177 | 0.8311 | +0.0134 |
| Macro AUROC | 0.9037 | 0.9083 | +0.0046 |
| Macro AUPRC | 0.8589 | 0.8691 | +0.0102 |

## Per-Class AUROC / AUPRC — Test

| Class | AUROC (val) | AUROC (test) | Gap | AUPRC (val) | AUPRC (test) | Gap |
|---|---:|---:|---:|---:|---:|---:|
| Low | 0.8745 | 0.8798 | +0.0053 | 0.8556 | 0.8587 | +0.0031 |
| Medium | 0.8517 | 0.8607 | +0.0090 | 0.7699 | 0.7920 | +0.0221 |
| High | 0.9850 | 0.9843 | -0.0007 | 0.9511 | 0.9566 | +0.0055 |

## Classification Report — Test

```
              precision    recall  f1-score   support

         Low     0.7987    0.7772    0.7878       781
      Medium     0.7422    0.7814    0.7613       700
        High     0.9935    0.8994    0.9441       169

    accuracy                         0.7915      1650
   macro avg     0.8448    0.8193    0.8311      1650
weighted avg     0.7947    0.7915    0.7926      1650
```

## Classification Report — Val vs Test, Per-Class

| Class | Precision (val) | Precision (test) | Recall (val) | Recall (test) | F1 (val) | F1 (test) |
|---|---:|---:|---:|---:|---:|---:|
| Low | 0.7806 | 0.7987 | 0.7545 | 0.7772 | 0.7673 | 0.7878 |
| Medium | 0.7223 | 0.7422 | 0.7652 | 0.7814 | 0.7431 | 0.7613 |
| High | 0.9933 | 0.9935 | 0.8970 | 0.8994 | 0.9427 | 0.9441 |

## Confusion Matrix — Test (rows = true, columns = predicted, order Low/Medium/High)

```
[[607 174   0]
 [152 547   1]
 [  1  16 152]]
```

## Val-vs-Test Gap Assessment

**No metric shows a gap of 0.03 or more between validation and test.** Test-set performance is consistent with the validation-set numbers already reported in `reports/full_evaluation_3class.md` — no evidence of overfitting to the validation split during the tuning/analysis process.

## Interpretation

This is a prototype-model result on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation. This evaluation was performed exactly once, against the already-saved final model, with no retraining, tuning, or model-selection change made in response to these numbers.
