import os
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .extensions import db, migrate, socketio


def create_app(config=None):
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://admin:admin@localhost:5432/mtg_sandbox"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Bare-metal Kachhapa listens on a Unix socket behind the local Nginx
    # default server; there is intentionally no TCP listener on port 5000.
    app.config["KACHHAPA_AUTH_URL"] = os.environ.get("KACHHAPA_AUTH_URL", "http://127.0.0.1")

    if config:
        app.config.update(config)

    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)

    # Import model modules so SQLAlchemy registers them
    from .models import mtgCore, mtgDecks, mtgGames, mtgAnalysis, mtgPrecons  # noqa: F401

    from .routes import api_bp, register_socket_handlers
    app.register_blueprint(api_bp)
    from .precon_routes import precons_bp
    from .services.precons import register_cli
    app.register_blueprint(precons_bp)
    from .deck_identity_routes import deck_identity_bp
    app.register_blueprint(deck_identity_bp)
    from .statistics_routes import statistics_bp
    app.register_blueprint(statistics_bp)
    register_cli(app)
    register_socket_handlers(socketio)

    @app.errorhandler(HTTPException)
    def api_error(error):
        return jsonify(error=error.description), error.code

    @app.get("/")
    def index():
        return {"app": "MTG Sandbox backend", "status": "running"}

    return app
