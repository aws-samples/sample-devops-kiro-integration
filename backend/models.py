from datetime import datetime, timezone

from app import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    articles = db.relationship("Article", backref="author", lazy=True)
    likes = db.relationship("Like", backref="user", lazy=True)
    comments = db.relationship("Comment", backref="user", lazy=True)


class Article(db.Model):
    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_public = db.Column(db.Boolean, nullable=False, default=True)
    author_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    likes = db.relationship("Like", backref="article", lazy=True)
    comments = db.relationship("Comment", backref="article", lazy=True)


class Like(db.Model):
    __tablename__ = "likes"
    __table_args__ = (
        db.UniqueConstraint("user_id", "article_id", name="uq_user_article_like"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    article_id = db.Column(
        db.Integer, db.ForeignKey("articles.id"), nullable=False
    )
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    body = db.Column(db.Text, nullable=False)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    article_id = db.Column(
        db.Integer, db.ForeignKey("articles.id"), nullable=False
    )
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
