from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

# Module-level blocklist set for logout support.
# auth.py adds tokens here on logout; middleware checks here on every request.
token_blocklist: set[str] = set()


def token_required(f):
    """Decorator that verifies a JWT from the Authorization: Bearer <token> header.

    On success, attaches ``user_id`` and ``is_admin`` to ``flask.g``.
    Returns 401 JSON for missing header, malformed token, expired token,
    or blocklisted token.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({"error": "auth_required", "message": "Authentication required"}), 401

        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != "Bearer":
            return jsonify({"error": "invalid_token", "message": "Invalid token"}), 401

        token = parts[1]

        if token in token_blocklist:
            return jsonify({"error": "token_invalidated", "message": "Token has been invalidated"}), 401

        try:
            payload = jwt.decode(
                token,
                current_app.config["SECRET_KEY"],
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token_expired", "message": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid_token", "message": "Invalid token"}), 401

        g.user_id = payload["user_id"]
        g.is_admin = payload.get("is_admin", False)

        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """Decorator that requires the caller to be an authenticated admin.

    Wraps ``token_required`` so the JWT is verified first, then checks
    ``g.is_admin``.  Returns 403 if the user is not an admin.
    """

    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        if not g.is_admin:
            return jsonify({"error": "forbidden", "message": "Admin access required"}), 403
        return f(*args, **kwargs)

    return decorated
