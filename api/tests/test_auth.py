"""Tests for auth middleware and auth routes."""
import json
import uuid
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask, g

# We build a minimal Flask app for testing instead of importing the real app,
# so tests stay self-contained with no Supabase connection needed.


def _make_app():
    """Create a minimal Flask app with auth routes for testing."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    from api.src.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    return app


# ─── Fixtures ────────────────────────────────────────────────────────────────

FAKE_AUTH_ID = str(uuid.uuid4())
FAKE_USER_ID = str(uuid.uuid4())
FAKE_AGENT_ID = str(uuid.uuid4())

VALID_JWT_PAYLOAD = {
    "sub": FAKE_AUTH_ID,
    "aud": "authenticated",
    "role": "authenticated",
    "email": "test@example.com",
    "exp": 9999999999,
    "iat": 1700000000,
}


@pytest.fixture
def app():
    """Provide a Flask test app with auth blueprint registered."""
    with patch("api.src.middleware.auth.supabase") as mock_sb, \
         patch("api.src.routes.auth.supabase") as mock_sb_routes:
        # Default: user exists
        mock_result = MagicMock()
        mock_result.data = [{"id": FAKE_USER_ID}]
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
        yield _make_app(), mock_sb, mock_sb_routes


@pytest.fixture
def client(app):
    app_instance, _, _ = app
    return app_instance.test_client()


def _auth_header(token="valid.jwt.token"):
    return {"Authorization": f"Bearer {token}"}


# ─── Middleware Tests ────────────────────────────────────────────────────────


@patch("api.src.middleware.auth.verify_jwt")
def test_valid_jwt_injects_user_id(mock_verify, app):
    """Valid JWT → g.user_id is set to the OpenPay user ID."""
    mock_verify.return_value = VALID_JWT_PAYLOAD
    app_instance, mock_sb, mock_sb_routes = app

    # Middleware looks up user by supabase_auth_id
    mock_user_result = MagicMock()
    mock_user_result.data = [{"id": FAKE_USER_ID}]
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_user_result

    # Route /api/auth/me needs user + agent data
    mock_user_full = MagicMock()
    mock_user_full.data = [{
        "id": FAKE_USER_ID, "name": "Test", "email": "test@example.com",
        "balance": 500.0, "stripe_customer_id": None, "created_at": "2026-01-01T00:00:00",
    }]
    mock_agent_result = MagicMock()
    mock_agent_result.data = [{
        "id": FAKE_AGENT_ID, "trust_score": 50,
        "constraints": {"max_per_transaction": 100, "max_per_week": 500,
                        "allowed_categories": ["electronics"], "blocked_merchants": []},
    }]
    # Chain: supabase.table("users").select("*").eq("id", ...).execute()
    mock_sb_routes.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
        mock_user_full, mock_agent_result
    ]

    client = app_instance.test_client()
    resp = client.get("/api/auth/me", headers=_auth_header())

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == FAKE_USER_ID
    mock_verify.assert_called_once_with("valid.jwt.token")


@patch("api.src.middleware.auth.verify_jwt")
def test_invalid_jwt_returns_401(mock_verify, app):
    """Bad token → 401 with error."""
    mock_verify.side_effect = Exception("Invalid token")
    app_instance, _, _ = app
    client = app_instance.test_client()

    resp = client.get("/api/auth/me", headers=_auth_header("bad.token"))
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["code"] in ("unauthorized", "invalid_token")


@patch("api.src.middleware.auth.verify_jwt")
def test_expired_jwt_returns_401(mock_verify, app):
    """Expired token → 401."""
    from jwt.exceptions import ExpiredSignatureError
    mock_verify.side_effect = ExpiredSignatureError("Token expired")
    app_instance, _, _ = app
    client = app_instance.test_client()

    resp = client.get("/api/auth/me", headers=_auth_header("expired.token"))
    assert resp.status_code == 401


def test_no_auth_header_returns_401(app):
    """Missing Authorization header → 401."""
    app_instance, _, _ = app
    client = app_instance.test_client()

    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["code"] == "unauthorized"


# ─── Route Tests: GET /api/auth/me ──────────────────────────────────────────


@patch("api.src.middleware.auth.verify_jwt")
def test_get_me_with_profile(mock_verify, app):
    """GET /api/auth/me with existing profile → 200 + user data + agent."""
    mock_verify.return_value = VALID_JWT_PAYLOAD
    app_instance, mock_sb, mock_sb_routes = app

    # Middleware: user exists
    mock_user_lookup = MagicMock()
    mock_user_lookup.data = [{"id": FAKE_USER_ID}]
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_user_lookup

    # Route: full user + agent
    mock_user_full = MagicMock()
    mock_user_full.data = [{
        "id": FAKE_USER_ID, "name": "Test User", "email": "test@example.com",
        "balance": 500.0, "stripe_customer_id": "cus_123", "created_at": "2026-01-01",
    }]
    mock_agent = MagicMock()
    mock_agent.data = [{
        "id": FAKE_AGENT_ID, "trust_score": 65,
        "constraints": {"max_per_transaction": 100, "max_per_week": 500,
                        "allowed_categories": ["electronics"], "blocked_merchants": []},
    }]
    mock_sb_routes.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
        mock_user_full, mock_agent
    ]

    client = app_instance.test_client()
    resp = client.get("/api/auth/me", headers=_auth_header())

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == FAKE_USER_ID
    assert data["name"] == "Test User"
    assert data["balance"] == 500.0
    assert data["agent"]["trust_score"] == 65
    assert data["agent"]["tier"] == "standard"


@patch("api.src.middleware.auth.verify_jwt")
def test_get_me_no_profile_returns_404(mock_verify, app):
    """GET /api/auth/me with valid JWT but no OpenPay user row → 404."""
    mock_verify.return_value = VALID_JWT_PAYLOAD
    app_instance, mock_sb, _ = app

    # Middleware: no user found
    mock_no_user = MagicMock()
    mock_no_user.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_no_user

    client = app_instance.test_client()
    resp = client.get("/api/auth/me", headers=_auth_header())

    assert resp.status_code == 404
    data = resp.get_json()
    assert data["code"] == "no_profile"


# ─── Route Tests: POST /api/auth/onboarding ─────────────────────────────────


@patch("api.src.middleware.auth.verify_jwt")
def test_onboarding_creates_user_and_agent(mock_verify, app):
    """POST /api/auth/onboarding creates user + agent rows with supabase_auth_id."""
    mock_verify.return_value = VALID_JWT_PAYLOAD
    app_instance, mock_sb, mock_sb_routes = app

    # Middleware: no existing user (onboarding not done yet)
    mock_no_user = MagicMock()
    mock_no_user.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_no_user

    # Route: insert user
    mock_user_insert = MagicMock()
    mock_user_insert.data = [{"id": FAKE_USER_ID, "name": "New User", "email": "new@example.com"}]
    # Route: insert agent
    mock_agent_insert = MagicMock()
    mock_agent_insert.data = [{"id": FAKE_AGENT_ID}]

    mock_sb_routes.table.return_value.insert.return_value.execute.side_effect = [
        mock_user_insert, mock_agent_insert
    ]

    client = app_instance.test_client()
    resp = client.post("/api/auth/onboarding",
                       data=json.dumps({
                           "name": "New User",
                           "email": "new@example.com",
                           "balance": 500.0,
                           "max_per_transaction": 100,
                           "max_per_week": 500,
                           "allowed_categories": ["electronics", "books"],
                           "blocked_merchants": [],
                       }),
                       content_type="application/json",
                       headers=_auth_header())

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["user_id"] == FAKE_USER_ID
    assert data["agent_id"] == FAKE_AGENT_ID


@patch("api.src.middleware.auth.verify_jwt")
def test_onboarding_already_exists_returns_409(mock_verify, app):
    """POST /api/auth/onboarding when profile exists → 409."""
    mock_verify.return_value = VALID_JWT_PAYLOAD
    app_instance, mock_sb, _ = app

    # Middleware: user already exists
    mock_existing = MagicMock()
    mock_existing.data = [{"id": FAKE_USER_ID}]
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_existing

    client = app_instance.test_client()
    resp = client.post("/api/auth/onboarding",
                       data=json.dumps({"name": "Test"}),
                       content_type="application/json",
                       headers=_auth_header())

    assert resp.status_code == 409
    data = resp.get_json()
    assert data["code"] == "already_exists"
