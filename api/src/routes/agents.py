"""Agent routes: CRUD for agent data, constraints, and trust score reset."""
from flask import Blueprint, jsonify, request
from api.src.db import supabase
from api.src.services.trust_score import score_to_tier

agents_bp = Blueprint("agents", __name__, url_prefix="/api")


@agents_bp.route("/users/<user_id>/agent", methods=["GET"])
def get_agent(user_id):
    result = supabase.table("agents").select("*").eq("user_id", user_id).execute()
    if not result.data:
        return jsonify({"error": "agent not found", "code": "not_found"}), 404

    agent = result.data[0]
    return jsonify({
        "id": agent["id"],
        "trust_score": agent["trust_score"],
        "tier": score_to_tier(agent["trust_score"]),
        "constraints": agent["constraints"],
        "openclaw_agent_id": agent.get("openclaw_agent_id"),
    })


@agents_bp.route("/users/<user_id>/agent/constraints", methods=["PUT"])
def update_constraints(user_id):
    data = request.get_json()
    result = supabase.table("agents").select("*").eq("user_id", user_id).execute()
    if not result.data:
        return jsonify({"error": "agent not found", "code": "not_found"}), 404

    agent = result.data[0]
    current = agent["constraints"]

    # Partial merge: only update provided keys
    for key in ["max_per_transaction", "max_per_week", "allowed_categories", "blocked_merchants"]:
        if key in data:
            current[key] = data[key]

    supabase.table("agents").update({"constraints": current}).eq("id", agent["id"]).execute()
    return jsonify({"constraints": current})


@agents_bp.route("/users/<user_id>/agent/effective-limits", methods=["GET"])
def effective_limits(user_id):
    TIER_LIMITS = {"frozen": 0, "restricted": 25, "standard": 100, "trusted": None}

    result = supabase.table("agents").select("*").eq("user_id", user_id).execute()
    if not result.data:
        return jsonify({"error": "agent not found", "code": "not_found"}), 404

    agent = result.data[0]
    tier = score_to_tier(agent["trust_score"])
    constraints = agent["constraints"]

    user_limit = constraints.get("max_per_transaction", 100)
    tier_limit = TIER_LIMITS[tier]
    effective_tx = user_limit if tier_limit is None else min(user_limit, tier_limit)

    overrides = []
    if tier_limit is not None and tier_limit < user_limit:
        overrides.append(f"{tier.capitalize()} tier caps your ${user_limit} limit to ${tier_limit}")

    return jsonify({
        "effective_max_per_transaction": effective_tx,
        "effective_max_per_week": constraints.get("max_per_week", 500),
        "tier": tier,
        "overrides": overrides,
    })


@agents_bp.route("/users/<user_id>/agent/trust-analysis", methods=["POST"])
def trust_analysis(user_id):
    from api.src.services.trust_model import compute_trust_score
    result = supabase.table("agents").select("id").eq("user_id", user_id).execute()
    if not result.data:
        return jsonify({"error": "agent not found", "code": "not_found"}), 404
    agent_id = result.data[0]["id"]
    analysis = compute_trust_score(agent_id)
    if not analysis:
        return jsonify({"error": "trust model unavailable", "code": "model_error"}), 503
    return jsonify(analysis)


@agents_bp.route("/users/<user_id>/agent/trust-history", methods=["GET"])
def trust_history(user_id):
    result = supabase.table("agents").select("id").eq("user_id", user_id).execute()
    if not result.data:
        return jsonify({"error": "agent not found", "code": "not_found"}), 404
    agent_id = result.data[0]["id"]
    history = supabase.table("trust_history").select("score,tier,factors,computed_at").eq("agent_id", agent_id).order("computed_at").execute()
    return jsonify(history.data)


@agents_bp.route("/users/<user_id>/agent/trust-analysis", methods=["GET"])
def get_trust_analysis(user_id):
    result = supabase.table("agents").select("trust_analysis").eq("user_id", user_id).execute()
    if not result.data:
        return jsonify({"error": "agent not found", "code": "not_found"}), 404
    analysis = result.data[0].get("trust_analysis")
    if not analysis:
        return jsonify({"error": "no analysis yet", "code": "not_found"}), 404
    return jsonify(analysis)


@agents_bp.route("/users/<user_id>/agent/reset-score", methods=["POST"])
def reset_score(user_id):
    result = supabase.table("agents").select("id").eq("user_id", user_id).execute()
    if not result.data:
        return jsonify({"error": "agent not found", "code": "not_found"}), 404

    agent_id = result.data[0]["id"]
    supabase.table("agents").update({"trust_score": 50}).eq("id", agent_id).execute()
    return jsonify({"trust_score": 50, "tier": "restricted"})
