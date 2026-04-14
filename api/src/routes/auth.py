"""Auth routes: /api/auth/me and /api/auth/onboarding."""
from flask import Blueprint, jsonify, request, g

from api.src.db import supabase
from api.src.middleware.auth import require_auth
from api.src.services.trust_score import score_to_tier

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/auth/me", methods=["GET"])
@require_auth
def get_me():
    """Returns the current user's OpenPay profile, or 404 if onboarding not complete."""
    if not g.user_id:
        return jsonify({"error": "Profile not found", "code": "no_profile"}), 404

    user = supabase.table("users").select("*").eq("id", g.user_id).execute().data[0]
    agent_result = supabase.table("agents").select("*").eq("user_id", g.user_id).execute()

    result = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "balance": user["balance"],
        "stripe_customer_id": user.get("stripe_customer_id"),
        "created_at": user["created_at"],
    }

    if agent_result.data:
        a = agent_result.data[0]
        result["agent"] = {
            "id": a["id"],
            "trust_score": a["trust_score"],
            "tier": score_to_tier(a["trust_score"]),
            "constraints": a["constraints"],
        }

    return jsonify(result)


@auth_bp.route("/api/auth/onboarding", methods=["POST"])
@require_auth
def onboarding():
    """Creates OpenPay user + agent from onboarding questionnaire data."""
    if g.user_id:
        return jsonify({"error": "Already onboarded", "code": "already_exists"}), 409

    data = request.get_json()

    user_result = supabase.table("users").insert({
        "supabase_auth_id": g.supabase_user_id,
        "name": data["name"],
        "email": data.get("email"),
        "balance": data.get("balance", 0.0),
    }).execute()
    user = user_result.data[0]

    agent_result = supabase.table("agents").insert({
        "user_id": user["id"],
        "trust_score": 50,
        "constraints": {
            "max_per_transaction": data.get("max_per_transaction", 100),
            "max_per_week": data.get("max_per_week", 500),
            "allowed_categories": data.get("allowed_categories",
                ["electronics", "groceries", "books", "clothing", "home", "office"]),
            "blocked_merchants": data.get("blocked_merchants", []),
        },
    }).execute()

    return jsonify({
        "user_id": user["id"],
        "agent_id": agent_result.data[0]["id"],
    }), 201
