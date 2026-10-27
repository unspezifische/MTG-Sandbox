# Phase 1: official precon catalog

## Architecture audit

- `mtgCore.cards.id` is a BIGINT primary key; `cards.uuid` is unique. `mtgCore.printings.id` is a BIGINT primary key; `printings.uuid` is the MTGJSON printing UUID and maps to `cardId`. The existing importer retains MTGJSON UUIDs. Catalog resolution checks exact printing UUID first, then exact card UUID. No name-based guesses.
- Personal decks use `mtgDecks.decks.id` (BIGINT). `deckCards` references `cardId`, optional `preferredPrintingId`, quantity, `boardType`, and `isCommander`. Its unique key is `(deckId, cardId, boardType)`. Multiple commanders are represented by multiple entries; the builder accepts up to two.
- Existing `deckVersions`/`deckVersionCards` can support later personal revision work. The catalog does not replace them. Existing `products`/`productContents` lack immutable revisions and exact printing/unresolved-card storage, so catalog-specific tables are needed.
- `mtgGames.gamePlayers` stores `deckId`, optional `deckVersionId`, participant identity, and participant `result`; games have mode/status. Current modes are `pvp`, `goldfish`, and `simulation`. They share game creation/persistence routes; deck summaries count result-bearing/completed participation without the future competitive eligibility policy. PvAI is not an existing standalone mode. No historical rows are changed.
- No authenticated account context or owner checks currently protect the deck CRUD routes. Creation accepts `ownerUserId` from JSON. Lobby tokens protect participant operations, not account ownership. Phase 1 only provides public read-only catalog endpoints. Account authentication/ownership must be resolved before the Phase 2 private-instance workflows.
- Flask-Migrate/Alembic uses sequential revisions with schema-qualified PostgreSQL tables. New revision `e71a2c903f65` follows `d6b8a4c91f20` and only adds catalog tables/indexes. Existing pending working changes were preserved.
- `/api` is the application prefix; the existing reverse proxy maps `/mtg/api` to it. New routes follow the same pattern.

## Implementation

Four new tables in `mtgDecks`: `precon_templates`, `precon_template_aliases`, `precon_template_versions`, `precon_template_cards`. Templates keep stable IDs; snapshots retain resolved IDs, original UUIDs, board distinctions, printing metadata, import metadata, checksums and validation issues. Versions are append-only through the importer and there are no catalog mutation HTTP routes. Card/printing foreign keys prevent deletion of referenced historical identities.

The external identity starts with MTGJSON `DeckList.fileName`; code/name remain metadata. Provider renames can be explicitly associated with an existing template using `--alias-of ID` with exactly one selected deck. This avoids guessing that similarly named decks are identical.

The sync command loads DeckList plus individual deck files, or accepts a local index and extracted AllDeckFiles directory. It commits each deck independently, rolls back/report failures, and uses a PostgreSQL transaction advisory lock to serialize concurrent catalog writes. It downloads source files on each explicit sync to detect changes; unchanged normalized records do not create new versions. It never runs at startup or writes personal decks.

Commanders remain in their source board; playable total uses `max(main quantity, commander quantity)` per printing UUID. Tokens, sideboards, planes and schemes have separate totals and do not inflate the playable total. Commander imports require commanders and exactly 100 playable cards. Missing UUID resolution, including auxiliary boards, conservatively marks a snapshot incomplete. Repairing the local card database and rerunning sync creates a resolved snapshot while retaining the incomplete one. `require_playable` is the guard for future Phase 2 game selection; Phase 1 has no play/save operation.

`GET /api/precons` accepts `q`, `format`, `set`, `year`, `commander`, `limit` (1–100) and `offset`. Returns `precons`, `total`, `limit`, `offset`. Substring searches escape wildcard input and use trigram indexes on deck/commander names in PostgreSQL.

`GET /api/precons/:id` returns current metadata, version/checksum/provider metadata, commanders, card entries grouped by board, counts, resolved existing card summaries, printing metadata, issues and `gameplayAvailable`. No browsing request accesses MTGJSON.

## Run

From the repository root, with the intended PostgreSQL `DATABASE_URL` configured:

```sh
source venv/bin/activate
cd backend
python -m flask --app run:app db upgrade
python -m flask --app run:app sync-precons --name 'Draconic Destruction' --limit 1
```

Then inspect `/api/precons?q=Draconic` and `/api/precons/ID`. To sync the full catalog, omit the name and limit. The existing card database must be populated first. An incomplete/failed sync exits nonzero and prints counts; successful decks are retained.

The sync always writes `precon-sync-results.json` in the current directory. It
contains the counts plus the stable `fileName`, name, code, and exact issues or
exception for every incomplete/failed deck. Once the underlying problem is
fixed, use it as the input to a focused retry:

```sh
python -m flask --app run:app sync-precons \
  --retry-report precon-sync-results.json \
  --report precon-sync-retry-results.json
```

The retry report is a fresh result: resolved entries disappear from its
`retry` list, while remaining entries can be passed to another run.

Offline source files:

```sh
python -m flask --app run:app sync-precons \
  --index /path/to/DeckList.json --deck-dir /path/to/extracted/decks
```

## Validation and limits

Run from the repository root:

```sh
PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -v
```

Tests use isolated SQLite databases with test-only compilation adapters for the existing PostgreSQL core types. They cover a real Draconic Destruction list (Atarka, World Render; 99 mainboard + 1 commander), printing resolution, immutable changes, idempotence, repair, board distinctions, double-count prevention, filters, pagination, read-only endpoints, alias identity, rollback and the local-file CLI. The fixture comes from the repository's MTGJSON AllPrintings.sqlite `setDecks`, enriched with card names; it is not a fresh remote download.

PostgreSQL migration upgrade/downgrade SQL was compiled offline. No PostgreSQL server, Docker executable, or direct MTGJSON network access was available in this environment, so populated-PostgreSQL migration execution, live synchronization, and lock concurrency remain deployment validation steps. Existing route registration is checked; this is not full gameplay regression validation.

No frontend changes: the browser belongs to Phase 4. No personal deck membership, gameplay selection, statistics or personal revisions are introduced in Phase 1. Do not infer that `gameplayAvailable` implements a Phase 2 launcher or format legality engine.

## Files

- `backend/app/models/mtgPrecons.py`: catalog models.
- `backend/app/services/precons.py`: normalization, resolution, synchronization CLI and gameplay guard.
- `backend/app/precon_routes.py`: read-only catalog APIs.
- `backend/app/__init__.py`: model, route and CLI registration.
- `backend/migrations/versions/e71a2c903f65_add_precon_catalog.py`: additive migration.
- `backend/tests/test_precons.py`, `backend/tests/fixtures/draconic_destruction.json`: offline validation.
- This document: audit, decisions, commands and limitations.

Source contracts checked: https://mtgjson.com/downloads/all-files/, https://mtgjson.com/downloads/all-decks/, https://mtgjson.com/data-models/deck/, https://mtgjson.com/data-models/deck-list/, https://mtgjson.com/data-models/card/card-deck/.
