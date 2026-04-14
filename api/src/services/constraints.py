"""Constraint enforcement: full pre-purchase validation pipeline."""
from datetime import datetime, timedelta

from api.src.db import supabase
from api.src.services.trust_score import apply_score_delta, score_to_tier

# Tier-based transaction limits
TIER_LIMITS = {
    "frozen": 0,
    "restricted": 25,
    "standard": 100,
    "trusted": None,  # uses user's constraint
}


def enforce_constraints(agent_id: str, amount: float, merchant: str, category: str) -> dict:
    """Full enforcement check: tier, risk rates, amount, category, balance, weekly spend.
    Returns: {decision: 'APPROVE'|'DENY'|'PAUSE_FOR_REVIEW', reason: str}
    """
    # 1. Look up agent
    agent_result = supabase.table("agents").select("*").eq("id", agent_id).execute()
    agent = agent_result.data[0]
    trust_score = agent["trust_score"]
    tier = score_to_tier(trust_score)
    constraints = agent["constraints"]
    user_id = agent["user_id"]

    # 2. Frozen check
    if tier == "frozen":
        return {"decision": "DENY", "reason": "agent_frozen"}

    # 3. Effective max_per_transaction: min(user constraint, tier limit)
    user_limit = constraints.get("max_per_transaction", 100)
    tier_limit = TIER_LIMITS[tier]
    if tier_limit is None:
        effective_limit = user_limit
    else:
        effective_limit = min(user_limit, tier_limit)

    if amount > effective_limit:
        apply_score_delta(agent_id, -5)
        return {"decision": "DENY", "reason": "exceeds_transaction_limit"}

    # 5. Category and merchant check
    allowed_categories = constraints.get("allowed_categories", [])
    blocked_merchants = constraints.get("blocked_merchants", [])

    if category not in allowed_categories or merchant in blocked_merchants:
        apply_score_delta(agent_id, -8)
        return {"decision": "DENY", "reason": "blocked_category_or_merchant"}

    # 6. Balance check
    user_result = supabase.table("users").select("balance").eq("id", user_id).execute()
    user = user_result.data[0]
    if amount > user["balance"]:
        return {"decision": "DENY", "reason": "insufficient_balance"}

    # 7. Weekly spending check
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    tx_result = supabase.table("transactions").select("amount").eq("agent_id", agent_id).gte("created_at", week_ago).execute()
    weekly_spent = sum(tx["amount"] for tx in tx_result.data)
    max_per_week = constraints.get("max_per_week", 500)

    if weekly_spent + amount > max_per_week:
        return {"decision": "DENY", "reason": "exceeds_weekly_limit"}

    # 8. All checks passed
    return {"decision": "APPROVE", "reason": "all_checks_passed"}
