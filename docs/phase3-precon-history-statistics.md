# Phase 3: match history and statistics

## Result

Statistics now come from persisted human participant results and the immutable deck revision selected for the game. Saving an unlisted precon changes only its current library membership: earlier qualifying games immediately enter Library Win Rate. Game IDs, participant IDs, deck IDs and revision references are not rewritten.

The five-game acceptance scenario is covered end to end: 3 wins and 2 losses appear in personal history but initially produce zero library games; saving the same deck produces a 60% Library Win Rate. Three later custom-version games aggregate with the earlier five while stock/current revision totals remain distinct.

## Audit and implementation decisions

Phase 2 already pins `mtgGames.gamePlayers.deckId` and `deckVersionId` during creation/join and seeds from that exact revision. Phase 3 reuses those fields; it does not create another game/deck association. Tests additionally verify that a deck edit after game creation cannot change the pinned game's seeded list.

`Game.status == completed` is the existing finalization signal. The concession workflow writes each participant's result and finalizes the game when appropriate. Statistics require a recognized participant result; they do not infer everyone's outcome from `winnerGamePlayerId`. This preserves multiplayer attribution and avoids inventing legacy results. The normal concession route is tested to confirm results enter statistics only when the game completes.

New fields `games.isInvalidated` (false by default) and `games.invalidationReason` support explicit invalidation without removing history. No player-facing result correction/invalidation workflow is introduced; administrative changes to persisted results or validity immediately affect the derived queries. There is no aggregate cache to invalidate.

Existing histories and unknown revision references remain unchanged. A missing/mismatched historical version appears as `configurationKnown: false`; such games can contribute to the complete deck/account record when their outcome and account are known, but are not assigned to a stock/current revision. Unknown account ownership is never inferred from a deck's owner.

## Central eligibility policy

Implemented in `backend/app/services/statistics.py`:

| Record | Competitive statistics |
|---|---|
| Completed, valid human PvP participation with recognized result | Included |
| Goldfish | Excluded; separate mode breakdown |
| Automated simulation | Excluded; separate mode breakdown |
| PvAI | Excluded; separate PvAI totals |
| Pending, active, aborted or invalidated games | Excluded |
| Completed games without a recognized participant result | Excluded |
| Computer participants | Excluded from account results |
| Ambiguous legacy games with the account in multiple human seats | Excluded from aggregate totals; retained in history |

Competitive mode labels are `pvp`, `multiplayer`, `one-v-one` and `two-headed-giant`. A seated computer opponent classifies a game as PvAI even if its older mode label says PvP. Explicit `pvai`/`pv-ai` labels are supported by the statistics policy. Goldfish/simulation classification takes precedence over opponent type. This phase does not add an AI engine or new launch mode.

Case/whitespace and existing outcome synonyms are normalized: win/won/winner; loss/lost/lose/loser; draw/drawn/tie. Unknown values are excluded rather than guessed. Each unambiguous account match is counted once. Duplicate personal decks receive no copies of original participation and cannot duplicate account totals.

Win rate is `100 × wins / (wins + losses)`, rounded to one decimal. Draws are reported separately and excluded from the denominator. No decided games yields null, displayed as an em dash. Average turns uses the recorded positive `Game.turnNumber` values; no missing turn information is reconstructed.

Library statistics join each participation to its deck's **current** saved status. Unlisted and archived decks remain in overall competitive results and history. Archive removes their games from Library Win Rate; restore adds them back. Existing shared ownerless decks retain Phase 2 compatibility, but only the authenticated user's own participation is counted.

## APIs

All endpoints verify the existing Kachhapa identity. Private deck statistics enforce the same ownership check as deck editing. Prefixes follow the existing `/api` and proxy `/mtg/api` configuration.

| Method | Endpoint | Response |
|---|---|---|
| GET | `/api/profile/stats` | `library`, `overallCompetitive`, `pvai`, `byMode`, `policy` |
| GET | `/api/decks/:id/stats` | Selected `stats`, all/stock/current `scopes`, revision totals, mode breakdown and policy |
| GET | `/api/profile/history` | Paginated personal games, including unlisted/archived/invalidated games and known/unknown revision metadata |

