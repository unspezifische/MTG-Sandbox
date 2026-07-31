from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.extensions import db


class CardRoleTag(db.Model):
    __tablename__ = "cardRoleTags"
    __table_args__ = (
        db.Index("ix_cardRoleTags_cardId_roleType_roleValue", "cardId", "roleType", "roleValue"),
        {"schema": "mtgAnalysis"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    cardId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    roleType = db.Column(db.Text, nullable=False, index=True)
    roleValue = db.Column(db.Text, nullable=False, index=True)
    weight = db.Column(db.Numeric)
    source = db.Column(db.Text, default="manual", index=True)
    confidence = db.Column(db.Numeric)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    card = db.relationship(
        "Card",
        back_populates="roleTags",
        lazy=True,
        foreign_keys="CardRoleTag.cardId",
    )


class CardMatchupTag(db.Model):
    __tablename__ = "cardMatchupTags"
    __table_args__ = (
        db.Index("ix_cardMatchupTags_cardId_relationType_targetTag", "cardId", "relationType", "targetTag"),
        {"schema": "mtgAnalysis"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    cardId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    relationType = db.Column(db.Text, nullable=False, index=True)
    targetTag = db.Column(db.Text, nullable=False, index=True)
    weight = db.Column(db.Numeric)
    source = db.Column(db.Text, default="manual", index=True)
    confidence = db.Column(db.Numeric)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    card = db.relationship(
        "Card",
        back_populates="matchupTags",
        lazy=True,
        foreign_keys="CardMatchupTag.cardId",
    )


class Archetype(db.Model):
    __tablename__ = "archetypes"
    __table_args__ = {"schema": "mtgAnalysis"}

    id = db.Column(db.BigInteger, primary_key=True)

    name = db.Column(db.Text, unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    tagsJson = db.Column(JSONB)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)


class DeckSnapshot(db.Model):
    __tablename__ = "deckSnapshots"
    __table_args__ = {"schema": "mtgAnalysis"}

    id = db.Column(db.BigInteger, primary_key=True)

    deckId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgDecks.decks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deckVersionId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgDecks.deckVersions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    summaryJson = db.Column(JSONB)
    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    deck = db.relationship(
        "Deck",
        back_populates="snapshots",
        lazy=True,
        foreign_keys="DeckSnapshot.deckId",
    )

    deckVersion = db.relationship(
        "DeckVersion",
        back_populates="snapshots",
        lazy=True,
        foreign_keys="DeckSnapshot.deckVersionId",
    )

    metrics = db.relationship(
        "DeckMetric",
        back_populates="deckSnapshot",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="DeckMetric.deckSnapshotId",
    )

    matchupProfiles = db.relationship(
        "DeckMatchupProfile",
        back_populates="deckSnapshot",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="DeckMatchupProfile.deckSnapshotId",
    )


class DeckMetric(db.Model):
    __tablename__ = "deckMetrics"
    __table_args__ = (
        db.Index("ix_deckMetrics_snapshot_metricName", "deckSnapshotId", "metricName"),
        {"schema": "mtgAnalysis"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    deckSnapshotId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgAnalysis.deckSnapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    metricGroup = db.Column(db.Text, index=True)
    metricName = db.Column(db.Text, nullable=False, index=True)

    metricValueNumeric = db.Column(db.Numeric)
    metricValueText = db.Column(db.Text)
    metricValueJson = db.Column(JSONB)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    deckSnapshot = db.relationship(
        "DeckSnapshot",
        back_populates="metrics",
        lazy=True,
        foreign_keys="DeckMetric.deckSnapshotId",
    )


class DeckMatchupProfile(db.Model):
    __tablename__ = "deckMatchupProfiles"
    __table_args__ = (
        db.Index("ix_deckMatchupProfiles_snapshot_archetype", "deckSnapshotId", "archetypeName"),
        {"schema": "mtgAnalysis"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    deckSnapshotId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgAnalysis.deckSnapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    archetypeName = db.Column(db.Text, nullable=False, index=True)
    strengthScore = db.Column(db.Numeric)
    confidence = db.Column(db.Numeric)
    notes = db.Column(db.Text)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    deckSnapshot = db.relationship(
        "DeckSnapshot",
        back_populates="matchupProfiles",
        lazy=True,
        foreign_keys="DeckMatchupProfile.deckSnapshotId",
    )


class SimulationRun(db.Model):
    __tablename__ = "simulationRuns"
    __table_args__ = {"schema": "mtgAnalysis"}

    id = db.Column(db.BigInteger, primary_key=True)

    deckId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgDecks.decks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deckVersionId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgDecks.deckVersions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    runType = db.Column(db.Text, nullable=False, index=True)
    opponentProfile = db.Column(db.Text, index=True)
    simulationCount = db.Column(db.Integer, nullable=False, default=1)

    configJson = db.Column(JSONB)
    resultSummaryJson = db.Column(JSONB)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    deck = db.relationship(
        "Deck",
        back_populates="simulationRuns",
        lazy=True,
        foreign_keys="SimulationRun.deckId",
    )

    deckVersion = db.relationship(
        "DeckVersion",
        back_populates="simulationRuns",
        lazy=True,
        foreign_keys="SimulationRun.deckVersionId",
    )