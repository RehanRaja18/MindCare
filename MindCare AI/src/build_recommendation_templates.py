"""Extract the dataset's recommendation templates for the manual testing form
(src/inference/template_advice.py) into data/processed/recommendation_templates.json.

Uses the 9,350 train + validation rows only (test rows excluded). Every value is
read from the data, not typed in: each tier's Exercises text, sleep template and
sleep reference, nutrition template, the protein figure per Gender, and the
(3-class label, Stress Level) -> most-common-tier lookup. The file is written
only if render() then rebuilds all three text columns for every row exactly.

See reports/recommendation_mapping_investigation.md for how the rules were found.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.inference import template_advice
from src.inference.template_advice import TEMPLATES_PATH, TIERS, render, severity_band

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "mindcare_dataset_final.csv"
SPLITS_PATH = ROOT / "data" / "processed" / "mindcare_processed_splits_12feature.npz"
CAFFEINE_THRESHOLD_MG = 200


def single(values: pd.Series, what: str):
    unique = values.dropna().unique()
    if len(unique) != 1:
        raise ValueError(f"expected exactly one value for {what}, found {len(unique)}: {unique[:5]}")
    return unique[0]


def nutrition_base(text: str) -> str:
    text = re.sub(r"^Protein: \d+ g/day; ", "", text)
    text = re.sub(r"; Reduce caffeine to <200 mg/day \(current: \d+ mg\)|; Caffeine OK: \d+ mg/day", "; <CAFFEINE>", text)
    return re.sub(r"; Eliminate alcohol \(current: \d+ drinks/week\)|; No alcohol: good", "; <ALCOHOL>", text)


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    with np.load(SPLITS_PATH) as splits:
        assert "test_original_idx" not in splits.files
        rows = np.concatenate([splits["train_original_idx"], splits["val_original_idx"]])
    d = df.iloc[rows].copy()
    anxiety, stress = d["Anxiety Level (1-10)"], d["Stress Level (1-10)"]
    assert all(severity_band(a, s) == t for a, s, t in zip(anxiety, stress, d["Severity"])), "Severity band rule broken"
    d["Class3"] = pd.cut(anxiety, [0, 3, 6, 10], labels=["Low", "Medium", "High"]).astype(str)

    sleep = d["Sleep_Schedule"].str.extract(r"^(?P<base>.*); Current: (?P<cur>[\d.]+) hrs; (?:Increase by (?P<inc>[\d.]+) hrs|On target)$")
    assert sleep["base"].notna().all()
    protein = d["Nutrition"].str.extract(r"^Protein: (\d+) g/day")[0].astype(int)

    tiers = {}
    for tier in TIERS:
        m = d["Severity"] == tier
        increase_rows = m & sleep["inc"].notna()
        tiers[tier] = {
            "exercises": single(d.loc[m, "Exercises"], f"{tier} exercises"),
            "sleep_base": single(sleep.loc[m, "base"], f"{tier} sleep template"),
            # Current + Increase is the same for every "Increase" row in a tier: that's the reference.
            "sleep_reference_hours": float(single((sleep.loc[increase_rows, "cur"].astype(float)
                                                   + sleep.loc[increase_rows, "inc"].astype(float)).round(2),
                                                  f"{tier} sleep reference")),
            "nutrition_base": single(d.loc[m, "Nutrition"].map(nutrition_base), f"{tier} nutrition template"),
        }
    protein_by_gender = {g: int(single(protein[d["Gender"] == g], f"protein for {g}")) for g in sorted(d["Gender"].unique())}

    lookup = {}
    for (label, s), group in d.groupby(["Class3", "Stress Level (1-10)"])["Severity"]:
        counts = group.value_counts()
        lookup[f"{label}|{int(s)}"] = {"tier": counts.index[0], "share": round(float(counts.iloc[0] / counts.sum()), 4),
                                       "n": int(counts.sum())}

    payload = {
        "source": "data/raw/mindcare_dataset_final.csv, train + validation rows only",
        "rows": int(len(d)),
        "built_by": "src/build_recommendation_templates.py",
        "caffeine_threshold_mg": CAFFEINE_THRESHOLD_MG,
        "protein_by_gender": protein_by_gender,
        "tiers": tiers,
        "tier_lookup": lookup,
    }

    # Verify before writing: render() must rebuild every original text exactly.
    mismatches = {"exercises": 0, "sleep_schedule": 0, "nutrition": 0}
    columns = {"exercises": "Exercises", "sleep_schedule": "Sleep_Schedule", "nutrition": "Nutrition"}
    for tier, gender, sleep_hours, caffeine, alcohol, *texts in zip(
            d["Severity"], d["Gender"], d["Sleep Hours"], d["Caffeine Intake (mg/day)"],
            d["Alcohol Consumption (drinks/week)"], *(d[c] for c in columns.values())):
        got = render(tier, gender, sleep_hours, int(caffeine), int(alcohol), templates=payload)
        for key, text in zip(columns, texts):
            mismatches[key] += got[key] != text
    print(f"exact-rebuild mismatches over {len(d):,} rows: {mismatches}")
    if any(mismatches.values()):
        raise SystemExit("STOP: templates do not reproduce the data exactly - nothing written.")

    TEMPLATES_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    template_advice.load_templates.cache_clear()
    print(f"Saved {TEMPLATES_PATH.relative_to(ROOT)} ({len(lookup)} lookup entries)")


if __name__ == "__main__":
    main()
