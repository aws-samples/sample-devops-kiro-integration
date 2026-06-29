from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
from flask import Blueprint, current_app, jsonify, request

from app import db
from middleware import token_blocklist, token_required
from models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "invalid_credentials", "message": "Invalid username or password"}), 401

    username = data["username"]
    password = data["password"]

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "invalid_credentials", "message": "Invalid username or password"}), 401

    if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        return jsonify({"error": "invalid_credentials", "message": "Invalid username or password"}), 401

    payload = {
        "user_id": user.id,
        "is_admin": user.is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")

    return jsonify({"token": token}), 200


@auth_bp.route("/logout", methods=["POST"])
@token_required
def logout():
    auth_header = request.headers.get("Authorization")
    token = auth_header.split()[1]
    token_blocklist.add(token)
    return jsonify({"message": "Successfully logged out"}), 200
