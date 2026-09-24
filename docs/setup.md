# Setup — Regenerating Model Artifacts

Trained models, preprocessors, label encoders and processed splits
(`data/processed/*.pkl`, `data/processed/*.npz`) are **not stored in git** (see `.gitignore`).
After a fresh clone, rebuild them with the scripts below before running the API or the tests.

**One exception is tracked on purpose:** `data/processed/mindcare_processed_splits.npz`, the
original train/val/test split. No script in this repo can create it from nothing —
`src/rebuild_preprocessor.py` re-splits the raw CSV but refuses to write unless its result
matches this existing file exactly (and fails with `FileNotFoundError` if it is missing). Every
other artifact is derived from it plus `data/raw/mindcare_dataset_final.csv`. **Do not delete
it.**

## Prerequisites

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

`scikit-learn` is pinned (`==1.9.1`) because pickled models and preprocessors are only reliably
loadable by the version that wrote them. On macOS/Linux use `.venv/bin/python` instead of
`.venv/Scripts/python`.

## Regenerate, in this order

Run from the repository root. Each step reads the output of the steps before it.

| # | Command | Writes | Needed by |
|---|---|---|---|
| 1 | `.venv/Scripts/python -m src.rebuild_preprocessor` | `mindcare_preprocessor.pkl`, `mindcare_label_encoder.pkl` (and rewrites `mindcare_processed_splits.npz` after verifying it is unchanged) | 5-class Severity scripts |
| 2 | `.venv/Scripts/python -m src.build_3class_target` | `mindcare_processed_splits_3class.npz`, `mindcare_label_encoder_3class.pkl` | steps 3-5, **the API** |
| 3 | `.venv/Scripts/python -m src.models.save_final_model` | `mindcare_final_model.pkl` (original 17-feature model, superseded) | historical evaluation/experiment scripts only |
| 4 | `.venv/Scripts/python -m src.models.adopt_11feature_model` | `mindcare_preprocessor_11feature.pkl`, `mindcare_processed_splits_11feature.npz`, `mindcare_final_model_11feature.pkl` (superseded) | `final_test_evaluation_11feature.py`, feature-reduction experiments only |
| 5 | `.venv/Scripts/python -m src.models.adopt_12feature_model` | `mindcare_preprocessor_12feature.pkl`, `mindcare_processed_splits_12feature.npz`, `mindcare_final_model_12feature.pkl` — **the current canonical model** | **the API**, `predict_single.py`, the tests |

To get only what the API and tests need, steps **2 and 5** are enough. Steps 3 and 4 do not feed
step 5.

Each script checks its own output and fails loudly if something doesn't match. Step 3 compares
its validation metrics against `reports/tuning_results_3class.json`; step 4 compares against
the numbers documented in `reports/feature_reduction_3class.md`.

**Side effect of step 5:** it also rewrites `reports/feature_addition_age_3class.md`. On a
correct rebuild the file comes out byte-identical, so `git status` should show no change to it.
If it does change, the rebuild did not reproduce the documented model; investigate before
using it.

## The final model and the PSS-4 / caffeine inputs

Step 5's 12-feature model is the one the API serves. **The model itself is trained on the
dataset's raw columns, including `Stress Level (1-10)` and `Caffeine Intake (mg/day)`**. The
PSS-4 questionnaire and caffeine serving counts are converted to those values at inference time,
in code, by `estimate_stress_level()` (`src/inference/stress_scale.py`) and
`estimate_caffeine_mg()` (`src/api/main.py`). No extra artifact or build step is needed for
them. See `docs/api_usage.md` for the conversion details and their validation caveats.

## Verify

```bash
.venv/Scripts/python -m pytest -q
```

All tests should pass. `tests/test_api.py` loads the step-2 and step-5 artifacts, and asserts
the example patients' predicted classes (Low / High / Medium), so a broken rebuild shows up here.

Last verified 2026-09-24 (Python 3.13.13, scikit-learn 1.9.1). All 5 steps ran in a clean copy
of the repo, about 45 seconds in total. The rebuilt 12-feature model gave the same predicted
classes on the validation set as the original, with probabilities differing by at most 4e-16
(floating-point noise).
