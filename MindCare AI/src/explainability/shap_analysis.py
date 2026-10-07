"""Compute SHAP feature importance for the tuned Random Forest model."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import shap
from sklearn.ensemble import RandomForestClassifier


SEED = 42
SAMPLE_SIZE = 500
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits.npz"
PLOT_PATH = ROOT / "reports" / "shap_summary.png"

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
OCCUPATIONS = [
    "Artist",
    "Athlete",
    "Chef",
    "Doctor",
    "Engineer",
    "Freelancer",
    "Lawyer",
    "Musician",
    "Nurse",
    "Other",
    "Scientist",
    "Student",
    "Teacher",
]
BINARY_FEATURES = [
    "Smoking",
    "Family History of Anxiety",
    "Dizziness",
    "Medication",
    "Recent Major Life Event",
]


def load_splits() -> dict[str, np.ndarray]:
    with np.load(SPLITS_PATH) as splits:
        return {name: splits[name] for name in splits.files}


def transformed_feature_names() -> list[str]:
    categorical_names = [
        f"Occupation={occupation}" for occupation in OCCUPATIONS
    ]
    categorical_names.extend(
        f"{feature}={value}"
        for feature in BINARY_FEATURES
        for value in ("No", "Yes")
    )
    names = NUMERIC_FEATURES + categorical_names
    if len(names) != 34:
        raise ValueError(f"Expected 34 transformed features, got {len(names)}")
    return names


def mean_absolute_shap_values(shap_values: object) -> np.ndarray:
    values = shap_values
    if isinstance(values, list):
        return np.mean(
            np.stack([np.abs(class_values) for class_values in values], axis=0),
            axis=(0, 1),
        )

    array = np.asarray(values)
    if array.ndim == 3:
        return np.mean(np.abs(array), axis=(0, 2))
    if array.ndim == 2:
        return np.mean(np.abs(array), axis=0)
    raise ValueError(f"Unexpected SHAP value shape: {array.shape}")


def main() -> None:
    splits = load_splits()
    x_train, y_train = splits["X_train"], splits["y_train"]
    x_val = splits["X_val"]
    sample_size = min(SAMPLE_SIZE, len(x_val))
    validation_sample = x_val[:sample_size]

    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=30,
        min_samples_split=10,
        min_samples_leaf=4,
        max_features="sqrt",
        class_weight="balanced",
        random_state=SEED,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(validation_sample)
    importances = mean_absolute_shap_values(shap_values)
    feature_names = transformed_feature_names()
    ranking = sorted(
        zip(feature_names, importances), key=lambda item: item[1], reverse=True
    )

    top_features = ranking[:10]
    print(f"SHAP sample rows: {sample_size}")
    print("Top 10 features by mean absolute SHAP value:")
    for rank, (name, importance) in enumerate(top_features, start=1):
        print(f"{rank:2d}. {name}: {importance:.8f}")
    stress_rank = next(
        rank for rank, (name, _) in enumerate(ranking, start=1)
        if name == "Stress Level (1-10)"
    )
    print(f"Stress Level (1-10) SHAP rank: {stress_rank}/{len(ranking)}")
    print(
        "Stress Level dominates: "
        f"{'yes' if stress_rank == 1 else 'no'}"
    )

    top_names = [name for name, _ in top_features]
    plot_names = top_names[::-1]
    plot_values = [importance for _, importance in ranking[:10]][::-1]
    fig, axis = plt.subplots(figsize=(10, 7))
    axis.barh(plot_names, plot_values, color="#1f6f8b")
    axis.set_xlabel("Mean absolute SHAP value")
    axis.set_title("Tuned Random Forest SHAP Feature Importance")
    fig.tight_layout()
    PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOT_PATH, dpi=200)
    plt.close(fig)
    print(f"Saved plot to {PLOT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()