"""add card instance playmat fields

Revision ID: 2a4a777a3f96
Revises: 14dab1a395db
Create Date: ...
"""

from alembic import op
import sqlalchemy as sa


revision = "2a4a777a3f96"
down_revision = "38fe89b1d3cc"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cardInstances",
        sa.Column("zone", sa.Text(), nullable=False, server_default="library"),
        schema="mtgGames",
    )
    op.add_column(
        "cardInstances",
        sa.Column("zoneIndex", sa.Integer(), nullable=True),
        schema="mtgGames",
    )
    op.add_column(
        "cardInstances",
        sa.Column("isTapped", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="mtgGames",
    )
    op.add_column(
        "cardInstances",
        sa.Column("rotationDeg", sa.Integer(), nullable=False, server_default="0"),
        schema="mtgGames",
    )
    op.add_column(
        "cardInstances",
        sa.Column("isFaceDown", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="mtgGames",
    )
    op.add_column(
        "cardInstances",
        sa.Column("displayFace", sa.Text(), nullable=True),
        schema="mtgGames",
    )
    op.add_column(
        "cardInstances",
        sa.Column("battlefieldX", sa.Numeric(), nullable=True),
        schema="mtgGames",
    )
    op.add_column(
        "cardInstances",
        sa.Column("battlefieldY", sa.Numeric(), nullable=True),
        schema="mtgGames",
    )
    op.add_column(
        "cardInstances",
        sa.Column("stackIndex", sa.Integer(), nullable=True),
        schema="mtgGames",
    )

    op.create_index(
        "ix_mtgGames_cardInstances_zone",
        "cardInstances",
        ["zone"],
        unique=False,
        schema="mtgGames",
    )


def downgrade():
    op.drop_index(
        "ix_mtgGames_cardInstances_zone",
        table_name="cardInstances",
        schema="mtgGames",
    )

    op.drop_column("cardInstances", "stackIndex", schema="mtgGames")
    op.drop_column("cardInstances", "battlefieldY", schema="mtgGames")
    op.drop_column("cardInstances", "battlefieldX", schema="mtgGames")
    op.drop_column("cardInstances", "displayFace", schema="mtgGames")
    op.drop_column("cardInstances", "isFaceDown", schema="mtgGames")
    op.drop_column("cardInstances", "rotationDeg", schema="mtgGames")
    op.drop_column("cardInstances", "isTapped", schema="mtgGames")
    op.drop_column("cardInstances", "zoneIndex", schema="mtgGames")
    op.drop_column("cardInstances", "zone", schema="mtgGames")