"""add deck settings metadata

Revision ID: d6b8a4c91f20
Revises: c83d4f18a921
"""

from alembic import op
import sqlalchemy as sa


revision = "d6b8a4c91f20"
down_revision = "c83d4f18a921"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("decks", sa.Column("folderName", sa.Text(), nullable=True), schema="mtgDecks")
    op.add_column("decks", sa.Column("commanderBracket", sa.Integer(), nullable=True), schema="mtgDecks")
    op.create_index("ix_decks_folder_name", "decks", ["folderName"], schema="mtgDecks")


def downgrade():
    op.drop_index("ix_decks_folder_name", table_name="decks", schema="mtgDecks")
    op.drop_column("decks", "commanderBracket", schema="mtgDecks")
    op.drop_column("decks", "folderName", schema="mtgDecks")
