from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.extensions import db


class Card(db.Model):
    __tablename__ = "cards"
    __table_args__ = {"schema": "mtgCore"}

    id = db.Column(db.BigInteger, primary_key=True)
    uuid = db.Column(db.Text, unique=True, nullable=False, index=True)

    oracleId = db.Column(db.Text, index=True)
    name = db.Column(db.Text, nullable=False, index=True)
    normalizedName = db.Column(db.Text, index=True)
    faceName = db.Column(db.Text)

    manaCost = db.Column(db.Text)
    manaValue = db.Column(db.Numeric, index=True)

    colors = db.Column(db.ARRAY(db.Text))
    colorIdentity = db.Column(db.ARRAY(db.Text))

    typeLine = db.Column(db.Text)
    oracleText = db.Column(db.Text)

    power = db.Column(db.Text)
    toughness = db.Column(db.Text)
    loyalty = db.Column(db.Text)
    defense = db.Column(db.Text)

    layout = db.Column(db.Text)
    side = db.Column(db.Text)

    isToken = db.Column(db.Boolean, default=False)
    isReserved = db.Column(db.Boolean)
    isReprint = db.Column(db.Boolean)

    edhrecRank = db.Column(db.Integer)

    defaultSetCode = db.Column(db.Text, index=True)
    defaultSetName = db.Column(db.Text)
    rarity = db.Column(db.Text)

    availability = db.Column(db.ARRAY(db.Text))
    identifiers = db.Column(JSONB)
    legalities = db.Column(JSONB)
    rawJson = db.Column(JSONB)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updatedAt = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    faces = db.relationship(
        "CardFace",
        back_populates="card",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="CardFace.cardId",
    )

    printings = db.relationship(
        "Printing",
        back_populates="card",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="Printing.cardId",
    )

    productContents = db.relationship(
        "ProductContent",
        back_populates="card",
        lazy=True,
        foreign_keys="ProductContent.cardId",
    )

    roleTags = db.relationship(
        "CardRoleTag",
        back_populates="card",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="CardRoleTag.cardId",
    )

    matchupTags = db.relationship(
        "CardMatchupTag",
        back_populates="card",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="CardMatchupTag.cardId",
    )


class CardFace(db.Model):
    __tablename__ = "cardFaces"
    __table_args__ = {"schema": "mtgCore"}

    id = db.Column(db.BigInteger, primary_key=True)

    cardId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    faceOrder = db.Column(db.Integer, nullable=False)
    name = db.Column(db.Text, nullable=False)
    manaCost = db.Column(db.Text)
    typeLine = db.Column(db.Text)
    oracleText = db.Column(db.Text)

    power = db.Column(db.Text)
    toughness = db.Column(db.Text)
    loyalty = db.Column(db.Text)
    defense = db.Column(db.Text)

    colors = db.Column(db.ARRAY(db.Text))
    identifiers = db.Column(JSONB)
    rawJson = db.Column(JSONB)

    card = db.relationship(
        "Card",
        back_populates="faces",
        lazy=True,
        foreign_keys="CardFace.cardId",
    )


class Set(db.Model):
    __tablename__ = "sets"
    __table_args__ = {"schema": "mtgCore"}

    id = db.Column(db.BigInteger, primary_key=True)
    code = db.Column(db.Text, unique=True, nullable=False, index=True)
    name = db.Column(db.Text, nullable=False, index=True)

    releaseDate = db.Column(db.Date)
    block = db.Column(db.Text)
    setType = db.Column(db.Text, index=True)

    isDigital = db.Column(db.Boolean, default=False)
    totalCards = db.Column(db.Integer)
    tokenCount = db.Column(db.Integer)

    rawJson = db.Column(JSONB)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    printings = db.relationship(
        "Printing",
        back_populates="set",
        lazy=True,
        foreign_keys="Printing.setId",
    )

    products = db.relationship(
        "Product",
        back_populates="set",
        lazy=True,
        foreign_keys="Product.setId",
    )


