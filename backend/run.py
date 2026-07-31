from app import create_app
from app.extensions import db, socketio
from sqlalchemy import text

app = create_app()


def initialize_database() -> None:
    """Create the PostgreSQL schemas and any tables missing from this database."""
    with app.app_context():
        with db.engine.begin() as connection:
            for schema in ("mtgCore", "mtgDecks", "mtgGames", "mtgAnalysis"):
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

        db.create_all()

        with db.engine.begin() as connection:
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames".games '
                    'ADD COLUMN IF NOT EXISTS "lobbyName" TEXT'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames".games '
                    'ADD COLUMN IF NOT EXISTS ruleset TEXT NOT NULL DEFAULT \'casual\''
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames".games '
                    'ADD COLUMN IF NOT EXISTS "maxPlayers" INTEGER NOT NULL DEFAULT 4'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames".games '
                    'ADD COLUMN IF NOT EXISTS "passwordHash" TEXT'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames".games '
                    'ADD COLUMN IF NOT EXISTS "hostUserId" BIGINT'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames".games '
                    'ADD COLUMN IF NOT EXISTS "turnNumber" INTEGER NOT NULL DEFAULT 1'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames".games '
                    'ADD COLUMN IF NOT EXISTS "activeSeatNumber" INTEGER NOT NULL DEFAULT 1'
                )
            )
            connection.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_games_lobby_name" '
                    'ON "mtgGames".games ("lobbyName")'
                )
            )
            connection.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_games_ruleset" '
                    'ON "mtgGames".games (ruleset)'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames"."gamePlayers" '
                    'ADD COLUMN IF NOT EXISTS "isReady" BOOLEAN NOT NULL DEFAULT FALSE'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames"."gamePlayers" '
                    'ADD COLUMN IF NOT EXISTS "isHost" BOOLEAN NOT NULL DEFAULT FALSE'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames"."gamePlayers" '
                    'ADD COLUMN IF NOT EXISTS "lobbyTokenHash" TEXT'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames"."gamePlayers" '
                    'ADD COLUMN IF NOT EXISTS "isConnected" BOOLEAN NOT NULL DEFAULT FALSE'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames"."gamePlayers" '
                    'ADD COLUMN IF NOT EXISTS "disconnectedAt" TIMESTAMPTZ'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames"."gamePlayers" '
                    'ADD COLUMN IF NOT EXISTS "sleeveStyle" TEXT NOT NULL DEFAULT \'classic\''
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgGames"."cardInstances" '
                    'ADD COLUMN IF NOT EXISTS "isCommander" BOOLEAN NOT NULL DEFAULT FALSE'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgDecks".decks '
                    'ADD COLUMN IF NOT EXISTS "lastUsedAt" TIMESTAMPTZ'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgDecks".decks '
                    'ADD COLUMN IF NOT EXISTS "folderName" TEXT'
                )
            )
            connection.execute(
                text(
                    'ALTER TABLE "mtgDecks".decks '
                    'ADD COLUMN IF NOT EXISTS "commanderBracket" INTEGER'
                )
            )
            connection.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_decks_folder_name" '
                    'ON "mtgDecks".decks ("folderName")'
                )
            )
            connection.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_decks_last_used_at" '
                    'ON "mtgDecks".decks ("lastUsedAt")'
                )
            )
            connection.execute(
                text(
                    'UPDATE "mtgGames"."cardInstances" '
                    'SET "isCommander" = TRUE '
                    'WHERE zone = \'command\' AND "isCommander" = FALSE'
                )
            )
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
