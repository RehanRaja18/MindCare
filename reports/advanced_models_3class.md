# Phase 12 — Advanced Models (3-Class Anxiety Level Target)

## Scope

Per `docs/master_project_instructions.md` PHASE 12: after establishing strong baselines
(Phases 11/13), evaluate a more advanced model class — "neural networks... depending on the
data" — without using deep learning merely because it is more sophisticated.

This dataset is small tabular data (7700 train rows, 34 preprocessed features), with no
image/text/sequence structure. A deep architecture, transformer, or multimodal model would be
inappropriate for this data shape and is exactly what the master document warns against ("do not
use deep learning merely because it is more sophisticated"). The applicable advanced-model
candidate is a **shallow multilayer perceptron** (`sklearn.neural_network.MLPClassifier`) — a
genuine neural network, scaled to the size and structure of this data.

- Tuning: `RandomizedSearchCV`, cv=5, n_iter=20, scoring=`balanced_accuracy`, seed=42, trained on
  `X_train`/`y_train` only, evaluated once on `X_val`/`y_val` (`src/models/train_advanced_3class.py`).
- Search space: `hidden_layer_sizes` ∈ {(32,), (64,), (32,16), (64,32), (100,)}, `activation` ∈
  {relu, tanh}, `alpha` ∈ {0.0001, 0.001, 0.01, 0.1}, `learning_rate_init` ∈ {0.0005, 0.001, 0.01}.
  `early_stopping=True`, `max_iter=500`.

## Result

Best CV balanced accuracy: **0.8104** (best params: `hidden_layer_sizes=(100,)`,
`activation=tanh`, `alpha=0.001`, `learning_rate_init=0.001`; converged after 56 iterations via
early stopping; total tuning time 69.5s for 100 fits).

| Model | Accuracy | Balanced accuracy | Macro-F1 | High recall |
|---|---:|---:|---:|---:|
| Random Forest (tuned) | 0.7733 | 0.8056 | **0.8177** | 0.8970 |
| XGBoost (tuned) | **0.7770** | **0.8074** | 0.8175 | 0.8970 |
| **MLP / neural net (tuned)** | 0.7733 | 0.8041 | 0.8160 | 0.8970 |

**The neural network does not outperform either tree ensemble on any metric.** It ties Random
Forest on accuracy and High recall, and is the weakest of the three on balanced accuracy and
macro-F1 (by 0.15–0.33 points — within noise, but not an improvement in any direction).

## Selection Judgment (Performance + Calibration + Interpretability + Robustness + Computational Cost + Clinical Usability)

Per the master document's explicit balance criteria, evaluated honestly against what's actually
been measured:

- **Performance:** No advantage. MLP is statistically indistinguishable from the two tree
  ensembles already in use, and marginally behind on 2 of 4 metrics.
- **Calibration:** Untested for MLP (Phase 15's calibration work was done only for the tuned
  Random Forest). Given no performance gain, there is no motivation to redo that analysis for
  MLP.
- **Interpretability:** **Materially worse.** Random Forest's feature-based splits support direct
  SHAP `TreeExplainer` analysis, already completed (Phase 17) and cheap to compute. An MLP would
  require a slower, approximate explainer (e.g., `KernelExplainer` or `DeepExplainer`) for
  comparable feature attributions, for a model that performs no better — a clear net loss for a
  psychologist-facing tool where interpretability was already named as a selection criterion for
  Random Forest over XGBoost (`docs/model_card.md`, "Model Selection Rationale").
- **Robustness:** Untested for MLP (see Phase 19 robustness report, which was run against the
  saved Random Forest only).
- **Computational cost:** **Worse.** Tuning the MLP took ~70 seconds for 100 fits; the existing
  Random Forest and XGBoost tuning runs (`reports/tuning_results_3class.json`) are comparably
  fast or faster, and MLP training itself is more sensitive to hyperparameters (needed
  early-stopping and a learning-rate search that tree ensembles don't require).
- **Clinical usability:** No advantage; the same decision-support framing applies regardless of
  model family, but a model that is harder to explain to a psychologist reviewer, for identical
  performance, is worse on this criterion.

## Decision

**Do not adopt the MLP.** It offers no performance advantage over the already-selected tuned
Random Forest, while being worse on interpretability and computational cost and untested on
calibration and robustness. This is a real, measured negative result, not an assumption — the
neural network was tuned and evaluated exactly as the master document instructs ("only after
establishing strong baselines... depending on the data"), and the data (a small, well-behaved
tabular problem with strong prior-established tree-ensemble performance) simply does not reward
the added complexity. Random Forest remains the selected model for this target.

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not clinical
validation. This result should not be read as "neural networks don't work for anxiety
prediction" in general — it is specific to this dataset's size, feature set, and structure, and
to the modest single-layer MLP architecture searched here.
