"""Risk metrics endpoint — GET /api/users/:id/risk."""

from flask import Blueprint, jsonify
from api.src.db import supabase
from api.src.services.risk_metrics import compute_risk_rates

risk_bp = Blueprint("risk", __name__, url_prefix="/api")


@risk_bp.route("/users/<user_id>/risk", methods=["GET"])
def get_risk_metrics(user_id):
    agent_result = supabase.table("agents").select("id").eq("user_id", user_id).execute()
    if not agent_result.data:
        return jsonify({"error": "agent not found", "code": "not_found"}), 404
    agent_id = agent_result.data[0]["id"]
    return jsonify(compute_risk_rates(agent_id))
