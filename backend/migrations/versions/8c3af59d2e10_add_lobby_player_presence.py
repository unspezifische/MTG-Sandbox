"""add lobby player presence

Revision ID: 8c3af59d2e10
Revises: 7b6df0ab41e2
Create Date: 2026-07-25

"""
from alembic import op
import sqlalchemy as sa


revision = "8c3af59d2e10"
down_revision = "7b6df0ab41e2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "gamePlayers",
        sa.Column("isConnected", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="mtgGames",
    )
    op.add_column(
        "gamePlayers",
        sa.Column("disconnectedAt", sa.DateTime(timezone=True), nullable=True),
        schema="mtgGames",
    )


def downgrade():
    op.drop_column("gamePlayers", "disconnectedAt", schema="mtgGames")
    op.drop_column("gamePlayers", "isConnected", schema="mtgGames")
