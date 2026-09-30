"""Input validation for the 12 MindCare features (canonical model as of the
Age re-addition - see reports/feature_addition_age_3class.md), used before
any prediction. Alcohol Consumption (drinks/week), Dizziness, Smoking,
Recent Major Life Event, and Medication remain dropped (bottom-5 of the
original bottom-6 by SHAP importance, no measurable performance cost -
reports/feature_reduction_3class.md) and have no bounds here. Age was
re-added on 2026-09-22 as a clinical/UX decision (not performance-driven);
its bounds below reuse the original justification from before it was ever
dropped. Caffeine Intake (mg/day)'s bounds are unchanged - they are checked
against the *computed* mg value (see src/api/main.py's
estimate_caffeine_mg()) rather than a raw user-entered mg figure. Likewise,
Stress Level (1-10)'s bounds are unchanged but are checked against the value
*computed* from the 4 PSS-4 answers (src/inference/stress_scale.py's
estimate_stress_level()) - no caller submits a raw Stress Level any more.
Since that function already clamps to [1, 10], the check cannot fail for a
PSS-derived value; it stays as a guard in case a future caller bypasses the
conversion.

Two tiers per numeric feature, derived (not guessed) as follows:
- `observed_min`/`observed_max`: the exact min/max seen in
  data/raw/mindcare_dataset_final.csv (11,000 rows) - values outside this
  range are outside the model's training distribution, but not necessarily
  impossible.
- `hard_min`/`hard_max`: physically/clinically plausible outer bounds.
  For open-ended physiological quantities (Age, Heart Rate, Breathing Rate,
  Sleep Hours), these are standard clinical/physiological outer limits, not
  the observed CSV range plus an arbitrary buffer - e.g. Heart Rate's
  observed range (60-119 bpm) reflects this dataset's population, but
  30-220 bpm is the standard outer clinical range spanning severe
  bradycardia to extreme tachycardia, and is used here as the physically-
  impossible cutoff. For fixed rating scales (Stress Level (1-10), Diet
  Quality (1-10), Sweating Level (1-5)), the same small-margin approach is
  used rather than treating the labeled range as an absolute cutoff: a
  small margin beyond the defined range accommodates minor reporting or
  rounding variance (e.g. a half-point or slightly-over-scale response,
  such as "10.5"), while values far outside the scale are still rejected.
  For logically bounded counts (Physical Activity hours/week, Therapy Sessions
  per month), the hard bound is the literal ceiling implied by the unit
  (168 hours in a week; at most 31 days in a month).

A value outside [hard_min, hard_max] is rejected outright (physically
impossible). A value inside the hard range but outside the observed CSV
range is allowed through with a warning (valid but untested territory for
this model). Categorical features are closed sets (exact values observed in
the training data); anything else is rejected - there is no "unusual but
valid" tier for a fixed category list.

Separately from those tiers, Age must fall in the model's supported range,
ELIGIBLE_AGE_MIN-ELIGIBLE_AGE_MAX (18-49, decided 2026-09-27). These are
scope rules, not plausibility bounds, and the two sides are handled
differently (decided 2026-09-28):
- Under 18: minors may not register for MindCare at all - the web app's
  registration must block them. A request reaching this model with Age < 18
  means that check failed; it is rejected as "not eligible for MindCare",
  with no referral (UNDER_AGE_RATIONALE).
- Over 49: adults 50+ may use MindCare but get no AI pre-assessment; the
  request is rejected with an error telling the caller to refer the person
  directly to a psychologist (OVER_AGE_RATIONALE).
"""

from __future__ import annotations

from dataclasses import dataclass


class InputValidationError(ValueError):
    """Raised when one or more input features are physically/logically impossible."""


@dataclass(frozen=True)
class NumericRange:
    observed_min: float
    observed_max: float
    hard_min: float
    hard_max: float
    rationale: str


NUMERIC_RANGES: dict[str, NumericRange] = {
    "Age": NumericRange(
        observed_min=18, observed_max=64, hard_min=0, hard_max=120,
        rationale="0-120: outer bound of recorded human lifespan.",
    ),
    "Sleep Hours": NumericRange(
        observed_min=2.3, observed_max=11.3, hard_min=0, hard_max=24,
        rationale="0-24: a day has 24 hours.",
    ),
    "Physical Activity (hrs/week)": NumericRange(
        observed_min=0.0, observed_max=10.1, hard_min=0, hard_max=168,
        rationale="0-168: a week has 168 hours; cannot exercise more hours than exist in a week.",
    ),
    "Caffeine Intake (mg/day)": NumericRange(
        observed_min=0, observed_max=599, hard_min=0, hard_max=1200,
        rationale="0-1200: commonly cited threshold above which caffeine intake is associated "
        "with acute toxicity in adults (vs. ~400mg/day considered a high-but-typical intake).",
    ),
    "Stress Level (1-10)": NumericRange(
        observed_min=1, observed_max=10, hard_min=0, hard_max=12,
        rationale="0-12: 1-10 rating scale plus a small margin for reporting/rounding variance "
        "(e.g. a half-point response of 10.5); further outside this is not a plausible reading.",
    ),
    "Heart Rate (bpm)": NumericRange(
        observed_min=60, observed_max=119, hard_min=30, hard_max=220,
        rationale="30-220 bpm: standard clinical outer range, severe bradycardia to extreme "
        "tachycardia/maximal exertion.",
    ),
    "Breathing Rate (breaths/min)": NumericRange(
        observed_min=12, observed_max=29, hard_min=5, hard_max=60,
        rationale="5-60 breaths/min: standard clinical outer range, severe bradypnea to severe "
        "tachypnea.",
    ),
    "Sweating Level (1-5)": NumericRange(
        observed_min=1, observed_max=5, hard_min=0, hard_max=6,
        rationale="0-6: 1-5 rating scale plus a small margin for reporting/rounding variance.",
    ),
    "Therapy Sessions (per month)": NumericRange(
        observed_min=0, observed_max=12, hard_min=0, hard_max=31,
        rationale="0-31: a month has at most 31 days; cannot have more sessions than days.",
    ),
    "Diet Quality (1-10)": NumericRange(
        observed_min=1, observed_max=10, hard_min=0, hard_max=12,
        rationale="0-12: 1-10 rating scale plus a small margin for reporting/rounding variance.",
    ),
}

