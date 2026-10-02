"""Estimated Severity tier and dataset recommendation bundle (Exercises /
Sleep_Schedule / Nutrition) for the psychologist-facing POST /patient-summary.

reports/recommendation_mapping_investigation.md found these dataset columns
are fixed synthetic templates: one bundle per Severity tier, with a few slots
filled from the patient's Sleep Hours, Caffeine Intake, Alcohol Consumption
and Gender. They are returned only as decision support for clinician review,
always with CAVEAT - never as validated advice, never shown to a patient
directly. /predict returns none of this.

The templates and the tier lookup are extracted from the train + validation
rows by src/build_recommendation_templates.py into
data/processed/recommendation_templates.json. That script refuses to write the
file unless render() rebuilds all 9,350 original texts exactly.

Severity tier: the model predicts Low/Medium/High, not a tier. A tier is a band
of (Anxiety Level + Stress Level) / 2, and the model never sees Anxiety Level,
so the tier here is only an ESTIMATE: the most common tier among train +
validation patients with the same 3-class label and Stress Level.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_PATH = ROOT / "data" / "processed" / "recommendation_templates.json"

TIERS = ["Minimal (1-2)", "Mild (3-4)", "Moderate (5-6)", "High (7-8)", "Severe (9-10)"]
# Representative Anxiety Level per 3-class label, used only when a (label, stress)
# combination never occurred in the data: the midpoint of the label's 1-3 / 4-6 / 7-10 range.
ANXIETY_MIDPOINT = {"Low": 2.0, "Medium": 5.0, "High": 8.5}

CAVEAT = (
    "Estimated severity and recommendation are a best-guess reconstruction (~88% accurate at best, "
    "lower given this model's own prediction error) from synthetic dataset templates. This is "
    "decision support for clinician review, not a recommendation to show a patient directly and "
    "not validated clinical advice."
)
NOT_PROVIDED_PROTEIN = "Protein: not provided (needs Gender)"
NOT_PROVIDED_ALCOHOL = "Alcohol: not provided (needs Alcohol Consumption)"


@lru_cache(maxsize=1)
def load_templates() -> dict:
    return json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))


def severity_band(anxiety: float, stress: float) -> str:
    """The dataset's Severity rule: a band of (Anxiety Level + Stress Level) / 2."""
    average = (anxiety + stress) / 2
    for upper, tier in zip([2.5, 4.5, 6.5, 8.5, 10.0], TIERS):
        if average <= upper:
            return tier
    return TIERS[-1]


def estimate_tier(predicted_class: str, stress_level: int) -> dict:
    """Most common tier for this (3-class label, Stress Level) in train + validation.

    Returns the tier, the share of those patients who actually had it (how often
    this guess would be right if the predicted class were correct), how many
    patients it's based on, and how it was chosen."""
    entry = load_templates()["tier_lookup"].get(f"{predicted_class}|{stress_level}")
    if entry is not None:
        return {**entry, "basis": "most common tier for this predicted level and stress level in the data"}
    return {
        "tier": severity_band(ANXIETY_MIDPOINT[predicted_class], stress_level),
        "share": None,
        "n": 0,
        "basis": "no patients with this combination in the data; used the band rule with a mid-range "
                 "anxiety level for the predicted class",
    }


def render(tier: str, gender: str | None, sleep_hours: float, caffeine_mg: int,
           alcohol_per_week: float | None, templates: dict | None = None) -> dict[str, str]:
    """Fill in one tier's templates exactly as the dataset does. `templates` defaults to the
    saved file; the build script passes its in-memory version to verify before saving.

    Gender and Alcohol Consumption are optional: when missing, their slots say "not provided"
    instead of guessing."""
    t = templates if templates is not None else load_templates()
    tier_t = t["tiers"][tier]
    reference = tier_t["sleep_reference_hours"]
    sleep = f"{tier_t['sleep_base']}; Current: {sleep_hours:.1f} hrs; " + (
        "On target" if sleep_hours >= reference - 1e-9 else f"Increase by {reference - sleep_hours:.1f} hrs")
    caffeine = (f"Reduce caffeine to <200 mg/day (current: {caffeine_mg} mg)"
                if caffeine_mg > t["caffeine_threshold_mg"] else f"Caffeine OK: {caffeine_mg} mg/day")
    if alcohol_per_week is None:
        alcohol = NOT_PROVIDED_ALCOHOL
    else:
        shown = int(alcohol_per_week) if float(alcohol_per_week).is_integer() else alcohol_per_week
        alcohol = f"Eliminate alcohol (current: {shown} drinks/week)" if alcohol_per_week > 0 else "No alcohol: good"
    protein = NOT_PROVIDED_PROTEIN if gender is None else f"Protein: {t['protein_by_gender'][gender]} g/day"
    nutrition = (f"{protein}; "
                 + tier_t["nutrition_base"].replace("<CAFFEINE>", caffeine).replace("<ALCOHOL>", alcohol))
    return {"exercises": tier_t["exercises"], "sleep_schedule": sleep, "nutrition": nutrition}
