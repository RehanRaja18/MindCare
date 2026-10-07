# Soft-Voting Ensemble Experiment (Exploratory) — 3-Class Anxiety Level Target

**Scope note: this script works on TRAIN and VALIDATION only. It never loads or references X_test, y_test, or test_original_idx anywhere. The test set was not touched by this experiment. No artifact here replaces the saved final model, preprocessor, or any canonical pipeline file — this is exploratory only.**

## Method

Original 11 numeric + 6 categorical feature set (existing `mindcare_processed_splits_3class.npz`) — not the engineered feature set from the prior experiment, since that experiment found no benefit. Tuned Random Forest and tuned XGBoost (both from `reports/tuning_results_3class.json`) are each fit on `X_train`/`y_train`, `predict_proba` is computed on `X_val` for each, the two probability arrays are averaged, and `argmax` gives the ensemble prediction.

## Sanity Check

- RF accuracy: computed 0.7733 vs documented 0.7733 (match: True)
- RF balanced accuracy: computed 0.8056 vs documented 0.8056 (match: True)
- XGBoost accuracy: computed 0.7770 vs documented 0.7770 (match: True)
- XGBoost balanced accuracy: computed 0.8074 vs documented 0.8074 (match: True)

## Results

| Model | Accuracy | Balanced acc. | Macro-F1 | Recall Low | Recall Medium | Recall High |
|---|---:|---:|---:|---:|---:|---:|
| Random Forest | 0.7733 | 0.8056 | 0.8177 | 0.7545 | 0.7652 | 0.8970 |
| XGBoost | 0.7770 | 0.8074 | 0.8175 | 0.7828 | 0.7426 | 0.8970 |
| **Ensemble (soft vote)** | **0.7770** | **0.8077** | **0.8193** | 0.7738 | 0.7525 | 0.8970 |

## Deltas

| Comparison | Δ Accuracy | Δ Balanced acc. | Δ Macro-F1 | Δ Recall Low | Δ Recall Medium | Δ Recall High |
|---|---:|---:|---:|---:|---:|---:|
| Ensemble − RF | +0.0036 | +0.0022 | +0.0016 | +0.0193 | -0.0127 | +0.0000 |
| Ensemble − XGBoost | +0.0000 | +0.0003 | +0.0018 | -0.0090 | +0.0099 | +0.0000 |
| Ensemble − best individual (random_forest) | +0.0036 | +0.0022 | +0.0016 | +0.0193 | -0.0127 | +0.0000 |

## Honest Verdict

The ensemble beats both individual models on macro-F1, but only marginally (+0.0016 over the best individual model, random_forest) — under the 1-point bar. **This should be read as splitting the difference between the two models with a very slight edge, not as a meaningful win.**

## Interpretability Cost If This Were Adopted

Neither individual model needed this tradeoff — Random Forest already has a cheap, exact `shap.TreeExplainer` (used throughout Phase 17), and XGBoost would too if it were ever adopted on its own. **A soft-voting ensemble of two different model types has no single, cheap explainer that covers the combined prediction.** In practice, adopting this ensemble would mean one of:

1. **Running SHAP separately on each sub-model** (two `TreeExplainer` runs, RF and XGBoost independently) and then trying to combine or reconcile two different attribution sets for the same prediction — doable, but doubles the explainability workload and gives a psychologist reviewer two potentially-disagreeing explanations to reconcile, not one.
2. **Using a model-agnostic method like `KernelExplainer` (KernelSHAP) on the ensemble's combined `predict_proba` directly** — this treats the ensemble as a black box and works correctly, but is dramatically slower than `TreeExplainer` (KernelSHAP requires many perturbed-input model evaluations per row, typically orders of magnitude more compute than a tree-structure-aware explainer), which matters for a workflow that's supposed to support real-time or near-real-time psychologist review.

Given the ensemble's actual performance in this experiment (see verdict above), this added interpretability cost is very unlikely to be worth paying — the Model Selection Rationale in `docs/model_card.md` already named interpretability as a deciding factor in choosing Random Forest over XGBoost alone; an ensemble of the two moves further in the wrong direction on that same criterion for, at best, a marginal accuracy gain.

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not clinical validation. This was an exploratory experiment only — no canonical artifact (preprocessor, saved model, or CLAUDE.md feature list) was changed as a result. The test set was never touched by this script.
