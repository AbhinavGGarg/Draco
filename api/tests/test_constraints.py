"""Tests for constraint enforcement — written BEFORE implementation (TDD)."""
from unittest.mock import patch, MagicMock

# Mock compute_risk_rates to return "normal" so constraint tests
# focus on constraint logic without needing to mock risk_metrics.supabase
_NORMAL_RISK = {"status": "normal", "dispute_rate": 0.0, "flagged_rate": 0.0,
                "unauthorized_rate": 0.0, "wrong_item_rate": 0.0,
                "total_completed_30d": 0, "total_disputes_30d": 0, "total_flagged_30d": 0}


def _mock_agent(trust_score=50, constraints=None):
    """Helper to create a mock agent record."""
    if constraints is None:
        constraints = {
            "max_per_transaction": 100,
            "max_per_week": 500,
            "allowed_categories": ["electronics", "groceries", "books", "clothing", "home", "office"],
            "blocked_merchants": [],
        }
    return {
        "id": "agent-1",
        "user_id": "user-1",
        "trust_score": trust_score,
        "constraints": constraints,
    }


def _mock_user(balance=500.0):
    return {"id": "user-1", "balance": balance}


class TestEnforceConstraints:
    """Test full constraint enforcement pipeline."""

    @patch("api.src.services.constraints.supabase")
    def test_frozen_agent_denied(self, mock_sb):
        from api.src.services.constraints import enforce_constraints
        # Agent with score 20 → frozen tier
        agent = _mock_agent(trust_score=20)
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[agent]
        )

        result = enforce_constraints("agent-1", 10.0, "Amazon", "electronics")
        assert result["decision"] == "DENY"
        assert result["reason"] == "agent_frozen"


    @patch("api.src.services.constraints.supabase")
    @patch("api.src.services.constraints.apply_score_delta")
    def test_exceeds_tier_limit_denied(self, mock_delta, mock_sb):
        from api.src.services.constraints import enforce_constraints
        # Restricted tier agent (score 40), effective limit $25
        agent = _mock_agent(trust_score=40, constraints={
            "max_per_transaction": 200,
            "max_per_week": 500,
            "allowed_categories": ["electronics"],
            "blocked_merchants": [],
        })
        user = _mock_user(balance=500.0)

        def table_side_effect(name):
            mock_tbl = MagicMock()
            if name == "agents":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[agent])
            elif name == "users":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[user])
            elif name == "transactions":
                mock_tbl.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=[])
            return mock_tbl

        mock_sb.table.side_effect = table_side_effect

        result = enforce_constraints("agent-1", 30.0, "Amazon", "electronics")
        assert result["decision"] == "DENY"
        assert result["reason"] == "exceeds_transaction_limit"
        mock_delta.assert_called_once_with("agent-1", -5)


    @patch("api.src.services.constraints.supabase")
    @patch("api.src.services.constraints.apply_score_delta")
    def test_blocked_category_denied(self, mock_delta, mock_sb):
        from api.src.services.constraints import enforce_constraints
        # Standard tier agent, but category not in allowed list
        agent = _mock_agent(trust_score=60, constraints={
            "max_per_transaction": 100,
            "max_per_week": 500,
            "allowed_categories": ["groceries", "books"],
            "blocked_merchants": [],
        })
        user = _mock_user(balance=500.0)

        def table_side_effect(name):
            mock_tbl = MagicMock()
            if name == "agents":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[agent])
            elif name == "users":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[user])
            elif name == "transactions":
                mock_tbl.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=[])
            return mock_tbl

        mock_sb.table.side_effect = table_side_effect

        result = enforce_constraints("agent-1", 50.0, "Amazon", "electronics")
        assert result["decision"] == "DENY"
        assert result["reason"] == "blocked_category_or_merchant"
        mock_delta.assert_called_once_with("agent-1", -8)


    @patch("api.src.services.constraints.supabase")
    @patch("api.src.services.constraints.apply_score_delta")
    def test_blocked_merchant_denied(self, mock_delta, mock_sb):
        from api.src.services.constraints import enforce_constraints
        agent = _mock_agent(trust_score=60, constraints={
            "max_per_transaction": 100,
            "max_per_week": 500,
            "allowed_categories": ["electronics"],
            "blocked_merchants": ["ShadyStore"],
        })
        user = _mock_user(balance=500.0)

        def table_side_effect(name):
            mock_tbl = MagicMock()
            if name == "agents":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[agent])
            elif name == "users":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[user])
            elif name == "transactions":
                mock_tbl.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=[])
            return mock_tbl

        mock_sb.table.side_effect = table_side_effect

        result = enforce_constraints("agent-1", 50.0, "ShadyStore", "electronics")
        assert result["decision"] == "DENY"
        assert result["reason"] == "blocked_category_or_merchant"
        mock_delta.assert_called_once_with("agent-1", -8)


    @patch("api.src.services.constraints.supabase")
    def test_insufficient_balance_denied(self, mock_sb):
        from api.src.services.constraints import enforce_constraints
        agent = _mock_agent(trust_score=60)
        user = _mock_user(balance=10.0)

        def table_side_effect(name):
            mock_tbl = MagicMock()
            if name == "agents":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[agent])
            elif name == "users":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[user])
            elif name == "transactions":
                mock_tbl.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=[])
            return mock_tbl

        mock_sb.table.side_effect = table_side_effect

        result = enforce_constraints("agent-1", 50.0, "Amazon", "electronics")
        assert result["decision"] == "DENY"
        assert result["reason"] == "insufficient_balance"


    @patch("api.src.services.constraints.supabase")
    def test_weekly_limit_exceeded_denied(self, mock_sb):
        from api.src.services.constraints import enforce_constraints
        agent = _mock_agent(trust_score=60, constraints={
            "max_per_transaction": 100,
            "max_per_week": 200,
            "allowed_categories": ["electronics"],
            "blocked_merchants": [],
        })
        user = _mock_user(balance=500.0)
        # Already spent $180 this week
        existing_txs = [{"amount": 90.0}, {"amount": 90.0}]

        def table_side_effect(name):
            mock_tbl = MagicMock()
            if name == "agents":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[agent])
            elif name == "users":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[user])
            elif name == "transactions":
                mock_tbl.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=existing_txs)
            return mock_tbl

        mock_sb.table.side_effect = table_side_effect

        result = enforce_constraints("agent-1", 50.0, "Amazon", "electronics")
        assert result["decision"] == "DENY"
        assert result["reason"] == "exceeds_weekly_limit"


    @patch("api.src.services.constraints.supabase")
    def test_all_checks_pass_approve(self, mock_sb):
        from api.src.services.constraints import enforce_constraints
        agent = _mock_agent(trust_score=60)
        user = _mock_user(balance=500.0)

        def table_side_effect(name):
            mock_tbl = MagicMock()
            if name == "agents":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[agent])
            elif name == "users":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[user])
            elif name == "transactions":
                mock_tbl.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=[])
            return mock_tbl

        mock_sb.table.side_effect = table_side_effect

        result = enforce_constraints("agent-1", 50.0, "Amazon", "electronics")
        assert result["decision"] == "APPROVE"
        assert result["reason"] == "all_checks_passed"


    @patch("api.src.services.constraints.supabase")
    def test_tier_override_restricted_effective_limit(self, mock_sb):
        from api.src.services.constraints import enforce_constraints
        # User set max $200, but restricted tier caps at $25
        agent = _mock_agent(trust_score=40, constraints={
            "max_per_transaction": 200,
            "max_per_week": 500,
            "allowed_categories": ["electronics"],
            "blocked_merchants": [],
        })
        user = _mock_user(balance=500.0)

        def table_side_effect(name):
            mock_tbl = MagicMock()
            if name == "agents":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[agent])
            elif name == "users":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[user])
            elif name == "transactions":
                mock_tbl.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=[])
            return mock_tbl

        mock_sb.table.side_effect = table_side_effect

        # $20 is under the $25 restricted limit → should pass
        result = enforce_constraints("agent-1", 20.0, "Amazon", "electronics")
        assert result["decision"] == "APPROVE"
        assert result["reason"] == "all_checks_passed"
