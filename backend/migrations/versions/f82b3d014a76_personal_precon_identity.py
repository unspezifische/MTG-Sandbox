"""Extend existing decks/versions for personal precon identity.

Revision ID: f82b3d014a76
Revises: e71a2c903f65
"""
from alembic import op
import sqlalchemy as sa

revision = "f82b3d014a76"
down_revision = "e71a2c903f65"
branch_labels = None
depends_on = None
S = "mtgDecks"


def upgrade():
    for column in (
        sa.Column("sourcePreconId", sa.BigInteger()),
        sa.Column("sourcePreconVersionId", sa.BigInteger()),
        sa.Column("libraryStatus", sa.Text(), nullable=False, server_default="saved"),
        sa.Column("isPrimaryPreconInstance", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("addedToLibraryAt", sa.DateTime(timezone=True)),
        sa.Column("currentVersionId", sa.BigInteger()),
    ):
        op.add_column("decks", column, schema=S)
    op.execute('UPDATE "mtgDecks".decks SET "addedToLibraryAt" = "createdAt"')
    op.create_check_constraint("ck_deck_library_status", "decks",
        '"libraryStatus" IN (\'unlisted\', \'saved\', \'archived\')', schema=S)
    for column in ("sourcePreconId", "libraryStatus"):
        op.create_index(f"ix_mtgDecks_decks_{column}", "decks", [column], schema=S)
    op.create_index("uq_deck_primary_precon", "decks", ["ownerUserId", "sourcePreconId"], unique=True,
                    schema=S, postgresql_where=sa.text('"isPrimaryPreconInstance"'))
    for column in (
        sa.Column("basePreconVersionId", sa.BigInteger()),
        sa.Column("revisionType", sa.Text(), nullable=False, server_default="custom"),
        sa.Column("contentHash", sa.String(64)),
    ):
        op.add_column("deckVersions", column, schema=S)
    for name, table, column, target in (
        ("fk_deck_source_precon", "decks", "sourcePreconId", "precon_templates"),
        ("fk_deck_source_precon_version", "decks", "sourcePreconVersionId", "precon_template_versions"),
        ("fk_deck_current_version", "decks", "currentVersionId", "deckVersions"),
        ("fk_version_base_precon", "deckVersions", "basePreconVersionId", "precon_template_versions"),
    ):
        op.create_foreign_key(name, table, target, [column], ["id"], source_schema=S, referent_schema=S)
    # Older matches keep their original NULL/legacy version references. Baselines for
    # existing editable lists are created lazily on first edit/game selection.


def downgrade():
    for name, table in (("fk_deck_source_precon", "decks"), ("fk_deck_source_precon_version", "decks"),
                        ("fk_deck_current_version", "decks"), ("fk_version_base_precon", "deckVersions")):
        op.drop_constraint(name, table, schema=S, type_="foreignkey")
    op.drop_index("uq_deck_primary_precon", table_name="decks", schema=S)
    for column in ("sourcePreconId", "libraryStatus"):
        op.drop_index(f"ix_mtgDecks_decks_{column}", table_name="decks", schema=S)
    op.drop_constraint("ck_deck_library_status", "decks", schema=S, type_="check")
    for column in ("basePreconVersionId", "revisionType", "contentHash"):
        op.drop_column("deckVersions", column, schema=S)
    for column in ("sourcePreconId", "sourcePreconVersionId", "libraryStatus", "isPrimaryPreconInstance",
                   "addedToLibraryAt", "currentVersionId"):
        op.drop_column("decks", column, schema=S)
