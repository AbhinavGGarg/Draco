"""Payment integration tests — Stripe real (test mode) + Rye."""
import pytest

from api.src.services.stripe_service import (
    attach_payment_method,
    charge,
    create_customer,
)
from api.src.services.rye_service import checkout


class TestStripeCustomer:
    def test_create_customer_returns_cus_prefix(self):
        result = create_customer("test@openpay.dev")
        assert result["id"].startswith("cus_")

    def test_create_customer_returns_dict_with_id(self):
        result = create_customer("test2@openpay.dev")
        assert "id" in result
        assert isinstance(result["id"], str)


class TestStripePaymentMethod:
    def test_attach_tok_visa_succeeds(self):
        customer = create_customer("pm-test@openpay.dev")
        result = attach_payment_method(customer["id"], "tok_visa")
        assert result["id"] is not None
        assert result["id"].startswith("pm_")

    def test_attach_returns_dict_with_id(self):
        customer = create_customer("pm-test2@openpay.dev")
        result = attach_payment_method(customer["id"], "tok_mastercard")
        assert "id" in result


class TestStripeCharge:
    def test_charge_succeeds_with_tok_visa(self):
        # Setup: create customer + attach card
        customer = create_customer("charge-test@openpay.dev")
        pm = attach_payment_method(customer["id"], "tok_visa")
        assert pm["id"] is not None

        # Charge $10
        result = charge(customer["id"], pm["id"], 10.00)
        assert result["status"] == "succeeded"
        assert result["id"].startswith("pi_")

    def test_charge_declined_graceful_error(self):
        """tok_chargeDeclined may fail at attach or charge — either way,
        the error must be handled gracefully (no exceptions, error in response)."""
        customer = create_customer("decline-test@openpay.dev")
        pm = attach_payment_method(customer["id"], "tok_chargeDeclined")

        if pm["id"] is None:
            # Declined at attach time — verify error is captured
            assert "error" in pm
        else:
            # Declined at charge time
            result = charge(customer["id"], pm["id"], 10.00)
            assert result["status"] == "failed"
            assert result["id"] is None
            assert "error" in result

    def test_charge_with_description(self):
        customer = create_customer("desc-test@openpay.dev")
        pm = attach_payment_method(customer["id"], "tok_visa")

        result = charge(customer["id"], pm["id"], 5.50, description="USB-C cable")
        assert result["status"] == "succeeded"


class TestRyeCheckout:
    @pytest.mark.slow
    def test_checkout_airtag_completes(self):
        """Real Rye checkout with Amazon AirTag test URL — polls until completed."""
        result = checkout(
            "https://www.amazon.com/Apple-MX532LL-A-AirTag/dp/B0CWXNS552/", 24.00
        )
        assert "order_id" in result
        assert result["status"] == "completed"
        assert not result["order_id"].startswith("rye_mock_")

    def test_checkout_raises_without_key(self):
        """If RYE_API_KEY is empty, should raise RuntimeError."""
        import api.src.services.rye_service as rye_mod
        original_key = rye_mod.RYE_API_KEY
        rye_mod.RYE_API_KEY = ""
        rye_mod._AUTH_HEADER = {}
        try:
            with pytest.raises(RuntimeError, match="RYE_API_KEY not set"):
                checkout("https://example.com/product", 10.00)
        finally:
            rye_mod.RYE_API_KEY = original_key
            rye_mod._AUTH_HEADER = {"Authorization": f"Bearer {original_key}"}
