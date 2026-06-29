"""Like and comment interaction routes for public articles."""

from flask import Blueprint, g, jsonify, request

from app import db
from middleware import token_required
from models import Article, Comment, Like, User

interactions_bp = Blueprint("interactions", __name__, url_prefix="/api")


@interactions_bp.route("/articles/<int:article_id>/like", methods=["POST"])
@token_required
def toggle_like(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        return jsonify({"error": "not_found", "message": "Article not found"}), 404

    if not article.is_public:
        return jsonify({"error": "forbidden", "message": "Interactions are only allowed on public articles"}), 403

    existing_like = Like.query.filter_by(
        user_id=g.user_id, article_id=article_id
    ).first()

    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        liked = False
    else:
        new_like = Like(user_id=g.user_id, article_id=article_id)
        db.session.add(new_like)
        db.session.commit()
        liked = True

    like_count = Like.query.filter_by(article_id=article_id).count()

    return jsonify({"liked": liked, "like_count": like_count}), 200


@interactions_bp.route("/articles/<int:article_id>/comments", methods=["POST"])
@token_required
def create_comment(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        return jsonify({"error": "not_found", "message": "Article not found"}), 404

    if not article.is_public:
        return jsonify({"error": "forbidden", "message": "Interactions are only allowed on public articles"}), 403

    data = request.get_json(silent=True)
    body = (data.get("body") or "").strip() if data else ""

    if not body:
        return jsonify({"error": "validation_error", "message": "Comment body is required"}), 400

    user = db.session.get(User, g.user_id)

    comment = Comment(body=body, user_id=g.user_id, article_id=article_id)
    db.session.add(comment)
    db.session.commit()

    return jsonify({
        "id": comment.id,
        "body": comment.body,
        "author_username": user.username,
        "created_at": comment.created_at.isoformat(),
    }), 201


@interactions_bp.route("/articles/<int:article_id>/comments", methods=["GET"])
@token_required
def list_comments(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        return jsonify({"error": "not_found", "message": "Article not found"}), 404

    if not article.is_public:
        return jsonify({"error": "forbidden", "message": "Interactions are only allowed on public articles"}), 403

    comments = (
        db.session.query(Comment, User.username)
        .join(User, Comment.user_id == User.id)
        .filter(Comment.article_id == article_id)
        .order_by(Comment.created_at.asc())
        .all()
    )

    return jsonify([
        {
            "id": comment.id,
            "body": comment.body,
            "author_username": username,
            "created_at": comment.created_at.isoformat(),
        }
        for comment, username in comments
    ]), 200


@interactions_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@token_required
def delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return jsonify({"error": "not_found", "message": "Comment not found"}), 404

    if g.user_id != comment.user_id:
        return jsonify({"error": "forbidden", "message": "You can only delete your own comments"}), 403

    db.session.delete(comment)
    db.session.commit()

    return jsonify({"message": "Comment deleted"}), 200
