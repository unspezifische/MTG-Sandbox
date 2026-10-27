"""Account-scoped history and derived statistics."""
from flask import Blueprint, jsonify, request
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.auth import current_user_id
from app.extensions import db
from app.models.mtgDecks import DeckVersion
from app.models.mtgGames import Game, GamePlayer
from app.services.deck_identity import owned_deck
from app.services.statistics import account_statistics, deck_statistics, COMPETITIVE_MODES

statistics_bp = Blueprint("statistics", __name__, url_prefix="/api")


@statistics_bp.get("/profile/stats")
def profile_stats():
    return jsonify(account_statistics(current_user_id(required=True)))


@statistics_bp.get("/decks/<int:deck_id>/stats")
def deck_stats(deck_id):
    uid = current_user_id(required=True)
    deck = owned_deck(deck_id)
    revision = request.args.get("revision", "all")
    mode = request.args.get("mode", "competitive")
    if mode not in {"competitive", "pvai", "all", "goldfish", "simulation", "pv-ai", *COMPETITIVE_MODES}:
        return jsonify(error="Unsupported statistics mode"), 400
    ids = None
    if revision not in {"all", "stock", "current"}:
        try:
            ids = [int(value) for value in revision.split(",")]
            if not ids or len(ids) > 100 or min(ids) <= 0:
                raise ValueError()
        except ValueError:
            return jsonify(error="revision must be all, stock, current, or up to 100 revision IDs"), 400
        found = set(db.session.scalars(select(DeckVersion.id).where(DeckVersion.deckId == deck.id, DeckVersion.id.in_(ids))))
        if found != set(ids):
            return jsonify(error="Deck revision not found"), 404
    return jsonify(deck_statistics(uid, deck, revision=revision, selected_ids=ids, mode=mode))


@statistics_bp.get("/profile/history")
def profile_history():
    uid = current_user_id(required=True)
    try:
        limit = int(request.args.get("limit", 25)); offset = int(request.args.get("offset", 0))
        if not 1 <= limit <= 100 or not 0 <= offset <= 2_147_483_647:
            raise ValueError()
    except ValueError:
        return jsonify(error="limit must be 1–100 and offset must be nonnegative"), 400
    query = select(Game).where(select(GamePlayer.id).where(GamePlayer.gameId == Game.id,
        GamePlayer.userId == uid, GamePlayer.playerType == "human").exists())
    status = request.args.get("status")
    if status:
        query = query.where(Game.status == status)
    total = db.session.scalar(select(func.count()).select_from(query.subquery()))
    games = db.session.scalars(query.options(selectinload(Game.players).selectinload(GamePlayer.deck),
        selectinload(Game.players).selectinload(GamePlayer.deckVersion))
        .order_by(Game.createdAt.desc(), Game.id.desc()).limit(limit).offset(offset)).all()
    from app.routes import serialize_game
    result = []
    for game in games:
        data = serialize_game(game, include_players=True, include_snapshot=False)
        participants = [p for p in game.players if p.userId == uid and p.playerType == "human"]
        data["myParticipations"] = [dict(gamePlayerId=p.id, deckId=p.deckId,
            revisionId=p.deckVersionId, configurationKnown=bool(p.deckVersion and p.deckVersion.deckId == p.deckId), result=p.result,
            revisionType=p.deckVersion.revisionType if p.deckVersion and p.deckVersion.deckId == p.deckId else "unknown",
            deckName=p.deck.name if p.deck else None,
            libraryStatus=p.deck.libraryStatus if p.deck else None) for p in participants]
        result.append(data)
    return jsonify(games=result, total=total, limit=limit, offset=offset)
