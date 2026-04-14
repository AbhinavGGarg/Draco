"""Evidence bundle creation and update for OpenPay transactions."""

from datetime import datetime, timezone
from api.src.db import supabase


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_evidence_bundle(intent: dict, account_state: dict, policy_checks: list, user_message: str | None = None) -> dict:
    """Creates the evidence bundle JSONB for a transaction.
    Returns the bundle dict to store in transactions.evidence"""
    bundle = {
        "intent_snapshot": intent,
        "account_state_at_purchase": account_state,
        "policy_checks": policy_checks,
        "timestamps": {
            "constraints_checked_at": _now(),
        },
    }
    if user_message:
        bundle["authorization"] = {
            "original_message": user_message,
            "authorized_at": _now(),
        }
    return bundle


def stamp_evidence(transaction_id: str, event: str) -> None:
    """Add a timestamp to the evidence bundle for a specific event."""
    tx = supabase.table("transactions").select("evidence").eq("id", transaction_id).execute()
    if not tx.data:
        return
    bundle = tx.data[0]["evidence"] or {}
    timestamps = bundle.get("timestamps", {})
    timestamps[event] = _now()
    bundle["timestamps"] = timestamps
    supabase.table("transactions").update({"evidence": bundle}).eq("id", transaction_id).execute()


def update_evidence_execution(transaction_id: str, execution_result: dict) -> dict:
    """Updates the evidence bundle with post-purchase execution result.
    Compares intent_snapshot vs execution_result:
    - amount_match: abs(final_amount - intent_amount) / intent_amount <= 0.05
    - merchant_match: final_merchant == intent_merchant (case-insensitive)
    - flagged: True if either doesn't match
    Returns the updated bundle."""
    tx = supabase.table("transactions").select("evidence").eq("id", transaction_id).execute()
    bundle = tx.data[0]["evidence"] or {}

    intent = bundle.get("intent_snapshot", {})
    intent_amount = intent.get("amount", 0)
    final_amount = execution_result.get("final_amount", 0)

    amount_match = abs(final_amount - intent_amount) / max(intent_amount, 0.01) <= 0.05
    merchant_match = execution_result.get("final_merchant", "").lower() == intent.get("merchant", "").lower()

    execution_result["amount_match"] = amount_match
    execution_result["merchant_match"] = merchant_match
    execution_result["flagged"] = not (amount_match and merchant_match)

    bundle["execution_result"] = execution_result

    # Add execution timestamp
    timestamps = bundle.get("timestamps", {})
    timestamps["execution_completed_at"] = _now()
    bundle["timestamps"] = timestamps

    supabase.table("transactions").update({"evidence": bundle}).eq("id", transaction_id).execute()

    return bundle
