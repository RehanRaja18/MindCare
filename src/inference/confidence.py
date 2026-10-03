"""Confident / borderline label for a prediction (canonical 3-class model).

A prediction is "confident" only if BOTH hold:
  1. its top-class probability is >= CONFIDENCE_THRESHOLD (0.70), and
  2. it is not a flagged non-High prediction: P(High) >= the review threshold
     while the predicted class is Low or Medium.
Otherwise it is "borderline".

Condition 2 exists because a plain confidence cut-off presented 108 of 968
true-High patients (out-of-fold) as a confident Medium; with it, 33 remain -
the ones the priority-review flag also misses.

Evidence (reports/confidence_label_11feature_v2.md, out-of-fold over the 9,350
train + validation rows): 56.2% of predictions are confident and 85.8% of those
are correct; borderline predictions are 70.2% correct. The label changes no
prediction and does not raise overall accuracy - it tells the reviewing
psychologist which predictions the model is unsure of. "Confident" means sure
of the top class, not that the patient is safe.
"""

from __future__ import annotations

CONFIDENCE_THRESHOLD = 0.70

REASON_LOW_CONFIDENCE = f"top probability below {CONFIDENCE_THRESHOLD:.2f}"
REASON_POSSIBLE_HIGH = "flagged as possibly High while predicting a lower class"


def confidence_label(probabilities: dict[str, float], predicted_class: str, review_flag: bool) -> dict:
    """Return the confidence fields for one prediction.

    probabilities: class name -> probability. review_flag: the priority-review
    flag for this prediction (P(High) >= its threshold).
    """
    ranked = sorted(probabilities, key=probabilities.get, reverse=True)
    confidence = float(probabilities[ranked[0]])
    reasons, between = [], [predicted_class]
    if confidence < CONFIDENCE_THRESHOLD:
        reasons.append(REASON_LOW_CONFIDENCE)
        between = ranked[:2]  # unsure between its two most likely classes
    if review_flag and predicted_class != "High":
        reasons.append(REASON_POSSIBLE_HIGH)
        if "High" not in between:
            between = between + ["High"]  # the doubt is about High, whatever the second-ranked class is
    return {
        "confidence": confidence,
        "confidence_label": "borderline" if reasons else "confident",
        "borderline_reasons": reasons,
        # The classes the prediction is unsure between; None when confident.
        "borderline_between": between if reasons else None,
    }