Each totals object contains `gamesPlayed`, `wins`, `losses`, `draws`, `decidedGames`, `winRate` and `averageTurns`.

Deck statistics accept:

- `revision=all` (default), `stock`, `current`, or a comma-separated list of up to 100 owned revision IDs.
- `mode=competitive` (default), `pvai`, `all`, or an explicit supported raw mode label. Selecting a raw PvP label includes games with that label; use `competitive` to enforce the competitive category.

`scopes` compare all, stock and current configurations under the requested mode. `revisions` report `revisionId`, `revisionType`, `configurationKnown` and totals, with a null revision ID for unknown historical configurations. `byMode` provides all finalized valid mode/category totals under the selected revision filter, independently of the main mode selector.

Personal history accepts `limit` (1–100, default 25), `offset` and optional `status`. It returns `{games, total, limit, offset}`. Each game includes `myParticipations` with participant/deck/revision IDs, result, current library status and `configurationKnown`. The game list uses an existence predicate, so multiple participant rows cannot duplicate a game in history. The public lobby listing `/api/games` remains available separately.

Existing deck summary fields `gamesPlayed`, `wins`, `winRate` now use the centralized competitive policy. Summaries also return `losses`, `draws` and `statisticsScope: competitive`. List summaries are aggregated in one batch rather than separately scanning every deck's participation.

## Profile

Profile now fetches account statistics directly and labels the default percentage **Library Win Rate**. It does not derive a percentage by adding deck summary values. Recent Games uses authenticated personal history and the relevant participant's result, including games using unsaved precons. Draws are no longer treated as losses in deck rows. Invalidated and ambiguous multiple-seat histories are labeled accordingly. Existing precon navigation changes were preserved.

Broader deck statistics screens and revision comparison remain Phase 4.

## Migration and deployment

Migration `a93c4e125b87` follows Phase 2 `f82b3d014a76`. It adds the invalidation fields and composite indexes on participant user/game/type and deck/user/revision. It preserves all existing cards, personal decks, versions, games and outcomes. Existing rows default to not explicitly invalidated, but still pass all other eligibility filters before contributing.

With the intended PostgreSQL `DATABASE_URL` configured, migrate before restarting the updated backend:

```sh
cd backend
../.venv/bin/python -m flask --app run:app db upgrade
```

Use the installed Pi virtualenv path when deploying there. PostgreSQL upgrade/downgrade SQL compiled successfully offline; execution against a populated PostgreSQL server remains unverified in this environment.

## Validation

- Backend: **35 passed, 1 skipped**. The skipped check is the pre-existing optional real-PostgreSQL concurrent save/play test.
- Frontend: **7 suites, 11 tests passed**, including API-driven library percentage and unsaved precon history on Profile.
- PostgreSQL migration upgrade/downgrade: compiled offline.
- Production React build: passed, including the existing shared-appearance prebuild check.
- `git diff --check`: passed.

The new acceptance tests cover retroactive attribution, unchanged historical associations, five-stock/three-custom revision isolation, finalized competitive eligibility, draws, Goldfish/simulation/PvAI separation, participant-specific multiplayer results, duplicate isolation, archive/restore, corrected results/invalidation, legacy unknown configurations, authentication/ownership, bounded history pagination, and pinning before subsequent edits.

Run the checks:

```sh
PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -v
cd frontend
CI=true npm test -- --watchAll=false --watchman=false --runInBand
npm run build
```

Tests use isolated SQLite databases and mock Kachhapa identity verification. Live PostgreSQL migration behavior, production query performance and browser-driven dev-server interaction remain deployment checks. The optional PostgreSQL race test can run with `MTG_TEST_POSTGRES_URL` configured for a test database as described in Phase 2 notes.

## Files changed for Phase 3

New:

- `backend/app/services/statistics.py`
- `backend/app/statistics_routes.py`
- `backend/migrations/versions/a93c4e125b87_statistics_validity.py`
- `backend/tests/test_statistics.py`
- `frontend/src/Profile.test.js`
- `docs/precon-history-statistics-phase3.md`

Updated:

- `backend/app/__init__.py`
- `backend/app/models/mtgGames.py`
- `backend/app/routes.py`
- `frontend/src/Profile.js`

Other pending changes were preserved.
