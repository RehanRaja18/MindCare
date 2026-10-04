"""
Clinical agreement evaluation tools for comparing AI predictions against
clinician-derived Hamilton scale classifications.

Phase 21/22 evaluation module - ready for paired AI prediction + clinician Hamilton score data.
"""

from sklearn.metrics import cohen_kappa_score, confusion_matrix
from typing import List, Tuple, Dict, Any


def compute_agreement_metrics(
    pairs: List[Tuple[str, str]]
) -> Dict[str, Any]:
    """
    Compute agreement metrics between AI predicted classes and Hamilton-derived classes.

    Args:
        pairs: List of tuples (ai_predicted_class, hamilton_derived_class)
               Classes are expected to be strings like 'Low', 'Medium', 'High'

    Returns:
        Dictionary with:
        - raw_agreement: float (0-1)
        - cohen_kappa: float (chance-corrected agreement)
        - confusion_matrix: 2D list (rows=hamilton, cols=AI)
        - labels: list of class labels in sorted order

    Note:
        This module is ready for use once real paired AI-prediction +
        clinician-Hamilton-score data exists (e.g., from a pilot study).
        There is no Hamilton score data currently available in this project.
        Do NOT run against synthetic or fabricated data.
    """
    if len(pairs) == 0:
        raise ValueError("At least one pair is required to compute agreement metrics")

    ai_preds = [pair[0] for pair in pairs]
    hamilton_classes = [pair[1] for pair in pairs]

    # Get all unique labels in sorted order
    labels = sorted(set(ai_preds + hamilton_classes))

    # Raw agreement rate
    matches = sum(1 for ai, hm in pairs if ai == hm)
    raw_agreement = matches / len(pairs)

    # Cohen's kappa
    kappa = cohen_kappa_score(hamilton_classes, ai_preds, labels=labels)

    # Confusion matrix
    cm = confusion_matrix(hamilton_classes, ai_preds, labels=labels)

    return {
        'raw_agreement': raw_agreement,
        'cohen_kappa': kappa,
        'confusion_matrix': cm.tolist(),
        'labels': labels,
        'n_samples': len(pairs)
    }