"""Dispute filing endpoint: unauthorized/wrong_item/fulfillment_issue."""
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta, timezone
from api.src.db import supabase
from api.src.services.trust_score import apply_score_delta

disputes_bp = Blueprint("disputes", __name__, url_prefix="/api")

DISPUTE_DELTAS = {
    "unauthorized": -12,
    "wrong_item": -10,
    "fulfillment_issue": -5,
}


@disputes_bp.route("/transactions/<tx_id>/dispute", methods=["PUT"])
def dispute_transaction(tx_id):
    data = request.get_json()
    dispute_type = data.get("type")

    if dispute_type not in DISPUTE_DELTAS:
        return jsonify({"error": "invalid dispute type", "code": "invalid_type"}), 400

    # Get transaction
    tx_result = supabase.table("transactions").select("*").eq("id", tx_id).execute()
    if not tx_result.data:
        return jsonify({"error": "transaction not found", "code": "not_found"}), 404
    tx = tx_result.data[0]

    # Record dispute on transaction
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("transactions").update({
        "status": "disputed",
        "dispute_type": dispute_type,
        "dispute_at": now,
    }).eq("id", tx_id).execute()

    # Check eligibility
    eligible = _check_eligibility(tx, dispute_type)

    # Recompute AI trust score after dispute
    try:
        from api.src.services.trust_model import compute_trust_score
        trust_result = compute_trust_score(tx["agent_id"])
        from api.src.services.trust_score import score_to_tier
        score_result = {
            "new_score": trust_result["score"] if trust_result else 50,
            "old_tier": score_to_tier(tx.get("trust_score", 50) if isinstance(tx.get("trust_score"), int) else 50),
            "new_tier": trust_result["tier"] if trust_result else "restricted",
        }
    except Exception:
        delta = DISPUTE_DELTAS[dispute_type]
        score_result = apply_score_delta(tx["agent_id"], delta)

    # Credit balance if eligible
    balance_credited = None
    if eligible:
        user_result = supabase.table("users").select("balance").eq("id", tx["user_id"]).execute()
        current_balance = user_result.data[0]["balance"]
        new_balance = current_balance + tx["amount"]
        supabase.table("users").update({"balance": new_balance}).eq("id", tx["user_id"]).execute()
        balance_credited = tx["amount"]

    return jsonify({
        "transaction_id": tx_id,
        "dispute_type": dispute_type,
        "eligible": eligible,
        "trust_score": score_result["new_score"],
        "old_tier": score_result["old_tier"],
        "new_tier": score_result["new_tier"],
        "balance_credited": balance_credited,
    })


def _check_eligibility(tx, dispute_type):
    """Check dispute eligibility: within 7 days and evidence bundle present."""
    try:
        raw = tx["created_at"].replace("Z", "+00:00")
        # Handle truncated fractional seconds from Supabase
        if "." in raw and "+" in raw:
            frac, tz = raw.rsplit("+", 1)
            base, frac_part = frac.split(".")
            frac_part = frac_part[:6].ljust(6, "0")
            raw = f"{base}.{frac_part}+{tz}"
        elif "." in raw:
            base, frac_part = raw.split(".")
            frac_part = frac_part[:6].ljust(6, "0")
            raw = f"{base}.{frac_part}"
        created = datetime.fromisoformat(raw)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created > timedelta(days=7):
            return False
    except (ValueError, AttributeError):
        return True
    if tx.get("evidence") is None:
        return False
    return True
