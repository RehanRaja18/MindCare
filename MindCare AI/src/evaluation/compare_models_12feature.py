"""Step 2 of the RF-vs-XGBoost comparison: run the full analysis suite on the
12-feature data for three candidates, side by side, VALIDATION + TRAIN only:

  - rf_current: the canonical model the API serves today
    (data/processed/mindcare_final_model_12feature.pkl - RF params tuned on
    the old 17 features).
  - rf_retuned / xgb_retuned: both re-tuned on the 12 features under one
    identical procedure (src/models/tune_models_12feature.py,
    reports/tuning_results_12feature.json), refit here from those params.

Analyses (each mirrors the method of the earlier 17-feature phase script):
  1. Headline + per-class metrics, confusion matrix, AUROC/AUPRC (Phase 14).
  2. Stability: 5-fold CV on train (same folds for all) and 5 random seeds.
  3. Calibration: log loss, per-class Brier, 10-bin expected calibration
     error (Phase 15).
  4. Uncertainty flag: the production rule P(High) >= 0.10 (the High base
     rate - model-agnostic, not tuned to any model), plus review workload at
     equal High recall (Phase 16).
  5. SHAP: mean |SHAP| per original feature, on a fixed validation sample
     (Phase 17).
  6. Fairness: per-occupation, age-band and gender balanced accuracy and High
     recall (Phase 18).
  7. Robustness: single-feature knockout (train mean/mode), Gaussian noise,
     Stress Level shift, Age sensitivity (Phase 19).
  8. Practical: single-prediction latency and pickled size.

The 12-feature splits file has no test arrays; nothing here touches the test
set. Writes reports/model_comparison_12feature.md and .json.
"""

from __future__ import annotations

import json
import pickle
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import label_binarize
from xgboost import XGBClassifier

from src.inference.input_validation import ALL_FEATURES, CATEGORICAL_ALLOWED

SEED = 42
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_12feature.npz"
PREPROCESSOR_PATH = ROOT / "data" / "processed" / "mindcare_preprocessor_12feature.pkl"
CURRENT_MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model_12feature.pkl"
TUNING_PATH = ROOT / "reports" / "tuning_results_12feature.json"
REPORT_PATH = ROOT / "reports" / "model_comparison_12feature.md"
JSON_PATH = ROOT / "reports" / "model_comparison_12feature.json"

CLASS_NAMES = ["Low", "Medium", "High"]
LOW, MEDIUM, HIGH = 0, 1, 2
FLAG_THRESHOLD = 0.10
NUMERIC_FEATURES = [f for f in ALL_FEATURES if f not in CATEGORICAL_ALLOWED]
SHAP_SAMPLE = 300
NOISE_LEVELS = [0.25, 0.5, 1.0]
STRESS_SHIFTS = [-3, -2, -1, 1, 2, 3]
MIN_SUPPORT = 15


def build_candidates(tuning: dict) -> dict[str, object]:
    rf = tuning["models"]["random_forest"]["best_params"]
    xgb = tuning["models"]["xgboost"]
    assert xgb["sample_weighting"] == "none", "refit below assumes the unweighted XGBoost won"
    return {
        "rf_current": joblib.load(CURRENT_MODEL_PATH),
        "rf_retuned": RandomForestClassifier(**rf, random_state=SEED, n_jobs=-1),
        "xgb_retuned": XGBClassifier(
            **xgb["best_params"], objective="multi:softprob", eval_metric="mlogloss",
            random_state=SEED, n_jobs=-1,
        ),
    }


def headline(y: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": accuracy_score(y, pred),
        "balanced_accuracy": balanced_accuracy_score(y, pred),
        "macro_f1": f1_score(y, pred, average="macro"),
        "high_recall": recall_score(y, pred, labels=[HIGH], average=None, zero_division=0)[0],
    }


def ece(y_true_binary: np.ndarray, prob: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(prob, edges[1:-1]), 0, bins - 1)
    return float(sum(
        (idx == b).mean() * abs(prob[idx == b].mean() - y_true_binary[idx == b].mean())
        for b in range(bins) if (idx == b).any()
    ))


def shap_ranking(model: object, x: np.ndarray, feature_names: list[str]) -> dict[str, float]:
    values = shap.TreeExplainer(model).shap_values(x)
    # Normalise to (rows, features, classes) across shap/model versions.
    values = np.stack(values, axis=-1) if isinstance(values, list) else np.asarray(values)
    per_column = np.abs(values).mean(axis=(0, 2))
    grouped: dict[str, float] = {}
    for name, value in zip(feature_names, per_column):
        original = next((c for c in CATEGORICAL_ALLOWED if name.startswith(f"cat__{c}_")), None)
        original = original or name.split("__", 1)[-1]
        grouped[original] = grouped.get(original, 0.0) + float(value)
    total = sum(grouped.values())
    return dict(sorted(((k, v / total) for k, v in grouped.items()), key=lambda kv: -kv[1]))


