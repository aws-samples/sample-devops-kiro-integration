import os

from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_overrides=None):
    app = Flask(__name__)

    # Database config from environment with local dev defaults
    db_user = os.environ.get("DB_USER", "root")
    db_password = os.environ.get("DB_PASSWORD", "")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "3306")
    db_name = os.environ.get("DB_NAME", "blog_portal")

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        import secrets
        secret_key = secrets.token_hex(32)
        import warnings
        warnings.warn(
            "SECRET_KEY not set. Generated a random key for this session. "
            "Set the SECRET_KEY environment variable for production use.",
            stacklevel=2,
        )
    app.config["SECRET_KEY"] = secret_key
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB max request size
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Connection pooling
    app.config["SQLALCHEMY_POOL_SIZE"] = int(
        os.environ.get("DB_POOL_SIZE", "2")
    )
    app.config["SQLALCHEMY_MAX_OVERFLOW"] = 5
    app.config["SQLALCHEMY_POOL_RECYCLE"] = 3600

    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    CORS(app, origins=os.environ.get("CORS_ORIGINS", "*").split(","))

    # Register blueprints (added as they are implemented)
    from auth import auth_bp
    app.register_blueprint(auth_bp)
    from users import users_bp
    app.register_blueprint(users_bp)
    from articles import articles_bp
    app.register_blueprint(articles_bp)
    from interactions import interactions_bp
    app.register_blueprint(interactions_bp)

    with app.app_context():
        import models  # noqa: F401 — ensure models are registered with SQLAlchemy

        db.create_all()

        from seed import seed_admin

        seed_admin()

    return app
