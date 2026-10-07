"""Complete SHAP feature importance ranking (all 34 transformed columns),
tuned Random Forest, 3-class Anxiety Level target - grouped back to the
17 original raw features for readability.

Uses the exact same model/sample setup as shap_analysis_3class.py (same
seed, same 500-row sample) so the per-column values here are directly
consistent with reports/shap_summary_3class.md's top-10 table, just
extended to all 34 columns and then grouped.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import shap
from sklearn.ensemble import RandomForestClassifier


SEED = 42
SAMPLE_SIZE = 500
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
REPORT_PATH = ROOT / "reports" / "shap_full_ranking_3class.md"

# Tuned Random Forest best params from reports/tuning_results_3class.json
RF_PARAMS = dict(
    n_estimators=200,
    max_depth=10,
    min_samples_split=10,
    min_samples_leaf=4,
    max_features="sqrt",
    class_weight="balanced",
    random_state=SEED,
    n_jobs=-1,
)

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
    "Artist", "Athlete", "Chef", "Doctor", "Engineer", "Freelancer", "Lawyer",
    "Musician", "Nurse", "Other", "Scientist", "Student", "Teacher",
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
    categorical_names = [f"Occupation={occupation}" for occupation in OCCUPATIONS]
    categorical_names.extend(
        f"{feature}={value}" for feature in BINARY_FEATURES for value in ("No", "Yes")
    )
    names = NUMERIC_FEATURES + categorical_names
    if len(names) != 34:
        raise ValueError(f"Expected 34 transformed features, got {len(names)}")
    return names


def original_feature_of(transformed_name: str) -> str:
    """Map a transformed column name back to its original raw feature name."""
    if transformed_name in NUMERIC_FEATURES:
        return transformed_name
    if transformed_name.startswith("Occupation="):
        return "Occupation"
    for feature in BINARY_FEATURES:
        if transformed_name.startswith(f"{feature}="):
            return feature
    raise ValueError(f"Could not map transformed column to an original feature: {transformed_name}")


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

    model = RandomForestClassifier(**RF_PARAMS)
    model.fit(x_train, y_train)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(validation_sample)
    importances = mean_absolute_shap_values(shap_values)
    feature_names = transformed_feature_names()

    full_ranking = sorted(zip(feature_names, importances), key=lambda item: item[1], reverse=True)

    # --- Group the 23 categorical dummy columns back into their 6 original features ---
    grouped: dict[str, float] = {}
    contributors: dict[str, list[tuple[str, float]]] = {}
    for name, importance in zip(feature_names, importances):
        original = original_feature_of(name)
        grouped[original] = grouped.get(original, 0.0) + float(importance)
        contributors.setdefault(original, []).append((name, float(importance)))

    grouped_ranking = sorted(grouped.items(), key=lambda item: item[1], reverse=True)

    if len(grouped_ranking) != 17:
        raise ValueError(f"Expected 17 grouped original features, got {len(grouped_ranking)}")

    print(f"SHAP sample rows: {sample_size}\n")
    print("=== FULL 34-column ranking (transformed/one-hot-encoded features) ===")
    for rank, (name, importance) in enumerate(full_ranking, start=1):
        print(f"{rank:2d}. {name}: {importance:.8f}")

    print("\n=== GROUPED 17-feature ranking (categorical dummies summed back to original feature) ===")
    for rank, (name, importance) in enumerate(grouped_ranking, start=1):
        n_cols = len(contributors[name])
        print(f"{rank:2d}. {name}: {importance:.8f}" + (f"  (sum of {n_cols} dummy columns)" if n_cols > 1 else ""))

    # --- Write report ---
    lines: list[str] = [
        "# Complete SHAP Feature Importance Ranking — 3-Class Anxiety Level Target",
        "",
        "## Scope",
        "",
        "- Model: tuned Random Forest from `reports/tuning_results_3class.json`"
        " (n_estimators=200, max_depth=10, min_samples_split=10,"
        " min_samples_leaf=4, max_features='sqrt', class_weight='balanced').",
        "- Training: existing `X_train`/`y_train` only.",
        f"- SHAP computed on the same {sample_size}-row sample of `X_val` as"
        " `reports/shap_summary_3class.md`, for direct consistency; test set untouched.",
        f"- Seed: {SEED}.",
        "- Importance = mean absolute SHAP value across all 3 classes and sampled rows.",
        "",
        "## Grouped Ranking — 17 Original Features (Primary Result)",
        "",
        "The 23 one-hot categorical columns (13 for Occupation, 2 each for the 5 binary"
        " features) are summed back to their original raw feature. Numeric features are"
        " unchanged (1 column each, no grouping needed).",
        "",
        "| Rank | Feature | Mean \\|SHAP\\| | Type | Columns summed |",
        "|---:|---|---:|---|---:|",
    ]
    for rank, (name, importance) in enumerate(grouped_ranking, start=1):
        feature_type = "Numeric" if name in NUMERIC_FEATURES else "Categorical"
        n_cols = len(contributors[name])
        lines.append(f"| {rank} | {name} | {importance:.8f} | {feature_type} | {n_cols} |")

    lines.extend(
        [
            "",
            "## Full 34-Column Ranking (Transformed / One-Hot-Encoded Features)",
            "",
            "Shown for transparency — this is the raw basis the grouped table above was"
            " computed from. Top 10 here reproduce `reports/shap_summary_3class.md` exactly.",
            "",
            "| Rank | Transformed column | Mean \\|SHAP\\| | Original feature |",
            "|---:|---|---:|---|",
        ]
    )
    for rank, (name, importance) in enumerate(full_ranking, start=1):
        lines.append(f"| {rank} | {name} | {importance:.8f} | {original_feature_of(name)} |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Prototype-model metrics on a very likely synthetic dataset (see `CLAUDE.md`); not"
            " clinical validation. Grouping by summing dummy-column importances is a standard,"
            " if approximate, convention for one-hot-encoded categorical features — it can"
            " overstate a high-cardinality feature's importance relative to a max-based"
            " grouping, since Occupation's importance here is a sum over 13 columns while each"
            " binary feature's is a sum over only 2. This is worth keeping in mind when comparing"
            " Occupation's rank directly against the binary categoricals.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
