"""Risk rate calculation — 30-day rolling window with escalation bands."""

from datetime import datetime, timedelta, timezone
from api.src.db import supabase


def compute_risk_rates(agent_id: str) -> dict:
    """Computes 30-day rolling risk rates.
    Returns: {
        'dispute_rate': float,
        'flagged_rate': float,
        'unauthorized_rate': float,
        'wrong_item_rate': float,
        'status': str,  # 'normal' | 'elevated' | 'restricted' | 'frozen'
        'total_completed_30d': int,
        'total_disputes_30d': int,
        'total_flagged_30d': int
    }"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    result = supabase.table("transactions") \
        .select("status, dispute_type") \
        .eq("agent_id", agent_id) \
        .gte("created_at", cutoff) \
        .execute()

    txns = result.data
    completed = [t for t in txns if t["status"] in ("completed", "disputed", "flagged")]
    total = len(completed)

    if total == 0:
        return {
            "dispute_rate": 0.0, "flagged_rate": 0.0,
            "unauthorized_rate": 0.0, "wrong_item_rate": 0.0,
            "status": "normal",
            "total_completed_30d": 0, "total_disputes_30d": 0, "total_flagged_30d": 0,
        }

    disputes = [t for t in completed if t["status"] == "disputed"]
    flagged = [t for t in completed if t["status"] == "flagged"]
    unauthorized = [t for t in disputes if t.get("dispute_type") == "unauthorized"]
    wrong_item = [t for t in disputes if t.get("dispute_type") == "wrong_item"]

    rates = {
        "dispute_rate": len(disputes) / total,
        "flagged_rate": len(flagged) / total,
        "unauthorized_rate": len(unauthorized) / total,
        "wrong_item_rate": len(wrong_item) / total,
    }

    worst_rate = max(rates.values())
    if worst_rate > 0.15:
        status = "frozen"
    elif worst_rate > 0.10:
        status = "restricted"
    elif worst_rate > 0.05:
        status = "elevated"
    else:
        status = "normal"

    return {
        **rates,
        "status": status,
        "total_completed_30d": total,
        "total_disputes_30d": len(disputes),
        "total_flagged_30d": len(flagged),
    }
