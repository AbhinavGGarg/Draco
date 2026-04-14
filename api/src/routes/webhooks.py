"""Purchase webhook routes: called by OpenClaw, not by frontend."""
import logging
import uuid
from flask import Blueprint, jsonify, request
from api.src.db import supabase
from api.src.services.constraints import enforce_constraints
from api.src.services.trust_score import apply_score_delta, score_to_tier
from api.src.services.evidence import create_evidence_bundle, update_evidence_execution, stamp_evidence
from api.src.services.risk_metrics import compute_risk_rates
from api.src.services.stripe_service import (
    charge as stripe_charge,
    create_customer,
    attach_payment_method,
)
from api.src.services.rye_service import checkout as rye_checkout

try:
    from api.src.services.solana_service import anchor_purchase
except ImportError:
    anchor_purchase = None
    logging.getLogger(__name__).warning(
        "solana_service not available — Solana anchoring disabled"
    )

try:
    from api.src.services.gemini_service import review_and_score
except ImportError:
    review_and_score = None
    logging.getLogger(__name__).warning(
        "gemini_service not available — Gemini post-execution review disabled"
    )

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/api")


def _ensure_stripe_setup(user_id, user):
    """Auto-provision Stripe customer + test card if not set up."""
    customer_id = user.get("stripe_customer_id")
    pm_id = user.get("stripe_payment_method_id")

    if customer_id and pm_id:
        return customer_id, pm_id

    email = user.get("email", f"{user_id}@openpay.dev")

    if not customer_id:
        cus = create_customer(email)
        customer_id = cus["id"]

    if not pm_id:
        pm = attach_payment_method(customer_id, "tok_visa")
        if pm.get("error"):
            return customer_id, None
        pm_id = pm["id"]

    supabase.table("users").update({
        "stripe_customer_id": customer_id,
        "stripe_payment_method_id": pm_id,
    }).eq("id", user_id).execute()

    return customer_id, pm_id


@webhooks_bp.route("/webhook/purchase-request", methods=["POST"])
def purchase_request():
    data = request.get_json()
    agent_id = data["agent_id"]
    user_id = data["user_id"]
    product_url = data.get("product_url", "")
    amount = data["amount"]
    merchant = data["merchant"]
    category = data["category"]
    product_description = data.get("product_description", "")
    user_message = data.get("user_message")
    session_id = data.get("session_id") or str(uuid.uuid4())

    # Look up user and agent for evidence bundle
    user_result = supabase.table("users").select("*").eq("id", user_id).execute()
    user = user_result.data[0]
    agent_result = supabase.table("agents").select("trust_score").eq("id", agent_id).execute()
    agent_score = agent_result.data[0]["trust_score"]
    agent_tier = score_to_tier(agent_score)
    risk = compute_risk_rates(agent_id)

    # Enforce constraints
    result = enforce_constraints(agent_id, amount, merchant, category)

    # Build evidence bundle with policy checks
    intent = {
        "product_url": product_url,
        "amount": amount,
        "merchant": merchant,
        "category": category,
        "product_description": product_description,
    }
    account_state = {
        "balance": user["balance"],
        "trust_score": agent_score,
        "tier": agent_tier,
        "risk_status": risk["status"],
    }
    policy_checks = result.get("checks", [
        {"check": "tier_not_frozen", "result": "pass" if agent_tier != "frozen" else "fail"},
        {"check": "risk_rate_check", "result": "pass" if risk["status"] == "normal" else "fail",
         "detail": f"status={risk['status']}"},
        {"check": "amount_under_limit", "result": "pass" if result["decision"] == "APPROVE" else "fail",
         "detail": f"{amount} vs limit"},
        {"check": "category_allowed", "result": "pass"},
        {"check": "balance_sufficient", "result": "pass" if amount <= user["balance"] else "fail"},
        {"check": "weekly_limit_ok", "result": "pass"},
    ])
    evidence = create_evidence_bundle(intent, account_state, policy_checks, user_message=user_message)

    if result["decision"] != "APPROVE":
        return jsonify(result)

    # Create pending transaction with evidence bundle
    tx_data = {
        "agent_id": agent_id,
        "user_id": user_id,
        "amount": amount,
        "merchant": merchant,
        "product_url": product_url,
        "product_description": product_description,
        "category": category,
        "status": "pending",
        "evidence": evidence,
        "session_id": session_id,
    }
    tx_result = supabase.table("transactions").insert(tx_data).execute()
    transaction = tx_result.data[0]
    tx_id = transaction["id"]
    customer_id, pm_id = _ensure_stripe_setup(user_id, user)

    if not pm_id:
        supabase.table("transactions").update({"status": "failed"}).eq("id", tx_id).execute()
        return jsonify({"decision": "DENY", "reason": "card_setup_failed"})

    stripe_result = stripe_charge(customer_id, pm_id, amount)
    stamp_evidence(tx_id, "stripe_charged_at")

    if stripe_result["status"] != "succeeded":
        supabase.table("transactions").update({"status": "failed"}).eq("id", tx_id).execute()
        return jsonify({"decision": "DENY", "reason": "card_declined"})

    # Rye checkout
    rye_result = rye_checkout(product_url, amount)
    stamp_evidence(tx_id, "rye_checkout_at")

    if rye_result["status"] != "completed" and not rye_result.get("mocked"):
        supabase.table("transactions").update({"status": "failed"}).eq("id", tx_id).execute()
        return jsonify({"decision": "DENY", "reason": "checkout_failed"})

    # Finalize: both Stripe and Rye succeeded — mark completed, decrement balance, +3 trust.
    # We finalize here (not in purchase-complete) because we poll Rye synchronously
    # and already know the outcome. purchase-complete is reserved for Stage 2b
    # post-purchase validation (evidence bundle comparison).
    supabase.table("transactions").update({
        "status": "completed",
        "stripe_payment_intent_id": stripe_result["id"],
        "rye_order_id": rye_result["order_id"],
    }).eq("id", tx_id).execute()

    # Decrement user balance
    current_balance = user["balance"]
    supabase.table("users").update({
        "balance": current_balance - amount,
    }).eq("id", user_id).execute()

    # Recompute AI trust score after successful purchase
    try:
        from api.src.services.trust_model import compute_trust_score
        compute_trust_score(agent_id)
    except Exception:
        # Fallback to simple delta if AI scoring fails
        apply_score_delta(agent_id, 3)

    # Post-purchase: update evidence with execution result
    execution_result = {
        "rye_order_id": rye_result["order_id"],
        "final_amount": amount,
        "final_merchant": merchant,
    }
    bundle = update_evidence_execution(tx_id, execution_result)

    # Anchor to Solana
    solana_sig = None
    if anchor_purchase and session_id:
        try:
            signature = anchor_purchase(session_id, tx_id, [], bundle)
            if signature:
                supabase.table("transactions").update(
                    {"solana_tx_signature": signature}
                ).eq("id", tx_id).execute()
                stamp_evidence(tx_id, "solana_anchored_at")
                solana_sig = signature
        except Exception:
            logging.getLogger(__name__).exception("Solana anchoring failed for tx %s", tx_id)

    return jsonify({
        "decision": "APPROVE",
        "reason": "all_checks_passed",
        "transaction_id": tx_id,
        "solana_tx_signature": solana_sig,
    })


