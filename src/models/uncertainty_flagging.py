"""Uncertainty flagging (Phase 16) for the tuned Random Forest, 3-class
Anxiety Level target.

Production rule: flag a validation row "borderline - recommend review" if
P(High) >= 0.10.

Why 0.10: this is the ~10% marginal base rate of the High class in this
dataset, so the threshold is not arbitrary — it flags any row where the
model assigns High at least its unconditional prior likelihood, i.e. any
row where the model sees more High-risk signal than "no information at
all" would predict. It is intentionally NOT gated on High being the
model's top prediction: the flag is not deciding who gets reviewed (every
prediction already goes through mandatory psychologist review per this
project's approval workflow — see CLAUDE.md's "Critical workflow
constraint"), it exists to *reprioritize* review attention toward rows the
model considers plausibly High-risk even when it argmaxed to Medium or Low.
Gatekeeping access to review is out of scope; this only helps a
psychologist triage which cases to look at first/more closely.

A margin-based trigger (flag when the top-2 predicted-class probabilities
are close) was evaluated and dropped: a threshold sweep
(reports/threshold_sweep_high.py / threshold_sweep_high.md) showed the
margin trigger caught 0 of the 17 known True-High/Predicted-Medium misses
while driving most of the flagged volume, because on those rows P(Medium)
dominates so strongly that the top-1/top-2 gap looks decisive even though
the top prediction is wrong. The P(High) trigger is what actually catches
those cases (9/17 at this threshold), so it is kept alone.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier


SEED = 42
HIGH_PROBA_THRESHOLD = 0.10  # ~10% marginal base rate of High in this target
ROOT = Path(__file__).resolve().parents[2]
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_3class.npz"
REPORT_PATH = ROOT / "reports" / "uncertainty_flagging.md"

CLASS_NAMES = ["Low", "Medium", "High"]
HIGH_INDEX = CLASS_NAMES.index("High")
MEDIUM_INDEX = CLASS_NAMES.index("Medium")

# Tuned Random Forest best params from reports/tuning_results_3class.json
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


def build_baseline_models() -> dict[str, object]:
    """Same untuned baseline models used in train_baselines_3class.py,
    reproduced here only to re-identify the 17 known unanimous misses."""
    return {
        "logistic_regression": LogisticRegression(max_iter=2000, random_state=SEED),
        "random_forest": RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1),
        "xgboost": XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.1, subsample=0.8,
            colsample_bytree=0.8, objective="multi:softprob", eval_metric="mlogloss",
            random_state=SEED, n_jobs=-1,
        ),
    }


def flag_borderline(probabilities: np.ndarray) -> np.ndarray:
    """Production uncertainty-flagging rule: P(High) >= HIGH_PROBA_THRESHOLD."""
    return probabilities[:, HIGH_INDEX] >= HIGH_PROBA_THRESHOLD


def main() -> None:
    splits = np.load(SPLITS_PATH)
    x_train, y_train = splits["X_train"], splits["y_train"]
    x_val, y_val = splits["X_val"], splits["y_val"]
    val_original_idx = splits["val_original_idx"]

    tuned_rf = RandomForestClassifier(**TUNED_RF_PARAMS)
    tuned_rf.fit(x_train, y_train)
    probabilities = tuned_rf.predict_proba(x_val)
    predictions = tuned_rf.predict(x_val)
    p_high = probabilities[:, HIGH_INDEX]

    flagged = flag_borderline(probabilities)
    n_val = len(y_val)
    n_flagged = int(flagged.sum())
    fraction_flagged = n_flagged / n_val

    correctly_classified = predictions == y_val

    print("Tuned Random Forest (3-class) — uncertainty flagging on X_val (n=%d)" % n_val)
    print(f"\nFlag rule: P(High) >= {HIGH_PROBA_THRESHOLD}")
    print(f"\nOverall flagged: {n_flagged} / {n_val} = {fraction_flagged:.4f}")

    # --- False-flag rate: of flagged rows, what fraction were correctly classified anyway ---
    n_flagged_correct = int((flagged & correctly_classified).sum())
    false_flag_rate = n_flagged_correct / n_flagged if n_flagged else float("nan")
    print(f"\nFalse-flag rate (flagged rows that were actually already correct): "
          f"{n_flagged_correct} / {n_flagged} = {false_flag_rate:.4f}")

    # --- Re-identify the 17 known unanimous True-High/Predicted-Medium misses ---
    baseline_models = build_baseline_models()
    baseline_predictions = {}
    for name, model in baseline_models.items():
        model.fit(x_train, y_train)
        baseline_predictions[name] = model.predict(x_val)

    true_high = y_val == HIGH_INDEX
    all_predicted_medium = (
        (baseline_predictions["logistic_regression"] == MEDIUM_INDEX)
        & (baseline_predictions["random_forest"] == MEDIUM_INDEX)
        & (baseline_predictions["xgboost"] == MEDIUM_INDEX)
    )
    miss_mask = true_high & all_predicted_medium
    miss_positions = np.where(miss_mask)[0]
    n_misses = len(miss_positions)

    misses_flagged = flagged[miss_positions]
    n_misses_flagged = int(misses_flagged.sum())
    fraction_misses_flagged = n_misses_flagged / n_misses

    print(f"\n=== KEY NUMBER: coverage of the 17 known True-High/Predicted-Medium misses ===")
    print(f"Flagged: {n_misses_flagged} / {n_misses} = {fraction_misses_flagged:.4f}")

    n_true_high = int(true_high.sum())
    true_high_flagged = int(flagged[true_high].sum())
    print(f"\nFor context, True-High rows overall flagged: "
          f"{true_high_flagged} / {n_true_high} = {true_high_flagged / n_true_high:.4f}")

    miss_original_rows = val_original_idx[miss_positions]
    miss_table = []
    print(f"\n{'orig_row':>10} {'P(High)':>8} {'predicted':>10} {'flagged':>8}")
    for pos, orig_row in zip(miss_positions, miss_original_rows):
        row_flagged = bool(flagged[pos])
        print(f"{orig_row:>10} {p_high[pos]:>8.4f} "
              f"{CLASS_NAMES[predictions[pos]]:>10} {str(row_flagged):>8}")
        miss_table.append(
            {
                "original_row": int(orig_row),
                "p_high": float(p_high[pos]),
                "predicted": CLASS_NAMES[predictions[pos]],
                "flagged": row_flagged,
            }
        )

    # --- Write report ---
    lines: list[str] = [
        "# Uncertainty Flagging Report (Phase 16, FINAL) — Tuned Random Forest, 3-Class Target",
        "",
        "## Scope",
        "",
        "- Model: tuned Random Forest (n_estimators=200, max_depth=10, min_samples_split=10,"
        " min_samples_leaf=4, max_features='sqrt', class_weight='balanced') from"
        " `reports/tuning_results_3class.json`.",
        "- Evaluation: `X_val`/`y_val` from `mindcare_processed_splits_3class.npz`; test set untouched.",
        f"- Validation rows: {n_val}; seed: {SEED}.",
        "",
        "## Flag Rule (Production, Finalized)",
        "",
        f"A row is flagged **\"borderline — recommend review\"** if P(High) >= {HIGH_PROBA_THRESHOLD}"
        f" (the ~10% marginal base rate of High), unconditional on the predicted class.",
        "",
        "This does not gate access to review — every prediction is already reviewed by a"
        " psychologist per this project's approval workflow — it reprioritizes review attention"
        " toward rows the model considers plausibly High-risk even when it did not predict High.",
        "",
        "A margin-based trigger was evaluated and dropped: it caught 0 of the 17 known"
        " True-High/Predicted-Medium misses while driving most of the flagged volume (see"
        " `reports/threshold_sweep_high.md`), so only the P(High) trigger is kept.",
        "",
        "## Overall Flagging Rate",
        "",
        f"**Flagged: {n_flagged} / {n_val} = {fraction_flagged:.4f}**",
        "",
        "## Key Number: Coverage of the 17 Known True-High/Predicted-Medium Misses",
        "",
        f"These are the validation rows where the true label is High and the three untuned baseline"
        f" models (Logistic Regression, Random Forest, XGBoost) all predicted Medium"
        f" (`reports/baseline_results_3class.json`, `reports/calibration_3class.md`).",
        "",
        f"**Flagged: {n_misses_flagged} / {n_misses} = {fraction_misses_flagged:.4f}**",
        "",
        f"For context, True-High rows overall flagged: {true_high_flagged} / {n_true_high} ="
        f" {true_high_flagged / n_true_high:.4f} (most already-correct High predictions also cross"
        f" this threshold, since P(High) is naturally high when High is the top prediction).",
        "",
        "| Original row | P(High) | Tuned-RF predicted | Flagged |",
        "|---:|---:|---|---|",
    ]
    for row in miss_table:
        lines.append(
            f"| {row['original_row']} | {row['p_high']:.4f} |"
            f" {row['predicted']} | {row['flagged']} |"
        )
    lines.extend(
        [
            "",
            "## False-Flag Rate (Cost of Extra Review)",
            "",
            f"Of the {n_flagged} rows flagged, {n_flagged_correct} were already correctly classified"
            f" by the tuned Random Forest.",
            "",
            f"**False-flag rate: {n_flagged_correct} / {n_flagged} = {false_flag_rate:.4f}**",
            "",
            "This is high mainly because the rule is unconditional: correctly-classified True-High"
            " rows also cross the threshold and get flagged, which is intended (they should also"
            " get priority attention), not a defect of the rule.",
            "",
            "## Interpretation",
            "",
            "Prototype-model metrics on a very likely synthetic dataset (see CLAUDE.md); not"
            " clinical validation. This flagging mechanism does not change any prediction — it only"
            " marks rows for prioritized psychologist review, consistent with the project's"
            " AI-prediction-then-psychologist-review workflow constraint.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved report to {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
