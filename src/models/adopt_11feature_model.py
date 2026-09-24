"""Adopt the 11-feature model as the new canonical model (3-class Anxiety
Level target), replacing the 17-feature model.

Per reports/feature_reduction_3class.md: the 6 lowest-SHAP-ranked features
(Age, Alcohol Consumption (drinks/week), Dizziness, Smoking, Recent Major
Life Event, Medication) are dropped entirely. Remaining 11 features: 9
numeric + 2 categorical (Family History of Anxiety, Occupation).

Saves NEW files only - the existing 17-feature preprocessor/splits/model
are never touched:
  data/processed/mindcare_preprocessor_11feature.pkl
  data/processed/mindcare_processed_splits_11feature.npz
  data/processed/mindcare_final_model_11feature.pkl

The test set IS preprocessed/transformed here (per explicit instruction)
so it's ready for later use, but it is NOT evaluated - no metric is ever
computed against X_test/y_test in this script.

Final step: reload the retrained model and verify its validation metrics
reproduce reports/feature_reduction_3class.md's documented numbers exactly
(accuracy 0.7770, balanced_accuracy 0.8084, macro_f1 0.8204). If they do
not match exactly, this script raises rather than silently proceeding.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.preprocessing import OneHotEncoder, StandardScaler


SEED = 42
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
EXISTING_SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"

NEW_PREPROCESSOR_PATH = ROOT / "data" / "processed" / "mindcare_preprocessor_11feature.pkl"
NEW_SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_11feature.npz"
NEW_MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model_11feature.pkl"

# Documented targets from reports/feature_reduction_3class.md - must reproduce exactly.
EXPECTED_ACCURACY = 0.7770
EXPECTED_BALANCED_ACCURACY = 0.8084
EXPECTED_MACRO_F1 = 0.8204
TOLERANCE = 1e-4  # documented values were rounded to 4dp; allow rounding-only slack

NUMERIC_FEATURES = [
    "Sleep Hours",
    "Physical Activity (hrs/week)",
    "Caffeine Intake (mg/day)",
    "Stress Level (1-10)",
    "Heart Rate (bpm)",
    "Breathing Rate (breaths/min)",
    "Sweating Level (1-5)",
    "Therapy Sessions (per month)",
    "Diet Quality (1-10)",
]
CATEGORICAL_FEATURES = ["Occupation", "Family History of Anxiety"]

REMOVED_FEATURES = [
    "Age", "Alcohol Consumption (drinks/week)", "Dizziness",
    "Smoking", "Recent Major Life Event", "Medication",
]

TUNED_RF_PARAMS = dict(
    n_estimators=200,
    max_depth=10,
    min_samples_split=10,
    min_samples_leaf=4,
    max_features="sqrt",
    class_weight="balanced",
    random_state=SEED,
    n_jobs=-1,
)


def main() -> None:
    total_features = len(NUMERIC_FEATURES) + len(CATEGORICAL_FEATURES)
    print(f"Numeric features ({len(NUMERIC_FEATURES)}): {NUMERIC_FEATURES}")
    print(f"Categorical features ({len(CATEGORICAL_FEATURES)}): {CATEGORICAL_FEATURES}")
    print(f"Total: {total_features} (removed: {REMOVED_FEATURES})")
    if total_features != 11:
        raise ValueError(f"Expected 11 features, got {total_features}")

    dataframe = pd.read_csv(DATA_PATH)

    with np.load(EXISTING_SPLITS_PATH) as splits:
        train_idx = splits["train_original_idx"]
        val_idx = splits["val_original_idx"]
        test_idx = splits["test_original_idx"]
        y_train = splits["y_train"]
        y_val = splits["y_val"]
        y_test = splits["y_test"]

    train_rows = dataframe.iloc[train_idx]
    val_rows = dataframe.iloc[val_idx]
    test_rows = dataframe.iloc[test_idx]

    # --- Step 1: build + fit new preprocessor on TRAIN rows only ---
    print("\n--- Step 1: fit new 11-feature preprocessor on train rows only ---")
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    x_train = preprocessor.fit_transform(train_rows[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
    x_val = preprocessor.transform(val_rows[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
    # Test set IS transformed here (explicitly authorized) but NEVER evaluated below.
    x_test = preprocessor.transform(test_rows[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
    print(f"Shapes: X_train={x_train.shape}, X_val={x_val.shape}, X_test={x_test.shape} (transformed, not evaluated)")

    # --- Step 2: save new preprocessor + splits (does NOT touch the 17-feature files) ---
    NEW_PREPROCESSOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(preprocessor, NEW_PREPROCESSOR_PATH)
    print(f"\n--- Step 2: saved new files ---")
    print(f"Saved: {NEW_PREPROCESSOR_PATH.relative_to(ROOT)}")

    np.savez(
        NEW_SPLITS_PATH,
        X_train=x_train,
        X_val=x_val,
        X_test=x_test,
        y_train=y_train,
        y_val=y_val,
        y_test=y_test,
        train_original_idx=train_idx,
        val_original_idx=val_idx,
        test_original_idx=test_idx,
    )
    print(f"Saved: {NEW_SPLITS_PATH.relative_to(ROOT)}")

    # --- Step 3: retrain tuned RF on new X_train, save ---
    print("\n--- Step 3: retrain tuned Random Forest on 11-feature X_train ---")
    model = RandomForestClassifier(**TUNED_RF_PARAMS)
    model.fit(x_train, y_train)
    joblib.dump(model, NEW_MODEL_PATH)
    print(f"Saved: {NEW_MODEL_PATH.relative_to(ROOT)}")

    # --- Step 4: verify against documented feature_reduction_3class.md numbers ---
    print("\n--- Step 4: verification against reports/feature_reduction_3class.md ---")
    # Reload from disk to verify the SAVED artifacts (not just the in-memory objects)
    reloaded_model = joblib.load(NEW_MODEL_PATH)
    with np.load(NEW_SPLITS_PATH) as reloaded_splits:
        reloaded_x_val = reloaded_splits["X_val"]
        reloaded_y_val = reloaded_splits["y_val"]

    predictions = reloaded_model.predict(reloaded_x_val)
    computed_accuracy = float(accuracy_score(reloaded_y_val, predictions))
    computed_balanced_accuracy = float(balanced_accuracy_score(reloaded_y_val, predictions))
    computed_macro_f1 = float(f1_score(reloaded_y_val, predictions, average="macro"))

    accuracy_match = abs(computed_accuracy - EXPECTED_ACCURACY) < TOLERANCE
    balanced_accuracy_match = abs(computed_balanced_accuracy - EXPECTED_BALANCED_ACCURACY) < TOLERANCE
    macro_f1_match = abs(computed_macro_f1 - EXPECTED_MACRO_F1) < TOLERANCE
    all_match = accuracy_match and balanced_accuracy_match and macro_f1_match

    print(f"  accuracy:          computed={computed_accuracy:.6f}  expected={EXPECTED_ACCURACY:.4f}  match={accuracy_match}")
    print(f"  balanced_accuracy: computed={computed_balanced_accuracy:.6f}  expected={EXPECTED_BALANCED_ACCURACY:.4f}  match={balanced_accuracy_match}")
    print(f"  macro_f1:          computed={computed_macro_f1:.6f}  expected={EXPECTED_MACRO_F1:.4f}  match={macro_f1_match}")
    print(f"\n  ALL METRICS MATCH: {all_match}")

    if not all_match:
        raise RuntimeError(
            "VERIFICATION FAILED: reloaded 11-feature model's validation metrics do not "
            "reproduce reports/feature_reduction_3class.md's documented numbers. STOPPING - "
            "do not treat the newly saved files as verified/canonical until this is resolved."
        )

    print("\nVerification passed. New 11-feature artifacts saved and confirmed reproducible.")
    print("NOT touched: 17-feature preprocessor/splits/model, test-set evaluation, "
          "predict_single.py, API.")


if __name__ == "__main__":
    main()
