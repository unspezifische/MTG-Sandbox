from app import create_app
from app.extensions import db, socketio
from sqlalchemy import text

app = create_app()


def initialize_database() -> None:
    """Apply the migration ledger before starting the development server.

    An unversioned populated database must be reviewed explicitly; never stamp
    it automatically or treat create_all() as an existing-schema migration.
    """
    from pathlib import Path
    from flask_migrate import upgrade

    with app.app_context():
        upgrade(directory=str(Path(__file__).resolve().parent / "migrations"))
        with db.engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            connection.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_cards_name_trgm" '
                    'ON "mtgCore".cards USING gin (name gin_trgm_ops)'
                )
            )
            connection.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_cards_oracle_text_trgm" '
                    'ON "mtgCore".cards USING gin ("oracleText" gin_trgm_ops)'
                )
            )
            connection.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_cards_type_line_trgm" '
                    'ON "mtgCore".cards USING gin ("typeLine" gin_trgm_ops)'
                )
            )
            connection.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_cards_name_lower" '
                    'ON "mtgCore".cards (lower(name))'
                )
            )


if __name__ == "__main__":
    initialize_database()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
