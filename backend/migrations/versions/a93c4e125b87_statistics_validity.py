"""Add match invalidation flags and participant statistics indexes.

Revision ID: a93c4e125b87
Revises: f82b3d014a76
"""
from alembic import op
import sqlalchemy as sa

revision = "a93c4e125b87"
down_revision = "f82b3d014a76"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("games", sa.Column("isInvalidated", sa.Boolean(), nullable=False, server_default=sa.false()), schema="mtgGames")
    op.add_column("games", sa.Column("invalidationReason", sa.Text()), schema="mtgGames")
    op.create_index("ix_gamePlayers_user_game_type", "gamePlayers", ["userId", "gameId", "playerType"], schema="mtgGames")
    op.create_index("ix_gamePlayers_deck_user_revision", "gamePlayers", ["deckId", "userId", "deckVersionId"], schema="mtgGames")


def downgrade():
    op.drop_index("ix_gamePlayers_deck_user_revision", table_name="gamePlayers", schema="mtgGames")
    op.drop_index("ix_gamePlayers_user_game_type", table_name="gamePlayers", schema="mtgGames")
    op.drop_column("games", "invalidationReason", schema="mtgGames")
    op.drop_column("games", "isInvalidated", schema="mtgGames")
