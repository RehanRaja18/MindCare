"""Compute SHAP feature importance for the tuned Random Forest, 3-class
Anxiety Level target. Mirrors shap_analysis.py's approach; also checks
whether Stress Level still dominates given the weaker correlation (0.65 vs
0.91) documented in CLAUDE.md for this target vs the 5-class Severity target.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import shap
from sklearn.ensemble import RandomForestClassifier


SEED = 42
SAMPLE_SIZE = 500  # >= 200 required
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
PLOT_PATH = ROOT / "reports" / "shap_summary_3class.png"
REPORT_PATH = ROOT / "reports" / "shap_summary_3class.md"

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

    model = RandomForestClassifier(**RF_PARAMS)
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
    print("Top 10 features by mean absolute SHAP value (3-class Anxiety Level target):")
    for rank, (name, importance) in enumerate(top_features, start=1):
        print(f"{rank:2d}. {name}: {importance:.8f}")

    stress_rank = next(
        rank for rank, (name, _) in enumerate(ranking, start=1)
        if name == "Stress Level (1-10)"
    )
    stress_dominates = stress_rank == 1
    stress_value = next(value for name, value in ranking if name == "Stress Level (1-10)")
    second_place_name, second_place_value = ranking[1] if stress_dominates else ranking[0]
    margin_ratio = stress_value / second_place_value if stress_dominates else None

    print(f"\nStress Level (1-10) SHAP rank: {stress_rank}/{len(ranking)}")
    print(f"Stress Level dominates (rank 1): {'yes' if stress_dominates else 'no'}")
    if stress_dominates:
        print(
            f"Margin over 2nd place ({second_place_name}): "
            f"{stress_value:.8f} vs {second_place_value:.8f} "
            f"({margin_ratio:.2f}x)"
        )

    top_names = [name for name, _ in top_features]
    plot_names = top_names[::-1]
    plot_values = [importance for _, importance in ranking[:10]][::-1]
    fig, axis = plt.subplots(figsize=(10, 7))
    axis.barh(plot_names, plot_values, color="#1f6f8b")
    axis.set_xlabel("Mean absolute SHAP value")
    axis.set_title("Tuned Random Forest SHAP Feature Importance (3-Class Anxiety Level)")
    fig.tight_layout()
    PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOT_PATH, dpi=200)
    plt.close(fig)
    print(f"Saved plot to {PLOT_PATH.relative_to(ROOT)}")

    # --- Write report ---
    lines: list[str] = [
        "# SHAP Feature Importance Report — 3-Class Anxiety Level Target",
        "",
        "## Scope",
        "",
        "- Model: tuned Random Forest from `reports/tuning_results_3class.json`"
        " (n_estimators=200, max_depth=10, min_samples_split=10,"
        " min_samples_leaf=4, max_features='sqrt', class_weight='balanced').",
        "- Training: existing `X_train`/`y_train` only.",
        f"- SHAP computed on a sample of {sample_size} rows from `X_val`"
        " (`mindcare_processed_splits_3class.npz`); test set untouched.",
        f"- Seed: {SEED}.",
        "",
        "## Top 10 Features by Mean Absolute SHAP Value",
        "",
        "| Rank | Feature | Mean |SHAP| |",
        "|---:|---|---:|",
    ]
    for rank, (name, importance) in enumerate(top_features, start=1):
        lines.append(f"| {rank} | {name} | {importance:.8f} |")

    lines.extend(
        [
            "",
            "## Does Stress Level Still Dominate?",
            "",
            f"Stress Level (1-10) SHAP rank: **{stress_rank} / {len(ranking)}**",
            "",
        ]
    )
    if stress_dominates:
        lines.append(
            f"**Yes — Stress Level still ranks #1**, but at a reduced margin over 2nd place"
            f" ({second_place_name}): {stress_value:.8f} vs {second_place_value:.8f}"
            f" ({margin_ratio:.2f}x). This is consistent with CLAUDE.md's documented finding"
            f" that Stress Level correlates 0.65 (ordinal) with this 3-class target, vs 0.91"
            f" with the 5-class Severity target — still the top feature, but less singularly"
            f" dominant."
        )
    else:
        lines.append(
            f"**No — Stress Level does NOT rank #1 by SHAP for this target.** It ranks"
            f" {stress_rank}, behind {ranking[0][0]} ({ranking[0][1]:.8f} vs Stress Level's"
            f" {stress_value:.8f}). This contradicts the expectation stated in the prompt"
            f" (that Stress Level dominates 'at a reduced margin') — the correlation finding in"
            f" CLAUDE.md (0.65 for 3-class) establishes Stress Level as A top feature, not"
            f" necessarily THE top feature by SHAP once the full feature interaction structure"
            f" of the tuned Random Forest is accounted for. Reporting this as-is rather than"
            f" the expected result."
        )
    lines.extend(
        [
            "",
            f"![SHAP summary]({PLOT_PATH.name})",
            "",
            "## Interpretation",
            "",
            "Prototype-model metrics on a very likely synthetic dataset (see CLAUDE.md); not"
            " clinical validation. SHAP importance here is mean absolute SHAP value across all"
            " 3 classes (Low/Medium/High) and the sampled validation rows, not a single-class"
            " or single-row explanation.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
