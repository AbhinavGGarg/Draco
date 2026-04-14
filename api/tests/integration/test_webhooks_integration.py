"""Integration tests for purchase webhooks: purchase-request and purchase-complete flows."""
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask

from api.src.routes.webhooks import webhooks_bp

# ---------------------------------------------------------------------------
# Normal risk rates (no escalation) used across tests
# ---------------------------------------------------------------------------
_NORMAL_RISK = {
    "status": "normal",
    "dispute_rate": 0.0,
    "flagged_rate": 0.0,
    "unauthorized_rate": 0.0,
    "wrong_item_rate": 0.0,
    "total_completed_30d": 0,
    "total_disputes_30d": 0,
    "total_flagged_30d": 0,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(webhooks_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_user(balance=500.0, stripe_customer_id="cus_test",
               stripe_payment_method_id="pm_test", email="demo@openpay.dev"):
    return {
        "id": "user-1",
        "name": "Demo",
        "email": email,
        "balance": balance,
        "stripe_customer_id": stripe_customer_id,
        "stripe_payment_method_id": stripe_payment_method_id,
    }


def _make_agent(trust_score=60):
    return {"id": "agent-1", "trust_score": trust_score}


def _make_transaction(tx_id="tx-1", agent_id="agent-1", user_id="user-1",
                      amount=29.99, merchant="Amazon", category="electronics",
                      status="completed", session_id="sess-1",
                      rye_order_id="rye_abc", evidence=None):
    if evidence is None:
        evidence = {
            "intent_snapshot": {
                "product_url": "https://amazon.com/usb-c",
                "amount": amount,
                "merchant": merchant,
                "category": category,
                "product_description": "USB-C cable",
            },
            "account_state_at_purchase": {
                "balance": 500.0,
                "trust_score": 60,
                "tier": "standard",
                "risk_status": "normal",
            },
            "policy_checks": [
                {"check": "tier_not_frozen", "result": "pass"},
            ],
        }
    return {
        "id": tx_id,
        "agent_id": agent_id,
        "user_id": user_id,
        "amount": amount,
        "merchant": merchant,
        "category": category,
        "status": status,
        "session_id": session_id,
        "rye_order_id": rye_order_id,
        "evidence": evidence,
        "product_url": "https://amazon.com/usb-c",
        "product_description": "USB-C cable",
    }


def _purchase_request_payload(**overrides):
    base = {
        "agent_id": "agent-1",
        "user_id": "user-1",
        "product_url": "https://amazon.com/usb-c",
        "amount": 29.99,
        "merchant": "Amazon",
        "category": "electronics",
        "product_description": "USB-C cable",
        "session_id": "sess-1",
    }
    base.update(overrides)
    return base


def _purchase_complete_payload(**overrides):
    base = {
        "transaction_id": "tx-1",
        "final_amount": 29.99,
        "final_merchant": "Amazon",
        "rye_order_id": "rye_abc",
    }
    base.update(overrides)
    return base


# ===================================================================
# TestPurchaseCompleteChain
# ===================================================================
class TestPurchaseCompleteChain:
    """Tests the post-execution chain in purchase-complete."""

    def _build_complete_table_router(self, tx, steps=None, evidence_bundle=None):
        """Build a table_side_effect router for purchase-complete Supabase calls.

        purchase-complete touches:
          - transactions (select by id, update status/solana_tx_signature/evidence)
          - agent_steps (select by session_id)
        """
        if evidence_bundle is None:
            evidence_bundle = tx.get("evidence", {})

        def table_side_effect(table_name):
            mock_tbl = MagicMock()
            if table_name == "transactions":
                # .select("*").eq("id", tx_id).execute()
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(
                    data=[tx]
                )
                # .update(...).eq("id", tx_id).execute()
                mock_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock()
            elif table_name == "agent_steps":
                # .select("*").eq("session_id", ...).order("created_at").execute()
                mock_tbl.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
                    data=steps or []
                )
            return mock_tbl

        return table_side_effect

    # ---------------------------------------------------------------
    # 1. All services succeed
    # ---------------------------------------------------------------
    @patch("api.src.routes.webhooks.review_and_score")
    @patch("api.src.routes.webhooks.anchor_purchase")
    @patch("api.src.services.evidence.supabase")
    @patch("api.src.routes.webhooks.supabase")
    @patch("api.src.services.trust_score.supabase")
    def test_all_services_succeed(
        self, mock_ts_sb, mock_wh_sb, mock_ev_sb, mock_anchor, mock_gemini, client
    ):
        tx = _make_transaction()
        evidence_bundle = dict(tx["evidence"])
        # evidence.update_evidence_execution reads then writes evidence
        mock_ev_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"evidence": evidence_bundle}]
        )
        mock_ev_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        steps = [{"id": "step-1", "action": "search"}]
        mock_wh_sb.table.side_effect = self._build_complete_table_router(tx, steps=steps)

        # trust_score service reads agent row
        mock_ts_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"trust_score": 60}]
        )
        mock_ts_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        mock_anchor.return_value = "solana_sig_abc123"
        mock_gemini.return_value = {"verdict": "MATCH", "confidence": 0.95, "summary": "ok"}

        resp = client.post("/api/webhook/purchase-complete",
                           json=_purchase_complete_payload())
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["flagged"] is False
        assert data["gemini_review"]["verdict"] == "MATCH"

        # Solana anchor was called with correct args
        mock_anchor.assert_called_once()
        call_args = mock_anchor.call_args
        assert call_args[0][0] == "sess-1"  # session_id
        assert call_args[0][1] == "tx-1"    # tx_id

        # Solana signature was stored in transactions table
        mock_wh_sb.table.assert_any_call("transactions")

    # ---------------------------------------------------------------
    # 2. Amount mismatch flags transaction
    # ---------------------------------------------------------------
    @patch("api.src.routes.webhooks.review_and_score", None)
    @patch("api.src.routes.webhooks.anchor_purchase", None)
    @patch("api.src.services.evidence.supabase")
    @patch("api.src.routes.webhooks.supabase")
    @patch("api.src.services.trust_score.supabase")
    def test_amount_mismatch_flags_transaction(
        self, mock_ts_sb, mock_wh_sb, mock_ev_sb, client
    ):
        tx = _make_transaction(amount=29.99)
        evidence_bundle = dict(tx["evidence"])

        # Simulate update_evidence_execution finding a mismatch:
        # final_amount = 50.0 vs intent 29.99 => flagged=True
        def ev_table_router(table_name):
            mock_tbl = MagicMock()
            mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"evidence": evidence_bundle}]
            )
            mock_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock()
            return mock_tbl

        mock_ev_sb.table.side_effect = ev_table_router

        mock_wh_sb.table.side_effect = self._build_complete_table_router(tx)

        mock_ts_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"trust_score": 60}]
        )
        mock_ts_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resp = client.post("/api/webhook/purchase-complete",
                           json=_purchase_complete_payload(final_amount=50.0))
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["flagged"] is True
        # gemini_review is None because Gemini is disabled (set to None) and
        # deterministic mismatch returns early before Gemini
        assert data["gemini_review"] is None

    # ---------------------------------------------------------------
    # 3. Solana fails, purchase still succeeds
    # ---------------------------------------------------------------
    @patch("api.src.routes.webhooks.review_and_score")
    @patch("api.src.routes.webhooks.anchor_purchase")
    @patch("api.src.services.evidence.supabase")
    @patch("api.src.routes.webhooks.supabase")
    @patch("api.src.services.trust_score.supabase")
    def test_solana_fails_purchase_still_succeeds(
        self, mock_ts_sb, mock_wh_sb, mock_ev_sb, mock_anchor, mock_gemini, client
    ):
        tx = _make_transaction()
        evidence_bundle = dict(tx["evidence"])
        mock_ev_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"evidence": evidence_bundle}]
        )
        mock_ev_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        steps = [{"id": "step-1"}]
        mock_wh_sb.table.side_effect = self._build_complete_table_router(tx, steps=steps)

        mock_ts_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"trust_score": 60}]
        )
        mock_ts_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        # Solana returns None (failure)
        mock_anchor.return_value = None
        mock_gemini.return_value = {"verdict": "MATCH", "confidence": 0.9}

        resp = client.post("/api/webhook/purchase-complete",
                           json=_purchase_complete_payload())
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["flagged"] is False

        # anchor_purchase was called but returned None, so no update to
        # solana_tx_signature should occur. The webhook code only calls
        # update when signature is truthy.
        mock_anchor.assert_called_once()

    # ---------------------------------------------------------------
    # 4. Gemini fails, purchase still succeeds
    # ---------------------------------------------------------------
    @patch("api.src.routes.webhooks.review_and_score")
    @patch("api.src.routes.webhooks.anchor_purchase", None)
    @patch("api.src.services.evidence.supabase")
    @patch("api.src.routes.webhooks.supabase")
    @patch("api.src.services.trust_score.supabase")
    def test_gemini_fails_purchase_still_succeeds(
        self, mock_ts_sb, mock_wh_sb, mock_ev_sb, mock_gemini, client
    ):
        tx = _make_transaction()
        evidence_bundle = dict(tx["evidence"])
        mock_ev_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"evidence": evidence_bundle}]
        )
        mock_ev_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        mock_wh_sb.table.side_effect = self._build_complete_table_router(tx)

        mock_ts_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"trust_score": 60}]
        )
        mock_ts_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        # Gemini raises an exception
        mock_gemini.side_effect = RuntimeError("Gemini API unreachable")

        resp = client.post("/api/webhook/purchase-complete",
                           json=_purchase_complete_payload())
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["flagged"] is False
        # gemini_review is None because it errored
        assert data["gemini_review"] is None

    # ---------------------------------------------------------------
    # 5. Both Solana and Gemini fail, only evidence updated
    # ---------------------------------------------------------------
    @patch("api.src.routes.webhooks.review_and_score")
    @patch("api.src.routes.webhooks.anchor_purchase")
    @patch("api.src.services.evidence.supabase")
    @patch("api.src.routes.webhooks.supabase")
    @patch("api.src.services.trust_score.supabase")
    def test_both_solana_and_gemini_fail(
        self, mock_ts_sb, mock_wh_sb, mock_ev_sb, mock_anchor, mock_gemini, client
    ):
        tx = _make_transaction()
        evidence_bundle = dict(tx["evidence"])
        mock_ev_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"evidence": evidence_bundle}]
        )
        mock_ev_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        steps = [{"id": "step-1"}]
        mock_wh_sb.table.side_effect = self._build_complete_table_router(tx, steps=steps)

        mock_ts_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"trust_score": 60}]
        )
        mock_ts_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        mock_anchor.return_value = None
        mock_gemini.side_effect = Exception("Gemini down")

        resp = client.post("/api/webhook/purchase-complete",
                           json=_purchase_complete_payload())
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["flagged"] is False
        assert data["gemini_review"] is None

        # anchor was called, but returned None
        mock_anchor.assert_called_once()

    # ---------------------------------------------------------------
    # 6. Transaction not found returns 404
    # ---------------------------------------------------------------
    @patch("api.src.services.evidence.supabase")
    @patch("api.src.routes.webhooks.supabase")
    def test_transaction_not_found_returns_404(self, mock_wh_sb, mock_ev_sb, client):
        # update_evidence_execution reads evidence first; but the webhook
        # checks for missing tx before calling it
        empty_result = MagicMock(data=[])
        mock_wh_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = empty_result

        resp = client.post("/api/webhook/purchase-complete",
                           json=_purchase_complete_payload(transaction_id="tx-nonexistent"))
        data = resp.get_json()

        assert resp.status_code == 404
        assert data["code"] == "not_found"


