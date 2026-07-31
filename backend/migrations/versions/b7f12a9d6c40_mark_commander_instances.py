"""mark commander card instances

Revision ID: b7f12a9d6c40
Revises: a4d7e10c2b83
Create Date: 2026-07-25

"""
from alembic import op
import sqlalchemy as sa


revision = "b7f12a9d6c40"
down_revision = "a4d7e10c2b83"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cardInstances",
        sa.Column("isCommander", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="mtgGames",
    )
    op.execute(
        'UPDATE "mtgGames"."cardInstances" '
        'SET "isCommander" = TRUE WHERE zone = \'command\''
    )


def downgrade():
    op.drop_column("cardInstances", "isCommander", schema="mtgGames")
