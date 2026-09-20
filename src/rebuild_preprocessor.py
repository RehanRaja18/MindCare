"""Rebuild preprocessing artifacts with the current environment's scikit-learn."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler


SEED = 42
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits.npz"
PREPROCESSOR_PATH = ROOT / "data" / "processed" / "mindcare_preprocessor.pkl"
LABEL_ENCODER_PATH = ROOT / "data" / "processed" / "mindcare_label_encoder.pkl"

NUMERIC_FEATURES = [
    "Age",
    "Sleep Hours",
    "Physical Activity (hrs/week)",
    "Caffeine Intake (mg/day)",
    "Alcohol Consumption (drinks/week)",
    "Stress Level (1-10)",
    "Heart Rate (bpm)",
    "Breathing Rate (breaths/min)",
    "Sweating Level (1-5)",
    "Therapy Sessions (per month)",
    "Diet Quality (1-10)",
]
CATEGORICAL_FEATURES = [
    "Occupation",
    "Smoking",
    "Family History of Anxiety",
    "Dizziness",
    "Medication",
    "Recent Major Life Event",
]


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
        ]
    )


def main() -> None:
    dataframe = pd.read_csv(DATA_PATH)
    features = dataframe[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    label_encoder = LabelEncoder()
    labels = label_encoder.fit_transform(dataframe["Severity"])

    x_train, x_temp, y_train, y_temp = train_test_split(
        features,
        labels,
        test_size=0.30,
        random_state=SEED,
        stratify=labels,
    )
    x_val, x_test, y_val, y_test = train_test_split(
        x_temp,
        y_temp,
        test_size=0.50,
        random_state=SEED,
        stratify=y_temp,
    )

    preprocessor = build_preprocessor()
    candidate_arrays = {
        "X_train": np.asarray(preprocessor.fit_transform(x_train)),
        "X_val": np.asarray(preprocessor.transform(x_val)),
        "X_test": np.asarray(preprocessor.transform(x_test)),
    }
    candidate_targets = {
        "y_train": y_train,
        "y_val": y_val,
        "y_test": y_test,
    }

    existing_names = ["X_train", "X_val", "X_test", "y_train", "y_val", "y_test"]
    before_arrays: dict[str, np.ndarray] = {}
    with np.load(SPLITS_PATH) as saved:
        for name, candidate in {**candidate_arrays, **candidate_targets}.items():
            if not np.array_equal(candidate.shape, saved[name].shape):
                raise ValueError(f"Shape mismatch for {name}")
            if name.startswith("X_"):
                matches = np.allclose(candidate, saved[name])
            else:
                matches = np.array_equal(candidate, saved[name])
            if not matches:
                raise ValueError(f"Saved split mismatch for {name}; refusing overwrite")
        for name in existing_names:
            before_arrays[name] = np.array(saved[name])

    train_original_idx = x_train.index.to_numpy()
    val_original_idx = x_val.index.to_numpy()
    test_original_idx = x_test.index.to_numpy()

    joblib.dump(preprocessor, PREPROCESSOR_PATH)
    joblib.dump(label_encoder, LABEL_ENCODER_PATH)

    np.savez(
        SPLITS_PATH,
        X_train=candidate_arrays["X_train"],
        X_val=candidate_arrays["X_val"],
        X_test=candidate_arrays["X_test"],
        y_train=candidate_targets["y_train"],
        y_val=candidate_targets["y_val"],
        y_test=candidate_targets["y_test"],
        train_original_idx=train_original_idx,
        val_original_idx=val_original_idx,
        test_original_idx=test_original_idx,
    )

    print(f"scikit-learn: {sklearn.__version__}")
    print("verified arrays: X_train, X_val, X_test, y_train, y_val, y_test")
    print("all split comparisons: PASS")
    print(f"saved: {PREPROCESSOR_PATH.relative_to(ROOT)}")
    print(f"saved: {LABEL_ENCODER_PATH.relative_to(ROOT)}")
    print(f"saved (with added index arrays): {SPLITS_PATH.relative_to(ROOT)}")

    print("\n--- Verification 2a: existing arrays unchanged by this rewrite ---")
    with np.load(SPLITS_PATH) as after:
        all_unchanged = True
        for name in existing_names:
            unchanged = np.array_equal(before_arrays[name], after[name])
            all_unchanged = all_unchanged and unchanged
            print(f"  {name}: array_equal(before, after) = {unchanged}")
        print(f"  ALL UNCHANGED: {all_unchanged}")

    print("\n--- Verification 2b: val_original_idx reproduces saved y_val ---")
    loaded_label_encoder = joblib.load(LABEL_ENCODER_PATH)
    with np.load(SPLITS_PATH) as after:
        raw_severity_at_val = dataframe.iloc[after["val_original_idx"]]["Severity"]
        reencoded_y_val = loaded_label_encoder.transform(raw_severity_at_val)
        matches_y_val = np.array_equal(reencoded_y_val, after["y_val"])
        print(f"  array_equal(reencoded_y_val, saved y_val): {matches_y_val}")
        print(f"  lengths: {len(reencoded_y_val)} {len(after['y_val'])}")
        print(f"  reencoded first 10: {reencoded_y_val[:10]}")
        print(f"  saved y_val first 10: {after['y_val'][:10]}")


if __name__ == "__main__":
    main()