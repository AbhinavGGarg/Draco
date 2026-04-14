"""Real Stripe service — test-mode integration using StripeClient API."""
import os
from pathlib import Path

from dotenv import load_dotenv
from stripe import StripeClient, CardError

# Load .env from project root
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

_key = os.getenv("STRIPE_SECRET_KEY", "")
_client = StripeClient(_key) if _key else None


def _get_client() -> StripeClient:
    if _client is None:
        raise RuntimeError("STRIPE_SECRET_KEY not set")
    return _client


def create_customer(email: str) -> dict:
    """Create a Stripe customer. Returns {'id': 'cus_...'}."""
    client = _get_client()
    customer = client.v1.customers.create(params={"email": email})
    return {"id": customer.id}


def attach_payment_method(customer_id: str, token: str) -> dict:
    """Create a PaymentMethod from token and attach to customer.
    Returns {'id': 'pm_...'} or {'id': None, 'error': '...'}.
    """
    client = _get_client()
    try:
        pm = client.v1.payment_methods.create(
            params={"type": "card", "card": {"token": token}}
        )
        client.v1.payment_methods.attach(
            pm.id, params={"customer": customer_id}
        )
        return {"id": pm.id}
    except CardError as e:
        return {"id": None, "error": e.user_message}


def charge(
    customer_id: str,
    payment_method_id: str,
    amount: float,
    description: str = "",
) -> dict:
    """Create a PaymentIntent and charge immediately.
    amount is in dollars (float), converted to cents internally.
    Returns {'id': 'pi_...', 'status': 'succeeded'}
    or {'id': None, 'status': 'failed', 'error': '...'}.
    """
    client = _get_client()
    amount_cents = int(round(amount * 100))
    try:
        pi = client.v1.payment_intents.create(
            params={
                "amount": amount_cents,
                "currency": "usd",
                "customer": customer_id,
                "payment_method": payment_method_id,
                "confirm": True,
                "automatic_payment_methods": {
                    "enabled": True,
                    "allow_redirects": "never",
                },
                "description": description or None,
            }
        )
        return {"id": pi.id, "status": pi.status}
    except CardError as e:
        return {"id": None, "status": "failed", "error": e.user_message}
