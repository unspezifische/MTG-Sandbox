from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.extensions import db


class Game(db.Model):
    __tablename__ = "games"
    __table_args__ = {"schema": "mtgGames"}

    id = db.Column(db.BigInteger, primary_key=True)

    parentGameId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.games.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parentSnapshotId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.stateSnapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    branchedFromSequence = db.Column(db.BigInteger, nullable=True)
    rootGameId = db.Column(db.BigInteger, nullable=True, index=True)

    gameMode = db.Column(db.Text, nullable=False, default="goldfish", index=True)
    format = db.Column(db.Text, nullable=False, default="commander", index=True)
    status = db.Column(db.Text, nullable=False, default="pending", index=True)
    lobbyName = db.Column(db.Text, index=True)
    ruleset = db.Column(db.Text, nullable=False, default="casual", index=True)
    maxPlayers = db.Column(db.Integer, nullable=False, default=4)
    passwordHash = db.Column(db.Text)
    hostUserId = db.Column(db.BigInteger, nullable=True, index=True)
    turnNumber = db.Column(db.Integer, nullable=False, default=1)
    activeSeatNumber = db.Column(db.Integer, nullable=False, default=1)

    rngSeed = db.Column(db.Text)
    engineVersion = db.Column(db.Text)
    rulesVersion = db.Column(db.Text)

    startedAt = db.Column(db.DateTime(timezone=True))
    endedAt = db.Column(db.DateTime(timezone=True))

    winnerGamePlayerId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.gamePlayers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    notes = db.Column(db.Text)
    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    parentGame = db.relationship(
        "Game",
        remote_side="Game.id",
        back_populates="childGames",
        lazy=True,
        foreign_keys="Game.parentGameId",
    )

    childGames = db.relationship(
        "Game",
        back_populates="parentGame",
        lazy=True,
        foreign_keys="Game.parentGameId",
    )

    players = db.relationship(
        "GamePlayer",
        back_populates="game",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="GamePlayer.gameId",
    )

    winnerGamePlayer = db.relationship(
        "GamePlayer",
        back_populates="wonGames",
        lazy=True,
        foreign_keys="Game.winnerGamePlayerId",
        post_update=True,
    )

    cardInstances = db.relationship(
        "CardInstance",
        back_populates="game",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="CardInstance.gameId",
    )

    events = db.relationship(
        "GameEvent",
        back_populates="game",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="GameEvent.gameId",
    )

    snapshots = db.relationship(
        "StateSnapshot",
        back_populates="game",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="StateSnapshot.gameId",
    )

    decisions = db.relationship(
        "GameDecision",
        back_populates="game",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="GameDecision.gameId",
    )

    branches = db.relationship(
        "GameBranch",
        back_populates="parentGame",
        lazy=True,
        foreign_keys="GameBranch.parentGameId",
        cascade="all, delete-orphan",
    )

    incomingBranch = db.relationship(
        "GameBranch",
        back_populates="childGame",
        lazy=True,
        uselist=False,
        foreign_keys="GameBranch.childGameId",
    )

    def __init__(
        self,
        *,
        parentGameId=None,
        parentSnapshotId=None,
        branchedFromSequence=None,
        rootGameId=None,
        gameMode="goldfish",
        format="commander",
        status="pending",
        lobbyName=None,
        ruleset="casual",
        maxPlayers=4,
        passwordHash=None,
        hostUserId=None,
        turnNumber=1,
        activeSeatNumber=1,
        rngSeed=None,
        engineVersion=None,
        rulesVersion=None,
        startedAt=None,
        endedAt=None,
        winnerGamePlayerId=None,
        notes=None,
    ):
        self.parentGameId = parentGameId
        self.parentSnapshotId = parentSnapshotId
        self.branchedFromSequence = branchedFromSequence
        self.rootGameId = rootGameId
        self.gameMode = gameMode
        self.format = format
        self.status = status
        self.lobbyName = lobbyName
        self.ruleset = ruleset
        self.maxPlayers = maxPlayers
        self.passwordHash = passwordHash
        self.hostUserId = hostUserId
        self.turnNumber = turnNumber
        self.activeSeatNumber = activeSeatNumber
        self.rngSeed = rngSeed
        self.engineVersion = engineVersion
        self.rulesVersion = rulesVersion
        self.startedAt = startedAt
        self.endedAt = endedAt
        self.winnerGamePlayerId = winnerGamePlayerId
        self.notes = notes

