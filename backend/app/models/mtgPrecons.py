"""Shared catalog snapshots; deliberately independent of personal decks."""
from sqlalchemy.sql import func
from app.extensions import db

ID = db.BigInteger().with_variant(db.Integer, "sqlite")
SCHEMA = "mtgDecks"


class PreconTemplate(db.Model):
    __tablename__ = "precon_templates"
    __table_args__ = (db.UniqueConstraint("provider", "external_key"), {"schema": SCHEMA})
    id = db.Column(ID, primary_key=True)
    provider = db.Column(db.Text, nullable=False, default="mtgjson")
    external_key = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text, nullable=False, index=True)
    set_code = db.Column(db.Text, nullable=False, index=True)
    deck_type = db.Column(db.Text, nullable=False)
    format = db.Column(db.Text, index=True)
    release_date = db.Column(db.Date, index=True)
    sealed_product_ids = db.Column(db.JSON, nullable=False, default=list)
    source_metadata = db.Column("metadata", db.JSON, nullable=False, default=dict)
    current_version_id = db.Column(ID, db.ForeignKey(
        "mtgDecks.precon_template_versions.id", name="fk_precon_current_version", use_alter=True))
    current_version = db.relationship("PreconTemplateVersion", foreign_keys=[current_version_id], post_update=True)


class PreconAlias(db.Model):
    __tablename__ = "precon_template_aliases"
    __table_args__ = (db.UniqueConstraint("provider", "external_key"), {"schema": SCHEMA})
    id = db.Column(ID, primary_key=True)
    provider = db.Column(db.Text, nullable=False)
    external_key = db.Column(db.Text, nullable=False)
    template_id = db.Column(ID, db.ForeignKey("mtgDecks.precon_templates.id"), nullable=False, index=True)


class PreconTemplateVersion(db.Model):
    __tablename__ = "precon_template_versions"
    __table_args__ = (db.UniqueConstraint("template_id", "checksum"), {"schema": SCHEMA})
    id = db.Column(ID, primary_key=True)
    template_id = db.Column(ID, db.ForeignKey("mtgDecks.precon_templates.id"), nullable=False, index=True)
    checksum = db.Column(db.String(64), nullable=False)
    imported_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    provider_metadata = db.Column(db.JSON, nullable=False)
    status = db.Column(db.Text, nullable=False)
    issues = db.Column(db.JSON, nullable=False, default=list)
    cards = db.relationship("PreconTemplateCard", lazy="select", order_by="PreconTemplateCard.id")


class PreconTemplateCard(db.Model):
    __tablename__ = "precon_template_cards"
    __table_args__ = (db.CheckConstraint("quantity > 0", name="ck_precon_quantity"), {"schema": SCHEMA})
    id = db.Column(ID, primary_key=True)
    version_id = db.Column(ID, db.ForeignKey("mtgDecks.precon_template_versions.id"), nullable=False, index=True)
    card_id = db.Column(db.BigInteger, db.ForeignKey("mtgCore.cards.id"), index=True)
    printing_id = db.Column(db.BigInteger, db.ForeignKey("mtgCore.printings.id"))
    provider_uuid = db.Column(db.Text, nullable=False, index=True)
    name = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    board = db.Column(db.Text, nullable=False)
    is_commander = db.Column(db.Boolean, nullable=False, default=False)
    source_metadata = db.Column(db.JSON, nullable=False)
    card = db.relationship("Card")
    printing = db.relationship("Printing")
