"""add deck last used timestamp

Revision ID: c83d4f18a921
Revises: b7f12a9d6c40
"""

from alembic import op
import sqlalchemy as sa


revision = "c83d4f18a921"
down_revision = "b7f12a9d6c40"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "decks",
        sa.Column("lastUsedAt", sa.DateTime(timezone=True), nullable=True),
        schema="mtgDecks",
    )
    op.create_index(
        "ix_decks_last_used_at",
        "decks",
        ["lastUsedAt"],
        unique=False,
        schema="mtgDecks",
    )


def downgrade():
    op.drop_index("ix_decks_last_used_at", table_name="decks", schema="mtgDecks")
    op.drop_column("decks", "lastUsedAt", schema="mtgDecks")
