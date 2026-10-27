"""Personal deck identity and immutable versions, sharing existing deck tables.

Routes own transactions. Lock the deck before materialization or revision writes.
"""
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from types import SimpleNamespace

from flask import abort
from sqlalchemy import select, text

from app.auth import check_deck_access, current_user_id
from app.extensions import db
from app.models.mtgDecks import Deck, DeckCard, DeckVersion, DeckVersionCard
from app.models.mtgPrecons import PreconTemplate, PreconTemplateVersion
from app.services.precons import require_playable


def stock_entries(version, deck_id=None):
    """Adapt official boards to existing deck/game conventions without writing rows."""
    require_playable(version)
    groups = {}
    commander_quantities = defaultdict(int)
    for entry in version.cards:
        if entry.board == "commander":
            commander_quantities[entry.provider_uuid] += entry.quantity
    for entry in version.cards:
        if entry.board in ("tokens", "display_commander"):
            continue
        board = {"commander": "command", "side": "sideboard", "planes": "planar"}.get(entry.board, entry.board)
        qty = entry.quantity
        if entry.board == "main":
            qty = max(0, qty - commander_quantities[entry.provider_uuid])
        if not qty:
            continue
        key = (entry.card_id, board)
        if key in groups:
            groups[key].quantity += qty
            continue
        groups[key] = SimpleNamespace(id=f"stock-{entry.id}", deckId=deck_id,
            cardId=entry.card_id, preferredPrintingId=entry.printing_id, quantity=qty,
            boardType=board, isCommander=board == "command", card=entry.card,
            preferredPrinting=entry.printing, addedAt=version.imported_at)
    return list(groups.values())


def revision_entries(version, deck_id=None):
    if version.revisionType == "stock":
        return stock_entries(version.basePreconVersion, deck_id)
    return version.cards


def deck_entries(deck):
    if deck.currentVersion and deck.currentVersion.revisionType == "stock":
        return revision_entries(deck.currentVersion, deck.id)
    return deck.cards


def content_hash(entries):
    content = sorted((c.cardId, c.preferredPrintingId or 0, c.quantity, c.boardType, bool(c.isCommander)) for c in entries)
    return hashlib.sha256(json.dumps(content, separators=(",", ":")).encode()).hexdigest()


def new_version(deck, *, stock=None):
    number = (db.session.scalar(select(db.func.max(DeckVersion.versionNumber)).where(DeckVersion.deckId == deck.id)) or 0) + 1
    version = DeckVersion(deckId=deck.id, versionNumber=number, label="Original precon" if stock else None)
    version.revisionType = "stock" if stock else "custom"
    version.basePreconVersionId = stock.id if stock else deck.sourcePreconVersionId
    entries = stock_entries(stock, deck.id) if stock else list(deck.cards)
    version.contentHash = content_hash(entries)
    db.session.add(version)
    db.session.flush()
    if stock is None:
        for entry in entries:
            db.session.add(DeckVersionCard(deckVersionId=version.id, cardId=entry.cardId,
                preferredPrintingId=entry.preferredPrintingId, quantity=entry.quantity,
                boardType=entry.boardType, isCommander=entry.isCommander))
    return version


def ensure_current_version(deck):
    if deck.currentVersion is None:
        deck.currentVersion = new_version(deck)
        db.session.flush()
    return deck.currentVersion


def owned_deck(deck_id, edit=False):
    deck = db.session.scalar(select(Deck).where(Deck.id == deck_id).with_for_update())
    if deck is None:
        abort(404, description="Deck not found")
    check_deck_access(deck, edit=edit)
    return deck


def prepare_edit(deck):
    """Pin the old custom configuration before changing it; stock copies on write."""
    version = ensure_current_version(deck)
    if version.revisionType == "stock" and not deck.cards:
        for entry in stock_entries(version.basePreconVersion, deck.id):
            db.session.add(DeckCard(deckId=deck.id, cardId=entry.cardId,
                preferredPrintingId=entry.preferredPrintingId, quantity=entry.quantity,
                boardType=entry.boardType, isCommander=entry.isCommander))
        db.session.flush()
        db.session.expire(deck, ["cards"])