class Printing(db.Model):
    __tablename__ = "printings"
    __table_args__ = {"schema": "mtgCore"}

    id = db.Column(db.BigInteger, primary_key=True)

    cardId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    setId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    uuid = db.Column(db.Text, unique=True, nullable=False, index=True)
    collectorNumber = db.Column(db.Text)
    rarity = db.Column(db.Text, index=True)

    artist = db.Column(db.Text)
    flavorText = db.Column(db.Text)
    frameVersion = db.Column(db.Text)
    borderColor = db.Column(db.Text)
    language = db.Column(db.Text, default="English")

    isPromo = db.Column(db.Boolean, default=False)
    isFullArt = db.Column(db.Boolean, default=False)

    availability = db.Column(db.ARRAY(db.Text))
    identifiers = db.Column(JSONB)
    rawJson = db.Column(JSONB)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    card = db.relationship(
        "Card",
        back_populates="printings",
        lazy=True,
        foreign_keys="Printing.cardId",
    )

    set = db.relationship(
        "Set",
        back_populates="printings",
        lazy=True,
        foreign_keys="Printing.setId",
    )

    printingImages = db.relationship(
        "PrintingImage",
        back_populates="printing",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="PrintingImage.printingId",
    )


class PrintingImage(db.Model):
    __tablename__ = "printingImages"
    __table_args__ = (
        db.UniqueConstraint(
            "printingId",
            "faceName",
            "imageSize",
            name="uq_printingImages_printing_face_size",
        ),
        db.Index(
            "ix_printingImages_printingId_faceName_imageSize",
            "printingId",
            "faceName",
            "imageSize",
        ),
        {"schema": "mtgCore"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    printingId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.printings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    faceName = db.Column(db.Text, nullable=False, default="front", index=True)
    imageSize = db.Column(db.Text, nullable=False, index=True)  # small, normal, large

    localPath = db.Column(db.Text, nullable=True)
    publicUrl = db.Column(db.Text, nullable=True)
    sourceUrl = db.Column(db.Text, nullable=True)

    status = db.Column(db.Text, nullable=False, default="pending", index=True)
    # pending, cached, missing, failed

    contentType = db.Column(db.Text, nullable=True)
    fileBytes = db.Column(db.BigInteger, nullable=True)

    lastError = db.Column(db.Text, nullable=True)

    lastAttemptedAt = db.Column(db.DateTime(timezone=True), nullable=True)
    downloadedAt = db.Column(db.DateTime(timezone=True), nullable=True)

    createdAt = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updatedAt = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    printing = db.relationship(
        "Printing",
        back_populates="printingImages",
        lazy=True,
        foreign_keys="PrintingImage.printingId",
    )

class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = {"schema": "mtgCore"}

    id = db.Column(db.BigInteger, primary_key=True)
    productCode = db.Column(db.Text, unique=True, index=True)
    name = db.Column(db.Text, nullable=False, index=True)
    productType = db.Column(db.Text, index=True)

    setId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    releaseDate = db.Column(db.Date)
    rawJson = db.Column(JSONB)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    contents = db.relationship(
        "ProductContent",
        back_populates="product",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="ProductContent.productId",
    )

    set = db.relationship(
        "Set",
        back_populates="products",
        lazy=True,
        foreign_keys="Product.setId",
    )


class ProductContent(db.Model):
    __tablename__ = "productContents"
    __table_args__ = (
        db.UniqueConstraint("productId", "cardId", "boardSection", name="uq_productContents_product_card_board"),
        {"schema": "mtgCore"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    productId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cardId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    quantity = db.Column(db.Integer, nullable=False, default=1)
    isCommander = db.Column(db.Boolean, default=False)
    boardSection = db.Column(db.Text, default="main")

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    product = db.relationship(
        "Product",
        back_populates="contents",
        lazy=True,
        foreign_keys="ProductContent.productId",
    )

    card = db.relationship(
        "Card",
        back_populates="productContents",
        lazy=True,
        foreign_keys="ProductContent.cardId",
    )