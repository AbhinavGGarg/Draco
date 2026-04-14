"""Gemini post-execution review: second AI auditing the first AI's work."""
import json
import logging
import os

logger = logging.getLogger(__name__)


def review_purchase(
    intent_snapshot: dict,
    agent_steps: list[dict],
    execution_result: dict,
) -> dict:
    """Ask Gemini to evaluate whether Claude's purchase matched user intent.

    Returns {"verdict": "MATCH"|"MISMATCH", "reasoning": str,
             "confidence": float, "flagged_issues": list[str]}
    """
    try:
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"verdict": "ERROR", "reasoning": "GEMINI_API_KEY not set"}

        client = genai.Client(api_key=api_key)

        steps_text = "\n".join(
            f"  Step {i+1}: [{s.get('step_type', 'unknown')}] {json.dumps(s.get('data', {}), default=str)}"
            for i, s in enumerate(agent_steps)
        )
        if not steps_text:
            steps_text = "  (no agent steps recorded)"

        prompt = f"""You are an independent auditor reviewing an AI shopping agent's purchase decision.

## What the user asked for (intent)
- Product: {intent_snapshot.get('product_description', 'N/A')}
- Target amount: ${intent_snapshot.get('amount', 'N/A')}
- Category: {intent_snapshot.get('category', 'N/A')}
- Merchant: {intent_snapshot.get('merchant', 'N/A')}

## What the agent did step by step
{steps_text}

## What actually happened (execution result)
- Final amount charged: ${execution_result.get('final_amount', 'N/A')}
- Final merchant: {execution_result.get('final_merchant', 'N/A')}
- Amount matched intent: {execution_result.get('amount_match', 'N/A')}
- Merchant matched intent: {execution_result.get('merchant_match', 'N/A')}

## Your evaluation
Answer these questions:
1. Did the agent buy what the user asked for?
2. Was the price reasonable given the user's intent?
3. Did the agent's reasoning make sense given the steps?

Respond ONLY with valid JSON (no markdown, no backticks):
{{
  "verdict": "MATCH" or "MISMATCH",
  "reasoning": "one paragraph explaining your verdict",
  "confidence": 0.0 to 1.0,
  "flagged_issues": ["list of specific concerns, or empty array if none"]
}}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        raw = response.text.strip()
        # Strip markdown code fences if Gemini wraps the response
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3].strip()

        result = json.loads(raw)

        # Validate expected fields
        if result.get("verdict") not in ("MATCH", "MISMATCH"):
            result["verdict"] = "MISMATCH"
        result.setdefault("reasoning", "")
        result.setdefault("confidence", 0.5)
        result.setdefault("flagged_issues", [])

        return result

    except Exception as e:
        logger.exception("Gemini review failed")
        return {"verdict": "ERROR", "reasoning": str(e)}


def review_and_score(transaction_id: str) -> dict:
    """Pull transaction + agent steps from Supabase, run Gemini review, store result."""
    try:
        from api.src.db import supabase

        # Pull transaction with evidence bundle
        tx_result = (
            supabase.table("transactions")
            .select("*")
            .eq("id", transaction_id)
            .execute()
        )
        if not tx_result.data:
            return {"verdict": "ERROR", "reasoning": "transaction not found"}

        tx = tx_result.data[0]
        evidence = tx.get("evidence") or {}
        intent_snapshot = evidence.get("intent_snapshot", {})
        execution_result = evidence.get("execution_result", {})

        # Pull agent steps for this session
        session_id = tx.get("session_id", "")
        agent_steps = []
        if session_id:
            steps_result = (
                supabase.table("agent_steps")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at")
                .execute()
            )
            agent_steps = steps_result.data if steps_result.data else []

        # Run Gemini review
        verdict = review_purchase(intent_snapshot, agent_steps, execution_result)

        # Store verdict in evidence bundle
        evidence["gemini_review"] = verdict
        supabase.table("transactions").update(
            {"evidence": evidence}
        ).eq("id", transaction_id).execute()

        logger.info(
            "Gemini review for tx %s: %s (confidence %.2f)",
            transaction_id,
            verdict.get("verdict"),
            verdict.get("confidence", 0),
        )

        return verdict

    except Exception as e:
        logger.exception("review_and_score failed for tx %s", transaction_id)
        return {"verdict": "ERROR", "reasoning": str(e)}
