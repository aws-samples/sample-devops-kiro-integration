"""Unit tests for backend/auth.py – login and logout routes."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import pytest

from app import create_app, db
from middleware import token_blocklist
from models import User

SECRET = "test-secret"


@pytest.fixture(autouse=True)
def _clear_blocklist():
    token_blocklist.clear()
    yield
    token_blocklist.clear()


@pytest.fixture()
def app():
    app = create_app(
        config_overrides={
            "TESTING": True,
            "SECRET_KEY": SECRET,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    with app.app_context():
        db.create_all()
        # Create a test user
        pw_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8")
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=pw_hash,
            is_admin=False,
        )
        db.session.add(user)
        db.session.commit()
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_token(user_id=1, is_admin=False, secret=SECRET):
    payload = {
        "user_id": user_id,
        "is_admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


class TestLogin:
    def test_valid_credentials_returns_token(self, client):
        resp = client.post("/api/auth/login", json={"username": "testuser", "password": "password123"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "token" in data
        # Decode and verify token contents
        decoded = jwt.decode(data["token"], SECRET, algorithms=["HS256"])
        assert decoded["is_admin"] is False
        assert "user_id" in decoded
        assert "exp" in decoded

    def test_wrong_password_returns_401(self, client):
        resp = client.post("/api/auth/login", json={"username": "testuser", "password": "wrongpass"})
        assert resp.status_code == 401
        assert resp.get_json()["error"] == "invalid_credentials"

    def test_nonexistent_user_returns_401(self, client):
        resp = client.post("/api/auth/login", json={"username": "noone", "password": "password123"})
        assert resp.status_code == 401
        assert resp.get_json()["error"] == "invalid_credentials"

    def test_missing_fields_returns_401(self, client):
        resp = client.post("/api/auth/login", json={"username": "testuser"})
        assert resp.status_code == 401

    def test_no_body_returns_401(self, client):
        resp = client.post("/api/auth/login")
        assert resp.status_code == 401

    def test_admin_login_sets_is_admin_true(self, app, client):
        with app.app_context():
            # The seed creates an admin user; query it
            admin = User.query.filter_by(username="admin").first()
            assert admin is not None
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123!"})
        assert resp.status_code == 200
        decoded = jwt.decode(resp.get_json()["token"], SECRET, algorithms=["HS256"])
        assert decoded["is_admin"] is True


class TestLogout:
    def test_logout_blocklists_token(self, client):
        # Login first
        resp = client.post("/api/auth/login", json={"username": "testuser", "password": "password123"})
        token = resp.get_json()["token"]
        # Logout
        resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.get_json()["message"] == "Successfully logged out"
        assert token in token_blocklist

    def test_logout_without_token_returns_401(self, client):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 401

    def test_token_rejected_after_logout(self, client):
        # Login
        resp = client.post("/api/auth/login", json={"username": "testuser", "password": "password123"})
        token = resp.get_json()["token"]
        # Logout
        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        # Try using the same token again for logout
        resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.get_json()["message"] == "Token has been invalidated"
