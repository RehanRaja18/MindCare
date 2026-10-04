"""
Unit tests for clinical scoring scales.
Uses invented example item-score lists (NOT real patient data)
purely to verify arithmetic and boundary mapping.
"""

import pytest
from src.evaluation.clinical_scales import (
    score_hama,
    hama_severity_band,
    score_hamd,
    hamd_severity_band,
)


# ==================== HAM-A Tests ====================

class TestHAMAScoring:
    """Test HAM-A scoring function."""

    def test_all_zero_scores(self):
        """All-zero HAM-A items should score 0 -> Low severity."""
        scores = [0] * 14
        total = score_hama(scores)
        assert total == 0
        assert hama_severity_band(total) == "Low"

    def test_all_maximum_scores(self):
        """All-maximum HAM-A items should score 56 -> High severity."""
        scores = [4] * 14
        total = score_hama(scores)
        assert total == 56
        assert hama_severity_band(total) == "High"

    def test_mixed_scores(self):
        """Test with mixed valid scores."""
        scores = [0, 1, 2, 3, 4, 0, 1, 2, 3, 4, 0, 1, 2, 3]
        total = score_hama(scores)
        assert total == sum(scores)

    def test_invalid_length_too_short(self):
        """Should raise error for wrong number of items."""
        with pytest.raises(ValueError):
            score_hama([0, 1, 2])

    def test_invalid_length_too_long(self):
        """Should raise error for too many items."""
        with pytest.raises(ValueError):
            score_hama([0] * 15)

    def test_invalid_score_negative(self):
        """Should raise error for negative score."""
        with pytest.raises(ValueError):
            score_hama([0] * 13 + [-1])

    def test_invalid_score_above_max(self):
        """Should raise error for score > 4."""
        with pytest.raises(ValueError):
            score_hama([0] * 13 + [5])


class TestHAMASeverityBand:
    """Test HAM-A severity band mapping."""

    def test_low_boundary(self):
        assert hama_severity_band(0) == "Low"
        assert hama_severity_band(7) == "Low"

    def test_medium_boundary(self):
        assert hama_severity_band(8) == "Medium"
        assert hama_severity_band(23) == "Medium"

    def test_high_boundary(self):
        assert hama_severity_band(24) == "High"
        assert hama_severity_band(56) == "High"

    def test_boundary_7_to_8(self):
        """Verify transition from Low to Medium at 7/8."""
        assert hama_severity_band(7) == "Low"
        assert hama_severity_band(8) == "Medium"

    def test_boundary_23_to_24(self):
        """Verify transition from Medium to High at 23/24."""
        assert hama_severity_band(23) == "Medium"
        assert hama_severity_band(24) == "High"


# ==================== HAM-D Tests ====================

class TestHAMDScoring:
    """Test HAM-D scoring function."""

    def test_all_zero_scores(self):
        """All-zero HAM-D items should score 0."""
        total = score_hamd([0] * 9, [0] * 8)
        assert total == 0

    def test_all_maximum_scores(self):
        """All-maximum HAM-D items should score 52."""
        total = score_hamd([4] * 9, [2] * 8)
        assert total == (4 * 9) + (2 * 8)
        assert total == 36 + 16
        assert total == 52

    def test_mixed_valid_scores(self):
        """Test with mixed valid scores."""
        scores_0to4 = [0, 1, 2, 3, 4, 0, 1, 2, 3]
        scores_0to2 = [0, 1, 2, 0, 1, 2, 0, 1]
        total = score_hamd(scores_0to4, scores_0to2)
        assert total == sum(scores_0to4) + sum(scores_0to2)

    def test_invalid_length_0to4_too_short(self):
        """Should raise error for wrong number of 0-4 items."""
        with pytest.raises(ValueError):
            score_hamd([0] * 8, [0] * 8)

    def test_invalid_length_0to4_too_long(self):
        """Should raise error for too many 0-4 items."""
        with pytest.raises(ValueError):
            score_hamd([0] * 10, [0] * 8)

    def test_invalid_length_0to2_too_short(self):
        """Should raise error for wrong number of 0-2 items."""
        with pytest.raises(ValueError):
            score_hamd([0] * 9, [0] * 7)

    def test_invalid_length_0to2_too_long(self):
        """Should raise error for too many 0-2 items."""
        with pytest.raises(ValueError):
            score_hamd([0] * 9, [0] * 9)

    def test_invalid_score_0to4_above_max(self):
        """Should raise error for 0-4 score > 4."""
        with pytest.raises(ValueError):
            score_hamd([0] * 8 + [5], [0] * 8)

    def test_invalid_score_0to2_above_max(self):
        """Should raise error for 0-2 score > 2."""
        with pytest.raises(ValueError):
            score_hamd([0] * 9, [0] * 7 + [3])


class TestHAMDSeverityBand:
    """Test HAM-D severity band mapping."""

    def test_low_boundary(self):
        assert hamd_severity_band(0) == "Low"
        assert hamd_severity_band(7) == "Low"

    def test_medium_boundary(self):
        assert hamd_severity_band(8) == "Medium"
        assert hamd_severity_band(23) == "Medium"

    def test_high_boundary(self):
        assert hamd_severity_band(24) == "High"
        assert hamd_severity_band(52) == "High"

    def test_boundary_7_to_8(self):
        assert hamd_severity_band(7) == "Low"
        assert hamd_severity_band(8) == "Medium"

    def test_boundary_23_to_24(self):
        assert hamd_severity_band(23) == "Medium"
        assert hamd_severity_band(24) == "High"