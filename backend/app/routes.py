from __future__ import annotations

import os
import random
import re
import secrets

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, cast

from flask import Blueprint, current_app, jsonify, request
from flask_socketio import emit, join_room
import requests
from sqlalchemy import case, func, or_, nullslast
from sqlalchemy.orm import selectinload
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, socketio
from .models.mtgCore import Card, Printing, PrintingImage, Set
from .models.mtgDecks import Deck, DeckCard
from .models.mtgGames import Game, GamePlayer, CardInstance, GameEvent, StateSnapshot

api_bp = Blueprint("api", __name__, url_prefix="/api")

ZONE_ORDER = ["library", "hand", "battlefield", "graveyard", "exile", "command", "stack"]
PREFERRED_IMAGE_FACES = ["front", "face1", "face2", "back"]
SCRYFALL_IMAGE_API = "https://api.scryfall.com/cards/{scryfall_id}"
SCRYFALL_TIMEOUT_SECONDS = 6

# Cache fallback lookups so repeated deck/search requests do not keep hitting Scryfall.
SCRYFALL_TARGET_CACHE: dict[tuple[str, str], list[dict[str, str]]] = {}
DECK_BOARD_TYPES = {
    "main",
    "sideboard",
    "considering",
    "attraction",
    "contraption",
    "stickers",
    "planar",
    "schemes",
    "command",
}
COMMANDER_FORMATS = {
    "commander",
    "brawl",
    "standard-brawl",
    "duel-commander",
    "pauper-edh",
    "oathbreaker",
}
LOBBY_GAME_MODES = {
    "multiplayer",
    "one-v-one",
    "two-headed-giant",
    "pvp",
    "goldfish",
    "simulation",
}
LOBBY_RULESETS = {"casual", "tournament", "playtest"}
SLEEVE_STYLES = {
    "classic",
    "obsidian-matte",
    "sapphire-glossy",
    "crimson-semi-gloss",
    "emerald-matte",
    "arcane-swirl",
    "dragon-scale",
}
LOBBY_DISCONNECT_GRACE_SECONDS = max(
    5,
    int(os.environ.get("LOBBY_DISCONNECT_GRACE_SECONDS", "60")),
)
LOBBY_PLAYER_SOCKETS: dict[tuple[int, int], set[str]] = defaultdict(set)
LOBBY_SOCKET_PLAYERS: dict[str, tuple[int, int]] = {}
LOBBY_DISCONNECT_MARKERS: dict[tuple[int, int], str] = {}
SOCKET_HANDLERS_REGISTERED = False


@api_bp.get("/health")
def health():
    return jsonify({"ok": True})


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(cast(Any, value))


def game_room(game_id: int) -> str:
    return f"game:{game_id}"


def extract_identifier(identifiers: Any, key: str) -> str | None:
    if not isinstance(identifiers, dict):
        return None
    value = identifiers.get(key)
    return value if isinstance(value, str) and value else None


