"""Tests for risk metrics computation — 30-day rolling rates and escalation bands."""
import pytest
from unittest.mock import patch, MagicMock

from api.src.services.risk_metrics import compute_risk_rates


def _mock_supabase_response(txns):
    """Helper to mock supabase.table('transactions').select(...).eq(...).gte(...).execute()."""
    mock_result = MagicMock()
    mock_result.data = txns
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_result
    return mock_sb


# --- Core tests ---

@patch("api.src.services.risk_metrics.supabase")
def test_no_transactions_returns_normal(mock_sb):
    """No transactions at all -> all rates 0, status 'normal'."""
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=[])

    result = compute_risk_rates("agent-1")

    assert result["dispute_rate"] == 0.0
    assert result["flagged_rate"] == 0.0
    assert result["unauthorized_rate"] == 0.0
    assert result["wrong_item_rate"] == 0.0
    assert result["status"] == "normal"
    assert result["total_completed_30d"] == 0
    assert result["total_disputes_30d"] == 0
    assert result["total_flagged_30d"] == 0


@patch("api.src.services.risk_metrics.supabase")
def test_no_disputes_returns_normal(mock_sb):
    """50 completed, 0 disputes -> all rates 0, status 'normal'."""
    txns = [{"status": "completed", "dispute_type": None} for _ in range(50)]
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=txns)

    result = compute_risk_rates("agent-1")

    assert result["dispute_rate"] == 0.0
    assert result["flagged_rate"] == 0.0
    assert result["status"] == "normal"
    assert result["total_completed_30d"] == 50


@patch("api.src.services.risk_metrics.supabase")
def test_one_dispute_in_50_normal(mock_sb):
    """1 dispute / 50 completed = 2% -> 'normal' (threshold is 5%)."""
    txns = [{"status": "completed", "dispute_type": None} for _ in range(49)]
    txns.append({"status": "disputed", "dispute_type": "wrong_item"})
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=txns)

    result = compute_risk_rates("agent-1")

    assert result["dispute_rate"] == pytest.approx(1 / 50)
    assert result["status"] == "normal"


@patch("api.src.services.risk_metrics.supabase")
def test_six_percent_elevated(mock_sb):
    """3 disputes / 50 completed = 6% -> 'elevated' (threshold is 5%)."""
    txns = [{"status": "completed", "dispute_type": None} for _ in range(47)]
    txns.extend([{"status": "disputed", "dispute_type": "wrong_item"} for _ in range(3)])
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=txns)

    result = compute_risk_rates("agent-1")

    assert result["dispute_rate"] == pytest.approx(3 / 50)
    assert result["status"] == "elevated"


@patch("api.src.services.risk_metrics.supabase")
def test_sixteen_percent_frozen(mock_sb):
    """8 disputes / 50 completed = 16% -> 'frozen' (threshold is 15%)."""
    txns = [{"status": "completed", "dispute_type": None} for _ in range(42)]
    txns.extend([{"status": "disputed", "dispute_type": "unauthorized"} for _ in range(8)])
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=txns)

    result = compute_risk_rates("agent-1")

    assert result["dispute_rate"] == pytest.approx(8 / 50)
    assert result["status"] == "frozen"


@patch("api.src.services.risk_metrics.supabase")
def test_worst_rate_determines_status(mock_sb):
    """dispute_rate=0%, flagged_rate=12% -> 'restricted' (worst wins, threshold 10%)."""
    txns = [{"status": "completed", "dispute_type": None} for _ in range(44)]
    txns.extend([{"status": "flagged", "dispute_type": None} for _ in range(6)])
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=txns)

    result = compute_risk_rates("agent-1")

    assert result["dispute_rate"] == 0.0
    assert result["flagged_rate"] == pytest.approx(6 / 50)
    assert result["status"] == "restricted"


@patch("api.src.services.risk_metrics.supabase")
def test_rates_computed_correctly(mock_sb):
    """Verify each individual rate calculation with mixed statuses."""
    txns = [{"status": "completed", "dispute_type": None} for _ in range(45)]
    txns.append({"status": "disputed", "dispute_type": "unauthorized"})
    txns.append({"status": "disputed", "dispute_type": "wrong_item"})
    txns.append({"status": "disputed", "dispute_type": "wrong_item"})
    txns.append({"status": "flagged", "dispute_type": None})
    txns.append({"status": "flagged", "dispute_type": None})
    # total completed (completed+disputed+flagged) = 50
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=txns)

    result = compute_risk_rates("agent-1")

    assert result["dispute_rate"] == pytest.approx(3 / 50)  # 3 disputed
    assert result["flagged_rate"] == pytest.approx(2 / 50)  # 2 flagged
    assert result["unauthorized_rate"] == pytest.approx(1 / 50)  # 1 unauthorized
    assert result["wrong_item_rate"] == pytest.approx(2 / 50)  # 2 wrong_item
    assert result["total_completed_30d"] == 50
    assert result["total_disputes_30d"] == 3
    assert result["total_flagged_30d"] == 2


@patch("api.src.services.risk_metrics.supabase")
def test_unauthorized_rate_counted(mock_sb):
    """Unauthorized disputes counted separately in unauthorized_rate."""
    txns = [{"status": "completed", "dispute_type": None} for _ in range(48)]
    txns.append({"status": "disputed", "dispute_type": "unauthorized"})
    txns.append({"status": "disputed", "dispute_type": "fulfillment_issue"})
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=txns)

    result = compute_risk_rates("agent-1")

    assert result["unauthorized_rate"] == pytest.approx(1 / 50)
    assert result["dispute_rate"] == pytest.approx(2 / 50)
    assert result["wrong_item_rate"] == 0.0


@patch("api.src.services.risk_metrics.supabase")
def test_pending_and_failed_not_counted(mock_sb):
    """Pending and failed transactions should not be included in totals."""
    txns = [
        {"status": "completed", "dispute_type": None},
        {"status": "completed", "dispute_type": None},
        {"status": "pending", "dispute_type": None},
        {"status": "failed", "dispute_type": None},
        {"status": "disputed", "dispute_type": "wrong_item"},
    ]
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=txns)

    result = compute_risk_rates("agent-1")

    # Only completed + disputed + flagged count: 2 + 1 = 3
    assert result["total_completed_30d"] == 3
    assert result["dispute_rate"] == pytest.approx(1 / 3)
