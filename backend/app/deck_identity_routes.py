"""Personal instances and immutable revisions; existing Deck Builder remains the editor."""
from flask import Blueprint, jsonify, request
from sqlalchemy import select

from app.extensions import db
from app.models.mtgDecks import DeckVersion
from app.services.deck_identity import (primary_instance, owned_deck, select_revision,
    revision_entries)

deck_identity_bp = Blueprint("deck_identity", __name__, url_prefix="/api")


@deck_identity_bp.post("/precons/<int:template_id>/save")
def save_precon(template_id):
    from app.routes import serialize_deck
    deck = primary_instance(template_id, save=True)
    db.session.commit()
    return jsonify(serialize_deck(deck, include_cards=True))


@deck_identity_bp.post("/precons/<int:template_id>/play")
def play_precon(template_id):
    from app.routes import serialize_deck
    deck = primary_instance(template_id, save=False)
    version = select_revision(deck, "stock")
    db.session.commit()
    return jsonify(deck=serialize_deck(deck), deckId=deck.id,
                   revisionId=version.id, deckVersionId=version.id)


def version_summary(v):
    return dict(id=v.id, deckId=v.deckId, revisionNumber=v.versionNumber,
        revisionType=v.revisionType, basePreconVersionId=v.basePreconVersionId,
        contentHash=v.contentHash, createdAt=v.createdAt.isoformat() if v.createdAt else None)


@deck_identity_bp.get("/decks/<int:deck_id>/revisions")
def list_revisions(deck_id):
    deck = owned_deck(deck_id)
    versions = db.session.scalars(select(DeckVersion).where(DeckVersion.deckId == deck.id)
                                  .order_by(DeckVersion.versionNumber.desc())).all()
    return jsonify(revisions=[version_summary(v) for v in versions], currentRevisionId=deck.currentVersionId)


@deck_identity_bp.get("/decks/<int:deck_id>/revisions/<int:revision_id>")
def get_revision(deck_id, revision_id):
    from app.routes import serialize_card_summary
    deck = owned_deck(deck_id)
    version = db.session.get(DeckVersion, revision_id)
    if version is None or version.deckId != deck.id:
        return jsonify(error="Deck revision not found"), 404
    data = version_summary(version)
    data["cards"] = [dict(cardId=e.cardId, preferredPrintingId=e.preferredPrintingId,
        quantity=e.quantity, boardType=e.boardType, isCommander=e.isCommander,
        card=serialize_card_summary(e.card)) for e in revision_entries(version, deck.id)]
    return jsonify(data)


@deck_identity_bp.post("/decks/<int:deck_id>/play")
def play_deck(deck_id):
    deck = owned_deck(deck_id)
    version = select_revision(deck, (request.get_json(silent=True) or {}).get("revision"))
    db.session.commit()
    return jsonify(deckId=deck.id, revisionId=version.id, deckVersionId=version.id)


@deck_identity_bp.post("/decks/<int:deck_id>/restore")
def restore_deck(deck_id):
    from app.routes import serialize_deck
    from datetime import datetime, timezone
    deck = owned_deck(deck_id)
    deck.libraryStatus = "saved"
    deck.addedToLibraryAt = deck.addedToLibraryAt or datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(serialize_deck(deck))


@deck_identity_bp.post("/decks/<int:deck_id>/duplicate")
def duplicate_deck(deck_id):
    from app.auth import current_user_id
    from app.models.mtgDecks import Deck, DeckCard, DeckTokenPreference
    from app.services.deck_identity import new_version, deck_entries
    from app.routes import serialize_deck
    from datetime import datetime, timezone
    source = owned_deck(deck_id)
    uid = current_user_id(required=True)
    clone = Deck(name=f"{source.name} (copy)", ownerUserId=uid, format=source.format,
        sourceType=source.sourceType, sourceProductId=source.sourceProductId, notes=source.notes,
        commanderCount=source.commanderCount)
    clone.sourcePreconId = source.sourcePreconId
    clone.sourcePreconVersionId = source.sourcePreconVersionId
    clone.libraryStatus = "saved"
    clone.addedToLibraryAt = datetime.now(timezone.utc)
    db.session.add(clone); db.session.flush()
    if source.sourcePreconVersionId:
        from app.models.mtgPrecons import PreconTemplateVersion
        stock = db.session.get(PreconTemplateVersion, source.sourcePreconVersionId)
        clone.currentVersion = new_version(clone, stock=stock)
    if not source.currentVersion or source.currentVersion.revisionType != "stock":
        for e in deck_entries(source):
            db.session.add(DeckCard(deckId=clone.id, cardId=e.cardId, quantity=e.quantity,
                preferredPrintingId=e.preferredPrintingId, boardType=e.boardType, isCommander=e.isCommander))
        db.session.flush(); db.session.expire(clone, ["cards"])
        clone.currentVersion = new_version(clone)
    for preference in source.tokenPreferences or []:
        db.session.add(DeckTokenPreference(
            deckId=clone.id,
            tokenOracleId=preference.tokenOracleId,
            preferredPrintingId=preference.preferredPrintingId,
        ))
    db.session.commit()
    return jsonify(serialize_deck(clone, include_cards=True)), 201
