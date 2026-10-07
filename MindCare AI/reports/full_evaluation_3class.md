# Full Evaluation Report (Phase 14) — 3-Class Anxiety Level Target

## Scope

- Model: tuned Random Forest from `reports/tuning_results_3class.json` (n_estimators=200, max_depth=10, min_samples_split=10, min_samples_leaf=4, max_features='sqrt', class_weight='balanced').
- Training: existing `X_train`/`y_train` only; no refitting of preprocessing.
- Evaluation: existing `X_val`/`y_val` only; test set untouched.
- Validation rows: 1650; seed: 42.
- AUROC/AUPRC computed one-vs-rest per class via `label_binarize`.

## Per-Class AUROC and AUPRC (One-vs-Rest)

| Class | AUROC | AUPRC |
|---|---:|---:|
| Low | 0.8745 | 0.8556 |
| Medium | 0.8517 | 0.7699 |
| High | 0.9850 | 0.9511 |
| **Macro average** | **0.9037** | **0.8589** |

## Classification Report

```
              precision    recall  f1-score   support

         Low     0.7806    0.7545    0.7673       778
      Medium     0.7223    0.7652    0.7431       707
        High     0.9933    0.8970    0.9427       165

    accuracy                         0.7733      1650
   macro avg     0.8321    0.8056    0.8177      1650
weighted avg     0.7769    0.7733    0.7745      1650
```

## Interpretation

These are prototype-model metrics on a very likely synthetic dataset (see CLAUDE.md) and should not be read as clinical validation.
Per CLAUDE.md, Stress Level correlates 0.65 (ordinal) with this 3-class target and removing it drops Logistic Regression accuracy by 17.6 points (77.8% -> 60.1%, still well above the 47.2% majority baseline) — a materially smaller single-feature dependency than the 5-class Severity target (0.91 correlation, ~49-point drop).
