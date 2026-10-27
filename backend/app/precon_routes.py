"""Local-only, read-only catalog API, mounted alongside the existing API."""
from collections import defaultdict
from datetime import date

from flask import Blueprint, jsonify, request
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.mtgPrecons import PreconTemplate, PreconTemplateVersion, PreconTemplateCard
from app.services.precons import playable_count

precons_bp = Blueprint("precons", __name__, url_prefix="/api/precons")


def summary(template):
    v = template.current_version
    return dict(id=template.id, provider=template.provider, externalKey=template.external_key,
        name=template.name, setCode=template.set_code, deckType=template.deck_type,
        format=template.format, releaseDate=template.release_date.isoformat() if template.release_date else None,
        sealedProductIds=template.sealed_product_ids, templateVersionId=v.id if v else None,
        importStatus=v.status if v else "unavailable", gameplayAvailable=bool(v and v.status == "complete"))


def integer_arg(name, default, minimum, maximum):
    value = int(request.args.get(name, default))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@precons_bp.get("")
def list_precons():
    try:
        limit = integer_arg("limit", 25, 1, 100)
        offset = integer_arg("offset", 0, 0, 2_147_483_647)
        year = integer_arg("year", 2000, 1, 9998) if "year" in request.args else None
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400
    query = select(PreconTemplate)
    for arg, field in (("format", PreconTemplate.format), ("set", PreconTemplate.set_code)):
        if request.args.get(arg):
            value = request.args[arg]
            query = query.where(field == (value.upper() if arg == "set" else value.lower()))
    if year:
        query = query.where(PreconTemplate.release_date >= date(year, 1, 1), PreconTemplate.release_date < date(year + 1, 1, 1))
    q = request.args.get("q", "").strip()
    if q:
        query = query.where(or_(PreconTemplate.name.icontains(q, autoescape=True),
                               PreconTemplate.set_code.icontains(q, autoescape=True)))
    commander = request.args.get("commander", "").strip()
    if commander:
        query = query.where(select(PreconTemplateCard.id).where(
            PreconTemplateCard.version_id == PreconTemplate.current_version_id,
            PreconTemplateCard.is_commander.is_(True),
            PreconTemplateCard.name.icontains(commander, autoescape=True)).exists())
    total = db.session.scalar(select(db.func.count()).select_from(query.subquery()))
    rows = db.session.scalars(query.options(joinedload(PreconTemplate.current_version).noload(PreconTemplateVersion.cards))
        .order_by(PreconTemplate.release_date.desc(), PreconTemplate.id).limit(limit).offset(offset)).all()
    return jsonify(precons=[summary(t) for t in rows], total=total, limit=limit, offset=offset)


@precons_bp.get("/<int:template_id>")
def get_precon(template_id):
    from app.routes import serialize_card_summary
    template = db.session.get(PreconTemplate, template_id)
    if template is None:
        return jsonify(error="Precon not found"), 404
    result = summary(template)
    version = template.current_version
    boards = defaultdict(list)
    counts = defaultdict(int)
    if version:
        entries = db.session.scalars(select(PreconTemplateCard).where(PreconTemplateCard.version_id == version.id)
            .options(joinedload(PreconTemplateCard.card), joinedload(PreconTemplateCard.printing))
            .order_by(PreconTemplateCard.board, PreconTemplateCard.name, PreconTemplateCard.id)).all()
        for c in entries:
            boards[c.board].append(dict(id=c.id, providerUuid=c.provider_uuid, quantity=c.quantity,
                isCommander=c.is_commander, name=c.name, cardId=c.card_id, printingId=c.printing_id,
                printing=c.source_metadata, card=serialize_card_summary(c.card) if c.card else None))
            counts[c.board] += c.quantity
        result.update(templateVersion=dict(id=version.id, checksum=version.checksum,
            importedAt=version.imported_at.isoformat(), providerMetadata=version.provider_metadata),
            issues=version.issues, playableCardCount=playable_count(entries))
    commanders = boards.get("commander", []) or [
        c for c in boards.get("main", []) if c["isCommander"]]
    result.update(boards=dict(boards), boardCounts=dict(counts), commanders=commanders)
    return jsonify(result)
