"""Tests for dispute filing endpoint: trust deltas, eligibility, balance credits."""
import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta, timezone
import json

from flask import Flask
from api.src.routes.disputes import disputes_bp

_SENTINEL = object()


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(disputes_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _mock_transaction(created_at=None, evidence=_SENTINEL, amount=29.99,
                      agent_id="agent-1", user_id="user-1", status="completed"):
    if created_at is None:
        created_at = datetime.now(timezone.utc).isoformat()
    if evidence is _SENTINEL:
        evidence = {"intent_snapshot": {"amount": 29.99}, "policy_checks": []}
    return {
        "id": "tx-1",
        "agent_id": agent_id,
        "user_id": user_id,
        "amount": amount,
        "status": status,
        "created_at": created_at,
        "evidence": evidence,
        "dispute_type": None,
    }


def _setup_mocks(mock_supabase, tx, agent_score=50, user_balance=470.0):
    """Wire up the chained Supabase mock calls."""
    tx_select = MagicMock()
    tx_select.data = [tx]
    tx_update = MagicMock()

    agent_select = MagicMock()
    agent_select.data = [{"trust_score": agent_score}]
    agent_update = MagicMock()

    user_select = MagicMock()
    user_select.data = [{"balance": user_balance}]
    user_update = MagicMock()

    def table_router(table_name):
        mock_table = MagicMock()
        if table_name == "transactions":
            mock_table.select.return_value.eq.return_value.execute.return_value = tx_select
            mock_table.update.return_value.eq.return_value.execute.return_value = tx_update
        elif table_name == "agents":
            mock_table.select.return_value.eq.return_value.execute.return_value = agent_select
            mock_table.update.return_value.eq.return_value.execute.return_value = agent_update
        elif table_name == "users":
            mock_table.select.return_value.eq.return_value.execute.return_value = user_select
            mock_table.update.return_value.eq.return_value.execute.return_value = user_update
        return mock_table

    mock_supabase.table.side_effect = table_router
    return mock_supabase


# --- Trust delta tests ---

@patch("api.src.routes.disputes.supabase")
@patch("api.src.services.trust_score.supabase")
def test_unauthorized_dispute_applies_minus_12(mock_ts_supa, mock_disp_supa, client):
    tx = _mock_transaction()
    _setup_mocks(mock_disp_supa, tx, agent_score=50)
    _setup_mocks(mock_ts_supa, tx, agent_score=50)

    resp = client.put("/api/transactions/tx-1/dispute",
                      json={"type": "unauthorized"})
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["trust_score"] == 38  # 50 + (-12)
    assert data["old_tier"] == "restricted"
    assert data["new_tier"] == "restricted"


@patch("api.src.routes.disputes.supabase")
@patch("api.src.services.trust_score.supabase")
def test_wrong_item_dispute_applies_minus_10(mock_ts_supa, mock_disp_supa, client):
    tx = _mock_transaction()
    _setup_mocks(mock_disp_supa, tx, agent_score=50)
    _setup_mocks(mock_ts_supa, tx, agent_score=50)

    resp = client.put("/api/transactions/tx-1/dispute",
                      json={"type": "wrong_item"})
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["trust_score"] == 40  # 50 + (-10)


@patch("api.src.routes.disputes.supabase")
@patch("api.src.services.trust_score.supabase")
def test_fulfillment_issue_applies_minus_5(mock_ts_supa, mock_disp_supa, client):
    tx = _mock_transaction()
    _setup_mocks(mock_disp_supa, tx, agent_score=50)
    _setup_mocks(mock_ts_supa, tx, agent_score=50)

    resp = client.put("/api/transactions/tx-1/dispute",
                      json={"type": "fulfillment_issue"})
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["trust_score"] == 45  # 50 + (-5)


# --- Eligibility + balance credit tests ---

@patch("api.src.routes.disputes.supabase")
@patch("api.src.services.trust_score.supabase")
def test_eligible_dispute_credits_balance(mock_ts_supa, mock_disp_supa, client):
    tx = _mock_transaction(amount=29.99)
    _setup_mocks(mock_disp_supa, tx, agent_score=50, user_balance=470.0)
    _setup_mocks(mock_ts_supa, tx, agent_score=50)

    resp = client.put("/api/transactions/tx-1/dispute",
                      json={"type": "unauthorized"})
    data = resp.get_json()

    assert data["eligible"] is True
    assert data["balance_credited"] == 29.99
    mock_disp_supa.table.assert_any_call("users")


@patch("api.src.routes.disputes.supabase")
@patch("api.src.services.trust_score.supabase")
def test_ineligible_dispute_over_7_days(mock_ts_supa, mock_disp_supa, client):
    old_date = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    tx = _mock_transaction(created_at=old_date)
    _setup_mocks(mock_disp_supa, tx, agent_score=50)
    _setup_mocks(mock_ts_supa, tx, agent_score=50)

    resp = client.put("/api/transactions/tx-1/dispute",
                      json={"type": "wrong_item"})
    data = resp.get_json()

    assert data["eligible"] is False
    assert data["balance_credited"] is None


# --- Status and type recording ---

@patch("api.src.routes.disputes.supabase")
@patch("api.src.services.trust_score.supabase")
def test_dispute_sets_status_and_type(mock_ts_supa, mock_disp_supa, client):
    tx = _mock_transaction()
    _setup_mocks(mock_disp_supa, tx, agent_score=50)
    _setup_mocks(mock_ts_supa, tx, agent_score=50)

    resp = client.put("/api/transactions/tx-1/dispute",
                      json={"type": "unauthorized"})

    assert resp.status_code == 200
    assert resp.get_json()["dispute_type"] == "unauthorized"

    update_calls = [c for c in mock_disp_supa.table.call_args_list
                    if c == call("transactions")]
    assert len(update_calls) >= 1


# --- Tier transition ---

@patch("api.src.routes.disputes.supabase")
@patch("api.src.services.trust_score.supabase")
def test_dispute_returns_tier_transition(mock_ts_supa, mock_disp_supa, client):
    tx = _mock_transaction()
    _setup_mocks(mock_disp_supa, tx, agent_score=26)
    _setup_mocks(mock_ts_supa, tx, agent_score=26)

    resp = client.put("/api/transactions/tx-1/dispute",
                      json={"type": "unauthorized"})
    data = resp.get_json()

    assert data["old_tier"] == "restricted"
    assert data["new_tier"] == "frozen"  # 26 - 12 = 14 -> frozen
    assert data["trust_score"] == 14


# --- Edge cases ---

@patch("api.src.routes.disputes.supabase")
def test_invalid_dispute_type_returns_400(mock_supa, client):
    resp = client.put("/api/transactions/tx-1/dispute",
                      json={"type": "nonexistent"})
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "invalid_type"


@patch("api.src.routes.disputes.supabase")
def test_transaction_not_found_returns_404(mock_supa, client):
    mock_result = MagicMock()
    mock_result.data = []
    mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

    resp = client.put("/api/transactions/tx-999/dispute",
                      json={"type": "unauthorized"})
    assert resp.status_code == 404
    assert resp.get_json()["code"] == "not_found"


@patch("api.src.routes.disputes.supabase")
@patch("api.src.services.trust_score.supabase")
def test_ineligible_no_evidence_no_credit(mock_ts_supa, mock_disp_supa, client):
    tx = _mock_transaction(evidence=None)  # explicitly None
    _setup_mocks(mock_disp_supa, tx, agent_score=50)
    _setup_mocks(mock_ts_supa, tx, agent_score=50)

    resp = client.put("/api/transactions/tx-1/dispute",
                      json={"type": "wrong_item"})
    data = resp.get_json()

    assert data["eligible"] is False
    assert data["balance_credited"] is None
