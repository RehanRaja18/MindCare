# Full Evaluation Report (Phase 14)

## Scope

- Model: tuned Random Forest from `reports/tuning_results.json` (n_estimators=500, max_depth=30, min_samples_split=10, min_samples_leaf=4, max_features='sqrt', class_weight='balanced').
- Training: existing `X_train`/`y_train` only; no refitting of preprocessing.
- Evaluation: existing `X_val`/`y_val` only; test set untouched.
- Validation rows: 1650; seed: 42.
- AUROC/AUPRC computed one-vs-rest per class via `label_binarize`.

## Per-Class AUROC and AUPRC (One-vs-Rest)

| Class | AUROC | AUPRC |
|---|---:|---:|
| High (7-8) | 0.9509 | 0.7785 |
| Mild (3-4) | 0.9454 | 0.8499 |
| Minimal (1-2) | 0.9855 | 0.9420 |
| Moderate (5-6) | 0.9350 | 0.8234 |
| Severe (9-10) | 0.9911 | 0.8621 |
| **Macro average** | **0.9616** | **0.8512** |

## Classification Report

```
                precision    recall  f1-score   support

    High (7-8)     0.7432    0.7432    0.7432       292
    Mild (3-4)     0.8715    0.6318    0.7325       440
 Minimal (1-2)     0.8105    0.9673    0.8820       367
Moderate (5-6)     0.7588    0.7723    0.7655       448
 Severe (9-10)     0.6966    0.9806    0.8145       103

      accuracy                         0.7861      1650
     macro avg     0.7761    0.8190    0.7875      1650
  weighted avg     0.7937    0.7861    0.7817      1650
```

## Interpretation

These are prototype-model metrics on a very likely synthetic dataset (see CLAUDE.md) and should not be read as clinical validation.
Per CLAUDE.md, Stress Level is a near-proxy for Severity (0.91 correlation); most of the discriminative signal behind these AUROC/AUPRC numbers is driven by that one feature, not broad multi-feature signal.
