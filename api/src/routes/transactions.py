"""Transaction routes: list transactions and mark/rate them."""
from flask import Blueprint, jsonify, request
from api.src.db import supabase
from api.src.services.trust_score import apply_score_delta

transactions_bp = Blueprint("transactions", __name__, url_prefix="/api")


@transactions_bp.route("/users/<user_id>/transactions", methods=["GET"])
def get_transactions(user_id):
    query = supabase.table("transactions").select("*").eq("user_id", user_id).order("created_at", desc=True)

    status_filter = request.args.get("status")
    if status_filter:
        query = query.eq("status", status_filter)

    result = query.execute()
    transactions = [
        {
            "id": tx["id"],
            "amount": tx["amount"],
            "merchant": tx.get("merchant"),
            "product_description": tx.get("product_description"),
            "category": tx.get("category"),
            "status": tx["status"],
            "evidence": tx.get("evidence"),
            "solana_tx_signature": tx.get("solana_tx_signature"),
            "session_id": tx.get("session_id"),
            "created_at": tx["created_at"],
            "evidence": tx.get("evidence"),
            "dispute_type": tx.get("dispute_type"),
            "dispute_at": tx.get("dispute_at"),
        }
        for tx in result.data
    ]
    return jsonify(transactions)


@transactions_bp.route("/transactions/<tx_id>/mark", methods=["PUT"])
def mark_transaction(tx_id):
    data = request.get_json()
    mark = data.get("mark")

    if mark not in ("good", "wrong_item"):
        return jsonify({"error": "mark must be 'good' or 'wrong_item'", "code": "invalid_mark"}), 400

    # Get transaction to find agent_id
    tx_result = supabase.table("transactions").select("agent_id").eq("id", tx_id).execute()
    if not tx_result.data:
        return jsonify({"error": "transaction not found", "code": "not_found"}), 404

    agent_id = tx_result.data[0]["agent_id"]
    delta = 5 if mark == "good" else -10

    score_result = apply_score_delta(agent_id, delta)

    return jsonify({
        "transaction_id": tx_id,
        "trust_score": score_result["new_score"],
        "old_tier": score_result["old_tier"],
        "new_tier": score_result["new_tier"],
    })