@webhooks_bp.route("/webhook/purchase-complete", methods=["POST"])
def purchase_complete():
    """Stage 2b: Post-purchase validation endpoint.

    Finalization (status, balance, trust) now happens in purchase-request
    since we poll Rye synchronously. This endpoint is reserved for:
    - Step 4: Compare intent snapshot vs Rye's final checkout result
    - Flag mismatches (status → 'flagged', -6 trust)
    - Update evidence bundle with execution_result
    """
    data = request.get_json()
    tx_id = data["transaction_id"]
    final_amount = data.get("final_amount")
    final_merchant = data.get("final_merchant")
    rye_order_id = data.get("rye_order_id", "")

    tx_result = supabase.table("transactions").select("*").eq("id", tx_id).execute()
    if not tx_result.data:
        return jsonify({"error": "transaction not found", "code": "not_found"}), 404

    tx = tx_result.data[0]

    # Post-purchase validation: compare intent vs actual execution
    execution_result = {
        "rye_order_id": rye_order_id or tx.get("rye_order_id", ""),
        "final_amount": final_amount if final_amount is not None else tx["amount"],
        "final_merchant": final_merchant or tx["merchant"],
    }

    bundle = update_evidence_execution(tx_id, execution_result)

    # Anchor the purchase audit trail on Solana
    if anchor_purchase:
        session_id = tx.get("session_id", "")
        if session_id:
            steps_result = (
                supabase.table("agent_steps")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at")
                .execute()
            )
            steps = steps_result.data if steps_result.data else []
            signature = anchor_purchase(session_id, tx_id, steps, bundle)
            if signature:
                supabase.table("transactions").update(
                    {"solana_tx_signature": signature}
                ).eq("id", tx_id).execute()

    # Tier 1: deterministic mismatch check
    flagged = bundle.get("execution_result", {}).get("flagged", False)

    if flagged:
        supabase.table("transactions").update({"status": "flagged"}).eq("id", tx_id).execute()
        apply_score_delta(tx["agent_id"], -6)
        return jsonify({"success": True, "flagged": True, "gemini_review": None})

    # Tier 2: Gemini review — only runs when deterministic check passes
    gemini_result = None
    if review_and_score:
        try:
            gemini_result = review_and_score(tx_id)
        except Exception:
            logging.getLogger(__name__).exception(
                "Gemini review failed for tx %s", tx_id
            )

    gemini_flagged = (
        gemini_result is not None
        and gemini_result.get("verdict") == "MISMATCH"
        and gemini_result.get("confidence", 0) >= 0.8
    )
    if gemini_flagged:
        supabase.table("transactions").update({"status": "flagged"}).eq("id", tx_id).execute()
        apply_score_delta(tx["agent_id"], -3)

    return jsonify({
        "success": True,
        "flagged": gemini_flagged,
        "gemini_review": gemini_result,
    })


