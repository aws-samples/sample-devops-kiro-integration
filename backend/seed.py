import os

import bcrypt

from app import db
from models import User


def seed_admin():
    """Seed the admin account if it does not already exist. Idempotent."""
    existing = User.query.filter_by(username="admin").first()
    if existing:
        return

    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_password:
        print("WARNING: ADMIN_PASSWORD not set. Skipping admin seed.")
        return

    password_hash = bcrypt.hashpw(
        admin_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    admin = User(
        username="admin",
        email="admin@blogportal.local",
        password_hash=password_hash,
        is_admin=True,
    )
    db.session.add(admin)
    db.session.commit()