def main() -> None:
    tuning = json.loads(TUNING_PATH.read_text(encoding="utf-8"))
    df = pd.read_csv(DATA_PATH)
    with np.load(SPLITS_PATH) as splits:
        assert "X_test" not in splits.files
        x_train, y_train = splits["X_train"], splits["y_train"]
        x_val, y_val = splits["X_val"], splits["y_val"]
        train_idx, val_idx = splits["train_original_idx"], splits["val_original_idx"]
    pre = joblib.load(PREPROCESSOR_PATH)
    raw_train = df.iloc[train_idx][ALL_FEATURES].reset_index(drop=True)
    raw_val = df.iloc[val_idx].reset_index(drop=True)
    assert np.allclose(pre.transform(raw_val[ALL_FEATURES]), x_val), "raw validation rows must reproduce X_val"
    feature_names = list(pre.get_feature_names_out())

    candidates = build_candidates(tuning)
    for name, model in candidates.items():
        if name != "rf_current":
            model.fit(x_train, y_train)

    rng = np.random.default_rng(SEED)
    shap_rows = rng.choice(len(x_val), size=SHAP_SAMPLE, replace=False)
    train_std = raw_train[NUMERIC_FEATURES].std()
    noise = {k: rng.normal(size=(len(raw_val), len(NUMERIC_FEATURES))) * train_std.to_numpy() * k for k in NOISE_LEVELS}
    true_high_medium_misses_union: set[int] = set()

    results: dict[str, dict] = {}
    for name, model in candidates.items():
        print(f"\n=== {name} ===")
        r: dict[str, object] = {}
        prob = model.predict_proba(x_val)
        pred = prob.argmax(axis=1)
        y_bin = label_binarize(y_val, classes=[LOW, MEDIUM, HIGH])

        # 1. Evaluation
        r["validation"] = headline(y_val, pred)
        r["per_class"] = {
            c: {
                "precision": precision_score(y_val, pred, labels=[k], average=None, zero_division=0)[0],
                "recall": recall_score(y_val, pred, labels=[k], average=None, zero_division=0)[0],
                "auroc": roc_auc_score(y_bin[:, k], prob[:, k]),
                "auprc": average_precision_score(y_bin[:, k], prob[:, k]),
            }
            for k, c in enumerate(CLASS_NAMES)
        }
        r["macro_auroc"] = roc_auc_score(y_bin, prob, average="macro")
        r["macro_auprc"] = average_precision_score(y_bin, prob, average="macro")
        r["confusion"] = confusion_matrix(y_val, pred, labels=[LOW, MEDIUM, HIGH]).tolist()
        print("  evaluation done")

        # 2. Stability
        template = clone(model)
        folds = StratifiedKFold(5, shuffle=True, random_state=SEED)
        cv = [headline(y_train[te], clone(template).fit(x_train[tr], y_train[tr]).predict(x_train[te]))
              for tr, te in folds.split(x_train, y_train)]
        r["cv"] = {m: (float(np.mean([f[m] for f in cv])), float(np.std([f[m] for f in cv]))) for m in cv[0]}
        seeds = [balanced_accuracy_score(y_val, clone(template).set_params(random_state=s).fit(x_train, y_train).predict(x_val))
                 for s in [0, 1, 2, 3, 42]]
        r["seed_balanced_accuracy"] = (float(np.mean(seeds)), float(np.std(seeds)), float(min(seeds)), float(max(seeds)))
        print("  stability done")

        # 3. Calibration
        r["calibration"] = {
            "log_loss": log_loss(y_val, prob),
            **{f"brier_{c}": brier_score_loss(y_bin[:, k], prob[:, k]) for k, c in enumerate(CLASS_NAMES)},
            **{f"ece_{c}": ece(y_bin[:, k], prob[:, k]) for k, c in enumerate(CLASS_NAMES)},
        }

        # 4. Uncertainty flag
        flagged = prob[:, HIGH] >= FLAG_THRESHOLD
        is_high = y_val == HIGH
        misses = np.flatnonzero(is_high & (pred == MEDIUM))
        true_high_medium_misses_union |= set(misses.tolist())
        workload = {}
        for target in [150, 155, 158, 160, 163, 165]:
            cut = np.sort(prob[is_high, HIGH])[::-1][target - 1]
            workload[target] = int((prob[:, HIGH] >= cut).sum())
        r["flag"] = {
            "flagged": int(flagged.sum()),
            "true_high_caught": int((flagged & is_high).sum()),
            "true_high_total": int(is_high.sum()),
            "false_flag_rate": float((flagged & ~is_high).sum() / flagged.sum()),
            "high_predicted_medium_misses": int(len(misses)),
            "misses_caught_by_flag": int(flagged[misses].sum()),
            "flags_needed_for_high_recall": workload,
        }
        r["_p_high"] = prob[:, HIGH]
        print("  calibration + flag done")

        # 5. SHAP
        r["shap"] = shap_ranking(model, x_val[shap_rows], feature_names)
        print("  SHAP done")

        # 6. Fairness
        fairness = {}
        groups = {
            "occupation": raw_val["Occupation"],
            "age_band": pd.cut(raw_val["Age"], [17, 29, 40, 49, 64], labels=["18-29", "30-40", "41-49", "50-64"]),
            "gender": raw_val["Gender"],
        }
        for group_name, labels in groups.items():
            rows = {}
            for value in labels.dropna().unique():
                mask = (labels == value).to_numpy()
                high_mask = mask & is_high
                rows[str(value)] = {
                    "n": int(mask.sum()),
                    "balanced_accuracy": float(balanced_accuracy_score(y_val[mask], pred[mask])),
                    "high_n": int(high_mask.sum()),
                    "high_recall": float((pred[high_mask] == HIGH).mean()) if high_mask.any() else None,
                }
            reliable = [v["high_recall"] for v in rows.values() if v["high_n"] >= MIN_SUPPORT]
            fairness[group_name] = {
                "groups": dict(sorted(rows.items())),
                "balanced_accuracy_range": float(max(v["balanced_accuracy"] for v in rows.values())
                                                 - min(v["balanced_accuracy"] for v in rows.values())),
                "high_recall_range_reliable": float(max(reliable) - min(reliable)) if len(reliable) > 1 else None,
            }
        r["fairness"] = fairness
        print("  fairness done")

        # 7. Robustness
        def predict_raw(frame: pd.DataFrame) -> np.ndarray:
            return model.predict(pre.transform(frame[ALL_FEATURES]))

        base_bal = r["validation"]["balanced_accuracy"]
        knockout = {}
        for feature in ALL_FEATURES:
            fill = raw_train[feature].mode()[0] if feature in CATEGORICAL_ALLOWED else raw_train[feature].mean()
            p = predict_raw(raw_val.assign(**{feature: fill}))
            knockout[feature] = {"balanced_accuracy": float(balanced_accuracy_score(y_val, p)),
                                 "high_recall": float(recall_score(y_val, p, labels=[HIGH], average=None)[0])}
        noisy = {}
        for k, delta in noise.items():
            frame = raw_val.copy()
            frame[NUMERIC_FEATURES] = frame[NUMERIC_FEATURES].to_numpy() + delta
            noisy[k] = float(balanced_accuracy_score(y_val, predict_raw(frame)))
        shift = {}
        for s in STRESS_SHIFTS:
            frame = raw_val.assign(**{"Stress Level (1-10)": (raw_val["Stress Level (1-10)"] + s).clip(1, 10)})
            shift[s] = float((predict_raw(frame) == HIGH).mean())
        high_young = raw_val[is_high & (raw_val["Age"] < 50).to_numpy()]
        age_sensitivity = {
            a: float(model.predict_proba(pre.transform(high_young.assign(Age=a)[ALL_FEATURES]))[:, HIGH].mean())
            for a in (18, 30, 40, 49, 55)
        }
        r["robustness"] = {
            "baseline_balanced_accuracy": base_bal,
            "knockout": knockout,
            "noise_balanced_accuracy": noisy,
            "stress_shift_predicted_high_fraction": {"0": float((pred == HIGH).mean()), **{str(k): v for k, v in shift.items()}},
            "age_sensitivity_mean_p_high": age_sensitivity,
        }
        print("  robustness done")

        # 8. Practical
        start = time.perf_counter()
        for _ in range(200):
            model.predict_proba(x_val[:1])
        r["practical"] = {"predict_ms": (time.perf_counter() - start) / 200 * 1000,
                          "pickle_mb": len(pickle.dumps(model)) / 1e6}
        results[name] = r

    # Shared: which of the union of "true High predicted Medium" misses each model's flag catches.
    union = np.array(sorted(true_high_medium_misses_union))
    for r in results.values():
        r["flag"]["union_misses_total"] = int(len(union))
        r["flag"]["union_misses_caught"] = int((r.pop("_p_high")[union] >= FLAG_THRESHOLD).sum())

    JSON_PATH.write_text(json.dumps(results, indent=2, default=float) + "\n", encoding="utf-8")
    write_report(results, tuning)
    print(f"\nSaved {REPORT_PATH.relative_to(ROOT)} and {JSON_PATH.relative_to(ROOT)}")


