"""MTGJSON import. One transaction per deck, never invoked at startup."""
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import click
import requests
from flask import current_app
from sqlalchemy import select, text

from app.extensions import db
from app.models.mtgCore import Card, Printing
from app.models.mtgPrecons import PreconAlias, PreconTemplate, PreconTemplateVersion, PreconTemplateCard

BASE_URL = "https://mtgjson.com/api/v5/"
BOARDS = {"commander": "commander", "mainBoard": "main", "sideBoard": "side",
          "tokens": "tokens", "planes": "planes", "schemes": "schemes",
          "displayCommander": "display_commander"}


def normalize_deck(source):
    """Keep source boards; playable totals use max(main, commander) per UUID."""
    if not isinstance(source, dict):
        raise ValueError("Deck must be an object")
    for key in ("name", "code", "type"):
        if not isinstance(source.get(key), str) or not source[key].strip():
            raise ValueError(f"Missing deck {key}")
    if not isinstance(source.get("mainBoard"), list) or not source["mainBoard"]:
        raise ValueError("Missing or empty mainBoard")
    entries = {}
    commanders = {c.get("uuid") for c in source.get("commander", []) or []}
    for key, board in BOARDS.items():
        values = source.get(key) or []
        if not isinstance(values, list):
            raise ValueError(f"Invalid {key}")
        for card in values:
            quantity = card.get("count", 1 if board == "tokens" else None)
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
                raise ValueError(f"Invalid quantity in {key}")
            if not card.get("uuid") or not card.get("name"):
                raise ValueError(f"Missing card UUID/name in {key}")
            identity = (board, card["uuid"])
            if identity not in entries:
                entries[identity] = dict(provider_uuid=card["uuid"], name=card["name"], quantity=0,
                    board=board, is_commander=card["uuid"] in commanders,
                    source_metadata={k: card[k] for k in ("identifiers", "setCode", "number", "isFoil", "isEtched") if k in card})
            entries[identity]["quantity"] += quantity
    return sorted(entries.values(), key=lambda c: (c["board"], c["provider_uuid"]))


def playable_count(entries):
    totals = defaultdict(lambda: defaultdict(int))
    for c in entries:
        board = c.board if hasattr(c, "board") else c["board"]
        uuid = c.provider_uuid if hasattr(c, "provider_uuid") else c["provider_uuid"]
        qty = c.quantity if hasattr(c, "quantity") else c["quantity"]
        totals[uuid][board] += qty
    return sum(max(v["main"], v["commander"]) for v in totals.values())


def require_playable(version):
    """Server-side guard for future game selection; Phase 1 exposes no play route."""
    if version is None or version.status != "complete":
        raise ValueError("Precon decklist is incomplete and cannot be played")
    return version


def import_deck(index, payload, *, alias_of=None):
    """Caller owns commit/rollback. Explicit aliases handle provider file renames."""
    source = payload["data"]
    entries = normalize_deck(source)
    if index.get("code") and index["code"].upper() != source["code"].upper():
        raise ValueError("DeckList code does not match the deck file")
    key = index["fileName"]
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", key):
        raise ValueError("Invalid fileName")
    if db.session.get_bind().dialect.name == "postgresql":
        # Serialize sync processes, including first imports and explicit aliases.
        db.session.execute(text("SELECT pg_advisory_xact_lock(684720193)"))
    alias = db.session.scalar(select(PreconAlias).filter_by(provider="mtgjson", external_key=key))
    template = db.session.get(PreconTemplate, alias.template_id) if alias else None
    if alias_of is not None:
        target = db.session.get(PreconTemplate, alias_of)
        if target is None or (template and template.id != target.id):
            raise ValueError("Alias target is missing or conflicts with an existing identity")
        template = target
    if template is None:
        template = PreconTemplate(provider="mtgjson", external_key=key)
        db.session.add(template)
    template.name = source["name"]
    template.set_code = source["code"].upper()
    template.deck_type = source["type"]
    kind = source["type"].lower()
    template.format = "commander" if "commander" in kind else ("brawl" if "brawl" in kind else None)
    template.release_date = date.fromisoformat(source["releaseDate"]) if source.get("releaseDate") else None
    template.sealed_product_ids = source.get("sealedProductUuids") or []
    template.source_metadata = dict(index)
    db.session.flush()
    if alias is None:
        db.session.add(PreconAlias(provider="mtgjson", external_key=key, template_id=template.id))
    uuids = [e["provider_uuid"] for e in entries]
    printings = {p.uuid: p for p in db.session.scalars(select(Printing).where(Printing.uuid.in_(uuids)))}
    cards = {c.uuid: c for c in db.session.scalars(select(Card).where(Card.uuid.in_(uuids)))}
    issues = []
    for entry in entries:
        printing = printings.get(entry["provider_uuid"])
        card = cards.get(entry["provider_uuid"])
        entry["card_id"] = printing.cardId if printing else (card.id if card else None)
        entry["printing_id"] = printing.id if printing else None
        if entry["card_id"] is None:
            issues.append(f"Unresolved {entry['board']} card: {entry['provider_uuid']} ({entry['name']})")
    if template.format == "commander" and (not any(e["is_commander"] for e in entries) or playable_count(entries) != 100):
        issues.append("Commander deck requires commanders and exactly 100 playable cards")
    # Include resolved identities so retrying after a card DB update repairs incomplete imports.
    canonical = {"cards": entries, "deck": {k: source.get(k) for k in
        ("name", "code", "type", "releaseDate", "sealedProductUuids")}}
    checksum = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    version = db.session.scalar(select(PreconTemplateVersion).filter_by(template_id=template.id, checksum=checksum))
    changed = version is None
    if changed:
        version = PreconTemplateVersion(template_id=template.id, checksum=checksum,
            provider_metadata={"meta": payload.get("meta", {}), "deck": canonical["deck"], "fileName": key},
            status="incomplete" if issues else "complete", issues=issues)
        db.session.add(version)
        db.session.flush()
        db.session.add_all(PreconTemplateCard(version_id=version.id, **e) for e in entries)
    template.current_version = version
    db.session.flush()
    return template, changed