class GamePlayer(db.Model):
    __tablename__ = "gamePlayers"
    __table_args__ = (
        db.UniqueConstraint("gameId", "seatNumber", name="uq_gamePlayers_game_seat"),
        {"schema": "mtgGames"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    gameId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    seatNumber = db.Column(db.Integer, nullable=False)
    playerType = db.Column(db.Text, nullable=False, default="human", index=True)

    userId = db.Column(db.BigInteger, nullable=True, index=True)
    aiProfile = db.Column(db.Text, nullable=True, index=True)

    deckId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgDecks.decks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    deckVersionId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgDecks.deckVersions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    startingLife = db.Column(db.Integer, default=40)
    startingHandSize = db.Column(db.Integer, default=7)
    isReady = db.Column(db.Boolean, nullable=False, default=False)
    isHost = db.Column(db.Boolean, nullable=False, default=False)
    lobbyTokenHash = db.Column(db.Text)
    isConnected = db.Column(db.Boolean, nullable=False, default=False)
    disconnectedAt = db.Column(db.DateTime(timezone=True))
    sleeveStyle = db.Column(db.Text, nullable=False, default="classic")

    finalPlacement = db.Column(db.Integer)
    result = db.Column(db.Text, index=True)

    commanderCastCount = db.Column(db.Integer, default=0)
    commanderDamageDealt = db.Column(db.Integer, default=0)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    game = db.relationship(
        "Game",
        back_populates="players",
        lazy=True,
        foreign_keys="GamePlayer.gameId",
    )

    wonGames = db.relationship(
        "Game",
        back_populates="winnerGamePlayer",
        lazy=True,
        foreign_keys="Game.winnerGamePlayerId",
    )

    deck = db.relationship(
        "Deck",
        back_populates="gamePlayers",
        lazy=True,
        foreign_keys="GamePlayer.deckId",
    )

    deckVersion = db.relationship(
        "DeckVersion",
        back_populates="gamePlayers",
        lazy=True,
        foreign_keys="GamePlayer.deckVersionId",
    )

    libraryOrders = db.relationship(
        "GamePlayerLibrary",
        back_populates="gamePlayer",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="GamePlayerLibrary.gamePlayerId",
    )

    decisions = db.relationship(
        "GameDecision",
        back_populates="gamePlayer",
        lazy=True,
        foreign_keys="GameDecision.gamePlayerId",
    )

    events = db.relationship(
        "GameEvent",
        back_populates="actingGamePlayer",
        lazy=True,
        foreign_keys="GameEvent.actingGamePlayerId",
    )

    cardInstances = db.relationship(
        "CardInstance",
        back_populates="gamePlayer",
        lazy=True,
        foreign_keys="CardInstance.gamePlayerId",
    )

    def __init__(
        self,
        *,
        gameId,
        seatNumber,
        playerType="human",
        userId=None,
        aiProfile=None,
        deckId=None,
        deckVersionId=None,
        startingLife=40,
        startingHandSize=7,
        isReady=False,
        isHost=False,
        lobbyTokenHash=None,
        isConnected=False,
        disconnectedAt=None,
        sleeveStyle="classic",
        finalPlacement=None,
        result=None,
        commanderCastCount=0,
        commanderDamageDealt=0,
    ):
        self.gameId = gameId
        self.seatNumber = seatNumber
        self.playerType = playerType
        self.userId = userId
        self.aiProfile = aiProfile
        self.deckId = deckId
        self.deckVersionId = deckVersionId
        self.startingLife = startingLife
        self.startingHandSize = startingHandSize
        self.isReady = isReady
        self.isHost = isHost
        self.lobbyTokenHash = lobbyTokenHash
        self.isConnected = isConnected
        self.disconnectedAt = disconnectedAt
        self.sleeveStyle = sleeveStyle
        self.finalPlacement = finalPlacement
        self.result = result
        self.commanderCastCount = commanderCastCount
        self.commanderDamageDealt = commanderDamageDealt


class CardInstance(db.Model):
    __tablename__ = "cardInstances"
    __table_args__ = {"schema": "mtgGames"}

    id = db.Column(db.BigInteger, primary_key=True)

    gameId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gamePlayerId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.gamePlayers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    cardId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.cards.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    printingId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgCore.printings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    sourceDeckCardId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgDecks.deckCards.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    instanceType = db.Column(db.Text, nullable=False, default="deckCard", index=True)
    createdByEventId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    zone = db.Column(db.Text, nullable=False, default="library", index=True)
    zoneIndex = db.Column(db.Integer, nullable=True)
    isCommander = db.Column(db.Boolean, nullable=False, default=False)

    isTapped = db.Column(db.Boolean, nullable=False, default=False)
    rotationDeg = db.Column(db.Integer, nullable=False, default=0)

    isFaceDown = db.Column(db.Boolean, nullable=False, default=False)
    displayFace = db.Column(db.Text, nullable=True, default="front")

    battlefieldX = db.Column(db.Numeric, nullable=True)
    battlefieldY = db.Column(db.Numeric, nullable=True)
    stackIndex = db.Column(db.Integer, nullable=True)

    metadataJson = db.Column(JSONB)
    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    game = db.relationship(
        "Game",
        back_populates="cardInstances",
        lazy=True,
        foreign_keys="CardInstance.gameId",
    )

    gamePlayer = db.relationship(
        "GamePlayer",
        back_populates="cardInstances",
        lazy=True,
        foreign_keys="CardInstance.gamePlayerId",
    )

    createdByEvent = db.relationship(
        "GameEvent",
        back_populates="createdCardInstances",
        lazy=True,
        foreign_keys="CardInstance.createdByEventId",
    )

    card = db.relationship("Card", lazy=True)
    printing = db.relationship("Printing", lazy=True)
    sourceDeckCard = db.relationship("DeckCard", lazy=True)

    def __init__(
        self,
        *,
        gameId,
        gamePlayerId=None,
        cardId=None,
        printingId=None,
        sourceDeckCardId=None,
        instanceType="deckCard",
        createdByEventId=None,
        zone="library",
        zoneIndex=None,
        isCommander=False,
        isTapped=False,
        rotationDeg=0,
        isFaceDown=False,
        displayFace="front",
        battlefieldX=None,
        battlefieldY=None,
        stackIndex=None,
        metadataJson=None,
    ):
        self.gameId = gameId
        self.gamePlayerId = gamePlayerId
        self.cardId = cardId
        self.printingId = printingId
        self.sourceDeckCardId = sourceDeckCardId
        self.instanceType = instanceType
        self.createdByEventId = createdByEventId
        self.zone = zone
        self.zoneIndex = zoneIndex
        self.isCommander = isCommander
        self.isTapped = isTapped
        self.rotationDeg = rotationDeg
        self.isFaceDown = isFaceDown
        self.displayFace = displayFace
        self.battlefieldX = battlefieldX
        self.battlefieldY = battlefieldY
        self.stackIndex = stackIndex
        self.metadataJson = metadataJson if metadataJson is not None else {}

class GameEvent(db.Model):
    __tablename__ = "events"
    __table_args__ = (
        db.UniqueConstraint("gameId", "sequenceNumber", name="uq_events_game_sequence"),
        {"schema": "mtgGames"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    gameId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sequenceNumber = db.Column(db.BigInteger, nullable=False)
    turnNumber = db.Column(db.Integer, index=True)
    phase = db.Column(db.Text, index=True)
    step = db.Column(db.Text, index=True)

    actingGamePlayerId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.gamePlayers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    eventType = db.Column(db.Text, nullable=False, index=True)
    visibilityScope = db.Column(db.Text, default="public", index=True)

    payloadJson = db.Column(JSONB, nullable=False)
    publicText = db.Column(db.Text)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    game = db.relationship(
        "Game",
        back_populates="events",
        lazy=True,
        foreign_keys="GameEvent.gameId",
    )

    actingGamePlayer = db.relationship(
        "GamePlayer",
        back_populates="events",
        lazy=True,
        foreign_keys="GameEvent.actingGamePlayerId",
    )

    createdCardInstances = db.relationship(
        "CardInstance",
        back_populates="createdByEvent",
        lazy=True,
        foreign_keys="CardInstance.createdByEventId",
    )

    decisionActions = db.relationship(
        "GameDecision",
        back_populates="actionTakenEvent",
        lazy=True,
        foreign_keys="GameDecision.actionTakenEventId",
    )

    def __init__(
        self,
        *,
        gameId,
        sequenceNumber,
        eventType,
        payloadJson,
        turnNumber=None,
        phase=None,
        step=None,
        actingGamePlayerId=None,
        visibilityScope="public",
        publicText=None,
    ):
        self.gameId = gameId
        self.sequenceNumber = sequenceNumber
        self.turnNumber = turnNumber
        self.phase = phase
        self.step = step
        self.actingGamePlayerId = actingGamePlayerId
        self.eventType = eventType
        self.visibilityScope = visibilityScope
        self.payloadJson = payloadJson
        self.publicText = publicText

class StateSnapshot(db.Model):
    __tablename__ = "stateSnapshots"
    __table_args__ = (
        db.Index("ix_stateSnapshots_gameId_sequenceNumber", "gameId", "sequenceNumber"),
        {"schema": "mtgGames"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    gameId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sequenceNumber = db.Column(db.BigInteger, nullable=False)
    turnNumber = db.Column(db.Integer, index=True)
    phase = db.Column(db.Text, index=True)

    stateJson = db.Column(JSONB, nullable=False)
    snapshotHash = db.Column(db.Text, index=True)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    game = db.relationship(
        "Game",
        back_populates="snapshots",
        lazy=True,
        foreign_keys="StateSnapshot.gameId",
    )

    decisions = db.relationship(
        "GameDecision",
        back_populates="snapshot",
        lazy=True,
        foreign_keys="GameDecision.snapshotId",
    )

    branchesFromSnapshot = db.relationship(
        "GameBranch",
        back_populates="parentSnapshot",
        lazy=True,
        foreign_keys="GameBranch.parentSnapshotId",
    )

    def __init__(
        self,
        *,
        gameId,
        sequenceNumber,
        stateJson,
        turnNumber=None,
        phase=None,
        snapshotHash=None,
    ):
        self.gameId = gameId
        self.sequenceNumber = sequenceNumber
        self.turnNumber = turnNumber
        self.phase = phase
        self.stateJson = stateJson
        self.snapshotHash = snapshotHash


class GameDecision(db.Model):
    __tablename__ = "decisions"
    __table_args__ = (
        db.Index("ix_decisions_gameId_sequenceNumber", "gameId", "sequenceNumber"),
        {"schema": "mtgGames"},
    )

    id = db.Column(db.BigInteger, primary_key=True)

    gameId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gamePlayerId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.gamePlayers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshotId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.stateSnapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    sequenceNumber = db.Column(db.BigInteger, nullable=False)
    decisionType = db.Column(db.Text, nullable=False, index=True)

    stateFeaturesJson = db.Column(JSONB)
    legalActionsJson = db.Column(JSONB)
    chosenActionJson = db.Column(JSONB)

    actionTakenEventId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    decisionSource = db.Column(db.Text, nullable=False, default="human", index=True)
    timeTakenMs = db.Column(db.Integer)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    game = db.relationship(
        "Game",
        back_populates="decisions",
        lazy=True,
        foreign_keys="GameDecision.gameId",
    )

    gamePlayer = db.relationship(
        "GamePlayer",
        back_populates="decisions",
        lazy=True,
        foreign_keys="GameDecision.gamePlayerId",
    )

    snapshot = db.relationship(
        "StateSnapshot",
        back_populates="decisions",
        lazy=True,
        foreign_keys="GameDecision.snapshotId",
    )

    actionTakenEvent = db.relationship(
        "GameEvent",
        back_populates="decisionActions",
        lazy=True,
        foreign_keys="GameDecision.actionTakenEventId",
    )

    def __init__(
        self,
        *,
        gameId,
        gamePlayerId,
        sequenceNumber,
        decisionType,
        snapshotId=None,
        stateFeaturesJson=None,
        legalActionsJson=None,
        chosenActionJson=None,
        actionTakenEventId=None,
        decisionSource="human",
        timeTakenMs=None,
    ):
        self.gameId = gameId
        self.gamePlayerId = gamePlayerId
        self.snapshotId = snapshotId
        self.sequenceNumber = sequenceNumber
        self.decisionType = decisionType
        self.stateFeaturesJson = stateFeaturesJson if stateFeaturesJson is not None else {}
        self.legalActionsJson = legalActionsJson if legalActionsJson is not None else {}
        self.chosenActionJson = chosenActionJson
        self.actionTakenEventId = actionTakenEventId
        self.decisionSource = decisionSource
        self.timeTakenMs = timeTakenMs

class GamePlayerLibrary(db.Model):
    __tablename__ = "gamePlayerLibraries"
    __table_args__ = {"schema": "mtgGames"}

    id = db.Column(db.BigInteger, primary_key=True)

    gamePlayerId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.gamePlayers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    zoneScope = db.Column(db.Text, nullable=False, default="initialLibrary", index=True)
    orderedCardInstanceIds = db.Column(JSONB, nullable=False)

    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    gamePlayer = db.relationship(
        "GamePlayer",
        back_populates="libraryOrders",
        lazy=True,
        foreign_keys="GamePlayerLibrary.gamePlayerId",
    )

    def __init__(
        self,
        *,
        gamePlayerId,
        orderedCardInstanceIds,
        zoneScope="initialLibrary",
    ):
        self.gamePlayerId = gamePlayerId
        self.zoneScope = zoneScope
        self.orderedCardInstanceIds = orderedCardInstanceIds


class GameBranch(db.Model):
    __tablename__ = "branches"
    __table_args__ = {"schema": "mtgGames"}

    id = db.Column(db.BigInteger, primary_key=True)

    parentGameId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    childGameId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.games.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    parentSnapshotId = db.Column(
        db.BigInteger,
        db.ForeignKey("mtgGames.stateSnapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    branchLabel = db.Column(db.Text)
    branchReason = db.Column(db.Text)

    createdByUserId = db.Column(db.BigInteger, nullable=True, index=True)
    createdAt = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    parentGame = db.relationship(
        "Game",
        back_populates="branches",
        lazy=True,
        foreign_keys="GameBranch.parentGameId",
    )

    childGame = db.relationship(
        "Game",
        back_populates="incomingBranch",
        lazy=True,
        foreign_keys="GameBranch.childGameId",
    )

    parentSnapshot = db.relationship(
        "StateSnapshot",
        back_populates="branchesFromSnapshot",
        lazy=True,
        foreign_keys="GameBranch.parentSnapshotId",
    )

    def __init__(
        self,
        *,
        parentGameId,
        childGameId,
        parentSnapshotId=None,
        branchLabel=None,
        branchReason=None,
        createdByUserId=None,
    ):
        self.parentGameId = parentGameId
        self.childGameId = childGameId
        self.parentSnapshotId = parentSnapshotId
        self.branchLabel = branchLabel
        self.branchReason = branchReason
        self.createdByUserId = createdByUserId