def finish_edit(deck):
    db.session.flush()
    db.session.expire(deck, ["cards"])
    entries = list(deck.cards)
    if deck.currentVersion is None or content_hash(entries) != deck.currentVersion.contentHash:
        deck.currentVersion = new_version(deck)
    deck.commanderCount = sum(1 for c in entries if c.isCommander)
    deck.updatedAt = datetime.now(timezone.utc)
    db.session.flush()


def find_entry(deck, entry_id):
    if str(entry_id).startswith("stock-"):
        stock = db.session.get(PreconTemplateVersion, deck.sourcePreconVersionId) if deck.sourcePreconVersionId else None
        original = next((e for e in stock_entries(stock, deck.id) if e.id == entry_id), None) if stock else None
        if original is None:
            return None
        return db.session.scalar(select(DeckCard).filter_by(deckId=deck.id, cardId=original.cardId, boardType=original.boardType))
    try:
        return db.session.scalar(select(DeckCard).filter_by(deckId=deck.id, id=int(entry_id)))
    except (TypeError, ValueError):
        return None


def primary_instance(template_id, *, save):
    uid = current_user_id(required=True)
    if db.session.get_bind().dialect.name == "postgresql":
        # Per-template transaction lock plus a partial unique index protects first creation.
        db.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": template_id})
    template = db.session.get(PreconTemplate, template_id)
    if template is None:
        abort(404, description="Precon not found")
    try:
        require_playable(template.current_version)
    except ValueError as exc:
        abort(409, description=str(exc))
    deck = db.session.scalar(select(Deck).filter_by(ownerUserId=uid, sourcePreconId=template_id,
                                                   isPrimaryPreconInstance=True).with_for_update())
    if deck is None:
        try:
            stock = require_playable(template.current_version)
        except ValueError as exc:
            abort(409, description=str(exc))
        deck = Deck(name=template.name, format=template.format or "none", ownerUserId=uid, sourceType="precon")
        deck.sourcePreconId = template.id
        deck.sourcePreconVersionId = stock.id
        deck.libraryStatus = "saved" if save else "unlisted"
        deck.isPrimaryPreconInstance = True
        db.session.add(deck)
        db.session.flush()
        deck.currentVersion = new_version(deck, stock=stock)
        deck.commanderCount = sum(c.isCommander for c in stock_entries(stock))
    if save:
        deck.libraryStatus = "saved"
        deck.addedToLibraryAt = deck.addedToLibraryAt or datetime.now(timezone.utc)
    db.session.flush()
    return deck


def select_revision(deck, selection=None):
    """Resolve user selection to an owned immutable version before gameplay."""
    check_deck_access(deck)
    current = ensure_current_version(deck)
    if selection == "stock":
        version = db.session.scalar(select(DeckVersion).filter_by(deckId=deck.id, revisionType="stock",
            basePreconVersionId=deck.sourcePreconVersionId)) if deck.sourcePreconVersionId else None
        if version is None:
            abort(400, description="This deck has no original precon")
    elif selection in (None, "", "current"):
        version = current
    else:
        try:
            version = db.session.get(DeckVersion, int(selection))
        except (ValueError, TypeError):
            abort(400, description="Invalid deck revision")
        if version is None or version.deckId != deck.id:
            abort(404, description="Deck revision not found")
    if version.revisionType == "stock":
        try:
            require_playable(version.basePreconVersion)
        except ValueError as exc:
            abort(409, description=str(exc))
    return version


def source_summary(deck):
    if not deck.sourcePreconId:
        return None
    stock = db.session.get(PreconTemplateVersion, deck.sourcePreconVersionId)
    original = stock_entries(stock, deck.id)
    def counts(entries):
        result = defaultdict(int)
        for c in entries:
            result[(c.cardId, c.boardType, bool(c.isCommander))] += c.quantity
        return result
    before, after = counts(original), counts(deck_entries(deck))
    added = sum(max(0, after[k] - before[k]) for k in after.keys() | before.keys())
    removed = sum(max(0, before[k] - after[k]) for k in after.keys() | before.keys())
    return dict(id=deck.sourcePreconId, name=deck.sourcePrecon.name,
        versionId=stock.id, originalCommanders=[e.card.name for e in original if e.isCommander],
        modifications=dict(added=added, removed=removed))
