# Full Evaluation Report (Phase-14 style) — 12-Feature Model, 3-Class Anxiety Level

## Scope

- Model: the saved canonical artifact `data/processed/mindcare_final_model_12feature.pkl` (built by `src/models/adopt_12feature_model.py`), evaluated as-is — not refit.
- Data: `X_val`/`y_val` from `data/processed/mindcare_processed_splits_12feature.npz` (1650 rows). That file contains only `X_train`, `X_val`, `train_original_idx`, `val_original_idx`, `y_train`, `y_val` — **no test arrays exist for this configuration, and none were used.** The 3-class test set is treated as fully spent (see CLAUDE.md); these are validation-only numbers.
- AUROC/AUPRC computed one-vs-rest per class via `label_binarize`.
- Script: `src/evaluation/full_evaluation_12feature.py`.

## Consistency Check (run before anything below was computed)

Recomputed from the saved model and compared with `reports/feature_addition_age_3class.md` at its 4 decimal places. The script stops without writing this report on any mismatch.

| Metric | Documented | Recomputed | Match |
|---|---:|---:|:---:|
| accuracy | 0.7739 | 0.773939 | yes |
| balanced_accuracy | 0.8062 | 0.806158 | yes |
| macro_f1 | 0.8182 | 0.818209 | yes |
| recall_Low | 0.7506 | 0.750643 | yes |
| recall_Medium | 0.7709 | 0.770863 | yes |
| recall_High | 0.8970 | 0.896970 | yes |

## Classification Report

```
              precision    recall  f1-score   support

         Low     0.7839    0.7506    0.7669       778
      Medium     0.7209    0.7709    0.7450       707
        High     0.9933    0.8970    0.9427       165

    accuracy                         0.7739      1650
   macro avg     0.8327    0.8062    0.8182      1650
weighted avg     0.7778    0.7739    0.7751      1650
```

## Confusion Matrix

Rows = true class, columns = predicted class.

| True \ Predicted | Low | Medium | High | Total |
|---|---:|---:|---:|---:|
| **Low** | 584 | 194 | 0 | 778 |
| **Medium** | 161 | 545 | 1 | 707 |
| **High** | 0 | 17 | 148 | 165 |

## Per-Class AUROC and AUPRC (One-vs-Rest)

With the 17-feature model's Phase 14 validation numbers (`reports/full_evaluation_3class.md`, same 1650 validation rows) for reference.

| Class | AUROC | AUPRC | 17-feature AUROC | 17-feature AUPRC | Δ AUROC | Δ AUPRC |
|---|---:|---:|---:|---:|---:|---:|
| Low | 0.8753 | 0.8553 | 0.8745 | 0.8556 | +0.0008 | -0.0003 |
| Medium | 0.8513 | 0.7645 | 0.8517 | 0.7699 | -0.0004 | -0.0054 |
| High | 0.9866 | 0.9530 | 0.9850 | 0.9511 | +0.0016 | +0.0019 |
| **Macro average** | **0.9044** | **0.8576** | 0.9037 | 0.8589 | +0.0007 | -0.0013 |

## Interpretation

- The largest single error cell is true **Low** predicted as **Medium** (194 rows). Low↔Medium confusion accounts for 355 of 373 errors (95.2%). Low↔High confusion: 0 true-Low predicted High, 0 true-High predicted Low.
- High: 148 of 165 true-High rows caught; the misses were predicted as Low (0), Medium (17). Rows wrongly predicted High: Low (0), Medium (1).
- The comparison columns above are both validation-set numbers on the same rows, so they are directly comparable — but they are not test-set results, and no test-set number exists for this model.
- These are prototype-model metrics on a very likely synthetic dataset (see CLAUDE.md) and should not be read as clinical validation.