def load_json(path_or_url):
    if str(path_or_url).startswith("https://"):
        response = requests.get(path_or_url, timeout=(10, 120))
        response.raise_for_status()
        return response.json()
    return json.loads(Path(path_or_url).read_text())


def load_retry_keys(report_path):
    """Read stable MTGJSON file names from this or an older sync report."""
    payload = json.loads(Path(report_path).read_text())
    entries = payload.get("retry", payload.get("problems"))
    if not isinstance(entries, list):
        raise ValueError("Retry report must contain a retry or problems list")
    keys = {
        entry.get("fileName")
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("fileName"), str)
    }
    keys.discard("")
    if not keys:
        raise ValueError("Retry report does not contain any precon fileName values")
    return keys


def write_sync_report(path, *, counts, problems, source, selected_count):
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "selectedCount": selected_count,
        "counts": counts,
        # Keep problems for compatibility with reports created before retry support.
        "problems": problems,
        "retry": problems,
    }
    temporary_path = report_path.with_name(report_path.name + ".tmp")
    temporary_path.write_text(json.dumps(payload, indent=2) + "\n")
    temporary_path.replace(report_path)
    return report_path


def register_cli(app):
    @app.cli.command("sync-precons")
    @click.option("--index", default=BASE_URL + "DeckList.json", help="DeckList URL or local JSON")
    @click.option("--deck-dir", type=click.Path(exists=True, file_okay=False), help="Extracted AllDeckFiles directory")
    @click.option("--name", help="Case-insensitive name substring")
    @click.option("--limit", type=click.IntRange(min=1))
    @click.option("--alias-of", type=int, help="Existing template ID; requires exactly one selected deck")
    @click.option(
        "--report",
        type=click.Path(dir_okay=False, path_type=Path),
        default=Path("precon-sync-results.json"),
        show_default=True,
        help="Write JSON counts and retry details for incomplete/failed decks.",
    )
    @click.option(
        "--retry-report",
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
        help="Only sync decks listed under retry/problems in a previous report.",
    )
    def sync_precons(index, deck_dir, name, limit, alias_of, report, retry_report):
        """Import official decks, preserving all previous snapshots."""
        try:
            index_payload = load_json(index)
            catalog = index_payload["data"]
            retry_keys = load_retry_keys(retry_report) if retry_report else None
            if retry_keys is not None:
                catalog = [d for d in catalog if d.get("fileName") in retry_keys]
            if name:
                catalog = [d for d in catalog if name.lower() in d["name"].lower()]
            if limit:
                catalog = catalog[:limit]
            if retry_keys is not None and not catalog:
                raise ValueError("No current DeckList entries matched the retry report")
            if alias_of is not None and len(catalog) != 1:
                raise ValueError("--alias-of requires exactly one selected deck")
        except (ValueError, KeyError, requests.RequestException, OSError) as exc:
            raise click.ClickException(str(exc)) from exc
        counts = dict(changed=0, unchanged=0, incomplete=0, failed=0)
        problems = []
        for item in catalog:
            try:
                filename = item["fileName"]
                if not re.fullmatch(r"[A-Za-z0-9_.-]+", filename):
                    raise ValueError("Invalid fileName")
                filename = filename if filename.endswith(".json") else filename + ".json"
                location = Path(deck_dir) / filename if deck_dir else BASE_URL + "decks/" + filename
                template, changed = import_deck(item, load_json(location), alias_of=alias_of)
                status = template.current_version.status
                problem = None
                if status != "complete":
                    problem = dict(fileName=item["fileName"], name=item["name"], code=item.get("code"),
                        status=status, templateId=template.id,
                        versionId=template.current_version_id,
                        issues=list(template.current_version.issues or []))
                db.session.commit()
                counts["changed" if changed else "unchanged"] += 1
                counts["incomplete"] += status != "complete"
                click.echo(f"{item['name']}: {status}")
                if problem is not None:
                    problems.append(problem)
                    for issue in problem["issues"]:
                        click.echo(f"  {issue}")
            except Exception as exc:
                db.session.rollback()
                counts["failed"] += 1
                problems.append(dict(fileName=item.get("fileName"), name=item.get("name"),
                    code=item.get("code"), status="failed",
                    errorType=type(exc).__name__, error=str(exc)))
                current_app.logger.exception("Precon import failed: %s", item.get("fileName"))
        report_path = write_sync_report(
            report,
            counts=counts,
            problems=problems,
            selected_count=len(catalog),
            source={
                "index": str(index),
                "indexMeta": index_payload.get("meta", {}),
                "deckDir": str(deck_dir) if deck_dir else None,
                "name": name,
                "limit": limit,
                "retryReport": str(retry_report) if retry_report else None,
            },
        )
        click.echo(f"Import report written to {report_path}")
        click.echo(json.dumps(counts))
        if counts["failed"] or counts["incomplete"]:
            raise click.ClickException(
                "Some precons failed or remain incomplete; successful decks were committed. "
                f"See import output and {report_path}")
