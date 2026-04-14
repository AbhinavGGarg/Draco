"""Supabase Auth JWT validation middleware for Flask.

Pre-fetches JWKS public key at startup via urllib (not httpx) for ES256
verification. No HS256 fallback — JWKS is the only supported method.
"""
import json
import logging
import os
import urllib.request
from functools import wraps

import jwt as pyjwt
from jwt.algorithms import ECAlgorithm
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidSignatureError,
)
from flask import g, jsonify, request

from api.src.db import supabase

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")


def _fetch_jwks_key():
    """Fetch JWKS from Supabase and return the ES256 public key.

    Uses urllib (not httpx/requests) to avoid conflicts with supabase-py.
    Called once at module load.
    """
    jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    with urllib.request.urlopen(jwks_url, timeout=10) as resp:
        jwks_data = json.loads(resp.read())

    for key_data in jwks_data.get("keys", []):
        if key_data.get("kty") == "EC":
            return ECAlgorithm(ECAlgorithm.SHA256).from_jwk(key_data)

    raise RuntimeError(f"No EC signing key found in JWKS at {jwks_url}")


# Lazy-loaded at first verify_jwt call (not at import time, so tests can mock)
_jwks_key = None


def verify_jwt(token: str) -> dict:
    """Decode and verify a Supabase JWT using JWKS key (ES256).

    Fetches and caches the JWKS key on first call (via urllib, not httpx).
    Returns decoded payload with 'sub' (Supabase Auth user ID).
    """
    global _jwks_key
    if _jwks_key is None:
        _jwks_key = _fetch_jwks_key()
        logger.info("JWKS EC signing key fetched for ES256 verification")

    return pyjwt.decode(
        token,
        _jwks_key,
        algorithms=["ES256"],
        audience="authenticated",
    )


def require_auth(f):
    """Decorator: extract Bearer token, verify JWT, inject g.user_id.

    On success sets:
      - g.supabase_user_id: the Supabase Auth UUID (from JWT 'sub')
      - g.user_id: the OpenPay user UUID (or None if not onboarded)
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header", "code": "unauthorized"}), 401

        token = auth_header.split(" ", 1)[1]

        try:
            payload = verify_jwt(token)
        except ExpiredSignatureError:
            return jsonify({"error": "Token expired", "code": "token_expired"}), 401
        except (InvalidAudienceError, InvalidSignatureError, DecodeError, Exception):
            return jsonify({"error": "Invalid token", "code": "invalid_token"}), 401

        sub = payload.get("sub")
        g.supabase_user_id = sub

        # Look up OpenPay user by supabase_auth_id
        result = supabase.table("users").select("id").eq("supabase_auth_id", sub).execute()
        if result.data:
            g.user_id = result.data[0]["id"]
        else:
            g.user_id = None

        return f(*args, **kwargs)
    return decorated
