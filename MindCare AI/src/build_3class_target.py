"""Build a new 3-class (Low/Medium/High) target from raw Anxiety Level (1-10),
reusing the existing preprocessed feature splits and split membership.

Does NOT re-split or re-preprocess anything: X_train/X_val/X_test and the
original row-index arrays are carried over unchanged from
mindcare_processed_splits.npz. Only y_train/y_val/y_test are rebuilt, from
Anxiety Level (1-10) binned directly (independent of the existing Severity
target/label encoder).
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits.npz"
OUT_SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
OUT_LABEL_ENCODER_PATH = ROOT / "data" / "processed" / "mindcare_label_encoder_3class.pkl"

ANXIETY_COLUMN = "Anxiety Level (1-10)"
CLASS_NAMES = ["Low", "Medium", "High"]  # index 0, 1, 2 respectively

EXPECTED_COUNTS = {"train": 7700, "val": 1650, "test": 1650}


def bin_anxiety_level(values: np.ndarray) -> np.ndarray:
    codes = np.full(len(values), -1, dtype=np.int64)
    codes[(values >= 1) & (values <= 3)] = 0  # Low
    codes[(values >= 4) & (values <= 6)] = 1  # Medium
    codes[(values >= 7) & (values <= 10)] = 2  # High
    unbinned = codes == -1
    if np.any(unbinned):
        raise ValueError(
            f"Anxiety Level values outside 1-10 binning range: {np.unique(values[unbinned])}"
        )
    return codes


def main() -> None:
    dataframe = pd.read_csv(DATA_PATH)
    splits = np.load(SPLITS_PATH)

    x_train, x_val, x_test = splits["X_train"], splits["X_val"], splits["X_test"]
    train_idx = splits["train_original_idx"]
    val_idx = splits["val_original_idx"]
    test_idx = splits["test_original_idx"]

    anxiety_level = dataframe[ANXIETY_COLUMN].to_numpy()

    y_train = bin_anxiety_level(anxiety_level[train_idx])
    y_val = bin_anxiety_level(anxiety_level[val_idx])
    y_test = bin_anxiety_level(anxiety_level[test_idx])

    np.savez(
        OUT_SPLITS_PATH,
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

    label_encoder = LabelEncoder()
    label_encoder.classes_ = np.array(CLASS_NAMES)
    joblib.dump(label_encoder, OUT_LABEL_ENCODER_PATH)

    print(f"saved: {OUT_SPLITS_PATH.relative_to(ROOT)}")
    print(f"saved: {OUT_LABEL_ENCODER_PATH.relative_to(ROOT)}")

    print("\nClass distribution:")
    all_match = True
    for split_name, y, expected in [
        ("train", y_train, EXPECTED_COUNTS["train"]),
        ("val", y_val, EXPECTED_COUNTS["val"]),
        ("test", y_test, EXPECTED_COUNTS["test"]),
    ]:
        counts = np.bincount(y, minlength=len(CLASS_NAMES))
        total = int(counts.sum())
        match = total == expected
        all_match = all_match and match
        print(f"  {split_name} (n={total}, expected={expected}, {'MATCH' if match else 'MISMATCH'}):")
        for class_index, class_name in enumerate(CLASS_NAMES):
            count = int(counts[class_index])
            frac = count / total
            print(f"    {class_name}: {count} ({frac:.4f})")

    print(f"\nAll row counts match original 5-class split: {all_match}")


if __name__ == "__main__":
    main()
