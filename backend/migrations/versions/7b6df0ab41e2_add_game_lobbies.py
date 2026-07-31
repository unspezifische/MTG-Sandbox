"""add game lobby metadata

Revision ID: 7b6df0ab41e2
Revises: 2a4a777a3f96
Create Date: 2026-07-24

"""
from alembic import op
import sqlalchemy as sa


revision = "7b6df0ab41e2"
down_revision = "2a4a777a3f96"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("games", sa.Column("lobbyName", sa.Text(), nullable=True), schema="mtgGames")
    op.add_column(
        "games",
        sa.Column("ruleset", sa.Text(), nullable=False, server_default="casual"),
        schema="mtgGames",
    )
    op.add_column(
        "games",
        sa.Column("maxPlayers", sa.Integer(), nullable=False, server_default="4"),
        schema="mtgGames",
    )
    op.add_column("games", sa.Column("passwordHash", sa.Text(), nullable=True), schema="mtgGames")
    op.add_column("games", sa.Column("hostUserId", sa.BigInteger(), nullable=True), schema="mtgGames")
    op.create_index("ix_games_lobby_name", "games", ["lobbyName"], schema="mtgGames")
    op.create_index("ix_games_ruleset", "games", ["ruleset"], schema="mtgGames")
    op.add_column(
        "gamePlayers",
        sa.Column("isReady", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="mtgGames",
    )
    op.add_column(
        "gamePlayers",
        sa.Column("isHost", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="mtgGames",
    )
    op.add_column(
        "gamePlayers",
        sa.Column("lobbyTokenHash", sa.Text(), nullable=True),
        schema="mtgGames",
    )


def downgrade():
    op.drop_column("gamePlayers", "lobbyTokenHash", schema="mtgGames")
    op.drop_column("gamePlayers", "isHost", schema="mtgGames")
    op.drop_column("gamePlayers", "isReady", schema="mtgGames")
    op.drop_index("ix_games_ruleset", table_name="games", schema="mtgGames")
    op.drop_index("ix_games_lobby_name", table_name="games", schema="mtgGames")
    op.drop_column("games", "hostUserId", schema="mtgGames")
    op.drop_column("games", "passwordHash", schema="mtgGames")
    op.drop_column("games", "maxPlayers", schema="mtgGames")
    op.drop_column("games", "ruleset", schema="mtgGames")
    op.drop_column("games", "lobbyName", schema="mtgGames")
