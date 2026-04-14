import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

# Load .env from project root before any project imports that read env vars
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from api.src.db import supabase  # noqa: E402
from api.src.services import stripe_service  # noqa: E402
from api.src.routes.agents import agents_bp  # noqa: E402
from api.src.routes.transactions import transactions_bp  # noqa: E402
from api.src.routes.webhooks import webhooks_bp  # noqa: E402
from api.src.routes.risk import risk_bp  # noqa: E402
from api.src.routes.disputes import disputes_bp  # noqa: E402
from api.src.routes.agent_steps import agent_steps_bp  # noqa: E402
from api.src.routes.solana import solana_bp  # noqa: E402
from api.src.routes.auth import auth_bp  # noqa: E402

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev")
_cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
CORS(app, origins=_cors_origins)

app.register_blueprint(agents_bp)
app.register_blueprint(transactions_bp)
app.register_blueprint(webhooks_bp)
app.register_blueprint(risk_bp)
app.register_blueprint(disputes_bp)
app.register_blueprint(agent_steps_bp)
app.register_blueprint(solana_bp)
app.register_blueprint(auth_bp)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")

    if not name:
        return jsonify({"error": "name is required", "code": "missing_name"}), 400

    user_data = {"name": name, "email": email, "balance": 0.0}
    result = supabase.table("users").insert(user_data).execute()
    user = result.data[0]

    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "balance": user["balance"],
    }), 201


@app.route("/api/users/<user_id>", methods=["GET"])
def get_user(user_id):
    result = supabase.table("users").select("*").eq("id", user_id).execute()

    if not result.data:
        return jsonify({"error": "user not found", "code": "not_found"}), 404

    user = result.data[0]
    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "stripe_customer_id": user.get("stripe_customer_id"),
        "balance": user["balance"],
        "created_at": user["created_at"],
    })


@app.route("/api/users/<user_id>/balance", methods=["POST"])
def set_balance(user_id):
    data = request.get_json()
    amount = data.get("amount")
    if amount is None or float(amount) < 0:
        return jsonify({"error": "valid amount required", "code": "invalid_amount"}), 400

    result = supabase.table("users").update({"balance": float(amount)}).eq("id", user_id).execute()
    if not result.data:
        return jsonify({"error": "user not found", "code": "not_found"}), 404

    return jsonify({"balance": result.data[0]["balance"]})


@app.route("/api/users/<user_id>/card", methods=["POST"])
def setup_card(user_id):
    data = request.get_json()
    stripe_token = data.get("stripe_token")
    if not stripe_token:
        return jsonify({"error": "stripe_token required", "code": "missing_token"}), 400

    user_result = supabase.table("users").select("*").eq("id", user_id).execute()
    if not user_result.data:
        return jsonify({"error": "user not found", "code": "not_found"}), 404

    user = user_result.data[0]

    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        customer = stripe_service.create_customer(user.get("email", ""))
        customer_id = customer["id"]

    pm = stripe_service.attach_payment_method(customer_id, stripe_token)
    if pm.get("error"):
        return jsonify({"error": pm["error"], "code": "stripe_error"}), 400

    supabase.table("users").update({
        "stripe_customer_id": customer_id,
        "stripe_payment_method_id": pm["id"],
    }).eq("id", user_id).execute()

    return jsonify({"stripe_customer_id": customer_id, "stripe_payment_method_id": pm["id"]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "True")
