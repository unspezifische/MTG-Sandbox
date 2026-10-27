"""Add per-deck token printing preferences.

Revision ID: 3ce4b97d8210
Revises: a93c4e125b87
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "3ce4b97d8210"
down_revision = "a93c4e125b87"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "deckTokenPreferences",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "deckId",
            sa.BigInteger(),
            sa.ForeignKey("mtgDecks.decks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tokenOracleId", sa.Text(), nullable=False),
        sa.Column(
            "preferredPrintingId",
            sa.BigInteger(),
            sa.ForeignKey("mtgCore.printings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "deckId",
            "tokenOracleId",
            name="uq_deckTokenPreferences_deck_oracle",
        ),
        schema="mtgDecks",
    )
    op.create_index(
        "ix_mtgDecks_deckTokenPreferences_deckId",
        "deckTokenPreferences",
        ["deckId"],
        schema="mtgDecks",
    )
    op.add_column(
        "gamePlayers",
        sa.Column(
            "tokenSelections",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        schema="mtgGames",
    )
    op.create_index(
        "ix_mtgDecks_deckTokenPreferences_tokenOracleId",
        "deckTokenPreferences",
        ["tokenOracleId"],
        schema="mtgDecks",
    )
    op.create_index(
        "ix_mtgDecks_deckTokenPreferences_preferredPrintingId",
        "deckTokenPreferences",
        ["preferredPrintingId"],
        schema="mtgDecks",
    )


def downgrade():
    op.drop_column("gamePlayers", "tokenSelections", schema="mtgGames")
    op.drop_table("deckTokenPreferences", schema="mtgDecks")
