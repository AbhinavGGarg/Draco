"""Tests for evidence bundle creation and update system."""
import pytest
from unittest.mock import patch, MagicMock

from api.src.services.evidence import create_evidence_bundle, update_evidence_execution


# --- Fixtures ---

@pytest.fixture
def sample_intent():
    return {
        "product_url": "https://amazon.com/dp/B08XYZ",
        "amount": 29.99,
        "merchant": "Amazon",
        "category": "electronics",
        "product_description": "USB-C cable",
    }


@pytest.fixture
def sample_account_state():
    return {
        "balance": 470.01,
        "trust_score": 53,
        "tier": "standard",
        "risk_status": "normal",
    }


@pytest.fixture
def sample_policy_checks():
    return [
        {"check": "tier_not_frozen", "result": "pass"},
        {"check": "risk_rate_check", "result": "pass", "detail": "all rates < 1%"},
        {"check": "amount_under_limit", "result": "pass", "detail": "29.99 < 100"},
        {"check": "category_allowed", "result": "pass"},
        {"check": "balance_sufficient", "result": "pass"},
        {"check": "weekly_limit_ok", "result": "pass"},
    ]


# --- create_evidence_bundle tests ---

def test_create_bundle_has_all_sections(sample_intent, sample_account_state, sample_policy_checks):
    bundle = create_evidence_bundle(sample_intent, sample_account_state, sample_policy_checks)
    assert "intent_snapshot" in bundle
    assert "account_state_at_purchase" in bundle
    assert "policy_checks" in bundle


def test_create_bundle_preserves_intent(sample_intent, sample_account_state, sample_policy_checks):
    bundle = create_evidence_bundle(sample_intent, sample_account_state, sample_policy_checks)
    assert bundle["intent_snapshot"] == sample_intent
    assert bundle["intent_snapshot"]["product_url"] == "https://amazon.com/dp/B08XYZ"
    assert bundle["intent_snapshot"]["amount"] == 29.99
    assert bundle["intent_snapshot"]["merchant"] == "Amazon"
    assert bundle["intent_snapshot"]["category"] == "electronics"
    assert bundle["intent_snapshot"]["product_description"] == "USB-C cable"


def test_create_bundle_preserves_account_state(sample_intent, sample_account_state, sample_policy_checks):
    bundle = create_evidence_bundle(sample_intent, sample_account_state, sample_policy_checks)
    assert bundle["account_state_at_purchase"] == sample_account_state
    assert bundle["account_state_at_purchase"]["balance"] == 470.01
    assert bundle["account_state_at_purchase"]["trust_score"] == 53
    assert bundle["account_state_at_purchase"]["tier"] == "standard"
    assert bundle["account_state_at_purchase"]["risk_status"] == "normal"


def test_create_bundle_preserves_policy_checks(sample_intent, sample_account_state, sample_policy_checks):
    bundle = create_evidence_bundle(sample_intent, sample_account_state, sample_policy_checks)
    assert bundle["policy_checks"] == sample_policy_checks
    assert len(bundle["policy_checks"]) == 6
    assert bundle["policy_checks"][0]["check"] == "tier_not_frozen"


# --- update_evidence_execution tests ---

@patch("api.src.services.evidence.supabase")
def test_update_matching_execution(mock_supabase, sample_intent):
    """Amount and merchant match exactly -> flagged=False."""
    existing_bundle = {"intent_snapshot": sample_intent, "account_state_at_purchase": {}, "policy_checks": []}
    mock_result = MagicMock()
    mock_result.data = [{"evidence": existing_bundle}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    execution = {"rye_order_id": "rye_abc123", "final_amount": 29.99, "final_merchant": "Amazon"}
    result = update_evidence_execution("tx-123", execution)

    assert result["execution_result"]["amount_match"] is True
    assert result["execution_result"]["merchant_match"] is True
    assert result["execution_result"]["flagged"] is False


@patch("api.src.services.evidence.supabase")
def test_update_amount_mismatch_over_5pct(mock_supabase, sample_intent):
    """Amount mismatch > 5% -> flagged=True, amount_match=False."""
    existing_bundle = {"intent_snapshot": sample_intent, "account_state_at_purchase": {}, "policy_checks": []}
    mock_result = MagicMock()
    mock_result.data = [{"evidence": existing_bundle}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    # 29.99 * 1.06 = 31.79 (6% over, exceeds 5% tolerance)
    execution = {"rye_order_id": "rye_abc123", "final_amount": 31.79, "final_merchant": "Amazon"}
    result = update_evidence_execution("tx-123", execution)

    assert result["execution_result"]["amount_match"] is False
    assert result["execution_result"]["flagged"] is True


@patch("api.src.services.evidence.supabase")
def test_update_amount_within_tolerance(mock_supabase, sample_intent):
    """Amount mismatch <= 5% -> flagged=False, amount_match=True."""
    existing_bundle = {"intent_snapshot": sample_intent, "account_state_at_purchase": {}, "policy_checks": []}
    mock_result = MagicMock()
    mock_result.data = [{"evidence": existing_bundle}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    # 29.99 * 1.04 = 31.19 (4% over, within 5% tolerance)
    execution = {"rye_order_id": "rye_abc123", "final_amount": 31.19, "final_merchant": "Amazon"}
    result = update_evidence_execution("tx-123", execution)

    assert result["execution_result"]["amount_match"] is True
    assert result["execution_result"]["flagged"] is False


@patch("api.src.services.evidence.supabase")
def test_update_merchant_mismatch(mock_supabase, sample_intent):
    """Different merchant -> flagged=True, merchant_match=False."""
    existing_bundle = {"intent_snapshot": sample_intent, "account_state_at_purchase": {}, "policy_checks": []}
    mock_result = MagicMock()
    mock_result.data = [{"evidence": existing_bundle}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    execution = {"rye_order_id": "rye_abc123", "final_amount": 29.99, "final_merchant": "Walmart"}
    result = update_evidence_execution("tx-123", execution)

    assert result["execution_result"]["merchant_match"] is False
    assert result["execution_result"]["flagged"] is True


@patch("api.src.services.evidence.supabase")
def test_update_merchant_case_insensitive(mock_supabase, sample_intent):
    """'amazon' vs 'Amazon' -> match (case-insensitive)."""
    existing_bundle = {"intent_snapshot": sample_intent, "account_state_at_purchase": {}, "policy_checks": []}
    mock_result = MagicMock()
    mock_result.data = [{"evidence": existing_bundle}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    execution = {"rye_order_id": "rye_abc123", "final_amount": 29.99, "final_merchant": "amazon"}
    result = update_evidence_execution("tx-123", execution)

    assert result["execution_result"]["merchant_match"] is True
    assert result["execution_result"]["flagged"] is False
