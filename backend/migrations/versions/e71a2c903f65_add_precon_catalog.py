"""Add immutable official precon catalog (no personal deck changes).

Revision ID: e71a2c903f65
Revises: d6b8a4c91f20
"""
from alembic import op
import sqlalchemy as sa

revision = "e71a2c903f65"
down_revision = "d6b8a4c91f20"
branch_labels = None
depends_on = None
S = "mtgDecks"


def _table_exists(table_name):
    if op.get_context().as_sql:
        return False  # Offline output describes a fresh schema, not live adoption.
    return sa.inspect(op.get_bind()).has_table(table_name, schema=S)


def _adopt_or_create_table(table_name, columns, *constraints):
    if not _table_exists(table_name):
        op.create_table(table_name, *columns, *constraints, schema=S)
        return

    existing_columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name, schema=S)
    }
    expected_columns = {column.name for column in columns}
    missing_columns = sorted(expected_columns - existing_columns)
    if missing_columns:
        raise RuntimeError(
            f'Cannot adopt existing {S}.{table_name}; missing columns: '
            + ", ".join(missing_columns)
        )


def _ensure_index(name, table_name, columns, **kwargs):
    existing_indexes = {
        index["name"] for index in ([] if op.get_context().as_sql else sa.inspect(op.get_bind()).get_indexes(table_name, schema=S))
    }
    if name not in existing_indexes:
        op.create_index(name, table_name, columns, schema=S, **kwargs)


def _ensure_current_version_foreign_key():
    existing_foreign_keys = {
        foreign_key["name"]
        for foreign_key in ([] if op.get_context().as_sql else sa.inspect(op.get_bind()).get_foreign_keys("precon_templates", schema=S))
    }
    if "fk_precon_current_version" not in existing_foreign_keys:
        op.create_foreign_key(
            "fk_precon_current_version",
            "precon_templates",
            "precon_template_versions",
            ["current_version_id"],
            ["id"],
            source_schema=S,
            referent_schema=S,
        )


def upgrade():
    _adopt_or_create_table("precon_templates", [
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("external_key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("set_code", sa.Text(), nullable=False),
        sa.Column("deck_type", sa.Text(), nullable=False),
        sa.Column("format", sa.Text()), sa.Column("release_date", sa.Date()),
        sa.Column("sealed_product_ids", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("current_version_id", sa.BigInteger()),
    ], sa.UniqueConstraint("provider", "external_key"))
    _adopt_or_create_table("precon_template_aliases", [
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("external_key", sa.Text(), nullable=False),
        sa.Column("template_id", sa.BigInteger(), sa.ForeignKey(f"{S}.precon_templates.id"), nullable=False),
    ], sa.UniqueConstraint("provider", "external_key"))
    _adopt_or_create_table("precon_template_versions", [
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("template_id", sa.BigInteger(), sa.ForeignKey(f"{S}.precon_templates.id"), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("provider_metadata", sa.JSON(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False), sa.Column("issues", sa.JSON(), nullable=False),
    ], sa.UniqueConstraint("template_id", "checksum"))
    _ensure_current_version_foreign_key()
    _adopt_or_create_table("precon_template_cards", [
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("version_id", sa.BigInteger(), sa.ForeignKey(f"{S}.precon_template_versions.id"), nullable=False),
        sa.Column("card_id", sa.BigInteger(), sa.ForeignKey("mtgCore.cards.id")),
        sa.Column("printing_id", sa.BigInteger(), sa.ForeignKey("mtgCore.printings.id")),
        sa.Column("provider_uuid", sa.Text(), nullable=False), sa.Column("name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("board", sa.Text(), nullable=False),
        sa.Column("is_commander", sa.Boolean(), nullable=False), sa.Column("source_metadata", sa.JSON(), nullable=False),
    ], sa.CheckConstraint("quantity > 0", name="ck_precon_quantity"))
    for table, columns in {
        "precon_templates": ["name", "set_code", "format", "release_date"],
        "precon_template_aliases": ["template_id"],
        "precon_template_versions": ["template_id"],
        "precon_template_cards": ["version_id", "card_id", "provider_uuid"],
    }.items():
        for column in columns:
            _ensure_index(f"ix_{S}_{table}_{column}", table, [column])
    # Existing deployments already use pg_trgm for card search.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    _ensure_index("ix_precon_name_trgm", "precon_templates", ["name"],
                  postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"})
    _ensure_index("ix_precon_commander_trgm", "precon_template_cards", ["name"],
                  postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"},
                  postgresql_where=sa.text("is_commander"))


def downgrade():
    op.drop_table("precon_template_cards", schema=S)
    op.drop_table("precon_template_aliases", schema=S)
    op.drop_constraint("fk_precon_current_version", "precon_templates", schema=S, type_="foreignkey")
    op.drop_table("precon_template_versions", schema=S)
    op.drop_table("precon_templates", schema=S)
