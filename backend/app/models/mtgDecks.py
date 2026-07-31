from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.extensions import db


class Deck(db.Model):
    __tablename__ = "decks"
    __table_args__ = {"schema": "mtgDecks"}

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.Text, nullable=False, index=True)
    slug = db.Column(db.Text, unique=True, index=True)

    format = db.Column(db.Text, nullable=False, default="commander", index=True)
    commanderCount = db.Column(db.Integer, default=1)
    colorIdentity = db.Column(db.ARRAY(db.Text))

    ownerUserId = db.Column(db.BigInteger, index=True, nullable=True)

    sourceType = db.Column(db.Text, default="custom", index=True)
    sourceProductId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    notes = db.Column(db.Text)
    isPublic = db.Column(db.Boolean, default=False)
    folderName = db.Column(db.Text, nullable=True, index=True)
    commanderBracket = db.Column(db.Integer, nullable=True)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updatedAt = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    lastUsedAt = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    cards = db.relationship(
        "DeckCard",
        back_populates="deck",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="DeckCard.deckId",
    )

    versions = db.relationship(
        "DeckVersion",
        back_populates="deck",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="DeckVersion.deckId",
    )

    snapshots = db.relationship(
        "DeckSnapshot",
        back_populates="deck",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="DeckSnapshot.deckId",
    )

    gamePlayers = db.relationship(
        "GamePlayer",
        back_populates="deck",
        lazy=True,
        foreign_keys="GamePlayer.deckId",
    )
    simulationRuns = db.relationship(
        "SimulationRun",
        back_populates="deck",
        lazy=True,
        foreign_keys="SimulationRun.deckId",
    )

    def __init__(
        self,
        *,
        name,
        slug=None,
        format="commander",
        commanderCount=1,
        colorIdentity=None,
        ownerUserId=None,
        sourceType="custom",
        sourceProductId=None,
        notes=None,
        isPublic=False,
        folderName=None,
        commanderBracket=None,
    ):
        self.name = name
        self.slug = slug
        self.format = format
        self.commanderCount = commanderCount
        self.colorIdentity = colorIdentity if colorIdentity is not None else []
        self.ownerUserId = ownerUserId
        self.sourceType = sourceType
        self.sourceProductId = sourceProductId
        self.notes = notes
        self.isPublic = isPublic
        self.folderName = folderName
        self.commanderBracket = commanderBracket


class DeckCard(db.Model):
    __tablename__ = "deckCards"
    __table_args__ = (
        db.UniqueConstraint("deckId", "cardId", "boardType", name="uq_deckCards_deck_card_board"),
        {"schema": "mtgDecks"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    deckId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgDecks.decks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cardId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preferredPrintingId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.printings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    quantity = db.Column(db.Integer, nullable=False, default=1)
    boardType = db.Column(db.Text, nullable=False, default="main", index=True)
    isCommander = db.Column(db.Boolean, default=False)

    addedAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    deck = db.relationship(
        "Deck",
        back_populates="cards",
        lazy=True,
        foreign_keys="DeckCard.deckId",
    )

    card = db.relationship("Card", lazy=True)
    preferredPrinting = db.relationship("Printing", lazy=True)

    def __init__(
        self,
        *,
        deckId,
        cardId,
        preferredPrintingId=None,
        quantity=1,
        boardType="main",
        isCommander=False,
    ):
        self.deckId = deckId
        self.cardId = cardId
        self.preferredPrintingId = preferredPrintingId
        self.quantity = quantity
        self.boardType = boardType
        self.isCommander = isCommander


class DeckVersion(db.Model):
    __tablename__ = "deckVersions"
    __table_args__ = (
        db.UniqueConstraint("deckId", "versionNumber", name="uq_deckVersions_deck_version"),
        {"schema": "mtgDecks"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    deckId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgDecks.decks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    versionNumber = db.Column(db.Integer, nullable=False)
    label = db.Column(db.Text)
    changeSummary = db.Column(db.Text)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    deck = db.relationship(
        "Deck",
        back_populates="versions",
        lazy=True,
        foreign_keys="DeckVersion.deckId",
    )

    cards = db.relationship(
        "DeckVersionCard",
        back_populates="deckVersion",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="DeckVersionCard.deckVersionId",
    )

    gamePlayers = db.relationship(
        "GamePlayer",
        back_populates="deckVersion",
        lazy=True,
        foreign_keys="GamePlayer.deckVersionId",
    )

    snapshots = db.relationship(
        "DeckSnapshot",
        back_populates="deckVersion",
        lazy=True,
        foreign_keys="DeckSnapshot.deckVersionId",
    )

    simulationRuns = db.relationship(
        "SimulationRun",
        back_populates="deckVersion",
        lazy=True,
        foreign_keys="SimulationRun.deckVersionId",
    )

    def __init__(
        self,
        *,
        deckId,
        versionNumber,
        label=None,
        changeSummary=None,
    ):
        self.deckId = deckId
        self.versionNumber = versionNumber
        self.label = label
        self.changeSummary = changeSummary


class DeckVersionCard(db.Model):
    __tablename__ = "deckVersionCards"
    __table_args__ = (
        db.UniqueConstraint("deckVersionId", "cardId", "boardType", name="uq_deckVersionCards_version_card_board"),
        {"schema": "mtgDecks"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    deckVersionId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgDecks.deckVersions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cardId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preferredPrintingId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.printings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    quantity = db.Column(db.Integer, nullable=False, default=1)
    boardType = db.Column(db.Text, nullable=False, default="main")
    isCommander = db.Column(db.Boolean, default=False)

    deckVersion = db.relationship(
        "DeckVersion",
        back_populates="cards",
        lazy=True,
        foreign_keys="DeckVersionCard.deckVersionId",
    )

    card = db.relationship("Card", lazy=True)
    preferredPrinting = db.relationship("Printing", lazy=True)

    def __init__(
        self,
        *,
        deckVersionId,
        cardId,
        preferredPrintingId=None,
        quantity=1,
        boardType="main",
        isCommander=False,
    ):
        self.deckVersionId = deckVersionId
        self.cardId = cardId
        self.preferredPrintingId = preferredPrintingId
        self.quantity = quantity
        self.boardType = boardType
        self.isCommander = isCommander


class DeckTag(db.Model):
    __tablename__ = "deckTags"
    __table_args__ = (
        db.Index("ix_deckTags_deckId_tagType_tagValue", "deckId", "tagType", "tagValue"),
        {"schema": "mtgDecks"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    deckId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgDecks.decks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tagType = db.Column(db.Text, nullable=False, index=True)
    tagValue = db.Column(db.Text, nullable=False, index=True)
    source = db.Column(db.Text, default="manual")
    confidence = db.Column(db.Numeric)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __init__(
        self,
        *,
        deckId,
        tagType,
        tagValue,
        source="manual",
        confidence=None,
    ):
        self.deckId = deckId
        self.tagType = tagType
        self.tagValue = tagValue
        self.source = source
        self.confidence = confidence


class DeckImport(db.Model):
    __tablename__ = "deckImports"
    __table_args__ = {"schema": "mtgDecks"}

    id = db.Column(db.BigInteger, primary_key=True)

    deckId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgDecks.decks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    importSource = db.Column(db.Text, index=True)
    originalPayload = db.Column(JSONB)
    importedAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __init__(
        self,
        *,
        deckId,
        importSource=None,
        originalPayload=None,
    ):
        self.deckId = deckId
        self.importSource = importSource
        self.originalPayload = originalPayload if originalPayload is not None else {}
