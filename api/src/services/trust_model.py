"""AI-powered trust scoring model using Gemini via Kie API.

Pulls agent history from Supabase, sends to Gemini for analysis,
returns a trust score (0-100) with reasoning and factor breakdown.
Result is cached in the agents table.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone

import requests

from api.src.db import supabase
from api.src.services.trust_score import score_to_tier

logger = logging.getLogger(__name__)

KIE_API_URL = "https://api.kie.ai/gemini/v1/models/gemini-3-flash-v1betamodels:streamGenerateContent"


def _gather_agent_data(agent_id: str) -> dict:
    """Pull all relevant data from Supabase for scoring."""
    agent = supabase.table("agents").select("*").eq("id", agent_id).execute().data[0]
    user = supabase.table("users").select("*").eq("id", agent["user_id"]).execute().data[0]

    # All transactions
    txs = supabase.table("transactions").select("*").eq("agent_id", agent_id).order("created_at").execute().data

    # 30-day window
    cutoff_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    recent_txs = [t for t in txs if t["created_at"] >= cutoff_30d]

    # Compute stats
    completed = [t for t in txs if t["status"] == "completed"]
    recent_completed = [t for t in recent_txs if t["status"] == "completed"]
    disputed = [t for t in txs if t["status"] == "disputed"]
    flagged = [t for t in txs if t["status"] == "flagged"]
    failed = [t for t in txs if t["status"] == "failed"]

    categories_used = list(set(t["category"] for t in completed if t.get("category")))
    merchants_used = list(set(t["merchant"] for t in completed if t.get("merchant")))

    total_spent = sum(t["amount"] for t in completed)
    avg_transaction = total_spent / len(completed) if completed else 0

    # Account age in days
    created_at = agent.get("created_at", datetime.now(timezone.utc).isoformat())
    try:
        age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(created_at.replace("Z", "+00:00"))).days
    except Exception:
        age_days = 0

    # Compute live risk rates
    from api.src.services.risk_metrics import compute_risk_rates
    risk = compute_risk_rates(agent_id)

    return {
        "agent_id": agent_id,
        "current_trust_score": agent["trust_score"],
        "current_tier": score_to_tier(agent["trust_score"]),
        "dispute_rate_30d": round(risk["dispute_rate"] * 100, 2),
        "flagged_rate_30d": round(risk["flagged_rate"] * 100, 2),
        "constraints": agent["constraints"],
        "account_age_days": age_days,
        "balance": user["balance"],
        "total_transactions": len(txs),
        "completed_count": len(completed),
        "recent_completed_30d": len(recent_completed),
        "disputed_count": len(disputed),
        "dispute_types": [t.get("dispute_type") for t in disputed if t.get("dispute_type")],
        "flagged_count": len(flagged),
        "failed_count": len(failed),
        "total_spent": round(total_spent, 2),
        "avg_transaction_amount": round(avg_transaction, 2),
        "categories_used": categories_used,
        "merchants_used": merchants_used[:20],  # cap for prompt size
        "max_per_transaction": agent["constraints"].get("max_per_transaction", 100),
        "max_per_week": agent["constraints"].get("max_per_week", 500),
        "blocked_merchants": agent["constraints"].get("blocked_merchants", []),
    }


def compute_trust_score(agent_id: str) -> dict | None:
    """Compute AI-powered trust score using Gemini.

    Returns: {score, tier, reasoning, factors} or None on failure.
    Also caches the result in the agents table.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — AI trust scoring unavailable")
        return None

    data = _gather_agent_data(agent_id)

    # --- Deterministic base score (Altman Z-Score inspired) ---
    # T = 30·R + 20·S + 25·D + 10·C + 15·M
    total = max(data["total_transactions"], 1)
    R = data["completed_count"] / total  # purchase reliability
    weekly_limit = max(data["max_per_week"], 1)
    S = max(0, 1 - (data["total_spent"] / (weekly_limit * 13)))  # spending behavior (13 weeks ~= 90 days)
    dispute_rate = (data["disputed_count"] + data["flagged_count"]) / total
    D = max(0, 1 - dispute_rate * 10)  # dispute history
    total_cats = 16  # total available categories
    C = len(data["categories_used"]) / total_cats  # category diversity
    M = min(data["account_age_days"] / 90, 1)  # account maturity

    base_score = round(30 * R + 20 * S + 25 * D + 10 * C + 15 * M)
    base_score = max(0, min(100, base_score))

    prompt = f"""You are the trust scoring model for OpenPay, an AI agent commerce platform.
Your job is to evaluate an agent's trustworthiness using a weighted factor model, enhanced by your qualitative judgment.

MATHEMATICAL MODEL (Altman Z-Score inspired):
T = 30·R + 20·S + 25·D + 10·C + 15·M

Where:
  R = Purchase Reliability = completed / total = {R:.3f}
  S = Spending Behavior = 1 - (total_spent / weekly_limit × 13) = {S:.3f}
  D = Dispute History = 1 - (dispute_rate × 10) = {D:.3f}
  C = Category Diversity = unique_categories / 16 = {C:.3f}
  M = Account Maturity = min(account_age / 90, 1) = {M:.3f}

Weights: Reliability=30, Spending=20, Disputes=25, Diversity=10, Maturity=15 (sum=100)

BASE SCORE FROM EQUATION: {base_score}

RAW DATA:
- Account age: {data['account_age_days']} days
- Balance remaining: ${data['balance']}
- Total transactions: {data['total_transactions']}
- Completed: {data['completed_count']}, Failed: {data['failed_count']}
- Disputed: {data['disputed_count']} ({', '.join(data['dispute_types']) if data['dispute_types'] else 'none'})
- Flagged: {data['flagged_count']}
- Recent purchases (30d): {data['recent_completed_30d']}
- Total spent: ${data['total_spent']}, Avg transaction: ${data['avg_transaction_amount']}
- Categories: {', '.join(data['categories_used'])}
- Merchants: {len(data['merchants_used'])} unique
- Dispute rate (30d): {data['dispute_rate_30d']}%, Flagged rate: {data['flagged_rate_30d']}%

INSTRUCTIONS:
1. Start with the base score of {base_score} computed by the equation above.
2. You may adjust the final score by up to ±5 points based on qualitative patterns the equation cannot capture (e.g., improving trend, suspicious merchant concentration, recent spike in disputes).
3. Report each factor as a 0-1 value matching the computed R, S, D, C, M values. You may adjust each by ±0.05 if your qualitative analysis warrants it.
4. Provide a 2-3 sentence reasoning explaining the score and any adjustment you made from the base.

TIER ZONES:
0-25: Frozen | 26-50: Restricted | 51-75: Standard | 76-100: Trusted

Respond with ONLY valid JSON, no markdown:
{{
  "score": <integer 0-100>,
  "base_score": {base_score},
  "reasoning": "<2-3 sentences>",
  "factors": {{
    "purchase_reliability": <float 0-1>,
    "spending_behavior": <float 0-1>,
    "dispute_history": <float 0-1>,
    "category_diversity": <float 0-1>,
    "account_maturity": <float 0-1>
  }}
}}"""

    try:
        resp = requests.post(
            KIE_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "stream": False,
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            },
            timeout=30,
        )

        if resp.status_code != 200:
            logger.error("Gemini API error %s: %s", resp.status_code, resp.text[:200])
            return None

        # Parse response — handle both streaming and non-streaming formats
        body = resp.json()

        # Extract text from Gemini response
        text = ""
        if isinstance(body, list):
            # Streaming concatenated responses
            for chunk in body:
                candidates = chunk.get("candidates", [])
                for c in candidates:
                    parts = c.get("content", {}).get("parts", [])
                    for p in parts:
                        if "text" in p:
                            text += p["text"]
        elif isinstance(body, dict):
            candidates = body.get("candidates", [])
            for c in candidates:
                parts = c.get("content", {}).get("parts", [])
                for p in parts:
                    if "text" in p:
                        text += p["text"]

        # Clean and parse JSON
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        result = json.loads(text)
        score = max(0, min(100, int(result["score"])))
        tier = score_to_tier(score)

        trust_data = {
            "score": score,
            "base_score": result.get("base_score", base_score),
            "tier": tier,
            "reasoning": result.get("reasoning", ""),
            "factors": result.get("factors", {}),
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Cache in agents table
        supabase.table("agents").update({
            "trust_score": score,
            "trust_analysis": trust_data,
        }).eq("id", agent_id).execute()

        # Write to trust history
        supabase.table("trust_history").insert({
            "agent_id": agent_id,
            "score": score,
            "tier": tier,
            "factors": result.get("factors", {}),
        }).execute()

        return trust_data

    except json.JSONDecodeError as e:
        logger.exception("Failed to parse Gemini response: %s", str(e))
        return None
    except Exception:
        logger.exception("Trust model computation failed")
        return None
