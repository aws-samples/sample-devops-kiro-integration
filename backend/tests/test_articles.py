"""Unit tests for backend/articles.py – article CRUD routes."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import pytest

from app import create_app, db
from middleware import token_blocklist
from models import Article, User

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
        pw = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8")
        user1 = User(username="alice", email="alice@example.com", password_hash=pw, is_admin=False)
        user2 = User(username="bob", email="bob@example.com", password_hash=pw, is_admin=False)
        db.session.add_all([user1, user2])
        db.session.commit()
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def _token(user_id, is_admin=False):
    payload = {
        "user_id": user_id,
        "is_admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def _auth(user_id, is_admin=False):
    return {"Authorization": f"Bearer {_token(user_id, is_admin)}"}


class TestCreateArticle:
    def _alice_id(self, app):
        with app.app_context():
            return User.query.filter_by(username="alice").first().id

    def test_create_public_article(self, app, client):
        alice_id = self._alice_id(app)
        resp = client.post(
            "/api/articles",
            json={"title": "Hello", "body": "World", "visibility": "public"},
            headers=_auth(alice_id),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["title"] == "Hello"
        assert data["body"] == "World"
        assert data["is_public"] is True
        assert data["author_id"] == alice_id
        assert "id" in data
        assert "created_at" in data

    def test_create_private_article(self, app, client):
        alice_id = self._alice_id(app)
        resp = client.post(
            "/api/articles",
            json={"title": "Secret", "body": "Hidden", "visibility": "private"},
            headers=_auth(alice_id),
        )
        assert resp.status_code == 201
        assert resp.get_json()["is_public"] is False

    def test_empty_title_returns_400(self, app, client):
        resp = client.post(
            "/api/articles",
            json={"title": "   ", "body": "Some body", "visibility": "public"},
            headers=_auth(self._alice_id(app)),
        )
        assert resp.status_code == 400
        assert "Title is required" in resp.get_json()["message"]

    def test_missing_title_returns_400(self, app, client):
        resp = client.post(
            "/api/articles",
            json={"body": "Some body", "visibility": "public"},
            headers=_auth(self._alice_id(app)),
        )
        assert resp.status_code == 400
        assert "Title is required" in resp.get_json()["message"]

    def test_word_limit_exceeded_returns_400(self, app, client):
        long_body = " ".join(["word"] * 1001)
        resp = client.post(
            "/api/articles",
            json={"title": "Long", "body": long_body, "visibility": "public"},
            headers=_auth(self._alice_id(app)),
        )
        assert resp.status_code == 400
        assert "1000 word limit" in resp.get_json()["message"]

    def test_exactly_1000_words_accepted(self, app, client):
        body = " ".join(["word"] * 1000)
        resp = client.post(
            "/api/articles",
            json={"title": "Exact", "body": body, "visibility": "public"},
            headers=_auth(self._alice_id(app)),
        )
        assert resp.status_code == 201

    def test_invalid_visibility_returns_400(self, app, client):
        resp = client.post(
            "/api/articles",
            json={"title": "Bad Vis", "body": "Body", "visibility": "unlisted"},
            headers=_auth(self._alice_id(app)),
        )
        assert resp.status_code == 400
        assert "Visibility must be public or private" in resp.get_json()["message"]

    def test_missing_visibility_returns_400(self, app, client):
        resp = client.post(
            "/api/articles",
            json={"title": "No Vis", "body": "Body"},
            headers=_auth(self._alice_id(app)),
        )
        assert resp.status_code == 400
        assert "Visibility must be public or private" in resp.get_json()["message"]

    def test_unauthenticated_returns_401(self, client):
        resp = client.post(
            "/api/articles",
            json={"title": "No Auth", "body": "Body", "visibility": "public"},
        )
        assert resp.status_code == 401


class TestListPublicArticles:
    def _seed_articles(self, app):
        with app.app_context():
            alice = User.query.filter_by(username="alice").first()
            bob = User.query.filter_by(username="bob").first()
            # alice creates 2 public, 1 private; bob creates 1 public, 1 private
            a1 = Article(title="Alice Public 1", body="A" * 250, is_public=True, author_id=alice.id)
            db.session.add(a1)
            db.session.commit()

            a2 = Article(title="Alice Private", body="secret", is_public=False, author_id=alice.id)
            db.session.add(a2)
            db.session.commit()

            a3 = Article(title="Bob Public", body="B" * 100, is_public=True, author_id=bob.id)
            db.session.add(a3)
            db.session.commit()

            a4 = Article(title="Alice Public 2", body="C" * 50, is_public=True, author_id=alice.id)
            db.session.add(a4)
            db.session.commit()

            a5 = Article(title="Bob Private", body="hidden", is_public=False, author_id=bob.id)
            db.session.add(a5)
            db.session.commit()

    def test_returns_only_public_articles(self, app, client):
        self._seed_articles(app)
        resp = client.get("/api/articles/public", headers=_auth(2))
        assert resp.status_code == 200
        data = resp.get_json()
        titles = [a["title"] for a in data]
        assert "Alice Private" not in titles
        assert "Bob Private" not in titles
        assert len(data) == 3

    def test_ordered_by_date_descending(self, app, client):
        self._seed_articles(app)
        resp = client.get("/api/articles/public", headers=_auth(2))
        data = resp.get_json()
        dates = [a["created_at"] for a in data]
        assert dates == sorted(dates, reverse=True)

    def test_includes_200_char_preview(self, app, client):
        self._seed_articles(app)
        resp = client.get("/api/articles/public", headers=_auth(2))
        data = resp.get_json()
        for a in data:
            assert "preview" in a
            assert len(a["preview"]) <= 200
        # The article with 250 chars body should be truncated
        alice1 = next(a for a in data if a["title"] == "Alice Public 1")
        assert len(alice1["preview"]) == 200

    def test_includes_author_username(self, app, client):
        self._seed_articles(app)
        resp = client.get("/api/articles/public", headers=_auth(2))
        data = resp.get_json()
        for a in data:
            assert "author_username" in a
            assert a["author_username"] in ("alice", "bob")

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/articles/public")
        assert resp.status_code == 401


class TestListMyArticles:
    def _seed_articles(self, app):
        with app.app_context():
            alice = User.query.filter_by(username="alice").first()
            bob = User.query.filter_by(username="bob").first()
            a1 = Article(title="Alice Pub", body="body", is_public=True, author_id=alice.id)
            db.session.add(a1)
            db.session.commit()

            a2 = Article(title="Alice Priv", body="body", is_public=False, author_id=alice.id)
            db.session.add(a2)
            db.session.commit()

            a3 = Article(title="Bob Pub", body="body", is_public=True, author_id=bob.id)
            db.session.add(a3)
            db.session.commit()
            return alice.id

    def test_returns_only_current_users_articles(self, app, client):
        alice_id = self._seed_articles(app)
        resp = client.get("/api/articles/mine", headers=_auth(alice_id))
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2
        titles = [a["title"] for a in data]
        assert "Alice Pub" in titles
        assert "Alice Priv" in titles
        assert "Bob Pub" not in titles

    def test_ordered_by_date_descending(self, app, client):
        alice_id = self._seed_articles(app)
        resp = client.get("/api/articles/mine", headers=_auth(alice_id))
        data = resp.get_json()
        dates = [a["created_at"] for a in data]
        assert dates == sorted(dates, reverse=True)

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/articles/mine")
        assert resp.status_code == 401


class TestGetArticle:
    def _seed(self, app):
        with app.app_context():
            alice = User.query.filter_by(username="alice").first()
            bob = User.query.filter_by(username="bob").first()
            pub = Article(title="Public Art", body="Full public body", is_public=True, author_id=alice.id)
            priv = Article(title="Private Art", body="Full private body", is_public=False, author_id=alice.id)
            db.session.add_all([pub, priv])
            db.session.commit()
            return pub.id, priv.id, alice.id, bob.id

    def test_public_article_accessible_by_any_user(self, app, client):
        pub_id, _, _, bob_id = self._seed(app)
        resp = client.get(f"/api/articles/{pub_id}", headers=_auth(bob_id))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["title"] == "Public Art"
        assert data["body"] == "Full public body"
        assert data["author_username"] == "alice"

    def test_private_article_accessible_by_author(self, app, client):
        _, priv_id, alice_id, _ = self._seed(app)
        resp = client.get(f"/api/articles/{priv_id}", headers=_auth(alice_id))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["title"] == "Private Art"
        assert data["body"] == "Full private body"

    def test_private_article_returns_403_for_non_author(self, app, client):
        _, priv_id, _, bob_id = self._seed(app)
        resp = client.get(f"/api/articles/{priv_id}", headers=_auth(bob_id))
        assert resp.status_code == 403
        assert resp.get_json()["error"] == "forbidden"

    def test_nonexistent_article_returns_404(self, app, client):
        _, _, alice_id, _ = self._seed(app)
        resp = client.get("/api/articles/9999", headers=_auth(alice_id))
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, app, client):
        pub_id, _, _, _ = self._seed(app)
        resp = client.get(f"/api/articles/{pub_id}")
        assert resp.status_code == 401