def normalize_face_name(face_name: str) -> str:
    return (
        face_name.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


def resolve_scryfall_image_targets(card_json: dict[str, Any], size: str) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []

    image_uris = card_json.get("image_uris") or {}
    if isinstance(image_uris, dict):
        image_url = image_uris.get(size)
        if isinstance(image_url, str) and image_url:
            targets.append({"faceName": "front", "sourceUrl": image_url})

    card_faces = card_json.get("card_faces") or []
    if isinstance(card_faces, list):
        for index, face in enumerate(card_faces):
            if not isinstance(face, dict):
                continue

            face_image_uris = face.get("image_uris") or {}
            if not isinstance(face_image_uris, dict):
                continue

            face_url = face_image_uris.get(size)
            if not isinstance(face_url, str) or not face_url:
                continue

            raw_face_name = face.get("name")
            face_name = raw_face_name if isinstance(raw_face_name, str) else f"face{index + 1}"
            targets.append(
                {
                    "faceName": normalize_face_name(face_name),
                    "sourceUrl": face_url,
                }
            )

    return targets


def pick_url_from_face_rows(rows: list[Any]) -> str | None:
    for face_name in PREFERRED_IMAGE_FACES:
        for row in rows:
            if row.faceName == face_name:
                return row.publicUrl or row.sourceUrl

    if not rows:
        return None
    first_row = rows[0]
    return first_row.publicUrl or first_row.sourceUrl


def pick_url_from_targets(targets: list[dict[str, str]]) -> str | None:
    for face_name in PREFERRED_IMAGE_FACES:
        for target in targets:
            if target.get("faceName") == face_name:
                source_url = target.get("sourceUrl")
                if isinstance(source_url, str) and source_url:
                    return source_url

    if not targets:
        return None

    first_url = targets[0].get("sourceUrl")
    return first_url if isinstance(first_url, str) and first_url else None


def fetch_scryfall_fallback_image(printing: Printing | None, size: str) -> str | None:
    if printing is None:
        return None

    scryfall_id = extract_identifier(getattr(printing, "identifiers", None), "scryfallId")
    if not scryfall_id:
        return None

    # Scryfall's CDN has a deterministic path for the front face. Returning it
    # directly keeps card searches entirely database-local instead of making an
    # API request for every result.
    if len(scryfall_id) >= 2:
        return (
            f"https://cards.scryfall.io/{size}/front/"
            f"{scryfall_id[0]}/{scryfall_id[1]}/{scryfall_id}.jpg"
        )

    cache_key = (scryfall_id, size)
    targets = SCRYFALL_TARGET_CACHE.get(cache_key)
    if targets is None:
        try:
            response = requests.get(
                SCRYFALL_IMAGE_API.format(scryfall_id=scryfall_id),
                headers={
                    "User-Agent": "MtG-webapp/1.0",
                    "Accept": "application/json",
                },
                timeout=SCRYFALL_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                return None
            targets = resolve_scryfall_image_targets(payload, size)
            SCRYFALL_TARGET_CACHE[cache_key] = targets
        except requests.RequestException:
            return None
        except ValueError:
            return None

    return pick_url_from_targets(targets)


# -------------------------
# Image helpers
# -------------------------

def pick_printing_image(printing: Printing | None, size: str = "small") -> str | None:
    if printing is None:
        return None

    printing_images = cast(list[PrintingImage], printing.printingImages or [])

    cached_rows = [
        row
        for row in printing_images
        if row.imageSize == size and row.status == "cached" and row.publicUrl
    ]

    cached_url = pick_url_from_face_rows(cached_rows)
    if cached_url:
        return cached_url

    source_rows = [
        row
        for row in printing_images
        if row.imageSize == size and row.sourceUrl
    ]
    source_url = pick_url_from_face_rows(source_rows)
    if source_url:
        return source_url

    return fetch_scryfall_fallback_image(printing, size)


def pick_card_cached_image(card: Card | None, size: str = "small") -> str | None:
    if card is None:
        return None

    printing = (
        Printing.query
        .filter_by(cardId=card.id)
        .order_by(Printing.id.asc())
        .first()
    )
    return pick_printing_image(printing, size)


# -------------------------
# Serialization helpers
# -------------------------

def serialize_card_summary(card: Card) -> dict[str, Any]:
    oracle_text = card.oracleText or ""
    partner_match = re.search(r"Partner with ([^(.\n]+)", oracle_text, re.IGNORECASE)
    partner_mode = None
    if partner_match:
        partner_mode = "named"
    elif re.search(r"(^|\n)Partner(\s|$)", oracle_text, re.IGNORECASE):
        partner_mode = "partner"
    elif "friends forever" in oracle_text.lower():
        partner_mode = "friends_forever"
    elif "doctor's companion" in oracle_text.lower():
        partner_mode = "doctors_companion"
    elif "choose a background" in oracle_text.lower():
        partner_mode = "background"

    scryfall_id = extract_identifier(card.identifiers, "scryfallId")

    return {
        "id": card.id,
        "uuid": card.uuid,
        "name": card.name,
        "manaCost": card.manaCost,
        "manaValue": float(card.manaValue) if card.manaValue is not None else None,
        "typeLine": card.typeLine,
        "oracleText": card.oracleText,
        "defaultSetCode": card.defaultSetCode,
        "defaultSetName": card.defaultSetName,
        "rarity": card.rarity,
        "colorIdentity": card.colorIdentity,
        "partnerMode": partner_mode,
        "partnerName": partner_match.group(1).strip() if partner_match else None,
        "scryfallId": scryfall_id,
    }


def serialize_card_detail(card: Card) -> dict[str, Any]:
    return {
        "id": card.id,
        "uuid": card.uuid,
        "name": card.name,
        "manaCost": card.manaCost,
        "manaValue": float(card.manaValue) if card.manaValue is not None else None,
        "typeLine": card.typeLine,
        "oracleText": card.oracleText,
        "colors": card.colors,
        "colorIdentity": card.colorIdentity,
        "defaultSetCode": card.defaultSetCode,
        "defaultSetName": card.defaultSetName,
        "rarity": card.rarity,
        "legalities": card.legalities,
        "imageSmall": pick_card_cached_image(card, "small"),
        "imageNormal": pick_card_cached_image(card, "normal") or pick_card_cached_image(card, "small"),
    }


def serialize_deck_card(deck_card: DeckCard) -> dict[str, Any]:
    card = cast(Card | None, deck_card.card)

    return {
        "id": deck_card.id,
        "deckId": deck_card.deckId,
        "cardId": deck_card.cardId,
        "preferredPrintingId": deck_card.preferredPrintingId,
        "quantity": deck_card.quantity,
        "boardType": deck_card.boardType,
        "isCommander": deck_card.isCommander,
        "addedAt": deck_card.addedAt.isoformat() if deck_card.addedAt else None,
        "card": serialize_card_summary(card) if card is not None else None,
    }


def estimate_commander_bracket(deck_cards: list[DeckCard]) -> dict[str, Any]:
    """Return an explainable first-pass Commander power estimate.

    This is intentionally advisory: card text and a few well-known packages can
    identify obvious power signals, but cannot replace a full rules-aware combo
    graph or the player's description of how the deck is intended to play.
    """
    main_entries = [
        entry for entry in deck_cards
        if entry.card is not None and entry.boardType in {"main", "command"}
    ]
    names = {entry.card.name.lower() for entry in main_entries if entry.card and entry.card.name}
    score = 0
    reasons: list[str] = []

    fast_mana = {
        "mana crypt", "jeweled lotus", "mox diamond", "chrome mox",
        "lion's eye diamond", "grim monolith", "mana vault",
    }
    premium_tutors = {
        "demonic tutor", "vampiric tutor", "imperial seal", "mystical tutor",
        "enlightened tutor", "worldly tutor", "gamble", "ad nauseam",
    }
    fast_count = len(names & fast_mana)
    tutor_count = len(names & premium_tutors)
    if fast_count:
        score += min(3, fast_count)
        reasons.append(f"{fast_count} high-efficiency mana card{'s' if fast_count != 1 else ''}")
    if tutor_count:
        score += min(3, tutor_count)
        reasons.append(f"{tutor_count} efficient tutor/card-selection card{'s' if tutor_count != 1 else ''}")

    combo_packages = [
        ({"thassa's oracle", "demonic consultation"}, "Thassa's Oracle + Demonic Consultation"),
        ({"thassa's oracle", "tainted pact"}, "Thassa's Oracle + Tainted Pact"),
        ({"dramatic reversal", "isochron scepter"}, "Dramatic Reversal + Isochron Scepter"),
        ({"heliod, sun-crowned", "walking ballista"}, "Heliod + Walking Ballista"),
        ({"kiki-jiki, mirror breaker", "zealous conscripts"}, "Kiki-Jiki + Zealous Conscripts"),
    ]
    detected_combos = [label for cards, label in combo_packages if cards <= names]
    if detected_combos:
        score += 4
        reasons.append(f"known synergy package: {detected_combos[0]}")

    text_signals = 0
    for entry in main_entries:
        text = str(entry.card.oracleText or "").lower()
        if (
            "take an extra turn" in text
            or "search your library for a card" in text
            or "you win the game" in text
        ):
            text_signals += 1
    if text_signals >= 3:
        score += 2
        reasons.append(f"{text_signals} cards with high-impact tutor, extra-turn, or win text")
    elif text_signals:
        score += 1
        reasons.append(f"{text_signals} card{'s' if text_signals != 1 else ''} with high-impact text")

    ranked = [
        entry.card.edhrecRank for entry in main_entries
        if entry.card.edhrecRank is not None and entry.card.edhrecRank > 0
    ]
    if ranked and sum(ranked) / len(ranked) < 1500:
        score += 1
        reasons.append("a high concentration of widely played Commander staples")

    if score >= 8:
        bracket = 5
    elif score >= 5:
        bracket = 4
    elif score >= 3:
        bracket = 3
    elif score >= 1:
        bracket = 2
    else:
        bracket = 1
    return {
        "bracket": bracket,
        "score": score,
        "reasons": reasons or ["no major high-power signals were detected"],
        "advisory": True,
    }


def serialize_deck(deck: Deck, include_cards: bool = False) -> dict[str, Any]:
    deck_cards = cast(list[DeckCard], deck.cards or [])
    commander_entries = [entry for entry in deck_cards if entry.isCommander]
    commander_names = [
        entry.card.name
        for entry in commander_entries
        if entry.card is not None and entry.card.name
    ]
    derived_colors = sorted(
        {
            color
            for entry in deck_cards
            if entry.card is not None
            for color in (entry.card.colorIdentity or [])
        },
        key=lambda color: "WUBRG".find(color) if color in "WUBRG" else 99,
    )
    game_players = cast(list[GamePlayer], deck.gamePlayers or [])
    completed_players = [
        player
        for player in game_players
        if player.result or (player.game is not None and player.game.status == "completed")
    ]
    wins = sum(
        1
        for player in completed_players
        if (player.result or "").lower() in {"win", "won", "winner"}
        or (
            player.game is not None
            and player.game.winnerGamePlayerId == player.id
        )
    )
    bracket_estimate = estimate_commander_bracket(deck_cards)

    payload: dict[str, Any] = {
        "id": deck.id,
        "name": deck.name,
        "slug": deck.slug,
        "format": deck.format,
        "commanderCount": deck.commanderCount,
        "colorIdentity": derived_colors or deck.colorIdentity or [],
        "commanderNames": commander_names,
        "requiresCommander": deck.format in COMMANDER_FORMATS,
        "hasRequiredCommander": deck.format not in COMMANDER_FORMATS or bool(commander_entries),
        "cardCount": sum(entry.quantity or 0 for entry in deck_cards),
        "gamesPlayed": len(completed_players),
        "wins": wins,
        "winRate": round((wins / len(completed_players)) * 100, 1) if completed_players else None,
        "ownerUserId": deck.ownerUserId,
        "sourceType": deck.sourceType,
        "sourceProductId": deck.sourceProductId,
        "notes": deck.notes,
        "isPublic": deck.isPublic,
        "visibility": "public" if deck.isPublic else "private",
        "folderName": deck.folderName,
        "commanderBracket": deck.commanderBracket,
        "estimatedCommanderBracket": bracket_estimate,
        "createdAt": deck.createdAt.isoformat() if deck.createdAt else None,
        "updatedAt": deck.updatedAt.isoformat() if deck.updatedAt else None,
        "lastUsedAt": deck.lastUsedAt.isoformat() if deck.lastUsedAt else None,
    }

    if include_cards:
        sorted_cards = sorted(
            deck_cards,
            key=lambda entry: (
                entry.boardType or "",
                entry.card.name.lower() if entry.card and entry.card.name else "",
            ),
        )
        payload["cards"] = [serialize_deck_card(entry) for entry in sorted_cards]

    return payload


def serialize_game_player(player: GamePlayer) -> dict[str, Any]:
    deck = player.deck
    return {
        "id": player.id,
        "gameId": player.gameId,
        "seatNumber": player.seatNumber,
        "playerType": player.playerType,
        "userId": player.userId,
        "aiProfile": player.aiProfile,
        "deckId": player.deckId,
        "deckVersionId": player.deckVersionId,
        "deckName": deck.name if deck else None,
        "startingLife": player.startingLife,
        "startingHandSize": player.startingHandSize,
        "isReady": bool(player.isReady),
        "isHost": bool(player.isHost),
        "isConnected": bool(player.isConnected),
        "disconnectedAt": player.disconnectedAt.isoformat() if player.disconnectedAt else None,
        "sleeveStyle": player.sleeveStyle or "classic",
        "result": player.result,
        "hasDeck": bool(player.deckId),
    }


def lobby_player_for_token(game: Game, participant_token: str | None) -> GamePlayer | None:
    if not participant_token:
        return None
    for player in cast(list[GamePlayer], game.players or []):
        if player.lobbyTokenHash and check_password_hash(player.lobbyTokenHash, participant_token):
            return player
    return None


def serialize_game_for_participant(
    game: Game,
    participant_token: str | None,
    *,
    include_snapshot: bool = True,
) -> dict[str, Any]:
    payload = serialize_game(game, include_players=True, include_snapshot=include_snapshot)
    current_player = lobby_player_for_token(game, participant_token)
    payload["currentPlayerId"] = current_player.id if current_player else None
    payload["currentUserIsHost"] = bool(current_player and current_player.isHost)
    return payload


def emit_lobby_change(game: Game, action: str) -> None:
    public_game = serialize_game(game, include_players=True, include_snapshot=False)
    socketio.emit(
        "game:lobby_updated",
        {"gameId": game.id, "game": public_game, "action": action},
        to=game_room(game.id),
    )
    socketio.emit(
        "lobbies:updated",
        {"gameId": game.id, "game": public_game, "action": action},
    )


def commander_pair_mode(card: Card) -> tuple[str | None, str | None]:
    text = card.oracleText or ""
    named_match = re.search(r"Partner with ([^(.\n]+)", text, re.IGNORECASE)
    if named_match:
        return "named", named_match.group(1).strip()
    if re.search(r"(^|\n)Partner(\s|$)", text, re.IGNORECASE):
        return "partner", None
    lowered = text.lower()
    if "friends forever" in lowered:
        return "friends_forever", None
    if "doctor's companion" in lowered:
        return "doctors_companion", None
    if "choose a background" in lowered:
        return "background", None
    return None, None


def commanders_are_compatible(first: Card, second: Card) -> bool:
    first_mode, first_partner = commander_pair_mode(first)
    second_mode, second_partner = commander_pair_mode(second)

    if first_mode == "named":
        return second.name.lower() == (first_partner or "").lower()
    if second_mode == "named":
        return first.name.lower() == (second_partner or "").lower()
    if first_mode == "partner" and second_mode == "partner":
        return True
    if first_mode == "friends_forever" and second_mode == "friends_forever":
        return True
    if first_mode == "background":
        return "background" in (second.typeLine or "").lower()
    if second_mode == "background":
        return "background" in (first.typeLine or "").lower()
    if first_mode == "doctors_companion":
        return "doctor" in (second.typeLine or "").lower()
    if second_mode == "doctors_companion":
        return "doctor" in (first.typeLine or "").lower()
    return False


def card_can_be_commander(card: Card) -> bool:
    type_line = card.typeLine or ""
    oracle_text = (card.oracleText or "").lower()
    return (
        "Legendary Creature" in type_line
        or "can be your commander" in oracle_text
        or "Legendary Background" in type_line
    )


def sync_deck_commander_count(deck: Deck) -> None:
    db.session.flush()
    deck.commanderCount = DeckCard.query.filter_by(
        deckId=deck.id,
        isCommander=True,
    ).count()


def serialize_event(event: GameEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "gameId": event.gameId,
        "sequenceNumber": event.sequenceNumber,
        "turnNumber": event.turnNumber,
        "phase": event.phase,
        "step": event.step,
        "actingGamePlayerId": event.actingGamePlayerId,
        "eventType": event.eventType,
        "visibilityScope": event.visibilityScope,
        "payload": event.payloadJson,
        "publicText": event.publicText,
        "createdAt": event.createdAt.isoformat() if event.createdAt else None,
    }


def serialize_snapshot(snapshot: StateSnapshot | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None

    return {
        "id": snapshot.id,
        "gameId": snapshot.gameId,
        "sequenceNumber": snapshot.sequenceNumber,
        "turnNumber": snapshot.turnNumber,
        "phase": snapshot.phase,
        "state": snapshot.stateJson,
        "snapshotHash": snapshot.snapshotHash,
        "createdAt": snapshot.createdAt.isoformat() if snapshot.createdAt else None,
    }


def serialize_game(game: Game, include_players: bool = True, include_snapshot: bool = True) -> dict[str, Any]:
    latest_snapshot: StateSnapshot | None = None
    if include_snapshot:
        latest_snapshot = cast(
            StateSnapshot | None,
            StateSnapshot.query.filter_by(gameId=game.id)
            .order_by(
                cast(Any, getattr(StateSnapshot, "sequenceNumber")).desc(),
                cast(Any, getattr(StateSnapshot, "id")).desc(),
            )
            .first(),
        )

    game_players = cast(list[GamePlayer], game.players or [])
    occupied_player_count = sum(1 for player in game_players if player.deckId)
    occupied_players = [player for player in game_players if player.deckId]
    max_players = game.maxPlayers or len(game_players) or 2
    payload: dict[str, Any] = {
        "id": game.id,
        "parentGameId": game.parentGameId,
        "parentSnapshotId": game.parentSnapshotId,
        "branchedFromSequence": game.branchedFromSequence,
        "rootGameId": game.rootGameId,
        "gameMode": game.gameMode,
        "format": game.format,
        "status": game.status,
        "lobbyName": game.lobbyName or f"Game #{game.id}",
        "ruleset": game.ruleset or "casual",
        "rulesEngineMode": (
            "disabled"
            if game.ruleset == "playtest"
            else "strict"
            if game.ruleset == "tournament"
            else "advisory"
        ),
        "maxPlayers": max_players,
        "occupiedPlayerCount": occupied_player_count,
        "openSeatCount": max(0, max_players - occupied_player_count),
        "allPlayersReady": bool(occupied_players) and all(player.isReady for player in occupied_players),
        "allSeatsFilled": occupied_player_count >= max_players,
        "disconnectGraceSeconds": LOBBY_DISCONNECT_GRACE_SECONDS,
        "isPasswordProtected": bool(game.passwordHash),
        "hostUserId": game.hostUserId,
        "turnNumber": game.turnNumber or 1,
        "activeSeatNumber": game.activeSeatNumber or 1,
        "rngSeed": game.rngSeed,
        "engineVersion": game.engineVersion,
        "rulesVersion": game.rulesVersion,
        "winnerGamePlayerId": game.winnerGamePlayerId,
        "notes": game.notes,
        "startedAt": game.startedAt.isoformat() if game.startedAt else None,
        "endedAt": game.endedAt.isoformat() if game.endedAt else None,
        "createdAt": game.createdAt.isoformat() if game.createdAt else None,
    }
    payload["playerCount"] = len(game_players)

    if include_players:
        players = sorted(game_players, key=lambda player: player.seatNumber)
        payload["players"] = [serialize_game_player(player) for player in players]

    if include_snapshot:
        payload["latestSnapshot"] = serialize_snapshot(latest_snapshot)

    return payload

def serialize_card_instance(card_instance: CardInstance) -> dict[str, Any]:
    card = getattr(card_instance, "card", None)
    printing = getattr(card_instance, "printing", None)

    return {
        "id": card_instance.id,
        "zone": getattr(card_instance, "zone", None),
        "zoneIndex": getattr(card_instance, "zoneIndex", None),
        "isCommander": bool(getattr(card_instance, "isCommander", False)),
        "isTapped": getattr(card_instance, "isTapped", False),
        "rotationDeg": getattr(card_instance, "rotationDeg", 0),
        "isFaceDown": getattr(card_instance, "isFaceDown", False),
        "displayFace": getattr(card_instance, "displayFace", "front"),
        "battlefieldX": to_optional_float(getattr(card_instance, "battlefieldX", None)),
        "battlefieldY": to_optional_float(getattr(card_instance, "battlefieldY", None)),
        "stackIndex": getattr(card_instance, "stackIndex", None),
        "card": {
            "id": card.id if card else None,
            "name": card.name if card else None,
            "manaCost": card.manaCost if card else None,
            "manaValue": float(card.manaValue) if card and card.manaValue is not None else None,
            "typeLine": card.typeLine if card else None,
            "oracleText": card.oracleText if card else None,
            "colorIdentity": list(card.colorIdentity or []) if card else [],
            "imageSmall": pick_printing_image(printing, "small"),
            "imageNormal": pick_printing_image(printing, "normal") or pick_printing_image(printing, "small"),
        },
        "printingId": card_instance.printingId,
        "gamePlayerId": card_instance.gamePlayerId,
    }


def serialize_game_state(game: Game) -> dict[str, Any]:
    players_payload = []
    alternate_win_conditions: list[dict[str, Any]] = []

    players = cast(list[GamePlayer], game.players or [])
    for player in sorted(players, key=lambda p: p.seatNumber):
        zone_map: dict[str, list[CardInstance]] = defaultdict(list)

        card_instances = cast(list[CardInstance], player.cardInstances or [])
        for card_instance in card_instances:
            zone = getattr(card_instance, "zone", "library")
            zone_map[zone].append(card_instance)
            card = getattr(card_instance, "card", None)
            oracle_text = str(getattr(card, "oracleText", "") or "")
            if re.search(r"\b(you win the game|wins the game|loses the game)\b", oracle_text, re.IGNORECASE):
                alternate_win_conditions.append({
                    "cardInstanceId": card_instance.id,
                    "cardName": card.name if card else "Unknown card",
                    "gamePlayerId": player.id,
                    "seatNumber": player.seatNumber,
                    "zone": zone,
                    "revealed": zone not in {"library", "hand"},
                    "status": "active" if zone == "battlefield" else "watching",
                })

        for zone_name in zone_map:
            zone_map[zone_name].sort(
                key=lambda c: (
                    getattr(c, "zoneIndex", 10**9) if getattr(c, "zoneIndex", None) is not None else 10**9,
                    c.id,
                )
            )

        zones_payload: dict[str, Any] = {}
        for zone_name in ZONE_ORDER:
            cards = zone_map.get(zone_name, [])
            if zone_name == "library":
                zones_payload["libraryCount"] = len(cards)
            else:
                zones_payload[zone_name] = [serialize_card_instance(c) for c in cards]

        players_payload.append(
            {
                "id": player.id,
                "seatNumber": player.seatNumber,
                "playerType": player.playerType,
                "startingLife": player.startingLife,
                "startingHandSize": player.startingHandSize,
                "deckId": player.deckId,
                "deckVersionId": player.deckVersionId,
                "sleeveStyle": player.sleeveStyle or "classic",
                "result": player.result,
                "zones": zones_payload,
            }
        )

    random_events = (
        GameEvent.query.filter(
            GameEvent.gameId == game.id,
            GameEvent.eventType.in_(["roll_dice", "flip_coins"]),
        )
        .order_by(cast(Any, GameEvent.id).desc())
        .limit(12)
        .all()
    )
    player_seats = {player.id: player.seatNumber for player in players}
    random_results = [
        {
            "eventId": event.id,
            "type": event.eventType,
            "gamePlayerId": event.actingGamePlayerId,
            "seatNumber": player_seats.get(event.actingGamePlayerId),
            "values": list((event.payloadJson or {}).get("values") or []),
            "sides": (event.payloadJson or {}).get("sides"),
            "label": (event.payloadJson or {}).get("label"),
            "createdAt": event.createdAt.isoformat() if event.createdAt else None,
        }
        for event in reversed(random_events)
    ]

    return {
        "game": {
            "id": game.id,
            "status": game.status,
            "format": game.format,
            "gameMode": game.gameMode,
            "turnNumber": game.turnNumber or 1,
            "activeSeatNumber": game.activeSeatNumber or 1,
            "activeGamePlayerId": next(
                (
                    player.id
                    for player in players
                    if player.seatNumber == (game.activeSeatNumber or 1)
                ),
                None,
            ),
            "winnerGamePlayerId": game.winnerGamePlayerId,
            "endedAt": game.endedAt.isoformat() if game.endedAt else None,
        },
        "players": players_payload,
        "alternateWinConditions": alternate_win_conditions,
        "randomResults": random_results,
    }

# -------------------------
# Game state helpers
# -------------------------

def build_initial_state(game: Game) -> dict[str, Any]:
    ordered_players = sorted(cast(list[GamePlayer], game.players or []), key=lambda player: player.seatNumber)
    active_player_id = ordered_players[0].id if ordered_players else None

    return {
        "gameId": game.id,
        "status": game.status,
        "turnNumber": 1,
        "phase": "beginning",
        "step": "untap",
        "priorityPlayerId": active_player_id,
        "activePlayerId": active_player_id,
        "stack": [],
        "players": [
            {
                "gamePlayerId": player.id,
                "seatNumber": player.seatNumber,
                "life": player.startingLife,
                "handCount": player.startingHandSize,
                "libraryCount": None,
                "graveyardCount": 0,
                "battlefieldCount": 0,
                "exileCount": 0,
                "commandZoneCount": 0,
            }
            for player in ordered_players
        ],
        "lastAction": None,
    }


def next_event_sequence(game_id: int) -> int:
    latest = cast(
        GameEvent | None,
        db.session.query(GameEvent)
        .filter_by(gameId=game_id)
        .order_by(cast(Any, getattr(GameEvent, "sequenceNumber")).desc())
        .first(),
    )
    return 1 if latest is None else int(latest.sequenceNumber) + 1


def create_game_event(game_id: int, acting_game_player_id: int | None, event_type: str, payload: dict[str, Any]) -> GameEvent:
    event = GameEvent(
        gameId=game_id,
        actingGamePlayerId=acting_game_player_id,
        eventType=event_type,
        visibilityScope="public",
        payloadJson=payload,
        publicText=event_type,
        sequenceNumber=next_event_sequence(game_id),
    )
    db.session.add(event)
    return event


def get_game_or_error(game_id: int) -> Game:
    game = Game.query.filter_by(id=game_id).first()
    if not game:
        raise ValueError(f"Game {game_id} not found")
    return game


# -------------------------
# Game action handlers
# -------------------------

def handle_draw_cards(game_id: int, game_player_id: int, count: int) -> dict[str, Any]:
    game = get_game_or_error(game_id)

    library_cards = (
        CardInstance.query.filter_by(gameId=game_id, gamePlayerId=game_player_id, zone="library")
        .order_by(
            func.coalesce(cast(Any, CardInstance.zoneIndex), 10**9).asc(),
            cast(Any, CardInstance.id).asc(),
        )
        .limit(count)
        .all()
    )

    hand_count = (
        CardInstance.query.filter_by(gameId=game_id, gamePlayerId=game_player_id, zone="hand")
        .count()
    )

    for idx, card in enumerate(library_cards):
        card.zone = "hand"
        card.zoneIndex = hand_count + idx
        card.battlefieldX = None
        card.battlefieldY = None
        card.stackIndex = None

    create_game_event(
        game_id,
        game_player_id,
        "draw_cards",
        {
            "gamePlayerId": game_player_id,
            "count": len(library_cards),
            "cardInstanceIds": [c.id for c in library_cards],
        },
    )

    db.session.commit()
    return serialize_game_state(game)


def handle_move_card(game_id: int, card_instance_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    game = get_game_or_error(game_id)

    card = CardInstance.query.filter_by(id=card_instance_id, gameId=game_id).first()
    if not card:
        raise ValueError(f"CardInstance {card_instance_id} not found in game {game_id}")

    requested_zone = payload.get("zone", card.zone)
    card.zone = (
        "command"
        if card.isCommander and requested_zone == "graveyard"
        else requested_zone
    )
    card.zoneIndex = payload.get("zoneIndex", card.zoneIndex)
    card.battlefieldX = Decimal(str(payload["battlefieldX"])) if payload.get("battlefieldX") is not None else None
    card.battlefieldY = Decimal(str(payload["battlefieldY"])) if payload.get("battlefieldY") is not None else None
    card.stackIndex = payload.get("stackIndex", card.stackIndex)

    create_game_event(
        game_id,
        card.gamePlayerId,
        "move_card",
        {
            "cardInstanceId": card.id,
            "zone": card.zone,
            "zoneIndex": card.zoneIndex,
            "battlefieldX": float(card.battlefieldX) if card.battlefieldX is not None else None,
            "battlefieldY": float(card.battlefieldY) if card.battlefieldY is not None else None,
            "stackIndex": card.stackIndex,
        },
    )

    db.session.commit()
    return serialize_game_state(game)


def ordered_library_cards(game_id: int, game_player_id: int) -> list[CardInstance]:
    return cast(
        list[CardInstance],
        CardInstance.query.filter_by(
            gameId=game_id,
            gamePlayerId=game_player_id,
            zone="library",
        )
        .order_by(
            func.coalesce(cast(Any, CardInstance.zoneIndex), 10**9).asc(),
            cast(Any, CardInstance.id).asc(),
        )
        .all(),
    )


def reindex_library(game_id: int, game_player_id: int) -> None:
    for index, library_card in enumerate(ordered_library_cards(game_id, game_player_id)):
        library_card.zoneIndex = index


def handle_return_to_library(
    game_id: int,
    card_instance_id: int,
    position: str,
    target_game_player_id: int | None = None,
) -> dict[str, Any]:
    game = get_game_or_error(game_id)
    card = CardInstance.query.filter_by(id=card_instance_id, gameId=game_id).first()
    if not card:
        raise ValueError(f"CardInstance {card_instance_id} not found in game {game_id}")
    if card.isCommander:
        raise ValueError("Commanders return to the Command Zone instead of the library.")

    owner_id = int(target_game_player_id or card.gamePlayerId)
    if not GamePlayer.query.filter_by(id=owner_id, gameId=game_id).first():
        raise ValueError("Target player was not found in this game.")

    library = [
        library_card
        for library_card in ordered_library_cards(game_id, owner_id)
        if library_card.id != card.id
    ]
    if position == "top":
        insertion_index = 0
    elif position == "bottom":
        insertion_index = len(library)
    elif position == "random":
        insertion_index = random.SystemRandom().randrange(len(library) + 1)
    else:
        raise ValueError("Library position must be top, bottom, or random.")

    card.gamePlayerId = owner_id
    card.zone = "library"
    card.zoneIndex = insertion_index
    card.battlefieldX = None
    card.battlefieldY = None
    for index, library_card in enumerate(library):
        library_card.zoneIndex = index + (1 if index >= insertion_index else 0)

    create_game_event(
        game_id,
        owner_id,
        "return_to_library",
        {
            "cardInstanceId": card.id,
            "position": position,
            "targetGamePlayerId": owner_id,
        },
    )
    db.session.commit()
    return serialize_game_state(game)


def handle_draw_from_player(
    game_id: int,
    source_game_player_id: int,
    target_game_player_id: int,
    count: int,
) -> dict[str, Any]:
    game = get_game_or_error(game_id)
    source = GamePlayer.query.filter_by(id=source_game_player_id, gameId=game_id).first()
    target = GamePlayer.query.filter_by(id=target_game_player_id, gameId=game_id).first()
    if not source or not target:
        raise ValueError("Source or target player was not found in this game.")

    cards = ordered_library_cards(game_id, source.id)[:max(0, count)]
    hand_count = CardInstance.query.filter_by(
        gameId=game_id,
        gamePlayerId=target.id,
        zone="hand",
    ).count()
    for index, card in enumerate(cards):
        card.gamePlayerId = target.id
        card.zone = "hand"
        card.zoneIndex = hand_count + index
    reindex_library(game_id, source.id)
    create_game_event(
        game_id,
        target.id,
        "draw_from_player",
        {
            "sourceGamePlayerId": source.id,
            "targetGamePlayerId": target.id,
            "cardInstanceIds": [card.id for card in cards],
        },
    )
    db.session.commit()
    return serialize_game_state(game)


def handle_draw_bottom(game_id: int, game_player_id: int, count: int) -> dict[str, Any]:
    game = get_game_or_error(game_id)
    library = ordered_library_cards(game_id, game_player_id)
    cards = list(reversed(library[-max(0, count):]))
    hand_count = CardInstance.query.filter_by(
        gameId=game_id,
        gamePlayerId=game_player_id,
        zone="hand",
    ).count()
    for index, card in enumerate(cards):
        card.zone = "hand"
        card.zoneIndex = hand_count + index
    reindex_library(game_id, game_player_id)
    create_game_event(
        game_id,
        game_player_id,
        "draw_bottom",
        {"count": len(cards), "cardInstanceIds": [card.id for card in cards]},
    )
    db.session.commit()
    return serialize_game_state(game)


def handle_shuffle_library(game_id: int, game_player_id: int) -> dict[str, Any]:
    game = get_game_or_error(game_id)
    cards = ordered_library_cards(game_id, game_player_id)
    random.SystemRandom().shuffle(cards)
    for index, card in enumerate(cards):
        card.zoneIndex = index
    create_game_event(
        game_id,
        game_player_id,
        "shuffle_library",
        {"gamePlayerId": game_player_id, "count": len(cards)},
    )
    db.session.commit()
    return serialize_game_state(game)


LIBRARY_CARD_CONDITIONS = {
    "land": ("Land",),
    "creature": ("Creature",),
    "instant": ("Instant",),
    "sorcery": ("Sorcery",),
    "instant-or-sorcery": ("Instant", "Sorcery"),
    "artifact": ("Artifact",),
    "enchantment": ("Enchantment",),
    "planeswalker": ("Planeswalker",),
}


def card_matches_library_condition(card: CardInstance, condition: str) -> bool:
    type_line = str(card.card.typeLine if card.card else "")
    if condition == "nonland":
        return "Land" not in type_line
    allowed_types = LIBRARY_CARD_CONDITIONS.get(condition)
    if not allowed_types:
        raise ValueError("Unsupported card-type condition.")
    return any(card_type in type_line for card_type in allowed_types)


def library_cards_through_condition(
    game_id: int,
    game_player_id: int,
    condition: str,
) -> tuple[list[CardInstance], bool]:
    inspected: list[CardInstance] = []
    matched = False
    for card in ordered_library_cards(game_id, game_player_id):
        inspected.append(card)
        if card_matches_library_condition(card, condition):
            matched = True
            break
    return inspected, matched


def handle_scry_library(
    game_id: int,
    game_player_id: int,
    inspected_card_ids: list[int],
    top_card_ids: list[int],
    bottom_card_ids: list[int],
) -> dict[str, Any]:
    game = get_game_or_error(game_id)
    library = ordered_library_cards(game_id, game_player_id)
    inspected_ids = [int(card_id) for card_id in inspected_card_ids]
    if not inspected_ids or inspected_ids != [card.id for card in library[:len(inspected_ids)]]:
        raise ValueError("The selected cards are no longer on top of that Library.")

    top_ids = [int(card_id) for card_id in top_card_ids]
    bottom_ids = [int(card_id) for card_id in bottom_card_ids]
    if set(top_ids + bottom_ids) != set(inspected_ids) or len(top_ids + bottom_ids) != len(inspected_ids):
        raise ValueError("Every inspected card must be placed on the top or bottom exactly once.")

    by_id = {card.id: card for card in library}
    untouched = [card for card in library if card.id not in set(inspected_ids)]
    reordered = [by_id[card_id] for card_id in top_ids] + untouched + [
        by_id[card_id] for card_id in bottom_ids
    ]
    for index, card in enumerate(reordered):
        card.zoneIndex = index

    create_game_event(
        game_id,
        game_player_id,
        "scry_library",
        {
            "count": len(inspected_ids),
            "topCount": len(top_ids),
            "bottomCount": len(bottom_ids),
        },
    )
    db.session.commit()
    return serialize_game_state(game)


def handle_exile_until(
    game_id: int,
    game_player_id: int,
    condition: str,
) -> dict[str, Any]:
    game = get_game_or_error(game_id)
    player = GamePlayer.query.filter_by(id=game_player_id, gameId=game_id).first()
    if not player:
        raise ValueError("Player was not found in this game.")
    cards, matched = library_cards_through_condition(game_id, game_player_id, condition)
    exile_count = CardInstance.query.filter_by(
        gameId=game_id,
        gamePlayerId=game_player_id,
        zone="exile",
    ).count()
    for offset, card in enumerate(cards):
        card.zone = "exile"
        card.zoneIndex = exile_count + offset
    reindex_library(game_id, game_player_id)
    create_game_event(
        game_id,
        game_player_id,
        "exile_until",
        {
            "condition": condition,
            "matched": matched,
            "count": len(cards),
            "cardInstanceIds": [card.id for card in cards],
        },
    )
    db.session.commit()
    return serialize_game_state(game)


def handle_roll_dice(
    game_id: int,
    game_player_id: int,
    sides: int,
    count: int,
) -> dict[str, Any]:
    game = get_game_or_error(game_id)
    player = GamePlayer.query.filter_by(id=game_player_id, gameId=game_id).first()
    if not player:
        raise ValueError("Player was not found in this game.")
    if sides < 2 or sides > 1000:
        raise ValueError("Dice must have between 2 and 1000 sides.")
    if count < 1 or count > 20:
        raise ValueError("Roll between 1 and 20 dice at a time.")

    generator = random.SystemRandom()
    values = [generator.randint(1, sides) for _ in range(count)]
    create_game_event(
        game_id,
        player.id,
        "roll_dice",
        {
            "sides": sides,
            "count": count,
            "values": values,
            "label": f"{count}d{sides}" if count > 1 else f"d{sides}",
        },
    )
    db.session.commit()
    return serialize_game_state(game)


def handle_flip_coins(
    game_id: int,
    game_player_id: int,
    count: int,
) -> dict[str, Any]:
    game = get_game_or_error(game_id)
    player = GamePlayer.query.filter_by(id=game_player_id, gameId=game_id).first()
    if not player:
        raise ValueError("Player was not found in this game.")
    if count < 1 or count > 20:
        raise ValueError("Flip between 1 and 20 coins at a time.")

    generator = random.SystemRandom()
    values = ["Heads" if generator.getrandbits(1) else "Tails" for _ in range(count)]
    create_game_event(
        game_id,
        player.id,
        "flip_coins",
        {
            "count": count,
            "values": values,
            "label": "Coin" if count == 1 else f"{count} coins",
        },
    )
    db.session.commit()
    return serialize_game_state(game)


def handle_ai_take_turn(game_id: int, game_player_id: int) -> dict[str, Any]:
    game = get_game_or_error(game_id)
    player = GamePlayer.query.filter_by(id=game_player_id, gameId=game_id).first()
    if not player or player.playerType not in {"computer", "ai"}:
        raise ValueError("That seat is not controlled by the computer.")
    if player.seatNumber != game.activeSeatNumber:
        raise ValueError("It is not that computer player's turn.")

    drawn = ordered_library_cards(game_id, player.id)[:1]
    hand_count = CardInstance.query.filter_by(
        gameId=game_id,
        gamePlayerId=player.id,
        zone="hand",
    ).count()
    for card in drawn:
        card.zone = "hand"
        card.zoneIndex = hand_count

    hand = cast(
        list[CardInstance],
        CardInstance.query.filter_by(
            gameId=game_id,
            gamePlayerId=player.id,
            zone="hand",
        ).all(),
    )
    lands = [card for card in hand if "Land" in str(card.card.typeLine if card.card else "")]
    nonlands = [card for card in hand if card not in lands]
    profile = str(player.aiProfile or "adaptive").lower()
    generator = random.SystemRandom()

    played: list[CardInstance] = []
    if lands:
        land = lands[0] if profile != "random" else generator.choice(lands)
        land.zone = "battlefield"
        land.zoneIndex = None
        land.battlefieldX = Decimal("320")
        land.battlefieldY = Decimal("300")
        played.append(land)

    if nonlands and not (profile == "relaxed" and generator.random() < 0.45):
        def priority(card: CardInstance) -> tuple[int, float, int]:
            type_line = str(card.card.typeLine if card.card else "")
            mana_value = float(card.card.manaValue or 0) if card.card else 0
            if profile == "aggressive":
                return (0 if "Creature" in type_line else 1, mana_value, card.id)
            if profile == "defensive":
                return (
                    0 if any(kind in type_line for kind in ("Instant", "Enchantment", "Artifact")) else 1,
                    mana_value,
                    card.id,
                )
            return (0 if "Creature" in type_line else 1, mana_value, card.id)

        selected = generator.choice(nonlands) if profile == "random" else sorted(nonlands, key=priority)[0]
        selected.zone = "battlefield"
        selected.zoneIndex = None
        selected.battlefieldX = Decimal("150")
        selected.battlefieldY = Decimal("150")
        played.append(selected)

    active_players = sorted(
        [
            candidate
            for candidate in cast(list[GamePlayer], game.players or [])
            if candidate.deckId and candidate.result != "loss"
        ],
        key=lambda candidate: candidate.seatNumber,
    )
    current_index = next(
        (index for index, candidate in enumerate(active_players) if candidate.id == player.id),
        0,
    )
    next_player = active_players[(current_index + 1) % len(active_players)]
    game.activeSeatNumber = next_player.seatNumber
    game.turnNumber = int(game.turnNumber or 1) + 1
    create_game_event(
        game_id,
        player.id,
        "ai_take_turn",
        {
            "strategy": profile,
            "drawnCardInstanceIds": [card.id for card in drawn],
            "playedCardInstanceIds": [card.id for card in played],
            "nextGamePlayerId": next_player.id,
        },
    )
    db.session.commit()
    return serialize_game_state(game)


def handle_transfer_card(
    game_id: int,
    card_instance_id: int,
    target_game_player_id: int,
    target_zone: str,
) -> dict[str, Any]:
    game = get_game_or_error(game_id)
    card = CardInstance.query.filter_by(id=card_instance_id, gameId=game_id).first()
    target = GamePlayer.query.filter_by(id=target_game_player_id, gameId=game_id).first()
    if not card or not target:
        raise ValueError("Card or target player was not found in this game.")
    if target_zone not in {"hand", "graveyard", "exile", "battlefield"}:
        raise ValueError("Unsupported transfer destination.")
    if card.isCommander and target_zone == "graveyard":
        target_zone = "command"

    previous_owner_id = card.gamePlayerId
    card.gamePlayerId = target.id
    card.zone = target_zone
    card.zoneIndex = CardInstance.query.filter_by(
        gameId=game_id,
        gamePlayerId=target.id,
        zone=target_zone,
    ).count()
    card.battlefieldX = Decimal("120") if target_zone == "battlefield" else None
    card.battlefieldY = Decimal("120") if target_zone == "battlefield" else None
    if previous_owner_id:
        reindex_library(game_id, previous_owner_id)
    create_game_event(
        game_id,
        target.id,
        "transfer_card",
        {
            "cardInstanceId": card.id,
            "targetGamePlayerId": target.id,
            "targetZone": target_zone,
        },
    )
    db.session.commit()
    return serialize_game_state(game)


def handle_swap_cards(game_id: int, first_card_id: int, second_card_id: int) -> dict[str, Any]:
    game = get_game_or_error(game_id)
    first = CardInstance.query.filter_by(id=first_card_id, gameId=game_id).first()
    second = CardInstance.query.filter_by(id=second_card_id, gameId=game_id).first()
    if not first or not second:
        raise ValueError("Both cards must exist in this game.")
    if first.isCommander or second.isCommander:
        raise ValueError("Commanders cannot be exchanged with this action.")

    first_owner, first_zone, first_index = first.gamePlayerId, first.zone, first.zoneIndex
    second_owner, second_zone, second_index = second.gamePlayerId, second.zone, second.zoneIndex
    first.gamePlayerId, first.zone, first.zoneIndex = second_owner, second_zone, second_index
    second.gamePlayerId, second.zone, second.zoneIndex = first_owner, first_zone, first_index
    create_game_event(
        game_id,
        first_owner,
        "swap_cards",
        {"firstCardInstanceId": first.id, "secondCardInstanceId": second.id},
    )
    db.session.commit()
    return serialize_game_state(game)


def handle_tap_card(game_id: int, card_instance_id: int, is_tapped: bool | None) -> dict[str, Any]:
    game = get_game_or_error(game_id)

    card = CardInstance.query.filter_by(id=card_instance_id, gameId=game_id).first()
    if not card:
        raise ValueError(f"CardInstance {card_instance_id} not found in game {game_id}")

    next_value = (not getattr(card, "isTapped", False)) if is_tapped is None else bool(is_tapped)
    card.isTapped = next_value
    card.rotationDeg = 90 if next_value else 0

    create_game_event(
        game_id,
        card.gamePlayerId,
        "tap_card",
        {
            "cardInstanceId": card.id,
            "isTapped": card.isTapped,
            "rotationDeg": card.rotationDeg,
        },
    )

    db.session.commit()
    return serialize_game_state(game)


def handle_set_display_face(game_id: int, card_instance_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    game = get_game_or_error(game_id)

    card = CardInstance.query.filter_by(id=card_instance_id, gameId=game_id).first()
    if not card:
        raise ValueError(f"CardInstance {card_instance_id} not found in game {game_id}")

    if "displayFace" in payload:
        card.displayFace = payload["displayFace"]
    if "isFaceDown" in payload:
        card.isFaceDown = bool(payload["isFaceDown"])

    create_game_event(
        game_id,
        card.gamePlayerId,
        "set_display_face",
        {
            "cardInstanceId": card.id,
            "displayFace": getattr(card, "displayFace", None),
            "isFaceDown": getattr(card, "isFaceDown", False),
        },
    )

    db.session.commit()
    return serialize_game_state(game)


def handle_pass_turn(game_id: int, game_player_id: int) -> dict[str, Any]:
    game = get_game_or_error(game_id)
    if game.status != "active":
        raise ValueError("Turns can only be passed after the game starts.")

    players = sorted(
        [
            player
            for player in cast(list[GamePlayer], game.players or [])
            if player.deckId is not None and player.result != "loss"
        ],
        key=lambda player: player.seatNumber,
    )
    if not players:
        raise ValueError("This game has no active players.")

    current_index = next(
        (
            index
            for index, player in enumerate(players)
            if player.seatNumber == (game.activeSeatNumber or players[0].seatNumber)
        ),
        0,
    )
    current_player = players[current_index]
    if current_player.id != game_player_id:
        raise ValueError(f"It is currently Player {current_player.seatNumber}'s turn.")

    next_player = players[(current_index + 1) % len(players)]
    game.activeSeatNumber = next_player.seatNumber
    game.turnNumber = int(game.turnNumber or 1) + 1
    create_game_event(
        game_id,
        game_player_id,
        "pass_turn",
        {
            "fromSeatNumber": current_player.seatNumber,
            "toSeatNumber": next_player.seatNumber,
            "turnNumber": game.turnNumber,
        },
    )
    db.session.commit()
    return serialize_game_state(game)


def dispatch_game_action(game_id: int, action: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    action_type = action.get("type")

    if action_type == "draw_cards":
        return action_type, handle_draw_cards(
            game_id=game_id,
            game_player_id=action["gamePlayerId"],
            count=int(action.get("count", 1)),
        )

    if action_type == "move_card":
        return action_type, handle_move_card(
            game_id=game_id,
            card_instance_id=action["cardInstanceId"],
            payload=action,
        )

    if action_type == "tap_card":
        return action_type, handle_tap_card(
            game_id=game_id,
            card_instance_id=action["cardInstanceId"],
            is_tapped=action.get("isTapped"),
        )

    if action_type == "set_display_face":
        return action_type, handle_set_display_face(
            game_id=game_id,
            card_instance_id=action["cardInstanceId"],
            payload=action,
        )

    if action_type == "pass_turn":
        return action_type, handle_pass_turn(
            game_id=game_id,
            game_player_id=int(action["gamePlayerId"]),
        )

    if action_type == "return_to_library":
        return action_type, handle_return_to_library(
            game_id=game_id,
            card_instance_id=int(action["cardInstanceId"]),
            position=str(action.get("position") or "top"),
            target_game_player_id=action.get("targetGamePlayerId"),
        )

    if action_type == "draw_from_player":
        return action_type, handle_draw_from_player(
            game_id=game_id,
            source_game_player_id=int(action["sourceGamePlayerId"]),
            target_game_player_id=int(action["targetGamePlayerId"]),
            count=int(action.get("count", 1)),
        )

    if action_type == "transfer_card":
        return action_type, handle_transfer_card(
            game_id=game_id,
            card_instance_id=int(action["cardInstanceId"]),
            target_game_player_id=int(action["targetGamePlayerId"]),
            target_zone=str(action.get("targetZone") or "hand"),
        )

    if action_type == "swap_cards":
        return action_type, handle_swap_cards(
            game_id=game_id,
            first_card_id=int(action["firstCardInstanceId"]),
            second_card_id=int(action["secondCardInstanceId"]),
        )

    if action_type == "draw_bottom":
        return action_type, handle_draw_bottom(
            game_id=game_id,
            game_player_id=int(action["gamePlayerId"]),
            count=int(action.get("count", 1)),
        )

    if action_type == "shuffle_library":
        return action_type, handle_shuffle_library(
            game_id=game_id,
            game_player_id=int(action["gamePlayerId"]),
        )

    if action_type == "scry_library":
        return action_type, handle_scry_library(
            game_id=game_id,
            game_player_id=int(action["gamePlayerId"]),
            inspected_card_ids=action.get("inspectedCardIds") or [],
            top_card_ids=action.get("topCardIds") or [],
            bottom_card_ids=action.get("bottomCardIds") or [],
        )

    if action_type == "exile_until":
        return action_type, handle_exile_until(
            game_id=game_id,
            game_player_id=int(action["gamePlayerId"]),
            condition=str(action.get("condition") or "land"),
        )

    if action_type == "roll_dice":
        return action_type, handle_roll_dice(
            game_id=game_id,
            game_player_id=int(action["gamePlayerId"]),
            sides=int(action.get("sides", 6)),
            count=int(action.get("count", 1)),
        )

    if action_type == "flip_coins":
        return action_type, handle_flip_coins(
            game_id=game_id,
            game_player_id=int(action["gamePlayerId"]),
            count=int(action.get("count", 1)),
        )

    if action_type == "ai_take_turn":
        return action_type, handle_ai_take_turn(
            game_id=game_id,
            game_player_id=int(action["gamePlayerId"]),
        )

    raise ValueError(f"Unsupported action type: {action_type}")


# -------------------------
# Card routes
# -------------------------

@api_bp.get("/cards")
def list_cards():
    q = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 25)), 100)

    query = Card.query

    if q:
        ilike = f"%{q}%"
        query = query.filter(
            or_(
                Card.name.ilike(ilike),
                Card.oracleText.ilike(ilike),
                Card.typeLine.ilike(ilike),
            )
        )

    if request.args.get("commanderOnly", "").lower() in {"1", "true", "yes"}:
        query = query.filter(
            or_(
                Card.typeLine.ilike("%Legendary Creature%"),
                Card.oracleText.ilike("%can be your commander%"),
                Card.typeLine.ilike("%Legendary Background%"),
            )
        )

    normalized_q = " ".join(q.lower().split())
    relevance = case(
        (func.lower(Card.name) == normalized_q, 0),
        (func.lower(Card.name).like(f"{normalized_q}%"), 1),
        (Card.name.ilike(f"%{q}%"), 2),
        else_=3,
    )
    candidates = (
        query.order_by(relevance.asc(), nullslast(Card.edhrecRank.asc()), Card.name.asc())
        .limit(min(limit * 12, 500))
        .all()
    )

    cards = []
    seen_names: set[str] = set()
    for card in candidates:
        key = (card.name or "").strip().lower()
        if not key or key in seen_names:
            continue
        seen_names.add(key)
        cards.append(card)
        if len(cards) >= limit:
            break

    return jsonify([serialize_card_summary(card) for card in cards])


@api_bp.get("/cards/<string:uuid>")
def get_card(uuid: str):
    card = Card.query.filter_by(uuid=uuid).first_or_404()
    return jsonify(serialize_card_detail(card))


# -------------------------
# Deck routes
# -------------------------

@api_bp.get("/decks")
def list_decks():
    recent_only = str(request.args.get("recent") or "").lower() in {"1", "true", "yes"}
    query = Deck.query
    if recent_only:
        query = query.filter(Deck.lastUsedAt.isnot(None)).order_by(
            Deck.lastUsedAt.desc(),
            Deck.id.desc(),
        )
    else:
        query = query.order_by(Deck.updatedAt.desc(), Deck.id.desc())
    decks = query.all()
    return jsonify([serialize_deck(deck, include_cards=False) for deck in decks])


@api_bp.post("/decks")
def create_deck():
    payload = request.get_json(silent=True) or {}

    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Deck name is required."}), 400

    commander_card_ids = payload.get("commanderCardIds")
    if not isinstance(commander_card_ids, list):
        legacy_commander_id = payload.get("commanderCardId")
        commander_card_ids = [legacy_commander_id] if legacy_commander_id is not None else []
    commander_card_ids = list(dict.fromkeys(commander_card_ids))[:2]
    commander_cards = (
        Card.query.filter(Card.id.in_(commander_card_ids)).all()
        if commander_card_ids
        else []
    )
    commander_by_id = {card.id: card for card in commander_cards}
    commander_cards = [commander_by_id[card_id] for card_id in commander_card_ids if card_id in commander_by_id]
    if len(commander_cards) != len(commander_card_ids):
        return jsonify({"error": "One or more commander cards were not found."}), 404
    if len(commander_cards) == 2 and not commanders_are_compatible(
        commander_cards[0], commander_cards[1]
    ):
        return jsonify({"error": "Those commanders cannot be paired."}), 400

    deck = Deck(
        name=name,
        slug=payload.get("slug"),
        format=payload.get("format") or "commander",
        commanderCount=len(commander_cards) or payload.get("commanderCount") or 1,
        colorIdentity=payload.get("colorIdentity"),
        ownerUserId=payload.get("ownerUserId"),
        sourceType=payload.get("sourceType") or "custom",
        sourceProductId=payload.get("sourceProductId"),
        notes=payload.get("notes"),
        isPublic=bool(payload.get("isPublic", False)),
        folderName=str(payload.get("folderName") or "").strip() or None,
        commanderBracket=payload.get("commanderBracket"),
    )

    db.session.add(deck)
    db.session.flush()

    for commander_card in commander_cards:
        db.session.add(
            DeckCard(
                deckId=deck.id,
                cardId=commander_card.id,
                quantity=1,
                boardType="command",
                isCommander=True,
            )
        )

    db.session.commit()

    return jsonify(serialize_deck(deck, include_cards=True)), 201


@api_bp.get("/decks/<int:deck_id>")
def get_deck(deck_id: int):
    deck = Deck.query.filter_by(id=deck_id).first_or_404()
    return jsonify(serialize_deck(deck, include_cards=True))


@api_bp.post("/decks/<int:deck_id>/used")
def mark_deck_used(deck_id: int):
    deck = Deck.query.filter_by(id=deck_id).first_or_404()
    deck.lastUsedAt = utcnow()
    db.session.commit()
    return jsonify(serialize_deck(deck, include_cards=False))


@api_bp.patch("/decks/<int:deck_id>")
def update_deck(deck_id: int):
    deck = Deck.query.filter_by(id=deck_id).first_or_404()
    payload = request.get_json(silent=True) or {}

    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Deck name is required."}), 400
        deck.name = name
    if "format" in payload:
        deck.format = str(payload.get("format") or "none").strip().lower()
    if "notes" in payload:
        deck.notes = str(payload.get("notes") or "").strip() or None
    if "isPublic" in payload:
        deck.isPublic = bool(payload.get("isPublic"))
    if "folderName" in payload:
        deck.folderName = str(payload.get("folderName") or "").strip() or None
    if "commanderBracket" in payload:
        raw_bracket = payload.get("commanderBracket")
        if raw_bracket in (None, "", 0, "0"):
            deck.commanderBracket = None
        else:
            try:
                bracket = int(raw_bracket)
            except (TypeError, ValueError):
                return jsonify({"error": "Commander bracket must be between 1 and 5."}), 400
            if bracket < 1 or bracket > 5:
                return jsonify({"error": "Commander bracket must be between 1 and 5."}), 400
            deck.commanderBracket = bracket

    db.session.commit()
    return jsonify(serialize_deck(deck, include_cards=True))


@api_bp.put("/decks/<int:deck_id>/commanders")
def replace_deck_commanders(deck_id: int):
    deck = Deck.query.filter_by(id=deck_id).first_or_404()
    payload = request.get_json(silent=True) or {}
    raw_ids = payload.get("commanderCardIds")
    if not isinstance(raw_ids, list):
        return jsonify({"error": "commanderCardIds must be a list."}), 400

    try:
        commander_card_ids = list(dict.fromkeys(int(card_id) for card_id in raw_ids))[:2]
    except (TypeError, ValueError):
        return jsonify({"error": "Commander card IDs must be integers."}), 400

    if deck.format in COMMANDER_FORMATS and not commander_card_ids:
        return jsonify({"error": "This format requires at least one commander."}), 400

    commander_cards = (
        Card.query.filter(Card.id.in_(commander_card_ids)).all()
        if commander_card_ids
        else []
    )
    commander_by_id = {card.id: card for card in commander_cards}
    commander_cards = [
        commander_by_id[card_id]
        for card_id in commander_card_ids
        if card_id in commander_by_id
    ]
    if len(commander_cards) != len(commander_card_ids):
        return jsonify({"error": "One or more commander cards were not found."}), 404
    if any(not card_can_be_commander(card) for card in commander_cards):
        return jsonify({"error": "One or more selected cards cannot be a commander."}), 400
    if len(commander_cards) == 2 and not commanders_are_compatible(
        commander_cards[0], commander_cards[1]
    ):
        return jsonify({"error": "Those commanders cannot be paired."}), 400

    target_ids = set(commander_card_ids)
    current_entries = cast(list[DeckCard], deck.cards or [])

    for entry in current_entries:
        if entry.isCommander and entry.cardId not in target_ids:
            db.session.delete(entry)

    db.session.flush()

    for commander_card in commander_cards:
        existing_command = DeckCard.query.filter_by(
            deckId=deck.id,
            cardId=commander_card.id,
            boardType="command",
        ).first()
        if existing_command is not None:
            existing_command.quantity = 1
            existing_command.isCommander = True
            continue

        existing_copy = (
            DeckCard.query.filter_by(deckId=deck.id, cardId=commander_card.id)
            .order_by(
                case((DeckCard.boardType == "main", 0), else_=1),
                DeckCard.id.asc(),
            )
            .first()
        )
        if existing_copy is not None and existing_copy.quantity == 1:
            existing_copy.boardType = "command"
            existing_copy.isCommander = True
            continue
        if existing_copy is not None and existing_copy.quantity > 1:
            existing_copy.quantity -= 1

        db.session.add(
            DeckCard(
                deckId=deck.id,
                cardId=commander_card.id,
                quantity=1,
                boardType="command",
                isCommander=True,
            )
        )

    sync_deck_commander_count(deck)
    db.session.commit()
    return jsonify(serialize_deck(deck, include_cards=True))


@api_bp.delete("/decks/<int:deck_id>")
def delete_deck(deck_id: int):
    deck = Deck.query.filter_by(id=deck_id).first_or_404()
    db.session.delete(deck)
    db.session.commit()
    return jsonify({"ok": True, "deckId": deck_id})


@api_bp.post("/decks/<int:deck_id>/cards")
def add_card_to_deck(deck_id: int):
    deck = Deck.query.filter_by(id=deck_id).first_or_404()
    payload = request.get_json(silent=True) or {}

    card_id = payload.get("cardId")
    if not card_id:
        return jsonify({"error": "cardId is required."}), 400

    card = Card.query.filter_by(id=card_id).first()
    if card is None:
        return jsonify({"error": "Card not found."}), 404

    try:
        quantity = int(payload.get("quantity", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "quantity must be an integer."}), 400

    if quantity < 1:
        return jsonify({"error": "quantity must be at least 1."}), 400

    board_type = (payload.get("boardType") or "main").strip()
    is_commander = bool(payload.get("isCommander", False))
    preferred_printing_id = payload.get("preferredPrintingId")
    if is_commander:
        if not card_can_be_commander(card):
            return jsonify({"error": "That card is not eligible to be a commander."}), 400
        other_commanders = [
            candidate
            for candidate in cast(list[DeckCard], deck.cards or [])
            if candidate.isCommander and candidate.card is not None
        ]
        if len(other_commanders) >= 2:
            return jsonify({"error": "A deck can have at most two paired commanders."}), 400
        if other_commanders and not commanders_are_compatible(
            cast(Card, other_commanders[0].card), card
        ):
            return jsonify({"error": "That card cannot be paired with the current commander."}), 400
        board_type = "command"
        quantity = 1

    existing_entry = DeckCard.query.filter_by(
        deckId=deck.id,
        cardId=card.id,
        boardType=board_type,
    ).first()

    if existing_entry:
        existing_entry.quantity = 1 if is_commander else existing_entry.quantity + quantity
        if preferred_printing_id is not None:
            existing_entry.preferredPrintingId = preferred_printing_id
        if is_commander:
            existing_entry.isCommander = True
        sync_deck_commander_count(deck)
        db.session.commit()
        return jsonify(serialize_deck_card(existing_entry)), 200

    deck_card = DeckCard(
        deckId=deck.id,
        cardId=card.id,
        preferredPrintingId=preferred_printing_id,
        quantity=quantity,
        boardType=board_type,
        isCommander=is_commander,
    )

    db.session.add(deck_card)
    sync_deck_commander_count(deck)
    db.session.commit()

    return jsonify(serialize_deck_card(deck_card)), 201


@api_bp.patch("/decks/<int:deck_id>/cards/<int:deck_card_id>")
def update_deck_card(deck_id: int, deck_card_id: int):
    deck = Deck.query.filter_by(id=deck_id).first_or_404()
    entry = DeckCard.query.filter_by(id=deck_card_id, deckId=deck.id).first()
    if entry is None:
        return jsonify({"error": "Deck card entry not found."}), 404

    payload = request.get_json(silent=True) or {}
    quantity = entry.quantity
    if "quantity" in payload:
        try:
            quantity = int(payload.get("quantity"))
        except (TypeError, ValueError):
            return jsonify({"error": "quantity must be an integer."}), 400
        if quantity < 1:
            return jsonify({"error": "quantity must be at least 1."}), 400

    board_type = str(payload.get("boardType", entry.boardType) or "main").strip().lower()
    if board_type not in DECK_BOARD_TYPES:
        return jsonify({"error": "Unsupported board type."}), 400

    is_commander = bool(payload.get("isCommander", entry.isCommander))
    card = cast(Card, entry.card)
    if is_commander:
        if not card_can_be_commander(card):
            return jsonify({"error": "That card is not eligible to be a commander."}), 400
        other_commanders = [
            candidate
            for candidate in cast(list[DeckCard], deck.cards or [])
            if candidate.id != entry.id and candidate.isCommander and candidate.card is not None
        ]
        if len(other_commanders) >= 2:
            return jsonify({"error": "A deck can have at most two paired commanders."}), 400
        if other_commanders and not commanders_are_compatible(
            cast(Card, other_commanders[0].card), card
        ):
            return jsonify({"error": "That card cannot be paired with the current commander."}), 400
        board_type = "command"
        quantity = 1
    elif entry.isCommander and "isCommander" in payload:
        board_type = "main" if board_type == "command" else board_type

    collision = DeckCard.query.filter_by(
        deckId=deck.id,
        cardId=entry.cardId,
        boardType=board_type,
    ).first()
    if collision is not None and collision.id != entry.id:
        collision.quantity = 1 if is_commander else collision.quantity + quantity
        collision.isCommander = collision.isCommander or is_commander
        if entry.preferredPrintingId is not None:
            collision.preferredPrintingId = entry.preferredPrintingId
        db.session.delete(entry)
    else:
        entry.quantity = quantity
        entry.boardType = board_type
        entry.isCommander = is_commander
        if "preferredPrintingId" in payload:
            entry.preferredPrintingId = payload.get("preferredPrintingId")

    sync_deck_commander_count(deck)
    db.session.commit()
    return jsonify(serialize_deck(deck, include_cards=True))


@api_bp.delete("/decks/<int:deck_id>/cards/<int:deck_card_id>")
def remove_card_from_deck(deck_id: int, deck_card_id: int):
    deck = Deck.query.filter_by(id=deck_id).first_or_404()

    deck_card = DeckCard.query.filter_by(id=deck_card_id, deckId=deck.id).first()
    if deck_card is None:
        return jsonify({"error": "Deck card entry not found."}), 404

    db.session.delete(deck_card)
    sync_deck_commander_count(deck)
    db.session.commit()

    return jsonify({"ok": True, "deletedDeckCardId": deck_card_id})


def parse_deck_list_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", "//")):
        return None

    with_printing = re.match(
        r"^(\d+)\s+(.+?)\s+\(([^)]+)\)\s+(\S+)(?:\s+.*)?$",
        stripped,
    )
    if with_printing:
        return {
            "quantity": int(with_printing.group(1)),
            "name": with_printing.group(2).strip(),
            "setCode": with_printing.group(3).strip(),
            "collectorNumber": with_printing.group(4).strip().rstrip("★"),
        }

    name_only = re.match(r"^(\d+)\s+(.+?)\s*$", stripped)
    if name_only:
        return {
            "quantity": int(name_only.group(1)),
            "name": name_only.group(2).strip(),
            "setCode": None,
            "collectorNumber": None,
        }
    raise ValueError("Expected “quantity card name (SET) collector-number”.")


def resolve_deck_list_card(parsed: dict[str, Any]) -> tuple[Card | None, Printing | None]:
    name = parsed["name"]
    name_options = [name]
    if " / " in name and " // " not in name:
        name_options.append(name.replace(" / ", " // "))

    printing = None
    if parsed.get("setCode") and parsed.get("collectorNumber"):
        printing = (
            Printing.query
            .join(Set, Printing.setId == Set.id)
            .join(Card, Printing.cardId == Card.id)
            .filter(
                func.lower(Set.code) == parsed["setCode"].lower(),
                func.lower(Printing.collectorNumber) == parsed["collectorNumber"].lower(),
                or_(*[func.lower(Card.name) == option.lower() for option in name_options]),
            )
            .first()
        )
        if printing is not None:
            return cast(Card, printing.card), printing

    card = (
        Card.query
        .filter(or_(*[func.lower(Card.name) == option.lower() for option in name_options]))
        .order_by(nullslast(Card.edhrecRank.asc()), Card.id.asc())
        .first()
    )
    if card is None:
        return None, None
    printing = (
        Printing.query
        .filter_by(cardId=card.id)
        .order_by(Printing.id.asc())
        .first()
    )
    return card, printing


@api_bp.post("/decks/<int:deck_id>/cards/bulk")
def bulk_add_deck_cards(deck_id: int):
    deck = Deck.query.filter_by(id=deck_id).first_or_404()
    payload = request.get_json(silent=True) or {}
    board_type = (payload.get("boardType") or "main").strip().lower()
    mode = (payload.get("mode") or "merge").strip().lower()
    deck_text = payload.get("text") or ""

    if board_type not in DECK_BOARD_TYPES - {"command"}:
        return jsonify({"error": "Unsupported board type."}), 400
    if mode not in {"merge", "replace"}:
        return jsonify({"error": "mode must be merge or replace."}), 400
    if not isinstance(deck_text, str) or not deck_text.strip():
        return jsonify({"error": "Paste or import at least one card line."}), 400

    resolved: list[tuple[dict[str, Any], Card, Printing | None]] = []
    issues: list[dict[str, Any]] = []
    for line_number, line in enumerate(deck_text.splitlines(), start=1):
        try:
            parsed = parse_deck_list_line(line)
            if parsed is None:
                continue
            if parsed["quantity"] < 1:
                raise ValueError("Quantity must be at least 1.")
            card, printing = resolve_deck_list_card(parsed)
            if card is None:
                issues.append(
                    {"line": line_number, "text": line, "error": f'Card “{parsed["name"]}” was not found.'}
                )
                continue
            resolved.append((parsed, card, printing))
        except ValueError as error:
            issues.append({"line": line_number, "text": line, "error": str(error)})

    if not resolved:
        return jsonify({"error": "No cards could be resolved.", "issues": issues}), 400

    if mode == "replace":
        DeckCard.query.filter_by(deckId=deck.id, boardType=board_type).delete()
        db.session.flush()

    imported_quantity = 0
    for parsed, card, printing in resolved:
        existing = DeckCard.query.filter_by(
            deckId=deck.id,
            cardId=card.id,
            boardType=board_type,
        ).first()
        if existing:
            existing.quantity += parsed["quantity"]
            if printing is not None:
                existing.preferredPrintingId = printing.id
        else:
            db.session.add(
                DeckCard(
                    deckId=deck.id,
                    cardId=card.id,
                    preferredPrintingId=printing.id if printing is not None else None,
                    quantity=parsed["quantity"],
                    boardType=board_type,
                    isCommander=False,
                )
            )
        imported_quantity += parsed["quantity"]

    db.session.commit()
    return jsonify(
        {
            "ok": True,
            "boardType": board_type,
            "mode": mode,
            "resolvedLines": len(resolved),
            "importedQuantity": imported_quantity,
            "issues": issues,
            "deck": serialize_deck(deck, include_cards=True),
        }
    )


@api_bp.post("/decks/<int:deck_id>/boards/swap")
def swap_deck_board(deck_id: int):
    deck = Deck.query.filter_by(id=deck_id).first_or_404()
    payload = request.get_json(silent=True) or {}
    source = (payload.get("sourceBoard") or "").strip().lower()
    target = (payload.get("targetBoard") or "").strip().lower()
    movable_boards = DECK_BOARD_TYPES - {"command"}

    if source not in movable_boards or target not in movable_boards:
        return jsonify({"error": "Unsupported board type."}), 400
    if source == target:
        return jsonify({"error": "Choose a different destination board."}), 400

    source_entries = DeckCard.query.filter_by(deckId=deck.id, boardType=source).all()
    moved_quantity = 0
    for entry in source_entries:
        target_entry = DeckCard.query.filter_by(
            deckId=deck.id,
            cardId=entry.cardId,
            boardType=target,
        ).first()
        if target_entry:
            target_entry.quantity += entry.quantity
            if entry.preferredPrintingId is not None:
                target_entry.preferredPrintingId = entry.preferredPrintingId
            db.session.delete(entry)
        else:
            entry.boardType = target
        moved_quantity += entry.quantity

    db.session.commit()
    return jsonify(
        {
            "ok": True,
            "sourceBoard": source,
            "targetBoard": target,
            "movedQuantity": moved_quantity,
            "deck": serialize_deck(deck, include_cards=True),
        }
    )


# -------------------------
# Game routes
# -------------------------

@api_bp.post("/games")
def create_game():
    payload = request.get_json(silent=True) or {}

    players_payload = payload.get("players") or []
    game_mode = str(payload.get("gameMode") or "pvp").strip().lower()
    if game_mode not in LOBBY_GAME_MODES:
        return jsonify({"error": "Unsupported game mode."}), 400
    minimum_players = 1 if game_mode == "goldfish" else 2
    try:
        player_count = int(
            payload.get("playerCount")
            or max(minimum_players, len(players_payload) or minimum_players)
        )
    except (TypeError, ValueError):
        return jsonify({"error": "playerCount must be an integer."}), 400
    if player_count < minimum_players or player_count > 8:
        return jsonify({
            "error": f"playerCount must be between {minimum_players} and 8."
        }), 400

    lobby_name = str(payload.get("lobbyName") or "").strip()
    if "lobbyName" in payload and not lobby_name:
        return jsonify({"error": "Lobby name is required."}), 400
    if len(lobby_name) > 80:
        return jsonify({"error": "Lobby name must be 80 characters or fewer."}), 400

    ruleset = str(payload.get("ruleset") or "casual").strip().lower()
    if ruleset not in LOBBY_RULESETS:
        return jsonify({"error": "Unsupported lobby ruleset."}), 400

    password = str(payload.get("password") or "")
    if password and len(password) < 4:
        return jsonify({"error": "Lobby passwords must be at least 4 characters."}), 400
    if len(password) > 128:
        return jsonify({"error": "Lobby passwords must be 128 characters or fewer."}), 400
    participant_token = str(payload.get("participantToken") or "")
    if lobby_name and len(participant_token) < 16:
        return jsonify({"error": "A valid participant token is required to host a lobby."}), 400

    game_status = "pending" if lobby_name or game_mode == "pvp" else "active"

    if not players_payload:
        host_deck_id = payload.get("hostDeckId")
        if host_deck_id is None:
            return jsonify({"error": "hostDeckId is required when players are not provided."}), 400

        players_payload = [
            {
                "seatNumber": 1,
                "playerType": "human",
                "deckId": host_deck_id,
                "userId": payload.get("userId"),
            }
        ]
        for seat_number in range(2, player_count + 1):
            players_payload.append(
                {
                    "seatNumber": seat_number,
                    "playerType": "human",
                    "deckId": None,
                    "userId": None,
                }
            )

    if len(players_payload) < minimum_players:
        return jsonify({
            "error": f"At least {minimum_players} player{' is' if minimum_players == 1 else 's are'} required."
        }), 400

    game = Game(
        gameMode=game_mode,
        format=payload.get("format") or "commander",
        status=game_status,
        lobbyName=lobby_name or None,
        ruleset=ruleset,
        maxPlayers=player_count,
        passwordHash=generate_password_hash(password) if password else None,
        hostUserId=payload.get("userId"),
        startedAt=utcnow() if game_status == "active" else None,
        notes=payload.get("notes"),
        engineVersion=payload.get("engineVersion") or "pre-rules-engine",
        rulesVersion=payload.get("rulesVersion") or "transport-only",
        rngSeed=str(payload.get("rngSeed") or random.SystemRandom().getrandbits(64)),
    )
    db.session.add(game)
    db.session.flush()

    for index, player_payload in enumerate(players_payload, start=1):
        deck_id = player_payload.get("deckId")
        if deck_id is not None:
            selected_deck = Deck.query.filter_by(id=deck_id).first()
            if selected_deck is None:
                db.session.rollback()
                return jsonify({"error": f"Deck {deck_id} was not found."}), 404
            selected_deck.lastUsedAt = utcnow()

        player = GamePlayer(
            gameId=game.id,
            seatNumber=int(player_payload.get("seatNumber") or index),
            playerType=player_payload.get("playerType") or "human",
            userId=player_payload.get("userId"),
            aiProfile=player_payload.get("aiProfile"),
            deckId=deck_id,
            deckVersionId=player_payload.get("deckVersionId"),
            startingLife=int(player_payload.get("startingLife") or 40),
            startingHandSize=int(player_payload.get("startingHandSize") or 7),
            isReady=False,
            isHost=bool(int(player_payload.get("seatNumber") or index) == 1),
            lobbyTokenHash=(
                generate_password_hash(participant_token)
                if participant_token
                and player_payload.get("playerType", "human") == "human"
                and int(player_payload.get("seatNumber") or index) == 1
                else None
            ),
        )
        db.session.add(player)

    db.session.flush()

    initial_snapshot = StateSnapshot(
        gameId=game.id,
        sequenceNumber=0,
        turnNumber=1,
        phase="beginning",
        stateJson=build_initial_state(game),
    )
    db.session.add(initial_snapshot)
    db.session.commit()

    if game_status == "active":
        _seed_game_from_decks(game)
        _deal_opening_hands(game)
        db.session.commit()

    if lobby_name:
        emit_lobby_change(game, "created")
    return jsonify(
        serialize_game_for_participant(game, participant_token, include_snapshot=True)
    ), 201


@api_bp.get("/games")
def list_games():
    status = request.args.get("status")
    search = str(request.args.get("q") or "").strip()
    game_mode = str(request.args.get("gameMode") or "").strip().lower()
    ruleset = str(request.args.get("ruleset") or "").strip().lower()

    query = Game.query
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(Game.lobbyName.ilike(f"%{search}%"))
    if game_mode:
        query = query.filter_by(gameMode=game_mode)
    if ruleset:
        query = query.filter_by(ruleset=ruleset)

    games = query.order_by(
        cast(Any, getattr(Game, "createdAt")).desc(),
        cast(Any, getattr(Game, "id")).desc(),
    ).limit(100).all()

    return jsonify([serialize_game(game, include_players=True, include_snapshot=False) for game in games])


@api_bp.get("/games/<int:game_id>")
def get_game(game_id: int):
    game = Game.query.filter_by(id=game_id).first_or_404()
    participant_token = request.headers.get("X-Lobby-Token") or request.args.get("participantToken")
    return jsonify(serialize_game_for_participant(game, participant_token, include_snapshot=True))


def _first_printing_id_for_card(card_id: int) -> int | None:
    printing = (
        Printing.query.filter_by(cardId=card_id)
        .order_by(cast(Any, Printing.id).asc())
        .first()
    )
    return printing.id if printing else None


def _seed_game_from_decks(game: Game) -> None:
    existing_instances = CardInstance.query.filter_by(gameId=game.id).count()
    if existing_instances > 0:
        return

    players = sorted(cast(list[GamePlayer], game.players or []), key=lambda player: player.seatNumber)

    for player in players:
        if not player.deckId:
            continue

        deck_cards = cast(
            list[DeckCard],
            DeckCard.query.filter_by(deckId=player.deckId)
            .order_by(cast(Any, DeckCard.id).asc())
            .all(),
        )

        library_entries: list[tuple[int, int | None]] = []
        command_entries: list[tuple[int, int | None]] = []

        for deck_card in deck_cards:
            preferred_printing_id = deck_card.preferredPrintingId or _first_printing_id_for_card(deck_card.cardId)

            for _ in range(deck_card.quantity):
                if deck_card.isCommander or deck_card.boardType == "command":
                    command_entries.append((deck_card.cardId, preferred_printing_id))
                else:
                    library_entries.append((deck_card.cardId, preferred_printing_id))

        # Each player gets an independent, reproducible shuffle derived from the
        # persisted game seed. Re-fetching or restarting the server cannot change
        # how a newly seeded game was ordered.
        random.Random(f"{game.rngSeed}:{player.seatNumber}").shuffle(library_entries)

        for index, (card_id, printing_id) in enumerate(library_entries):
            db.session.add(
                CardInstance(
                    gameId=game.id,
                    gamePlayerId=player.id,
                    cardId=card_id,
                    printingId=printing_id,
                    instanceType="deckCard",
                    zone="library",
                    zoneIndex=index,
                )
            )

        for index, (card_id, printing_id) in enumerate(command_entries):
            db.session.add(
                CardInstance(
                    gameId=game.id,
                    gamePlayerId=player.id,
                    cardId=card_id,
                    printingId=printing_id,
                    instanceType="deckCard",
                    zone="command",
                    zoneIndex=index,
                    isCommander=True,
                )
            )


def _deal_opening_hands(game: Game) -> None:
    db.session.flush()
    for player in sorted(
        cast(list[GamePlayer], game.players or []),
        key=lambda candidate: candidate.seatNumber,
    ):
        if not player.deckId:
            continue
        existing_hand = CardInstance.query.filter_by(
            gameId=game.id,
            gamePlayerId=player.id,
            zone="hand",
        ).count()
        if existing_hand:
            continue
        cards = ordered_library_cards(game.id, player.id)[: int(player.startingHandSize or 7)]
        for index, card in enumerate(cards):
            card.zone = "hand"
            card.zoneIndex = index
        create_game_event(
            game.id,
            player.id,
            "draw_opening_hand",
            {
                "gamePlayerId": player.id,
                "count": len(cards),
                "cardInstanceIds": [card.id for card in cards],
            },
        )


@api_bp.post("/games/<int:game_id>/join")
def join_game(game_id: int):
    game = Game.query.filter_by(id=game_id).with_for_update().first_or_404()
    payload = request.get_json(silent=True) or {}

    if game.status != "pending":
        return jsonify({"error": "Only pending games can be joined."}), 400
    if game.passwordHash and not check_password_hash(
        game.passwordHash,
        str(payload.get("password") or ""),
    ):
        return jsonify({"error": "Incorrect lobby password."}), 403
    participant_token = str(payload.get("participantToken") or "")
    if game.lobbyName and len(participant_token) < 16:
        return jsonify({"error": "A valid participant token is required to join."}), 400
    if lobby_player_for_token(game, participant_token) is not None:
        return jsonify({"error": "This browser has already joined the lobby."}), 409

    deck_id = payload.get("deckId")
    if not deck_id:
        return jsonify({"error": "deckId is required."}), 400

    deck = Deck.query.filter_by(id=deck_id).first()
    if deck is None:
        return jsonify({"error": f"Deck {deck_id} was not found."}), 404
    deck.lastUsedAt = utcnow()

    players = sorted(cast(list[GamePlayer], game.players or []), key=lambda player: player.seatNumber)
    requested_seat = payload.get("seatNumber")
    if requested_seat is not None:
        try:
            requested_seat = int(requested_seat)
        except (TypeError, ValueError):
            return jsonify({"error": "seatNumber must be an integer."}), 400

        open_player = next(
            (
                player
                for player in players
                if player.seatNumber == requested_seat
                and not player.deckId
                and player.playerType == "human"
            ),
            None,
        )
        if open_player is None:
            return jsonify({"error": f"Seat {requested_seat} is not open."}), 400
    else:
        open_player = next(
            (player for player in players if not player.deckId and player.playerType == "human"),
            None,
        )

    if open_player is None:
        return jsonify({"error": "No open seats remain in this game."}), 400

    open_player.deckId = deck_id
    open_player.isReady = False
    open_player.lobbyTokenHash = generate_password_hash(participant_token) if participant_token else None
    if payload.get("userId") is not None:
        open_player.userId = payload.get("userId")

    db.session.commit()

    updated_game = Game.query.filter_by(id=game_id).first_or_404()
    response = serialize_game_for_participant(
        updated_game,
        participant_token,
        include_snapshot=True,
    )
    emit_lobby_change(updated_game, "joined")
    return jsonify(response)


@api_bp.post("/games/<int:game_id>/ready")
def set_lobby_ready(game_id: int):
    game = Game.query.filter_by(id=game_id).with_for_update().first_or_404()
    payload = request.get_json(silent=True) or {}
    if game.status != "pending":
        return jsonify({"error": "Readiness can only change while a lobby is pending."}), 400

    participant_token = str(payload.get("participantToken") or "")
    player = lobby_player_for_token(game, participant_token)
    if player is None or not player.deckId:
        return jsonify({"error": "You have not joined this lobby."}), 403

    player.isReady = bool(payload.get("ready", True))
    db.session.commit()
    updated_game = Game.query.filter_by(id=game_id).first_or_404()
    emit_lobby_change(updated_game, "ready")
    return jsonify(
        serialize_game_for_participant(updated_game, participant_token, include_snapshot=True)
    )


@api_bp.post("/games/<int:game_id>/sleeve")
def set_lobby_sleeve(game_id: int):
    game = Game.query.filter_by(id=game_id).with_for_update().first_or_404()
    payload = request.get_json(silent=True) or {}
    if game.status != "pending":
        return jsonify({"error": "Sleeves can only be changed while a lobby is pending."}), 400

    participant_token = str(payload.get("participantToken") or "")
    player = lobby_player_for_token(game, participant_token)
    if player is None or not player.deckId:
        return jsonify({"error": "You have not joined this lobby."}), 403

    sleeve_style = str(payload.get("sleeveStyle") or "").strip().lower()
    if sleeve_style not in SLEEVE_STYLES:
        return jsonify({"error": "Unsupported sleeve style."}), 400

    player.sleeveStyle = sleeve_style
    db.session.commit()
    updated_game = Game.query.filter_by(id=game_id).first_or_404()
    emit_lobby_change(updated_game, "sleeve_changed")
    return jsonify(
        serialize_game_for_participant(updated_game, participant_token, include_snapshot=True)
    )


@api_bp.post("/games/<int:game_id>/leave")
def leave_lobby(game_id: int):
    game = Game.query.filter_by(id=game_id).with_for_update().first_or_404()
    payload = request.get_json(silent=True) or {}
    if game.status != "pending":
        return jsonify({"error": "Only pending lobbies can be left."}), 400

    participant_token = str(payload.get("participantToken") or "")
    player = lobby_player_for_token(game, participant_token)
    if player is None:
        return jsonify({"error": "You have not joined this lobby."}), 403
    if player.isHost:
        return jsonify({"error": "The host must close the lobby instead of leaving it."}), 400

    player_key = (game_id, player.id)
    for sid in LOBBY_PLAYER_SOCKETS.pop(player_key, set()):
        LOBBY_SOCKET_PLAYERS.pop(sid, None)
    LOBBY_DISCONNECT_MARKERS.pop(player_key, None)
    player.deckId = None
    player.deckVersionId = None
    player.userId = None
    player.isReady = False
    player.isConnected = False
    player.disconnectedAt = None
    player.lobbyTokenHash = None
    db.session.commit()
    updated_game = Game.query.filter_by(id=game_id).first_or_404()
    emit_lobby_change(updated_game, "left")
    return jsonify({"ok": True, "gameId": game_id})


@api_bp.delete("/games/<int:game_id>")
def close_lobby(game_id: int):
    game = Game.query.filter_by(id=game_id).with_for_update().first_or_404()
    payload = request.get_json(silent=True) or {}
    if game.status != "pending":
        return jsonify({"error": "Only pending lobbies can be closed."}), 400

    participant_token = str(payload.get("participantToken") or "")
    player = lobby_player_for_token(game, participant_token)
    if player is None or not player.isHost:
        return jsonify({"error": "Only the lobby host can close this lobby."}), 403

    db.session.delete(game)
    db.session.commit()
    socketio.emit(
        "lobbies:updated",
        {"gameId": game_id, "game": None, "action": "closed"},
    )
    socketio.emit(
        "game:lobby_closed",
        {"gameId": game_id},
        to=game_room(game_id),
    )
    return jsonify({"ok": True, "gameId": game_id})


@api_bp.post("/games/<int:game_id>/start")
def start_game(game_id: int):
    game = Game.query.filter_by(id=game_id).with_for_update().first_or_404()
    payload = request.get_json(silent=True) or {}
    participant_token = str(payload.get("participantToken") or "")
    force_start = bool(payload.get("force", False))

    if game.status == "active":
        active_game = (
            Game.query.options(
                selectinload(cast(Any, Game.players))
                .selectinload(cast(Any, GamePlayer.cardInstances))
                .selectinload(cast(Any, CardInstance.card)),
                selectinload(cast(Any, Game.players))
                .selectinload(cast(Any, GamePlayer.cardInstances))
                .selectinload(cast(Any, CardInstance.printing))
                .selectinload(cast(Any, Printing.printingImages)),
            )
            .filter_by(id=game_id)
            .first_or_404()
        )
        state = serialize_game_state(active_game)
        return jsonify({
            "gameId": game_id,
            "state": state,
            "game": serialize_game(active_game, include_players=True, include_snapshot=True),
        })

    players = sorted(cast(list[GamePlayer], game.players or []), key=lambda player: player.seatNumber)
    if game.lobbyName:
        host = lobby_player_for_token(game, participant_token)
        if host is None or not host.isHost:
            return jsonify({"error": "Only the lobby host can start this game."}), 403

        occupied_players = [player for player in players if player.deckId]
        if len(occupied_players) < 2:
            return jsonify({"error": "At least two players must join before starting."}), 400

        reasons = []
        if len(occupied_players) < (game.maxPlayers or len(players)):
            reasons.append(
                f"Only {len(occupied_players)} of {game.maxPlayers or len(players)} seats are filled. "
                f"Starting now will make this a {len(occupied_players)}-player game and close the empty seats."
            )
        not_ready = [player for player in occupied_players if not player.isReady]
        if not_ready:
            reasons.append(
                f"{len(not_ready)} seated player{' has' if len(not_ready) == 1 else 's have'} not marked ready."
            )
        if reasons and not force_start:
            return jsonify({
                "error": "The lobby is not fully ready.",
                "requiresConfirmation": True,
                "reasons": reasons,
            }), 409
        if force_start:
            for empty_player in [player for player in players if not player.deckId]:
                db.session.delete(empty_player)
            game.maxPlayers = len(occupied_players)
            db.session.flush()
            players = occupied_players

    if len(players) < 2:
        return jsonify({"error": "At least two players are required."}), 400

    if any(not player.deckId for player in players):
        return jsonify({"error": "All players must join and select a deck before starting."}), 400

    game.status = "active"
    if not game.startedAt:
        game.startedAt = utcnow()
    occupied_players = sorted(
        [player for player in cast(list[GamePlayer], game.players or []) if player.deckId],
        key=lambda player: player.seatNumber,
    )
    game.turnNumber = 1
    game.activeSeatNumber = occupied_players[0].seatNumber if occupied_players else 1

    _seed_game_from_decks(game)
    _deal_opening_hands(game)
    db.session.commit()

    active_game = (
        Game.query.options(
            selectinload(cast(Any, Game.players))
            .selectinload(cast(Any, GamePlayer.cardInstances))
            .selectinload(cast(Any, CardInstance.card)),
            selectinload(cast(Any, Game.players))
            .selectinload(cast(Any, GamePlayer.cardInstances))
            .selectinload(cast(Any, CardInstance.printing))
            .selectinload(cast(Any, Printing.printingImages)),
        )
        .filter_by(id=game_id)
        .first_or_404()
    )

    state = serialize_game_state(active_game)
    game_payload = serialize_game(active_game, include_players=True, include_snapshot=True)

    socketio.emit(
        "game:state_updated",
        {
            "gameId": game_id,
            "actionType": "start_game",
            "state": state,
        },
        to=game_room(game_id),
    )
    socketio.emit(
        "lobbies:updated",
        {"gameId": game_id, "game": serialize_game(active_game, include_players=True, include_snapshot=False), "action": "started"},
    )

    return jsonify({"gameId": game_id, "state": state, "game": game_payload})

@api_bp.get("/games/<int:game_id>/events")
def get_game_events(game_id: int):
    Game.query.filter_by(id=game_id).first_or_404()
    events = cast(
        list[GameEvent],
        GameEvent.query.filter_by(gameId=game_id)
        .order_by(
            cast(Any, getattr(GameEvent, "sequenceNumber")).asc(),
            cast(Any, getattr(GameEvent, "id")).asc(),
        )
        .all(),
    )
    return jsonify([serialize_event(event) for event in events])


@api_bp.get("/games/<int:game_id>/state")
def get_game_state(game_id: int):
    game = (
        Game.query.options(
            selectinload(cast(Any, Game.players))
            .selectinload(cast(Any, GamePlayer.cardInstances))
            .selectinload(cast(Any, CardInstance.card)),
            selectinload(cast(Any, Game.players))
            .selectinload(cast(Any, GamePlayer.cardInstances))
            .selectinload(cast(Any, CardInstance.printing))
            .selectinload(cast(Any, Printing.printingImages)),
        )
        .filter_by(id=game_id)
        .first_or_404()
    )

    return jsonify(serialize_game_state(game))


@api_bp.post("/games/<int:game_id>/library/peek")
def peek_game_library(game_id: int):
    game = Game.query.filter_by(id=game_id).first_or_404()
    payload = request.get_json(silent=True) or {}
    participant_token = str(payload.get("participantToken") or "")
    player = lobby_player_for_token(game, participant_token)
    if not player:
        return jsonify({"error": "You do not control a player in this game."}), 403

    until_condition = str(payload.get("untilCondition") or "").strip().lower()
    matched = None
    if until_condition:
        try:
            cards, matched = library_cards_through_condition(game_id, player.id, until_condition)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
    else:
        try:
            count = max(1, min(int(payload.get("count") or 5), 20))
        except (TypeError, ValueError):
            return jsonify({"error": "Peek count must be an integer."}), 400
        cards = ordered_library_cards(game_id, player.id)[:count]
    return jsonify({
        "gameId": game_id,
        "gamePlayerId": player.id,
        "count": len(cards),
        "untilCondition": until_condition or None,
        "matched": matched,
        "cards": [serialize_card_instance(card) for card in cards],
    })


@api_bp.post("/games/<int:game_id>/concede")
def concede_game(game_id: int):
    game = Game.query.filter_by(id=game_id).with_for_update().first_or_404()
    payload = request.get_json(silent=True) or {}
    if game.status != "active":
        return jsonify({"error": "Only active games can be conceded."}), 400

    participant_token = str(payload.get("participantToken") or "")
    player = lobby_player_for_token(game, participant_token)
    if not player:
        return jsonify({"error": "You do not control a player in this game."}), 403

    player.result = "loss"
    active_players = [
        candidate
        for candidate in cast(list[GamePlayer], game.players or [])
        if candidate.deckId and candidate.result != "loss"
    ]
    if len(active_players) == 1:
        winner = active_players[0]
        winner.result = "win"
        winner.finalPlacement = 1
        game.winnerGamePlayerId = winner.id
        game.status = "completed"
        game.endedAt = utcnow()
    elif len(active_players) == 0:
        game.status = "completed"
        game.endedAt = utcnow()

    create_game_event(
        game_id,
        player.id,
        "concede_game",
        {"gamePlayerId": player.id, "gameCompleted": game.status == "completed"},
    )
    db.session.commit()
    state = serialize_game_state(game)
    socketio.emit(
        "game:state_updated",
        {"gameId": game_id, "actionType": "concede_game", "state": state},
        to=game_room(game_id),
    )
    return jsonify({"ok": True, "gameId": game_id, "state": state})


@api_bp.post("/games/<int:game_id>/actions")
def post_game_action(game_id: int):
    payload = request.get_json(force=True) or {}
    action = payload.get("action", payload)
    action_type, state = dispatch_game_action(game_id, action)

    socketio.emit(
        "game:state_updated",
        {
            "gameId": game_id,
            "actionType": action_type,
            "state": state,
        },
        to=game_room(game_id),
    )

    return jsonify(
        {
            "gameId": game_id,
            "actionType": action_type,
            "state": state,
        }
    )


# -------------------------
# Socket.IO handlers
# -------------------------

def expire_disconnected_lobby_player(
    app,
    game_id: int,
    player_id: int,
    disconnect_marker: str,
) -> None:
    socketio.sleep(LOBBY_DISCONNECT_GRACE_SECONDS)
    player_key = (game_id, player_id)
    if LOBBY_DISCONNECT_MARKERS.get(player_key) != disconnect_marker:
        return

    with app.app_context():
        player = db.session.get(GamePlayer, player_id)
        game = db.session.get(Game, game_id)
        if (
            not player
            or not game
            or player.isConnected
            or LOBBY_PLAYER_SOCKETS.get(player_key)
        ):
            return

        # Started games retain their seats and token indefinitely so a player can
        # recover after a longer network interruption.
        if game.status != "pending":
            return

        LOBBY_DISCONNECT_MARKERS.pop(player_key, None)
        if player.isHost:
            db.session.delete(game)
            db.session.commit()
            socketio.emit("game:lobby_closed", {"gameId": game_id}, to=game_room(game_id))
            socketio.emit("lobbies:updated", {"gameId": game_id, "action": "closed"})
            return

        player.deckId = None
        player.deckVersionId = None
        player.userId = None
        player.isReady = False
        player.lobbyTokenHash = None
        player.isConnected = False
        player.disconnectedAt = None
        db.session.commit()
        emit_lobby_change(game, "player_timed_out")


def register_socket_handlers(socketio) -> None:
    global SOCKET_HANDLERS_REGISTERED
    if SOCKET_HANDLERS_REGISTERED:
        return
    SOCKET_HANDLERS_REGISTERED = True

    @socketio.on("lobby:presence")
    def handle_lobby_presence(payload):
        try:
            game_id = int(payload.get("gameId"))
        except (TypeError, ValueError):
            emit("game:error", {"message": "Missing or invalid gameId"})
            return

        participant_token = str(payload.get("participantToken") or "")
        game = db.session.get(Game, game_id)
        player = lobby_player_for_token(game, participant_token) if game else None
        if not game or not player:
            emit("game:error", {"message": "This browser does not own a seat in that lobby."})
            return

        sid = request.sid
        previous_key = LOBBY_SOCKET_PLAYERS.get(sid)
        if previous_key and previous_key != (game_id, player.id):
            LOBBY_PLAYER_SOCKETS[previous_key].discard(sid)

        player_key = (game_id, player.id)
        LOBBY_SOCKET_PLAYERS[sid] = player_key
        LOBBY_PLAYER_SOCKETS[player_key].add(sid)
        LOBBY_DISCONNECT_MARKERS.pop(player_key, None)
        join_room(game_room(game_id))

        was_disconnected = not player.isConnected
        player.isConnected = True
        player.disconnectedAt = None
        db.session.commit()
        if was_disconnected:
            emit_lobby_change(game, "player_reconnected")
        emit(
            "lobby:presence_confirmed",
            {"gameId": game_id, "playerId": player.id},
        )

    @socketio.on("game:join")
    def handle_game_join(payload):
        game_id = payload.get("gameId")
        if not game_id:
            emit("game:error", {"message": "Missing gameId"})
            return

        room_name = game_room(int(game_id))
        join_room(room_name)
        emit("game:joined", {"gameId": int(game_id), "room": room_name})

    @socketio.on("disconnect")
    def handle_disconnect(reason=None):
        sid = request.sid
        player_key = LOBBY_SOCKET_PLAYERS.pop(sid, None)
        if not player_key:
            return

        sockets = LOBBY_PLAYER_SOCKETS[player_key]
        sockets.discard(sid)
        if sockets:
            return
        LOBBY_PLAYER_SOCKETS.pop(player_key, None)

        game_id, player_id = player_key
        player = db.session.get(GamePlayer, player_id)
        game = db.session.get(Game, game_id)
        if not player or not game:
            return

        player.isConnected = False
        player.disconnectedAt = utcnow()
        disconnect_marker = secrets.token_urlsafe(16)
        LOBBY_DISCONNECT_MARKERS[player_key] = disconnect_marker
        db.session.commit()
        emit_lobby_change(game, "player_disconnected")
        app = current_app._get_current_object()
        socketio.start_background_task(
            expire_disconnected_lobby_player,
            app,
            game_id,
            player_id,
            disconnect_marker,
        )

    @socketio.on("game:action")
    def handle_game_action(payload):
        try:
            game_id = payload.get("gameId")
            action = payload.get("action", {})

            if not game_id:
                emit("game:error", {"message": "Missing gameId"})
                return

            room_name = game_room(int(game_id))
            action_type, state = dispatch_game_action(int(game_id), action)

            emit(
                "game:state_updated",
                {
                    "gameId": int(game_id),
                    "actionType": action_type,
                    "state": state,
                },
                to=room_name,
            )
        except Exception as exc:
            emit("game:error", {"message": str(exc)})
