# Phase 2: personal precon identity and library integration

## Result

A verified Kachhapa user can select a precon without saving, reuse that unlisted instance, save the same instance, edit its personal configuration, and play either the pinned original list or the current custom version. Stock instances reference the global snapshot; their cards are copied into the existing editable `deckCards` only on first edit. Normal library/recent-deck listings include saved decks only. Global templates and previous versions are never edited by these operations.

Existing deck/game IDs and card references are preserved. Game participation already has `deckVersionId`, so new game selections pin that existing FK and seeding now reads that immutable version. Historical games without a version keep their old references and are not retroactively assigned invented configurations. Statistics policy/aggregation remains Phase 3; catalog browsing and the full precon comparison UI remain Phase 4.

## Architecture decisions

- Extend `mtgDecks.decks` with `sourcePreconId`, `sourcePreconVersionId`, `libraryStatus`, `isPrimaryPreconInstance`, `addedToLibraryAt` and `currentVersionId`.
- Extend existing `deckVersions` with `basePreconVersionId`, `revisionType` and `contentHash`. This reuses `deckVersionCards` and `GamePlayer.deckVersionId` rather than introducing a parallel revision system.
- A stock revision references the official immutable snapshot. Its source remains pinned even after catalog updates. Custom revisions snapshot the existing editable list once per successful API operation. Bulk edits and board moves create one revision for the entire request; unchanged configurations do not create another version. Metadata-only renames retain the source and current card revision.
- Editing acquires a row lock before copying/changing cards and snapshotting. Save/play first-creation uses a per-template PostgreSQL transaction advisory lock and a partial unique index on `(ownerUserId, sourcePreconId)` for primary instances.
- Stock card responses use opaque IDs such as `stock-123`. Existing card PATCH/DELETE paths now accept opaque strings as well as legacy numeric IDs. The backend maps these IDs to the personal copy during first edit. Clients should continue treating entry IDs as opaque.
- Source boards map to existing engine conventions (`commander` → `command`, `side` → `sideboard`, `planes` → `planar`). Commander overlap is removed during adaptation; tokens and display commanders are excluded from personal/playable entries. Game seeding uses main/command only, preserving auxiliary boards without shuffling them into the library.
- Deck deletion archives rather than cascading through revisions/history. Restore preserves the same deck ID. Explicit duplication creates a non-primary personal instance with the same source, its own revisions and no copied game participation.

## Identity and compatibility

The enclosing Kachhapa app already exposes `/api/session` for the shared `kachhapa_session` cookie and `/api/profile` for bearer authentication. MTG verifies these credentials server-side with a fixed configured upstream. It never trusts `ownerUserId`, `userId` or `user_id` from JSON. Cookie-authenticated mutation requests reject a different `Origin`. Upstream failures fail closed with 503; unauthenticated account operations return 401. Errors are JSON for frontend handling.

Set `KACHHAPA_AUTH_URL` to the core Kachhapa service origin, **not** the MTG service or a reverse-proxy route back to MTG. Default for the Pi installation:

```ini
KACHHAPA_AUTH_URL=http://127.0.0.1
```

The Pi default uses its local nginx server, which forwards the core `/api/session` and `/api/profile` routes to Kachhapa.

Sign in through Kachhapa before creating new personal decks or saving/playing precons. Frontend fetches use the existing same-origin shared cookie, including under `/mtg/api`. Standalone installations need a reachable Kachhapa identity backend or a separately implemented identity adapter; no new login system or hardcoded account was added.

Legacy ownerless decks remain shared and accessible through the existing workflows. This is a deliberate compatibility policy: no account ownership is guessed during migration. Decks with an existing owner ID are accessible only to that verified owner. The pre-existing public/private toggle is preserved as metadata; cross-account public deck sharing is outside this phase. Administrators should check any old placeholder owner IDs before deployment and map them explicitly if needed.

## Migration and deployment

Migration `f82b3d014a76` follows Phase 1 revision `e71a2c903f65`. It adds columns, constraints and indexes, backfills existing decks as saved, and fills their library timestamp from `createdAt`. Original origins remain null. Existing custom lists receive a baseline lazily on their next edit or game selection; existing matches are untouched.

With the intended PostgreSQL `DATABASE_URL` configured, run before starting the updated backend:

```sh
cd backend
../.venv/bin/python -m flask --app run:app db upgrade
```

