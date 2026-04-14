"""Rye service — staging API integration.

Uses Rye's single-step purchase endpoint with Bearer auth for POST,
Bearer auth for polling (Basic requires base64 encoding of key:).
"""
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

RYE_BASE_URL = "https://staging.api.rye.com"
RYE_API_KEY = os.getenv("RYE_API_KEY", "")

# Default buyer for agent purchases (configurable per-user in production)
DEFAULT_BUYER = {
    "firstName": "OpenPay",
    "lastName": "Agent",
    "email": "agent@openpay.dev",
    "phone": "212-555-0100",
    "address1": "123 Main St",
    "city": "New York",
    "province": "NY",
    "postalCode": "10001",
    "country": "US",
}

_AUTH_HEADER = {"Authorization": f"Bearer {RYE_API_KEY}"} if RYE_API_KEY else {}


def checkout(product_url: str, amount: float) -> dict:
    """Purchase a product via Rye single-step checkout.

    POST with Bearer auth, poll with Bearer auth until terminal state.
    Returns {'order_id': '...', 'status': 'completed', ...}
    or {'order_id': '...', 'status': 'failed', 'error': '...'}.
    """
    if not RYE_API_KEY:
        raise RuntimeError("RYE_API_KEY not set")

    # Step 1: Single-step purchase (Bearer auth)
    resp = requests.post(
        f"{RYE_BASE_URL}/api/v1/checkout-intents/purchase",
        headers={**_AUTH_HEADER, "Content-Type": "application/json"},
        json={
            "buyer": DEFAULT_BUYER,
            "productUrl": product_url,
            "quantity": 1,
            "paymentMethod": {
                "stripeToken": "tok_visa",
                "type": "stripe_token",
            },
        },
        timeout=15,
    )
    resp.raise_for_status()
    intent = resp.json()
    intent_id = intent.get("id", "")

    # Step 2: Poll for terminal state (Bearer auth)
    for _ in range(12):
        time.sleep(5)
        poll_resp = requests.get(
            f"{RYE_BASE_URL}/api/v1/checkout-intents/{intent_id}",
            headers=_AUTH_HEADER,
            timeout=10,
        )
        if poll_resp.status_code != 200:
            continue
        data = poll_resp.json()
        state = data.get("state", "")
        if state == "completed":
            return {
                "order_id": data.get("orderId", intent_id),
                "status": "completed",
            }
        if state == "failed":
            reason = data.get("failureReason", {})
            return {
                "order_id": intent_id,
                "status": "failed",
                "error": reason.get("message", "checkout failed"),
            }

    return {"order_id": intent_id, "status": "failed", "error": "polling timeout"}
