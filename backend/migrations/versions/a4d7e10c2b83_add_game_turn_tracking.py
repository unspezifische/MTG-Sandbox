"""add game turn tracking

Revision ID: a4d7e10c2b83
Revises: 9e51c8b17fa4
Create Date: 2026-07-25

"""
from alembic import op
import sqlalchemy as sa


revision = "a4d7e10c2b83"
down_revision = "9e51c8b17fa4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "games",
        sa.Column("turnNumber", sa.Integer(), nullable=False, server_default="1"),
        schema="mtgGames",
    )
    op.add_column(
        "games",
        sa.Column("activeSeatNumber", sa.Integer(), nullable=False, server_default="1"),
        schema="mtgGames",
    )


def downgrade():
    op.drop_column("games", "activeSeatNumber", schema="mtgGames")
    op.drop_column("games", "turnNumber", schema="mtgGames")