For your Pi, substitute its existing virtualenv path (for example `/home/ijohnson/MtG-webapp/venv/bin/python`). Configure the identity upstream in the service environment and restart MTG after migration. A PostgreSQL populated-database upgrade still needs deployment validation; only offline upgrade/downgrade SQL compilation could run here.

## API

| Method | Path | Behavior |
|---|---|---|
| POST | `/api/precons/:id/play` | Resolve/reuse primary instance and pinned stock revision; does not save it |
| POST | `/api/precons/:id/save` | Create/promote/restore the same primary instance |
| GET | `/api/decks` | Saved decks owned by the verified user plus shared legacy decks |
| GET | `/api/decks?status=unlisted` | Explicit unlisted listing for the same account |
| GET | `/api/decks?status=archived` | Explicit archived listing |
| GET | `/api/decks/:id/revisions` | Immutable versions and current version ID |
| GET | `/api/decks/:id/revisions/:revisionId` | One exact configuration |
| POST | `/api/decks/:id/play` | Resolve `{"revision":"stock"}` / `"current"` / owned revision ID |
| POST | `/api/decks/:id/duplicate` | New non-primary copy without historical games |
| DELETE | `/api/decks/:id` | Archive and retain historical references |
| POST | `/api/decks/:id/restore` | Restore saved visibility |

Play resolvers return `deckId`, `revisionId`, and compatibility alias `deckVersionId`. Direct precon play also returns deck metadata. Existing deck-edit endpoints remain the only editor; unlisted/archived decks must be saved/restored before edits. Card add/update checks that preferred printings belong to the selected card.

Game creation accepts `revision` (`stock` or `current`) or `deckVersionId` on each player selection. Lobby host selection accepts top-level `revision`/`hostDeckVersionId`; joining accepts `revision`/`deckVersionId`. Every supplied revision is checked against the selected accessible deck. If absent, the server pins the current configuration. New participant identity comes from verification, not submitted IDs. The existing transport participant tokens continue to control lobby actions.

Deck responses now include source IDs, library status, current revision ID/number/type, source name, original commander names, and added/removed quantities. The Deck Builder displays these fields and stock/current Goldfish buttons. Match setup, simulation opponent selection, lobby hosting and lobby joining include the stock/current selector for precon-derived decks.

## Validation

- Backend: **26 passed, 1 skipped** using isolated SQLite integration databases. Covers reuse/promotion, copy-on-write, immutable revisions, exact game seeding, ownership, bearer/cookie checks, upstream failure, catalog updates, stock/current selection, duplicate history isolation, archival/restoration, database primary uniqueness, custom/legacy decks and grouped edits, plus all Phase 1 catalog tests.
- The skipped test exercises a real concurrent save/play race in PostgreSQL. It creates and cleans uniquely named schemas and can be enabled with `MTG_TEST_POSTGRES_URL` pointing to a test PostgreSQL database where the account may create schemas. No actual PostgreSQL server was available here.
- Frontend: **4 suites / 7 tests passed**, including stock/current selection and submitted match configuration.
- Production React build: passed, including the existing shared-appearance prebuild check.
- Phase 2 PostgreSQL migration upgrade/downgrade SQL: compiled successfully offline.
- `git diff --check`: passed.

Run locally:

```sh
PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -v
cd frontend
CI=true npm test -- --watchAll=false --watchman=false --runInBand
npm run build
```

Not verified here: populated PostgreSQL migration execution, live Kachhapa identity calls, real PostgreSQL locking, and browser-driven interaction against the dev server. Identity calls are mocked in the automated tests. Existing unrelated working changes remain in place.

## Files changed for Phase 2

New:

- `backend/app/auth.py`
- `backend/app/services/deck_identity.py`
- `backend/app/deck_identity_routes.py`
- `backend/migrations/versions/f82b3d014a76_personal_precon_identity.py`
- `backend/tests/test_deck_identity.py`
- `backend/tests/test_precon_concurrency.py`
- `frontend/src/DeckRevisionSelect.js`
- `frontend/src/DeckRevisionSelect.test.js`
- `docs/precon-personal-library-phase2.md`

Updated:

- `backend/app/__init__.py`
- `backend/app/models/mtgDecks.py`
- `backend/app/routes.py`
- `backend/mtg-backend.env.example`
- `frontend/src/DeckBuilder.js`
- `frontend/src/MatchSetupModal.js`
- `frontend/src/GameLobby.js`
- `frontend/src/App.js`
