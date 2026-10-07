"""Perceived Stress Scale (PSS-4) -> model Stress Level (1-10) conversion.

The model was trained on the dataset's raw "Stress Level (1-10)" column, an
ungrounded self-rating with no defined anchors. At inference time the API
instead asks the 4 items of the PSS-4 (Cohen, Kamarck & Mermelstein, 1983)
and converts the answers into the 1-10 value the model expects. Training and
evaluation code is unaffected: it still uses the dataset's real 1-10 column.

Shared by src/api/main.py (the patient-facing API) and
src/inference/predict_single.py (the developer debug script), so both speak
the same PSS input format.
"""

from __future__ import annotations

import math

from src.inference.input_validation import InputValidationError


PSS_ITEM_MIN = 0
PSS_ITEM_MAX = 4
PSS_TOTAL_MAX = 4 * PSS_ITEM_MAX  # 16
STRESS_LEVEL_MIN = 1
STRESS_LEVEL_MAX = 10

# The 4 PSS-4 answer fields, in questionnaire order. Each is answered for "in the last month,
# how often have you..." on 0=Never, 1=Almost never, 2=Sometimes, 3=Fairly often, 4=Very often.
PSS_FIELDS = (
    "pss_uncontrollable",          # ...felt unable to control the important things in your life?
    "pss_confident",               # ...felt confident about your ability to handle personal problems? (reverse)
    "pss_going_your_way",          # ...felt that things were going your way? (reverse)
    "pss_difficulties_piling_up",  # ...felt difficulties were piling up so high you could not overcome them?
)


def estimate_stress_level(
    pss_uncontrollable: int,
    pss_confident: int,
    pss_going_your_way: int,
    pss_difficulties_piling_up: int,
) -> int:
    """Convert PSS-4 answers to the model's Stress Level (1-10) scale.

    Scoring follows the PSS-4 of Cohen, S., Kamarck, T., & Mermelstein, R.
    (1983). A global measure of perceived stress. Journal of Health and
    Social Behavior, 24(4), 385-396:

        1. Each item is answered 0-4.
        2. The two positively-worded items are reverse-scored:
           pss_confident -> 4 - pss_confident,
           pss_going_your_way -> 4 - pss_going_your_way.
        3. PSS-4 total = sum of the 4 (reverse-scored where applicable) items,
           range 0-16; higher = more perceived stress.

    The total is then mapped onto the model's 1-10 scale:

        stress_level = clamp(round_half_up(1 + total * 9 / 16), 1, 10)

    so total 0 -> 1 and total 16 -> 10, rounded to an integer because the
    training data's Stress Level column only ever holds integers 1-10.
    Rounding is half-up (not Python's banker's rounding), so e.g. a total of 8
    (1 + 4.5 = 5.5) maps to 6. The clamp is a safety net - for in-range
    answers the formula already stays within [1, 10].

    Caveat: this linear mapping is a pragmatic convention, not a validated
    crosswalk. The dataset's Stress Level was never measured with the PSS, so
    there is no evidence that a PSS-derived 6 means the same thing as a
    dataset 6 - only that both run low-to-high over the same range.

    Raises InputValidationError if any answer is not an integer in 0-4 (the
    API already enforces this via Pydantic; this guards other callers).
    """
    answers = {
        "pss_uncontrollable": pss_uncontrollable,
        "pss_confident": pss_confident,
        "pss_going_your_way": pss_going_your_way,
        "pss_difficulties_piling_up": pss_difficulties_piling_up,
    }
    errors = [
        f"{name}={value!r} is not a valid PSS-4 answer; expected an integer "
        f"{PSS_ITEM_MIN}-{PSS_ITEM_MAX}"
        for name, value in answers.items()
        if not isinstance(value, int) or isinstance(value, bool)
        or not PSS_ITEM_MIN <= value <= PSS_ITEM_MAX
    ]
    if errors:
        raise InputValidationError(
            f"Input validation failed with {len(errors)} error(s):\n  - " + "\n  - ".join(errors)
        )

    total = (
        pss_uncontrollable
        + (PSS_ITEM_MAX - pss_confident)
        + (PSS_ITEM_MAX - pss_going_your_way)
        + pss_difficulties_piling_up
    )
    scaled = STRESS_LEVEL_MIN + total * (STRESS_LEVEL_MAX - STRESS_LEVEL_MIN) / PSS_TOTAL_MAX
    return max(STRESS_LEVEL_MIN, min(STRESS_LEVEL_MAX, math.floor(scaled + 0.5)))
