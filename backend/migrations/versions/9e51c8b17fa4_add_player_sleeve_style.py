"""add player sleeve style

Revision ID: 9e51c8b17fa4
Revises: 8c3af59d2e10
Create Date: 2026-07-25

"""
from alembic import op
import sqlalchemy as sa


revision = "9e51c8b17fa4"
down_revision = "8c3af59d2e10"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "gamePlayers",
        sa.Column(
            "sleeveStyle",
            sa.Text(),
            nullable=False,
            server_default="classic",
        ),
        schema="mtgGames",
    )


def downgrade():
    op.drop_column("gamePlayers", "sleeveStyle", schema="mtgGames")
