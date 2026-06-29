"""User management routes – Admin only."""

import bcrypt
from flask import Blueprint, jsonify, request

from app import db
from middleware import admin_required
from models import User

users_bp = Blueprint("users", __name__, url_prefix="/api/users")


@users_bp.route("", methods=["POST"])
@admin_required
def create_user():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "validation_error", "message": "Request body is required"}), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "validation_error", "message": "Username, email, and password are required"}), 400

    if len(password) < 8:
        return jsonify({"error": "validation_error", "message": "Password must be at least 8 characters"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "validation_error", "message": "Username is already taken"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "validation_error", "message": "Email is already registered"}), 400

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        is_admin=False,
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "created_at": user.created_at.isoformat(),
    }), 201


@users_bp.route("/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "not_found", "message": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "User deleted successfully"}), 200


@users_bp.route("", methods=["GET"])
@admin_required
def list_users():
    users = User.query.all()
    return jsonify([
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_admin": u.is_admin,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]), 200
