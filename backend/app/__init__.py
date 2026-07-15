import os

from flask import Flask, jsonify

from app.config import config_by_name
from app.extensions import db, migrate, jwt, cors


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}}, supports_credentials=True)

    from app import models  # noqa: F401  ensures models are registered before migrations

    from app.api import register_blueprints
    register_blueprints(app)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Not found"), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify(error="Internal server error"), 500

    return app