# ===================================================================
# TestPurchaseRequestFlow
# ===================================================================
class TestPurchaseRequestFlow:
    """Tests the pre-execution flow in purchase-request."""

    def _build_request_table_router(self, user, agent, inserted_tx=None):
        """Build table_side_effect for purchase-request Supabase calls.

        purchase-request touches:
          - users (select by id, update balance/stripe fields)
          - agents (select trust_score by id)
          - transactions (insert, update status)
        """
        if inserted_tx is None:
            inserted_tx = {
                "id": "tx-new-1",
                "agent_id": agent["id"] if isinstance(agent, dict) else "agent-1",
                "user_id": user["id"],
                "amount": 29.99,
                "status": "pending",
            }

        def table_side_effect(table_name):
            mock_tbl = MagicMock()
            if table_name == "users":
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(
                    data=[user]
                )
                mock_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock()
            elif table_name == "agents":
                agent_data = agent if isinstance(agent, dict) else {"trust_score": agent}
                mock_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(
                    data=[agent_data]
                )
                mock_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock()
            elif table_name == "transactions":
                mock_tbl.insert.return_value.execute.return_value = MagicMock(
                    data=[inserted_tx]
                )
                mock_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock()
            return mock_tbl

        return table_side_effect

    # ---------------------------------------------------------------
    # 1. Happy path: approve
    # ---------------------------------------------------------------
    @patch("api.src.routes.webhooks.rye_checkout")
    @patch("api.src.routes.webhooks.stripe_charge")
    @patch("api.src.routes.webhooks.enforce_constraints")
    @patch("api.src.routes.webhooks.compute_risk_rates", return_value=_NORMAL_RISK)
    @patch("api.src.services.trust_score.supabase")
    @patch("api.src.routes.webhooks.supabase")
    def test_happy_path_approve(
        self, mock_wh_sb, mock_ts_sb, mock_risk, mock_enforce,
        mock_stripe, mock_rye, client
    ):
        user = _make_user()
        agent = _make_agent(trust_score=60)

        mock_wh_sb.table.side_effect = self._build_request_table_router(user, agent)

        # trust_score service (apply_score_delta for +3)
        mock_ts_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"trust_score": 60}]
        )
        mock_ts_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        mock_enforce.return_value = {"decision": "APPROVE", "reason": "all_checks_passed"}
        mock_stripe.return_value = {"id": "pi_test123", "status": "succeeded"}
        mock_rye.return_value = {"order_id": "rye_order_1", "status": "completed"}

        resp = client.post("/api/webhook/purchase-request",
                           json=_purchase_request_payload())
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["decision"] == "APPROVE"
        assert data["reason"] == "all_checks_passed"
        assert data["transaction_id"] == "tx-new-1"

        mock_stripe.assert_called_once_with("cus_test", "pm_test", 29.99)
        mock_rye.assert_called_once_with("https://amazon.com/usb-c", 29.99)

    # ---------------------------------------------------------------
    # 2. Stripe decline denies
    # ---------------------------------------------------------------
    @patch("api.src.routes.webhooks.rye_checkout")
    @patch("api.src.routes.webhooks.stripe_charge")
    @patch("api.src.routes.webhooks.enforce_constraints")
    @patch("api.src.routes.webhooks.compute_risk_rates", return_value=_NORMAL_RISK)
    @patch("api.src.services.trust_score.supabase")
    @patch("api.src.routes.webhooks.supabase")
    def test_stripe_decline_denies(
        self, mock_wh_sb, mock_ts_sb, mock_risk, mock_enforce,
        mock_stripe, mock_rye, client
    ):
        user = _make_user()
        agent = _make_agent(trust_score=60)

        mock_wh_sb.table.side_effect = self._build_request_table_router(user, agent)
        mock_ts_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"trust_score": 60}]
        )
        mock_ts_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        mock_enforce.return_value = {"decision": "APPROVE", "reason": "all_checks_passed"}
        mock_stripe.return_value = {"id": None, "status": "failed", "error": "card declined"}

        resp = client.post("/api/webhook/purchase-request",
                           json=_purchase_request_payload())
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["decision"] == "DENY"
        assert data["reason"] == "card_declined"
        # Rye should never be called when Stripe fails
        mock_rye.assert_not_called()

    # ---------------------------------------------------------------
    # 3. Rye checkout fails
    # ---------------------------------------------------------------
    @patch("api.src.routes.webhooks.rye_checkout")
    @patch("api.src.routes.webhooks.stripe_charge")
    @patch("api.src.routes.webhooks.enforce_constraints")
    @patch("api.src.routes.webhooks.compute_risk_rates", return_value=_NORMAL_RISK)
    @patch("api.src.services.trust_score.supabase")
    @patch("api.src.routes.webhooks.supabase")
    def test_rye_checkout_fails(
        self, mock_wh_sb, mock_ts_sb, mock_risk, mock_enforce,
        mock_stripe, mock_rye, client
    ):
        user = _make_user()
        agent = _make_agent(trust_score=60)

        mock_wh_sb.table.side_effect = self._build_request_table_router(user, agent)
        mock_ts_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"trust_score": 60}]
        )
        mock_ts_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        mock_enforce.return_value = {"decision": "APPROVE", "reason": "all_checks_passed"}
        mock_stripe.return_value = {"id": "pi_test123", "status": "succeeded"}
        mock_rye.return_value = {"order_id": "rye_fail_1", "status": "failed", "error": "out of stock"}

        resp = client.post("/api/webhook/purchase-request",
                           json=_purchase_request_payload())
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["decision"] == "DENY"
        assert data["reason"] == "checkout_failed"

        mock_stripe.assert_called_once()
        mock_rye.assert_called_once()

    # ---------------------------------------------------------------
    # 4. Frozen agent denied (constraint check fails)
    # ---------------------------------------------------------------
    @patch("api.src.routes.webhooks.rye_checkout")
    @patch("api.src.routes.webhooks.stripe_charge")
    @patch("api.src.routes.webhooks.enforce_constraints")
    @patch("api.src.routes.webhooks.compute_risk_rates", return_value=_NORMAL_RISK)
    @patch("api.src.routes.webhooks.supabase")
    def test_frozen_agent_denied(
        self, mock_wh_sb, mock_risk, mock_enforce,
        mock_stripe, mock_rye, client
    ):
        user = _make_user()
        agent = _make_agent(trust_score=20)  # frozen tier

        mock_wh_sb.table.side_effect = self._build_request_table_router(user, agent)

        mock_enforce.return_value = {"decision": "DENY", "reason": "agent_frozen"}

        resp = client.post("/api/webhook/purchase-request",
                           json=_purchase_request_payload())
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["decision"] == "DENY"
        assert data["reason"] == "agent_frozen"

        # Neither Stripe nor Rye should be called when constraints deny
        mock_stripe.assert_not_called()
        mock_rye.assert_not_called()
