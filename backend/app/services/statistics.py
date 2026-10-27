"""Database-derived participant statistics. No mutable totals or percentage cache."""
from sqlalchemy import and_, case, func, or_, select, false
from sqlalchemy.orm import aliased

from app.extensions import db
from app.models.mtgDecks import Deck, DeckVersion
from app.models.mtgGames import Game, GamePlayer

COMPETITIVE_MODES = ("pvp", "multiplayer", "one-v-one", "two-headed-giant")
POLICY = dict(competitiveModes=list(COMPETITIVE_MODES), completedStatus="completed",
    winRateDenominator="wins + losses", drawsExcludedFromDenominator=True,
    winRateUnit="percent", libraryMembership="current saved status",
    ambiguousAccountSeats="excluded", unknownHistoricalRevisions="preserved as unknown")


def normalized_result(column):
    value = func.lower(func.trim(func.coalesce(column, "")))
    return case((value.in_(("win", "won", "winner")), "win"),
                (value.in_(("loss", "lost", "lose", "loser")), "loss"),
                (value.in_(("draw", "drawn", "tie")), "draw"), else_=None)


def mode_category():
    opponent = aliased(GamePlayer)
    has_computer = select(opponent.id).where(opponent.gameId == Game.id,
        opponent.playerType == "computer", opponent.deckId.is_not(None)).correlate(Game).exists()
    return case((Game.gameMode == "goldfish", "goldfish"),
        (Game.gameMode == "simulation", "simulation"),
        (or_(Game.gameMode.in_(("pvai", "pv-ai")), has_computer), "pvai"),
        (Game.gameMode.in_(COMPETITIVE_MODES), "competitive"), else_="other")


def participation_query(user_id, *, deck_id=None, library=False):
    """One account's human participation. Never infer an unknown user from a deck."""
    seat = aliased(GamePlayer)
    # A legacy hardcoded account may appear in several human seats. Guessing which
    # seat was the user's would invent a result, so exclude that ambiguous match.
    seats = select(func.count()).select_from(seat).where(seat.gameId == Game.id,
        seat.userId == user_id, seat.playerType == "human",
        or_(seat.deckId.is_not(None), seat.result.is_not(None))).correlate(Game).scalar_subquery()
    version_id = case((DeckVersion.id.is_not(None), GamePlayer.deckVersionId), else_=None)
    query = select(GamePlayer.id.label("participant_id"), Game.id.label("game_id"),
        GamePlayer.deckId.label("deck_id"), version_id.label("revision_id"),
        DeckVersion.revisionType.label("revision_type"), normalized_result(GamePlayer.result).label("result"),
        Game.gameMode.label("mode"), mode_category().label("category"),
        case((Game.turnNumber > 0, Game.turnNumber), else_=None).label("turns"))\
        .select_from(GamePlayer).join(Game, Game.id == GamePlayer.gameId)\
        .outerjoin(Deck, Deck.id == GamePlayer.deckId)\
        .outerjoin(DeckVersion, and_(DeckVersion.id == GamePlayer.deckVersionId, DeckVersion.deckId == GamePlayer.deckId))\
        .where(GamePlayer.userId == user_id, GamePlayer.playerType == "human",
            Game.status == "completed", Game.isInvalidated.is_(False),
            normalized_result(GamePlayer.result).is_not(None), seats == 1)
    if deck_id is not None:
        query = query.where(GamePlayer.deckId == deck_id)
    if library:
        query = query.where(Deck.libraryStatus == "saved", or_(Deck.ownerUserId == user_id, Deck.ownerUserId.is_(None)))
    return query


def totals(rows, *, category=None, mode=None, group=None):
    """Aggregate in SQL; the rows subquery has exactly one unambiguous account seat/game."""
    columns = [func.count().label("gamesPlayed"),
        func.coalesce(func.sum(case((rows.c.result == "win", 1), else_=0)), 0).label("wins"),
        func.coalesce(func.sum(case((rows.c.result == "loss", 1), else_=0)), 0).label("losses"),
        func.coalesce(func.sum(case((rows.c.result == "draw", 1), else_=0)), 0).label("draws"),
        func.avg(rows.c.turns).label("averageTurns")]
    groups = [rows.c[name] for name in (group or ())]
    query = select(*groups, *columns).select_from(rows)
    if category:
        query = query.where(rows.c.category == category)
    if mode:
        query = query.where(rows.c.mode == mode)
    if groups:
        query = query.group_by(*groups)
    def serialize(row):
        data = dict(row)
        for key in ("gamesPlayed", "wins", "losses", "draws"):
            data[key] = int(data[key])
        decided = data["wins"] + data["losses"]
        data["decidedGames"] = decided
        data["winRate"] = round(100 * data["wins"] / decided, 1) if decided else None
        data["averageTurns"] = round(float(data["averageTurns"]), 2) if data["averageTurns"] is not None else None
        return data
    results = [serialize(row) for row in db.session.execute(query).mappings()]
    return results if group else results[0]


def account_statistics(user_id):
    overall = participation_query(user_id).subquery()
    library = participation_query(user_id, library=True).subquery()
    return dict(library=totals(library, category="competitive"),
        overallCompetitive=totals(overall, category="competitive"),
        pvai=totals(overall, category="pvai"),
        byMode=totals(overall, group=("mode", "category")), policy=POLICY)


def deck_summaries(user_id, deck_ids):
    if user_id is None or not deck_ids:
        return {}
    rows = participation_query(user_id).where(GamePlayer.deckId.in_(deck_ids)).subquery()
    return {r.pop("deck_id"): r for r in totals(rows, category="competitive", group=("deck_id",))}


def empty_summary():
    return dict(gamesPlayed=0, wins=0, losses=0, draws=0, decidedGames=0, winRate=None, averageTurns=None)


def deck_statistics(user_id, deck, *, revision="all", selected_ids=None, mode="competitive"):
    base = participation_query(user_id, deck_id=deck.id)
    rows = base.subquery()
    query = base
    if revision == "stock":
        query = query.where(DeckVersion.revisionType == "stock")
    elif revision == "current":
        query = query.where(GamePlayer.deckVersionId == deck.currentVersionId) if deck.currentVersionId else query.where(false())
    elif selected_ids is not None:
        query = query.where(GamePlayer.deckVersionId.in_(selected_ids))
    selected = query.subquery()
    category = mode if mode in ("competitive", "pvai") else None
    raw_mode = mode if mode not in ("competitive", "pvai", "all") else None
    # Scope totals share the same eligibility policy; unknown revisions count only in all.
    stock = base.where(DeckVersion.revisionType == "stock").subquery()
    current = (base.where(GamePlayer.deckVersionId == deck.currentVersionId)
        if deck.currentVersionId else base.where(false())).subquery()
    return dict(deckId=deck.id, libraryStatus=deck.libraryStatus, currentRevisionId=deck.currentVersionId,
        revision=revision, mode=mode, stats=totals(selected, category=category, mode=raw_mode),
        scopes=dict(all=totals(rows, category=category, mode=raw_mode),
                    stock=totals(stock, category=category, mode=raw_mode),
                    current=totals(current, category=category, mode=raw_mode)),
        byMode=totals(selected, group=("mode", "category")),
        revisions=_revision_totals(rows, category=category, mode=raw_mode),
        policy=POLICY)


def _revision_totals(rows, *, category, mode):
    results = totals(rows, category=category, mode=mode, group=("revision_id", "revision_type"))
    for result in results:
        result["revisionId"] = result.pop("revision_id")
        result["revisionType"] = result.pop("revision_type")
        result["configurationKnown"] = result["revisionId"] is not None
    return results
