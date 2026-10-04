"""
Clinical scoring scales for Hamilton Anxiety (HAM-A) and Hamilton Depression (HAM-D) scales.
These functions are intended for clinical validation comparison, not patient-facing input.
"""

def score_hama(item_scores: list[int]) -> int:
    """
    Calculate total HAM-A score from 14 item scores.

    Args:
        item_scores: List of 14 integers, each in range 0-4

    Returns:
        Total score (0-56)

    Raises:
        ValueError: If input list is not length 14 or any score not in 0-4
    """
    if len(item_scores) != 14:
        raise ValueError(f"HAM-A requires exactly 14 items, got {len(item_scores)}")

    for i, score in enumerate(item_scores):
        if not isinstance(score, int) or score < 0 or score > 4:
            raise ValueError(f"HAM-A item {i} must be integer in range 0-4, got {score}")

    return sum(item_scores)


def hama_severity_band(total: int) -> str:
    """
    Map HAM-A total score to severity band using Bruss et al. cutoffs.

    Args:
        total: HAM-A total score (0-56)

    Returns:
        Severity band: 'Low', 'Medium', or 'High'

    Note:
        Uses Bruss et al. cutoffs adapted to 3 bands to match model's output classes:
        - Low: 0-7
        - Medium: 8-23
        - High: 24-56

        Original Hamilton (1959) cutoffs differ and could be swapped in if needed.
    """
    if total <= 7:
        return "Low"
    elif total <= 23:
        return "Medium"
    else:
        return "High"


def score_hamd(item_scores_0to4: list[int], item_scores_0to2: list[int]) -> int:
    """
    Calculate total HAM-D score from separate 0-4 and 0-2 scale items.

    Args:
        item_scores_0to4: List of 9 integers, each in range 0-4
        item_scores_0to2: List of 8 integers, each in range 0-2

    Returns:
        Total score (0-52)

    Raises:
        ValueError: If input lists are incorrect length or contain invalid scores

    Important:
        The assignment of which HAM-D items use 0-4 vs 0-2 scale MUST be verified
        against the official public-domain HAM-D instrument (e.g., from NIH or APA)
        before using with real per-item data. This function expects pre-split lists.
    """
    # Validate 0-4 scale items
    if len(item_scores_0to4) != 9:
        raise ValueError(f"HAM-D 0-4 scale requires exactly 9 items, got {len(item_scores_0to4)}")

    for i, score in enumerate(item_scores_0to4):
        if not isinstance(score, int) or score < 0 or score > 4:
            raise ValueError(f"HAM-D 0-4 scale item {i} must be integer in range 0-4, got {score}")

    # Validate 0-2 scale items
    if len(item_scores_0to2) != 8:
        raise ValueError(f"HAM-D 0-2 scale requires exactly 8 items, got {len(item_scores_0to2)}")

    for i, score in enumerate(item_scores_0to2):
        if not isinstance(score, int) or score < 0 or score > 2:
            raise ValueError(f"HAM-D 0-2 scale item {i} must be integer in range 0-2, got {score}")

    return sum(item_scores_0to4) + sum(item_scores_0to2)


def hamd_severity_band(total: int) -> str:
    """
    Map HAM-D total score to severity band using Zimmerman et al. (2013) empirical cutoffs.

    Args:
        total: HAM-D total score (0-52)

    Returns:
        Severity band: 'Low', 'Medium', or 'High'

    Note:
        Uses Zimmerman et al. 2013 empirical cutoffs adapted to 3 bands to match model's output classes:
        - Low: 0-7
        - Medium: 8-23
        - High: 24-52
    """
    if total <= 7:
        return "Low"
    elif total <= 23:
        return "Medium"
    else:
        return "High"