"""Unit tests for backend/users.py – user CRUD routes (admin only)."""

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
        # Create a non-admin test user
        pw_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8")
        user = User(
            username="regularuser",
            email="regular@example.com",
            password_hash=pw_hash,
            is_admin=False,
        )
        db.session.add(user)
        db.session.commit()
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def _admin_token():
    payload = {
        "user_id": 1,
        "is_admin": True,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def _user_token(user_id=2):
    payload = {
        "user_id": user_id,
        "is_admin": False,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


class TestCreateUser:
    def test_admin_creates_user_successfully(self, client):
        resp = client.post(
            "/api/users",
            json={"username": "newuser", "email": "new@example.com", "password": "securepass"},
            headers={"Authorization": f"Bearer {_admin_token()}"},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert data["is_admin"] is False
        assert "id" in data
        assert "created_at" in data

    def test_duplicate_username_returns_400(self, client):
        token = _admin_token()
        client.post(
            "/api/users",
            json={"username": "dupuser", "email": "dup1@example.com", "password": "securepass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = client.post(
            "/api/users",
            json={"username": "dupuser", "email": "dup2@example.com", "password": "securepass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "Username is already taken" in resp.get_json()["message"]

    def test_duplicate_email_returns_400(self, client):
        token = _admin_token()
        client.post(
            "/api/users",
            json={"username": "user1", "email": "same@example.com", "password": "securepass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = client.post(
            "/api/users",
            json={"username": "user2", "email": "same@example.com", "password": "securepass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "Email is already registered" in resp.get_json()["message"]

    def test_short_password_returns_400(self, client):
        resp = client.post(
            "/api/users",
            json={"username": "shortpw", "email": "short@example.com", "password": "1234567"},
            headers={"Authorization": f"Bearer {_admin_token()}"},
        )
        assert resp.status_code == 400
        assert "Password must be at least 8 characters" in resp.get_json()["message"]

    def test_missing_fields_returns_400(self, client):
        resp = client.post(
            "/api/users",
            json={"username": "onlyname"},
            headers={"Authorization": f"Bearer {_admin_token()}"},
        )
        assert resp.status_code == 400

    def test_non_admin_cannot_create_user(self, client):
        resp = client.post(
            "/api/users",
            json={"username": "blocked", "email": "blocked@example.com", "password": "securepass"},
            headers={"Authorization": f"Bearer {_user_token()}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error"] == "forbidden"

    def test_no_auth_returns_401(self, client):
        resp = client.post(
            "/api/users",
            json={"username": "noauth", "email": "noauth@example.com", "password": "securepass"},
        )
        assert resp.status_code == 401


class TestDeleteUser:
    def test_admin_deletes_user(self, app, client):
        token = _admin_token()
        # Create a user to delete
        client.post(
            "/api/users",
            json={"username": "todelete", "email": "del@example.com", "password": "securepass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        with app.app_context():
            user = User.query.filter_by(username="todelete").first()
            user_id = user.id

        resp = client.delete(
            f"/api/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "deleted" in resp.get_json()["message"].lower()

        # Verify user is gone
        with app.app_context():
            assert User.query.filter_by(username="todelete").first() is None

    def test_delete_nonexistent_user_returns_404(self, client):
        resp = client.delete(
            "/api/users/9999",
            headers={"Authorization": f"Bearer {_admin_token()}"},
        )
        assert resp.status_code == 404

    def test_non_admin_cannot_delete_user(self, client):
        resp = client.delete(
            "/api/users/1",
            headers={"Authorization": f"Bearer {_user_token()}"},
        )
        assert resp.status_code == 403


class TestListUsers:
    def test_admin_lists_users(self, client):
        resp = client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {_admin_token()}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        # At least admin + regularuser from fixture
        assert len(data) >= 2
        usernames = [u["username"] for u in data]
        assert "admin" in usernames
        assert "regularuser" in usernames

    def test_non_admin_cannot_list_users(self, client):
        resp = client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {_user_token()}"},
        )
        assert resp.status_code == 403

    def test_no_auth_returns_401(self, client):
        resp = client.get("/api/users")
        assert resp.status_code == 401
