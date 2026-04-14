"""Tests for trust score engine — written BEFORE implementation (TDD)."""
from unittest.mock import patch, MagicMock


class TestScoreToTier:
    """Test tier derivation from trust score."""

    def test_frozen_at_zero(self):
        from api.src.services.trust_score import score_to_tier
        assert score_to_tier(0) == "frozen"

    def test_frozen_at_boundary(self):
        from api.src.services.trust_score import score_to_tier
        assert score_to_tier(25) == "frozen"

    def test_restricted_at_lower_boundary(self):
        from api.src.services.trust_score import score_to_tier
        assert score_to_tier(26) == "restricted"

    def test_restricted_at_upper_boundary(self):
        from api.src.services.trust_score import score_to_tier
        assert score_to_tier(50) == "restricted"

    def test_standard_at_lower_boundary(self):
        from api.src.services.trust_score import score_to_tier
        assert score_to_tier(51) == "standard"

    def test_standard_at_upper_boundary(self):
        from api.src.services.trust_score import score_to_tier
        assert score_to_tier(75) == "standard"

    def test_trusted_at_lower_boundary(self):
        from api.src.services.trust_score import score_to_tier
        assert score_to_tier(76) == "trusted"

    def test_trusted_at_max(self):
        from api.src.services.trust_score import score_to_tier
        assert score_to_tier(100) == "trusted"

    def test_mid_range_frozen(self):
        from api.src.services.trust_score import score_to_tier
        assert score_to_tier(12) == "frozen"

    def test_mid_range_restricted(self):
        from api.src.services.trust_score import score_to_tier
        assert score_to_tier(38) == "restricted"

    def test_mid_range_standard(self):
        from api.src.services.trust_score import score_to_tier
        assert score_to_tier(63) == "standard"

    def test_mid_range_trusted(self):
        from api.src.services.trust_score import score_to_tier
        assert score_to_tier(88) == "trusted"


class TestApplyScoreDelta:
    """Test trust score delta application with clamping."""

    @patch("api.src.services.trust_score.supabase")
    def test_positive_delta(self, mock_sb):
        from api.src.services.trust_score import apply_score_delta
        # Agent has score 50, apply +3
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "agent-1", "trust_score": 50}]
        )
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

        result = apply_score_delta("agent-1", 3)
        assert result["old_score"] == 50
        assert result["new_score"] == 53
        assert result["old_tier"] == "restricted"
        assert result["new_tier"] == "standard"

    @patch("api.src.services.trust_score.supabase")
    def test_negative_delta(self, mock_sb):
        from api.src.services.trust_score import apply_score_delta
        # Agent has score 50, apply -10
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "agent-1", "trust_score": 50}]
        )
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

        result = apply_score_delta("agent-1", -10)
        assert result["old_score"] == 50
        assert result["new_score"] == 40
        assert result["old_tier"] == "restricted"
        assert result["new_tier"] == "restricted"

    @patch("api.src.services.trust_score.supabase")
    def test_clamp_at_zero(self, mock_sb):
        from api.src.services.trust_score import apply_score_delta
        # Agent has score 5, apply -20 → should clamp to 0
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "agent-1", "trust_score": 5}]
        )
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

        result = apply_score_delta("agent-1", -20)
        assert result["new_score"] == 0
        assert result["new_tier"] == "frozen"

    @patch("api.src.services.trust_score.supabase")
    def test_clamp_at_100(self, mock_sb):
        from api.src.services.trust_score import apply_score_delta
        # Agent has score 95, apply +10 → should clamp to 100
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "agent-1", "trust_score": 95}]
        )
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

        result = apply_score_delta("agent-1", 10)
        assert result["new_score"] == 100
        assert result["new_tier"] == "trusted"

    @patch("api.src.services.trust_score.supabase")
    def test_tier_transition_down(self, mock_sb):
        from api.src.services.trust_score import apply_score_delta
        # Agent at 26 (restricted), apply -1 → 25 (frozen)
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "agent-1", "trust_score": 26}]
        )
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

        result = apply_score_delta("agent-1", -1)
        assert result["old_tier"] == "restricted"
        assert result["new_tier"] == "frozen"

    @patch("api.src.services.trust_score.supabase")
    def test_returns_agent_id(self, mock_sb):
        from api.src.services.trust_score import apply_score_delta
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "agent-1", "trust_score": 50}]
        )
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

        result = apply_score_delta("agent-1", 5)
        assert result["agent_id"] == "agent-1"