def write_report(results: dict, tuning: dict) -> None:
    names = list(results)
    head = "| | " + " | ".join(f"`{n}`" for n in names) + " |"
    rule = "|---|" + "---:|" * len(names)

    def row(label: str, values: list, fmt: str = "{:.4f}") -> str:
        return f"| {label} | " + " | ".join("—" if v is None else fmt.format(v) for v in values) + " |"

    def pm(pair: tuple) -> str:
        return f"{pair[0]:.4f} ± {pair[1]:.4f}"

    rf_p = tuning["models"]["random_forest"]["best_params"]
    xgb_p = tuning["models"]["xgboost"]["best_params"]
    lines = [
        "# Model Comparison — Random Forest vs XGBoost, 12-Feature Data (3-Class Anxiety Level)",
        "",
        "Validation and training data only — the 12-feature splits contain no test arrays, and the"
        " 3-class test set is treated as spent. Script: `src/evaluation/compare_models_12feature.py`.",
        "",
        "## Candidates",
        "",
        "- `rf_current` — the model the API serves today (`mindcare_final_model_12feature.pkl`):"
        " 200 trees, max_depth 10, class_weight balanced (params tuned on the old 17 features).",
        f"- `rf_retuned` — Random Forest re-tuned on the 12 features: {rf_p}.",
        f"- `xgb_retuned` — XGBoost re-tuned on the 12 features: {xgb_p}; unweighted"
        " (beat balanced sample weights in CV,"
        f" {tuning['models']['xgboost']['cv_score_by_weighting']['none']:.4f} vs"
        f" {tuning['models']['xgboost']['cv_score_by_weighting']['balanced']:.4f}).",
        "- Re-tuning: identical procedure for both (`src/models/tune_models_12feature.py`) — 40"
        " configurations each, 5-fold CV on train, balanced-accuracy scoring; validation never used"
        " to choose.",
        "",
        "## 1. Performance (validation, n=1650)",
        "",
        head, rule,
        row("Accuracy", [r["validation"]["accuracy"] for r in results.values()]),
        row("Balanced accuracy", [r["validation"]["balanced_accuracy"] for r in results.values()]),
        row("Macro-F1", [r["validation"]["macro_f1"] for r in results.values()]),
        row("High recall", [r["validation"]["high_recall"] for r in results.values()]),
        row("High precision", [r["per_class"]["High"]["precision"] for r in results.values()]),
        row("Medium recall", [r["per_class"]["Medium"]["recall"] for r in results.values()]),
        row("Low recall", [r["per_class"]["Low"]["recall"] for r in results.values()]),
        row("Macro AUROC", [r["macro_auroc"] for r in results.values()]),
        row("Macro AUPRC", [r["macro_auprc"] for r in results.values()]),
        "",
        "Confusion matrices (rows = true Low/Medium/High, columns = predicted):",
        "",
    ]
    for n, r in results.items():
        lines.append(f"- `{n}`: " + " / ".join(str(rw) for rw in r["confusion"]))
    lines += [
        "",
        "## 2. Stability",
        "",
        head, rule,
        "| 5-fold CV balanced accuracy (train) | " + " | ".join(pm(r["cv"]["balanced_accuracy"]) for r in results.values()) + " |",
        "| 5-fold CV macro-F1 (train) | " + " | ".join(pm(r["cv"]["macro_f1"]) for r in results.values()) + " |",
        "| 5-fold CV High recall (train) | " + " | ".join(pm(r["cv"]["high_recall"]) for r in results.values()) + " |",
        "| Validation balanced accuracy over 5 seeds | " + " | ".join(
            f"{r['seed_balanced_accuracy'][0]:.4f} ± {r['seed_balanced_accuracy'][1]:.4f}" for r in results.values()) + " |",
        "",
        "## 3. Calibration (validation; lower is better)",
        "",
        head, rule,
        row("Log loss", [r["calibration"]["log_loss"] for r in results.values()]),
        *[row(f"Brier — {c}", [r["calibration"][f"brier_{c}"] for r in results.values()]) for c in CLASS_NAMES],
        *[row(f"ECE (10-bin) — {c}", [r["calibration"][f"ece_{c}"] for r in results.values()]) for c in CLASS_NAMES],
        "",
        "## 4. Uncertainty Flag (production rule P(High) ≥ 0.10)",
        "",
        head, rule,
        row("Rows flagged", [r["flag"]["flagged"] for r in results.values()], "{}"),
        "| True-High caught | " + " | ".join(f"{r['flag']['true_high_caught']} / {r['flag']['true_high_total']}" for r in results.values()) + " |",
        row("False-flag rate", [r["flag"]["false_flag_rate"] for r in results.values()]),
        "| Own True-High→Medium misses caught | " + " | ".join(
            f"{r['flag']['misses_caught_by_flag']} / {r['flag']['high_predicted_medium_misses']}" for r in results.values()) + " |",
        "| Union of all models' True-High→Medium misses caught | " + " | ".join(
            f"{r['flag']['union_misses_caught']} / {r['flag']['union_misses_total']}" for r in results.values()) + " |",
        "",
        "Rows each model must flag to catch N of the 165 true-High cases (its own best threshold; fewer = less review work):",
        "",
        "| High cases caught | " + " | ".join(f"`{n}`" for n in names) + " |",
        rule,
    ]
    for target in results[names[0]]["flag"]["flags_needed_for_high_recall"]:
        lines.append(f"| {target} | " + " | ".join(str(r["flag"]["flags_needed_for_high_recall"][target]) for r in results.values()) + " |")
    lines += [
        "",
        f"## 5. SHAP Feature Importance (share of mean |SHAP|, {SHAP_SAMPLE} validation rows)",
        "",
        "| Rank | " + " | ".join(f"`{n}`" for n in names) + " |",
        rule,
    ]
    rankings = [list(r["shap"].items()) for r in results.values()]
    for i in range(len(rankings[0])):
        lines.append(f"| {i + 1} | " + " | ".join(f"{rk[i][0]} ({rk[i][1]:.1%})" for rk in rankings) + " |")
    lines += ["", "## 6. Fairness (validation)", ""]
    for group in ("occupation", "age_band", "gender"):
        lines += [
            f"**{group}** — balanced-accuracy range across groups, and High-recall range across groups"
            f" with ≥{MIN_SUPPORT} true-High rows:",
            "",
            head, rule,
            row("Balanced-accuracy range", [r["fairness"][group]["balanced_accuracy_range"] for r in results.values()]),
            row("High-recall range (reliable groups)", [r["fairness"][group]["high_recall_range_reliable"] for r in results.values()]),
            "",
        ]
    lines += [
        "Per-group detail is in `reports/model_comparison_12feature.json`. Most occupations have"
        f" fewer than {MIN_SUPPORT} true-High validation rows, so their High recall is not"
        " comparable.",
        "",
        "## 7. Robustness (validation)",
        "",
        "Single-feature knockout (feature replaced by its train mean/mode) — balanced accuracy:",
        "",
        head, rule,
        row("No knockout", [r["robustness"]["baseline_balanced_accuracy"] for r in results.values()]),
    ]
    for feature in ALL_FEATURES:
        lines.append(row(feature, [r["robustness"]["knockout"][feature]["balanced_accuracy"] for r in results.values()]))
    lines += [
        "",
        "Gaussian noise on all numeric features (multiples of each feature's train std; identical"
        " noise for every model) — balanced accuracy:",
        "",
        head, rule,
        *[row(f"{k}× std", [r["robustness"]["noise_balanced_accuracy"][k] for r in results.values()]) for k in NOISE_LEVELS],
        "",
        "Stress Level shifted for every row (clipped to 1-10) — fraction predicted High:",
        "",
        head, rule,
        *[row(f"shift {k}", [r["robustness"]["stress_shift_predicted_high_fraction"][k] for r in results.values()])
          for k in ["-3", "-2", "-1", "0", "1", "2", "3"]],
        "",
        "Age sensitivity — mean P(High) for the true-High validation rows under 50, with only Age"
        " changed (the API accepts 18-49 only; 55 shows the dataset's age artifact):",
        "",
        head, rule,
        *[row(f"Age {a}", [r["robustness"]["age_sensitivity_mean_p_high"][a] for r in results.values()]) for a in (18, 30, 40, 49, 55)],
        "",
        "## 8. Practical",
        "",
        head, rule,
        row("Single prediction (ms)", [r["practical"]["predict_ms"] for r in results.values()], "{:.1f}"),
        row("Pickled size (MB)", [r["practical"]["pickle_mb"] for r in results.values()], "{:.1f}"),
        "",
        "## Caveats",
        "",
        "- Validation/train evidence only; no candidate has a test-set number.",
        "- The dataset is very likely synthetic (see CLAUDE.md) — these are prototype comparisons,"
        " not clinical validation.",
        "- Latency depends on the machine; compare the ratio, not the absolute numbers.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
