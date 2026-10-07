"""Investigate how the raw dataset's recommendation columns (Exercises,
Sleep_Schedule, Nutrition) relate to Severity and to the 3-class
Low/Medium/High target the deployed model predicts.

Analysis only - builds nothing. Uses the 9,350 train + validation rows
(via the saved original indices); the test rows are excluded, so they stay
available as an untouched check if a recommendation component is built later.

Writes reports/recommendation_mapping_investigation.md.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.tree import DecisionTreeClassifier

SEED = 42
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_12feature.npz"
REPORT_PATH = ROOT / "reports" / "recommendation_mapping_investigation.md"

TIERS = ["Minimal (1-2)", "Mild (3-4)", "Moderate (5-6)", "High (7-8)", "Severe (9-10)"]
CLASSES = ["Low", "Medium", "High"]
A, S = "Anxiety Level (1-10)", "Stress Level (1-10)"
CAF, ALC, SLEEP = "Caffeine Intake (mg/day)", "Alcohol Consumption (drinks/week)", "Sleep Hours"
SLEEP_REF = dict(zip(TIERS, [7.0, 7.5, 8.0, 8.5, 9.0]))  # inferred below, then verified by exact rebuild
PROTEIN = {"Female": 50, "Other": 54, "Male": 58}      # inferred below, then verified by exact rebuild
NUMERIC = ["Age", SLEEP, "Physical Activity (hrs/week)", CAF, ALC, S, "Heart Rate (bpm)",
           "Breathing Rate (breaths/min)", "Sweating Level (1-5)", "Therapy Sessions (per month)",
           "Diet Quality (1-10)", A]
CATEGORICAL = ["Gender", "Occupation", "Smoking", "Family History of Anxiety", "Dizziness", "Medication",
               "Recent Major Life Event"]


def nutrition_base(text: str) -> str:
    text = re.sub(r"^Protein: \d+ g/day; ", "", text)
    text = re.sub(r"; Reduce caffeine to <200 mg/day \(current: \d+ mg\)|; Caffeine OK: \d+ mg/day", "; <CAFFEINE>", text)
    return re.sub(r"; Eliminate alcohol \(current: \d+ drinks/week\)|; No alcohol: good", "; <ALCOHOL>", text)


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    with np.load(SPLITS_PATH) as splits:
        assert "test_original_idx" not in splits.files
        rows = np.concatenate([splits["train_original_idx"], splits["val_original_idx"]])
    d = df.iloc[rows].copy()
    d["Class3"] = pd.cut(d[A], [0, 3, 6, 10], labels=CLASSES)
    n = len(d)

    # ---- Decompose each text into its fixed template and its per-patient slots ----
    sleep = d["Sleep_Schedule"].str.extract(
        r"^(?P<base>.*); Current: (?P<cur>[\d.]+) hrs; (?:Increase by (?P<inc>[\d.]+) hrs|(?P<ok>On target))$")
    assert sleep["base"].notna().all()
    d["sleep_base"], d["sleep_on_target"] = sleep["base"], sleep["ok"].notna()
    d["nutrition_base"] = d["Nutrition"].map(nutrition_base)
    d["caffeine_branch"] = np.where(d["Nutrition"].str.contains("Caffeine OK:"), "Caffeine OK", "Reduce caffeine")
    d["alcohol_branch"] = np.where(d["Nutrition"].str.contains("No alcohol: good"), "No alcohol: good", "Eliminate alcohol")
    d["bundle"] = d["Exercises"] + " || " + d["sleep_base"] + " || " + d["nutrition_base"]
    d["variant"] = (np.where(d["sleep_on_target"], "sleep on target", "sleep increase") + " / "
                    + d["caffeine_branch"] + " / " + d["alcohol_branch"])

    # ---- Exact rebuild from the inferred rules ----
    first = d.groupby("Severity").first()
    ex, sb, nb = first["Exercises"].to_dict(), first["sleep_base"].to_dict(), first["nutrition_base"].to_dict()

    def build(r: pd.Series) -> tuple[str, str, str]:
        tier, sh, c, a = r["Severity"], r[SLEEP], int(r[CAF]), int(r[ALC])
        sleep_text = f"{sb[tier]}; Current: {sh:.1f} hrs; " + (
            "On target" if sh >= SLEEP_REF[tier] - 1e-9 else f"Increase by {SLEEP_REF[tier] - sh:.1f} hrs")
        caf = f"Reduce caffeine to <200 mg/day (current: {c} mg)" if c > 200 else f"Caffeine OK: {c} mg/day"
        alc = f"Eliminate alcohol (current: {a} drinks/week)" if a > 0 else "No alcohol: good"
        nut = f"Protein: {PROTEIN[r['Gender']]} g/day; " + nb[tier].replace("<CAFFEINE>", caf).replace("<ALCOHOL>", alc)
        return ex[tier], sleep_text, nut

    rebuilt = pd.DataFrame(d.apply(build, axis=1).tolist(), index=d.index, columns=["Exercises", "Sleep_Schedule", "Nutrition"])
    exact = {c: int((rebuilt[c] == d[c]).sum()) for c in rebuilt.columns}

    # ---- Severity rule and alignment with the 3-class target ----
    band = pd.cut((d[A] + d[S]) / 2, [0, 2.5, 4.5, 6.5, 8.5, 10], labels=TIERS).astype(str)
    severity_rule_matches = int((band == d["Severity"]).sum())
    pair_conflicts = int((d.groupby([A, S])["Severity"].nunique() > 1).sum())
    class_to_tier = pd.crosstab(d["Class3"], d["Severity"], normalize="index")[TIERS]
    tier_by_class_counts = pd.crosstab(d["Severity"], d["Class3"]).reindex(TIERS)

    # ---- What predicts the tier (= bundle) within each 3-class group ----
    X = pd.concat([d[NUMERIC], pd.get_dummies(d[CATEGORICAL], dtype=float)], axis=1)
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    within = []
    for k in CLASSES:
        g = (d["Class3"] == k).to_numpy()
        y = d.loc[g, "Severity"]
        mi = pd.Series(mutual_info_classif(X[g], y, random_state=SEED), index=X.columns).sort_values(ascending=False)
        others = mi.drop([A, S])
        within.append({
            "class": k, "n": int(g.sum()), "majority": float(y.value_counts(normalize=True).iloc[0]),
            "tree_as": float(cross_val_score(DecisionTreeClassifier(random_state=SEED), d.loc[g, [A, S]], y, cv=cv).mean()),
            "tree_others": float(cross_val_score(DecisionTreeClassifier(max_depth=8, random_state=SEED),
                                                 X[g].drop(columns=[A, S]), y, cv=cv).mean()),
            "mi_a": float(mi[A]), "mi_s": float(mi[S]), "mi_other_name": others.index[0], "mi_other": float(others.iloc[0]),
        })

    # ---- Recoverability from what the deployed system knows (3-class label + Stress Level) ----
    grp = d.groupby(["Class3", S], observed=True)["Severity"]
    best = grp.agg(lambda x: x.value_counts(normalize=True).iloc[0])
    size = grp.size()
    recover = float((best * size).sum() / size.sum())

    # ---------------------------------------------------------------- report
    L = [
        "# Recommendation Mapping Investigation — Exercises, Sleep_Schedule, Nutrition",
        "",
        "Script: `src/experiments/recommendation_mapping_investigation.py`. Analysis only; nothing was built.",
        f"Data: the {n:,} train + validation rows (test rows excluded, so they stay untouched for any later check).",
        "",
        "## Finding",
        "",
        "**A deterministic lookup with per-patient fill-ins — no randomness at all.**",
        "",
        f"- **Severity is a fixed rule:** the average of Anxiety Level and Stress Level, cut into five bands"
        f" (matches {severity_rule_matches:,}/{n:,} rows).",
        "- **Each Severity tier maps to exactly one recommendation bundle:** one Exercises text, one Sleep"
        " template and one Nutrition template.",
        "- **Inside a bundle, only fill-in slots vary,** and each is set by a simple rule from the patient's own"
        " Sleep Hours, Caffeine Intake, Alcohol Consumption and Gender.",
        f"- **Proof:** rebuilding every text from these rules reproduces the originals **character for character**:"
        f" Exercises {exact['Exercises']:,}/{n:,}, Sleep_Schedule {exact['Sleep_Schedule']:,}/{n:,},"
        f" Nutrition {exact['Nutrition']:,}/{n:,}.",
        "- **Keyed by the 3-class target, the bundles are *not* consistent:** each Low/Medium/High class receives"
        " 3–4 different bundles. That isn't noise. The bundle depends on Stress Level as well as Anxiety Level,"
        " while the 3-class label comes from Anxiety Level alone.",
        "",
        "The texts are almost certainly generated by the dataset's (very likely synthetic) construction, not"
        " written per patient by clinicians. They are templates, not clinical advice.",
        "",
        "## 1. Combinations per tier",
        "",
        "Raw texts look nearly unique (Sleep_Schedule and Nutrition have hundreds to thousands of distinct"
        " strings) only because they embed each patient's numbers. With the numbers separated out:",
        "",
        "| Severity tier | Rows | Bundles | Within-bundle variants seen (share of tier) |",
        "|---|---:|---:|---|",
    ]
    for tier in TIERS:
        g = d[d["Severity"] == tier]
        variants = g["variant"].value_counts(normalize=True)
        L.append(f"| {tier} | {len(g):,} | {g['bundle'].nunique()} | "
                 + "; ".join(f"{v} ({pct(p)})" for v, p in variants.items()) + " |")
    L += [
        "",
        "Every tier has exactly **one** bundle. The variants are on/off switches inside it, set by the rules in"
        " the next table.",
        "",
        "Keyed by the 3-class target instead:",
        "",
        "| 3-class | Rows | Bundles | Bundle mix (share of class) |",
        "|---|---:|---:|---|",
    ]
    for k in CLASSES:
        g = d[d["Class3"] == k]
        mix = class_to_tier.loc[k]
        L.append(f"| {k} | {len(g):,} | {g['bundle'].nunique()} | "
                 + "; ".join(f"{t} bundle {pct(v)}" for t, v in mix.items() if v > 0) + " |")
    L += [
        "",
        "### The slot rules (all verified by the exact rebuild)",
        "",
        "| Slot | Rule |",
        "|---|---|",
        "| Exercises | Fixed text per Severity tier; no slots. |",
        "| Sleep `Current: X hrs` | X = the patient's `Sleep Hours`. |",
        "| Sleep `On target` / `Increase by Y hrs` | On target if Sleep Hours ≥ the tier's reference, otherwise Y ="
        " reference − Sleep Hours. References: " + ", ".join(f"{t.split(' ')[0]} {v:.1f} h" for t, v in SLEEP_REF.items())
        + " (0.5 h per tier). Mild's text says \"7-9 hrs\" and High's says \"8-9 hrs\", but the rule uses 7.5 and 8.5."
        " Severe patients are never on target (Sleep Hours never reaches 9.0 in this tier). |",
        "| Nutrition `Protein: N g/day` | N set by **Gender**: " + ", ".join(f"{g} {v}" for g, v in PROTEIN.items()) + ". |",
        "| Nutrition caffeine | `Reduce caffeine to <200 mg/day (current: C mg)` if Caffeine Intake > 200, otherwise"
        " `Caffeine OK: C mg/day`; C = the patient's Caffeine Intake. Also appended in the Severe tier, whose text"
        " already says \"Eliminate all caffeine\". |",
        "| Nutrition alcohol | `No alcohol: good` if Alcohol Consumption = 0, otherwise `Eliminate alcohol (current:"
        " N drinks/week)`; N = the patient's Alcohol Consumption. Also appended in the Severe tier. |",
        "",
        "## 2. Severity vs the 3-class target",
        "",
        "**Severity is not derived from Anxiety Level alone.** It is a band of the average of Anxiety Level and"
        " Stress Level:",
        "",
        "| (Anxiety + Stress) / 2 | 1.0–2.5 | 3.0–4.5 | 5.0–6.5 | 7.0–8.5 | 9.0–10.0 |",
        "|---|---|---|---|---|---|",
        "| Severity | Minimal | Mild | Moderate | High | Severe |",
        "",
        f"That matches {severity_rule_matches:,} of {n:,} rows, and no (Anxiety, Stress) pair maps to more than one"
        f" tier ({pair_conflicts} conflicts). The tier labels (\"Mild (3-4)\" etc.) describe this average, not"
        " Anxiety Level, which is why the early-EDA note found Severity misaligned with the 3-class boundaries.",
        "",
        "Rows by Severity tier and 3-class label:",
        "",
        "| Severity | Low | Medium | High |",
        "|---|---:|---:|---:|",
        *[f"| {t} | {tier_by_class_counts.loc[t, 'Low']:,} | {tier_by_class_counts.loc[t, 'Medium']:,} |"
          f" {tier_by_class_counts.loc[t, 'High']:,} |" for t in TIERS],
        "",
        "**Collapsing to 3 classes changes which bundle a patient gets:** a Low/Medium/High label alone does not"
        " determine the bundle. Patients in the same class receive different bundles depending on their Stress"
        " Level. This is systematic, not noisy: for a given (Anxiety, Stress) pair the bundle is always the same.",
        "",
        "## 3. What predicts the bundle",
        "",
        "- **Within a Severity tier:** nothing chooses between bundles, because there is only one per tier. The"
        " in-bundle switches are fully explained by Sleep Hours, Caffeine Intake, Alcohol Consumption and Gender,"
        " as the exact rebuild shows.",
        "- **Within a 3-class group:** the tier, and therefore the bundle, is decided by Anxiety Level and Stress"
        " Level. Nothing else carries meaningful information. (5-fold CV, decision trees; mutual information on"
        " the same rows.)",
        "",
        "| 3-class | Rows | Majority-tier share | Tree on Anxiety + Stress | Tree on all other features | MI: Stress / Anxiety | Highest MI of any other feature |",
        "|---|---:|---:|---:|---:|---:|---|",
        *[f"| {w['class']} | {w['n']:,} | {w['majority']:.3f} | {w['tree_as']:.3f} | {w['tree_others']:.3f} |"
          f" {w['mi_s']:.3f} / {w['mi_a']:.3f} | {w['mi_other_name']} {w['mi_other']:.3f} |" for w in within],
        "",
        "Without Anxiety and Stress, the other features do no better than always guessing the most common"
        " tier for Low and Medium, and only slightly better for High (Breathing Rate and Caffeine correlate"
        " with anxiety in this synthetic data). Age and Occupation play no part. Gender affects only the"
        " protein figure inside a bundle, never which bundle is chosen.",
        "",
        "## 4. What this means (nothing built yet)",
        "",
        "- **The deployed model can't fully recover the bundle.** Choosing a bundle needs Anxiety Level and Stress"
        " Level. The API has Stress Level (from the PSS-4), but Anxiety Level is what the model *predicts* — it"
        " only outputs Low/Medium/High. Even with the **true** 3-class label plus Stress Level, the best"
        f" single-guess Severity is right for only **{pct(recover)}** of rows"
        f" ({int((best < 1).sum())} of {len(best)} label-and-stress combinations are ambiguous). The model's"
        " predicted class is itself wrong for roughly a fifth of patients, so in practice it would be lower.",
        "- **Two fill-ins use data the API doesn't collect.** Protein grams come from **Gender**, and the alcohol"
        " line comes from **Alcohol Consumption**, which was dropped from the model's inputs.",
        "- **These columns are leakage, as CLAUDE.md already notes.** Each is a deterministic function of"
        " Anxiety/Stress plus a few inputs, so using them as model features would leak the target.",
        "- **The texts are not clinical guidance.** They are fixed synthetic templates (supplement doses, a"
        " \"Biofeedback Therapy recommended\" line, a \"Sleep study referral\"). Any use in the product would need"
        " clinical review, and like every model output, psychologist approval before a patient sees it.",
    ]
    REPORT_PATH.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"exact rebuild: {exact}; severity rule {severity_rule_matches}/{n}; recover {recover:.3f}")
    print(f"Saved {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
