"""Unit tests for backend/middleware.py – token_required and admin_required decorators."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from flask import Flask, g, jsonify

from middleware import admin_required, token_blocklist, token_required

SECRET = "test-secret"


@pytest.fixture(autouse=True)
def _clear_blocklist():
    """Ensure the blocklist is empty before each test."""
    token_blocklist.clear()
    yield
    token_blocklist.clear()


@pytest.fixture()
def app():
    """Minimal Flask app with a protected route and an admin route."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET
    app.config["TESTING"] = True

    @app.route("/protected")
    @token_required
    def protected():
        return jsonify({"user_id": g.user_id, "is_admin": g.is_admin})

    @app.route("/admin-only")
    @admin_required
    def admin_only():
        return jsonify({"msg": "admin access granted"})

    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_token(payload_overrides=None, secret=SECRET):
    payload = {
        "user_id": 1,
        "is_admin": False,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    if payload_overrides:
        payload.update(payload_overrides)
    return jwt.encode(payload, secret, algorithm="HS256")


# ── token_required tests ──────────────────────────────────────────────


class TestTokenRequired:
    def test_missing_auth_header(self, client):
        resp = client.get("/protected")
        assert resp.status_code == 401
        assert resp.get_json()["message"] == "Authentication required"

    def test_malformed_header_no_bearer(self, client):
        resp = client.get("/protected", headers={"Authorization": "Token abc"})
        assert resp.status_code == 401
        assert resp.get_json()["message"] == "Invalid token"

    def test_malformed_header_extra_parts(self, client):
        resp = client.get("/protected", headers={"Authorization": "Bearer a b"})
        assert resp.status_code == 401
        assert resp.get_json()["message"] == "Invalid token"

    def test_expired_token(self, client):
        token = _make_token({"exp": datetime.now(timezone.utc) - timedelta(seconds=1)})
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.get_json()["message"] == "Token expired"

    def test_invalid_signature(self, client):
        token = _make_token(secret="wrong-secret")
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.get_json()["message"] == "Invalid token"

    def test_blocklisted_token(self, client):
        token = _make_token()
        token_blocklist.add(token)
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.get_json()["message"] == "Token has been invalidated"

    def test_valid_token_attaches_context(self, client):
        token = _make_token({"user_id": 42, "is_admin": True})
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["user_id"] == 42
        assert data["is_admin"] is True

    def test_valid_token_defaults_is_admin_false(self, client):
        payload = {
            "user_id": 7,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.get_json()["is_admin"] is False


# ── admin_required tests ──────────────────────────────────────────────


class TestAdminRequired:
    def test_non_admin_gets_403(self, client):
        token = _make_token({"is_admin": False})
        resp = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert resp.get_json()["message"] == "Admin access required"

    def test_admin_gets_access(self, client):
        token = _make_token({"is_admin": True})
        resp = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.get_json()["msg"] == "admin access granted"

    def test_missing_token_still_401(self, client):
        resp = client.get("/admin-only")
        assert resp.status_code == 401
