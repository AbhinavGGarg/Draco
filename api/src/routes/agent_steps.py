"""Agent step audit log endpoints."""
from flask import Blueprint, jsonify, request
from datetime import datetime, timezone
from api.src.db import supabase

agent_steps_bp = Blueprint("agent_steps", __name__, url_prefix="/api")


@agent_steps_bp.route("/webhook/agent-step", methods=["POST"])
def create_agent_step():
    data = request.get_json()
    session_id = data.get("session_id")
    step_type = data.get("step_type")

    if not session_id or not step_type:
        return jsonify({"error": "session_id and step_type are required", "code": "missing_fields"}), 400

    timestamp = data.get("timestamp") or datetime.now(timezone.utc).isoformat()

    row = {
        "session_id": session_id,
        "step_type": step_type,
        "data": data.get("data"),
    }

    result = supabase.table("agent_steps").insert(row).execute()
    step = result.data[0]

    return jsonify({"success": True, "step_id": step["id"]}), 201


@agent_steps_bp.route("/sessions/<session_id>/steps", methods=["GET"])
def get_session_steps(session_id):
    result = (
        supabase.table("agent_steps")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at")
        .execute()
    )

    return jsonify(result.data)


@agent_steps_bp.route("/api/agents/<agent_id>/live-steps", methods=["GET"])
def get_live_steps(agent_id):
    """Return recent agent steps for a given agent, newest first.

    Joins through the transactions table since agent_steps only has session_id.
    """
    limit = request.args.get("limit", 20, type=int)

    # Get session_ids from transactions for this agent
    tx_result = (
        supabase.table("transactions")
        .select("session_id")
        .eq("agent_id", agent_id)
        .not_.is_("session_id", "null")
        .execute()
    )
    session_ids = list(set(
        tx["session_id"] for tx in tx_result.data if tx.get("session_id")
    ))

    if not session_ids:
        return jsonify([])

    result = (
        supabase.table("agent_steps")
        .select("*")
        .in_("session_id", session_ids)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return jsonify(result.data)
