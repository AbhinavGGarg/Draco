"""Trust score engine: tier derivation and score delta application."""
from api.src.db import supabase


def score_to_tier(score: int) -> str:
    """Derive tier from trust score.
    0-25: frozen, 26-50: restricted, 51-75: standard, 76-100: trusted
    """
    if score <= 25:
        return "frozen"
    elif score <= 50:
        return "restricted"
    elif score <= 75:
        return "standard"
    return "trusted"


def apply_score_delta(agent_id: str, delta: int) -> dict:
    """Read current score, apply delta, clamp 0-100, write back.
    Returns: {agent_id, old_score, new_score, old_tier, new_tier}
    """
    result = supabase.table("agents").select("trust_score").eq("id", agent_id).execute()
    agent = result.data[0]
    old_score = agent["trust_score"]
    new_score = max(0, min(100, old_score + delta))
    old_tier = score_to_tier(old_score)
    new_tier = score_to_tier(new_score)

    supabase.table("agents").update({"trust_score": new_score}).eq("id", agent_id).execute()

    return {
        "agent_id": agent_id,
        "old_score": old_score,
        "new_score": new_score,
        "old_tier": old_tier,
        "new_tier": new_tier,
    }
