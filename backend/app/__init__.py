import os
from flask import Flask

from .extensions import db, migrate, socketio


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://admin:admin@localhost:5432/mtg_sandbox"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)

    # Import model modules so SQLAlchemy registers them
    from .models import mtgCore, mtgDecks, mtgGames, mtgAnalysis  # noqa: F401

    from .routes import api_bp, register_socket_handlers
    app.register_blueprint(api_bp)
    register_socket_handlers(socketio)

    @app.get("/")
    def index():
        return {"app": "MTG Sandbox backend", "status": "running"}

    return app
