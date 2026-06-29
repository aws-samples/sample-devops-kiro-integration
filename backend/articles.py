"""Article CRUD routes with visibility enforcement."""

from flask import Blueprint, g, jsonify, request

from app import db
from middleware import token_required
from models import Article, Comment, Like, User

articles_bp = Blueprint("articles", __name__, url_prefix="/api/articles")


def _validate_article(data):
    """Validate article input. Returns (error_response, status_code) or (None, None)."""
    if not data:
        return {"error": "validation_error", "message": "Request body is required"}, 400

    title = data.get("title", "")
    if not isinstance(title, str) or not title.strip():
        return {"error": "validation_error", "message": "Title is required"}, 400

    body = data.get("body", "")
    if isinstance(body, str) and len(body.split()) > 1000:
        return {"error": "validation_error", "message": "Article body exceeds 1000 word limit"}, 400

    visibility = data.get("visibility")
    if visibility not in ("public", "private"):
        return {"error": "validation_error", "message": "Visibility must be public or private"}, 400

    return None, None


@articles_bp.route("", methods=["POST"])
@token_required
def create_article():
    data = request.get_json(silent=True)
    error, status = _validate_article(data)
    if error:
        return jsonify(error), status

    article = Article(
        title=data["title"].strip(),
        body=data.get("body", ""),
        is_public=data["visibility"] == "public",
        author_id=g.user_id,
    )
    db.session.add(article)
    db.session.commit()

    return jsonify({
        "id": article.id,
        "title": article.title,
        "body": article.body,
        "is_public": article.is_public,
        "author_id": article.author_id,
        "created_at": article.created_at.isoformat(),
    }), 201


@articles_bp.route("/public", methods=["GET"])
@token_required
def list_public_articles():
    articles = (
        Article.query
        .filter_by(is_public=True)
        .order_by(Article.created_at.desc())
        .all()
    )
    result = []
    for a in articles:
        author = db.session.get(User, a.author_id)
        like_count = Like.query.filter_by(article_id=a.id).count()
        comment_count = Comment.query.filter_by(article_id=a.id).count()
        result.append({
            "id": a.id,
            "title": a.title,
            "author_username": author.username if author else None,
            "created_at": a.created_at.isoformat(),
            "preview": a.body[:200],
            "like_count": like_count,
            "comment_count": comment_count,
        })
    return jsonify(result), 200


@articles_bp.route("/mine", methods=["GET"])
@token_required
def list_my_articles():
    articles = (
        Article.query
        .filter_by(author_id=g.user_id)
        .order_by(Article.created_at.desc())
        .all()
    )
    result = []
    for a in articles:
        result.append({
            "id": a.id,
            "title": a.title,
            "body": a.body,
            "is_public": a.is_public,
            "created_at": a.created_at.isoformat(),
        })
    return jsonify(result), 200


@articles_bp.route("/<int:article_id>", methods=["GET"])
@token_required
def get_article(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        return jsonify({"error": "not_found", "message": "Article not found"}), 404

    if not article.is_public and article.author_id != g.user_id:
        return jsonify({"error": "forbidden", "message": "Access denied"}), 403

    author = db.session.get(User, article.author_id)
    like_count = Like.query.filter_by(article_id=article.id).count()
    comment_count = Comment.query.filter_by(article_id=article.id).count()
    user_has_liked = Like.query.filter_by(user_id=g.user_id, article_id=article.id).first() is not None
    return jsonify({
        "id": article.id,
        "title": article.title,
        "body": article.body,
        "is_public": article.is_public,
        "author_id": article.author_id,
        "author_username": author.username if author else None,
        "created_at": article.created_at.isoformat(),
        "like_count": like_count,
        "comment_count": comment_count,
        "user_has_liked": user_has_liked,
    }), 200