CATEGORICAL_ALLOWED: dict[str, set[str]] = {
    "Occupation": {
        "Artist", "Athlete", "Chef", "Doctor", "Engineer", "Freelancer", "Lawyer",
        "Musician", "Nurse", "Other", "Scientist", "Student", "Teacher",
    },
    "Family History of Anxiety": {"Yes", "No"},
}

ALL_FEATURES = list(NUMERIC_RANGES) + list(CATEGORICAL_ALLOWED)

# Supported age range for AI pre-assessment (inclusive). Outside it the model is not used at all.
ELIGIBLE_AGE_MIN = 18
ELIGIBLE_AGE_MAX = 49
UNDER_AGE_RATIONALE = (
    "the training data contains no one under 18, and physiological norms and consent rules "
    "differ for minors"
)
OVER_AGE_RATIONALE = (
    "in the training data the High-anxiety rate drops from 12-15% below age 50 to about 1% from "
    "50 on (a dataset artifact), so there is almost no evidence the model can recognise High "
    "anxiety at these ages"
)


def validate_patient(patient: dict) -> list[str]:
    """Validate one patient's raw feature dict.

    Returns a list of human-readable warnings for values that are valid but
    outside the training data's observed range. Raises InputValidationError
    (listing every violation found, not just the first) if any feature is
    missing or physically/logically impossible, or if Age is outside the
    supported ELIGIBLE_AGE_MIN-ELIGIBLE_AGE_MAX range.
    """
    errors: list[str] = []
    warnings: list[str] = []

    missing = [feature for feature in ALL_FEATURES if feature not in patient]
    if missing:
        errors.append(f"Missing required feature(s): {sorted(missing)}")

    for feature, bounds in NUMERIC_RANGES.items():
        if feature not in patient:
            continue
        value = patient[feature]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{feature}: expected a number, got {value!r} ({type(value).__name__})")
            continue
        if value < bounds.hard_min or value > bounds.hard_max:
            errors.append(
                f"{feature}={value} is outside the physically plausible range "
                f"[{bounds.hard_min}, {bounds.hard_max}] ({bounds.rationale})"
            )
        elif value < bounds.observed_min or value > bounds.observed_max:
            warnings.append(
                f"{feature}={value} is outside the training data's observed range "
                f"[{bounds.observed_min}, {bounds.observed_max}] - plausible, but this model has "
                f"never seen a value like this; treat the prediction with extra caution."
            )

    # Eligibility, checked only for a plausible numeric Age (an impossible one is already an error above).
    age = patient.get("Age")
    age_bounds = NUMERIC_RANGES["Age"]
    if (
        isinstance(age, (int, float)) and not isinstance(age, bool)
        and age_bounds.hard_min <= age <= age_bounds.hard_max
    ):
        if age < ELIGIBLE_AGE_MIN:
            errors.append(
                f"Age={age} is under {ELIGIBLE_AGE_MIN} - not eligible for MindCare (adults only; "
                f"registration should have blocked this user). No prediction is made "
                f"({UNDER_AGE_RATIONALE})."
            )
        elif age > ELIGIBLE_AGE_MAX:
            errors.append(
                f"Age={age} is outside the supported range for AI pre-assessment "
                f"[{ELIGIBLE_AGE_MIN}, {ELIGIBLE_AGE_MAX}] - no prediction is made; refer this person "
                f"directly to a psychologist ({OVER_AGE_RATIONALE})."
            )

    for feature, allowed in CATEGORICAL_ALLOWED.items():
        if feature not in patient:
            continue
        value = patient[feature]
        if value not in allowed:
            errors.append(f"{feature}={value!r} is not a recognized value; expected one of {sorted(allowed)}")

    if errors:
        raise InputValidationError(
            f"Input validation failed with {len(errors)} error(s):\n  - " + "\n  - ".join(errors)
        )

    return warnings
