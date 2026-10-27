# Phase 4: implementation and release gate

**Status: implemented locally; release gate NOT passed.** No deployment or live database backup was performed from this workspace. Do not describe the feature as release-complete until the remaining checks below have evidence.

## Implemented

- Public catalog search with `q`, `format`, `set`, `year`, `commander`, `limit` and `offset`; filters survive pagination. Official details load from the existing detail API and show release metadata, commanders, quantities, board counts, resolved/unresolved cards and import issues.
- Separate Play Original and Add to Your Decks actions. Both disable for incomplete catalog versions; backend save/play also reject an incomplete current catalog even when a primary personal instance already exists.
- Resolver-returned deck metadata remains available in game selectors independently of `/api/decks`. Goldfish, simulation and PvP hosting/joining preserve the exact returned revision ID. No cards or account IDs are synthesized in React. Promotion refreshes saved metadata without losing the pinned original selection.
- Saving refreshes the saved library before opening the existing Deck Builder. Backend identity promotion and historical attribution remain the Phase 2/3 workflows.
- Paginated personal History uses `/api/profile/history`; `/api/games` remains the lobby feed. History shows the relevant participant's outcome, mode, selected deck, stock/custom/unknown configuration, current membership, invalidation and ambiguous multiple-seat cases.
- The existing Deck Builder now displays server-derived all/stock/current totals and revision comparison. Mode and selected revision filters call `/decks/:id/stats`. Counts, percentages and averages are not calculated in React. Profile continues using `/profile/stats`.
- 401/409/503 guidance, retry/loading/empty states, responsive filters/cards, contained scrolling for wide statistics tables, and accessible details focus.

No parallel schema, statistics cache, provider/importer, AI engine, new game mode, rebasing, legacy revision reassignment or administrator correction UI was added.

## Snapshot and deployment hardening

A pre-Phase-4 source snapshot and SHA-256 manifest are retained under `docs/release/phase1-3-worktree-20261021T194351Z.*`. The manifest records the Git HEAD, working-tree changes/deletions and file hashes. It is a source checkpoint, not a database backup or a copy of remotely deployed build artifacts.

Docker startup now requires an explicit external `KACHHAPA_AUTH_URL`, probes `/api/session`, and runs Alembic before Gunicorn. Container-local loopback is rejected. Compose exposes the Linux `host.docker.internal` host-gateway alias; configure its URL to the actual core service, e.g. `http://host.docker.internal` when the host nginx routes core `/api` endpoints. A TCP or HTTPS core-service address is also supported. Bare-metal retains its existing local nginx default.

`run.py` initialization also uses Alembic, retaining the existing card-search index setup afterward. Neither startup path uses `db.create_all()` to upgrade existing databases. An unversioned populated database is not stamped automatically: reconcile its schema and ledger explicitly before upgrading.

The initial migration had forward/circular foreign keys referencing tables before creation. Its 48 foreign keys are now added after all initial tables exist; fresh-initial downgrade drops those named constraints before tables. Already-applied revisions are not rerun. The existing catalog-adoption migration was preserved and gained a fresh-schema offline SQL path. Offline SQL cannot verify the online adoption branch, and rollback of a historically created schema should use its backup rather than attempting an unverified downgrade to base.

Phase 4 adds **no new database revision**. The required head remains `a93c4e125b87`.

## Local validation evidence

- Backend: **38 passed, 1 skipped**; all Phase 1–3 tests retained. The skipped test is the optional real PostgreSQL race/resync test.
- Frontend: **9 suites, 27 tests passed**. Tests cover filters/pagination, API-loaded details, all three match setups, exact unlisted revision submission, same-primary save/library display, history states, server-driven scope/mode/revision comparison, promotion metadata refresh and actionable identity failures.
- Production React build: passed, including the shared appearance prebuild check.
- Full Alembic chain through `a93c4e125b87`: compiled to PostgreSQL SQL offline. Initial dependency ordering checked for all 48 foreign keys.
- Docker startup rejection of missing/container-local identity configuration: tested.
- Local fixture browser inspection: catalog, details, history and statistics at 390px and 1280px. No page-level horizontal overflow observed; statistics tables scroll in their own regions. The preview used isolated SQLite data and an explicit test identity, not a real signed-in Kachhapa session. The shared application theme was loaded for visual checks. Temporary preview server and viewport overrides were cleaned up.
- `git diff --check`, release helper Python compilation/help and entrypoint shell syntax: passed.

The PostgreSQL test was explicitly invoked and skipped because `MTG_TEST_POSTGRES_URL` is unset. It now also checks that a valid changed global cardlist creates a snapshot while existing personal origin/revision IDs remain pinned. A skip is not a release pass.

This workspace has no target database variables or PostgreSQL/Docker clients on PATH. Local database/app ports were not listening. SSH to `ijohnson@raspberrypii.local` failed hostname resolution. Consequently, no live target was available for the remaining gate.

## Gate status

| Gate | Status |
|---|---|
| Snapshot Phase 1–3 working tree | Passed: source archive + hash manifest |
| Back up populated PostgreSQL and retain old deployed artifacts | Blocked: target unavailable |
| Apply and verify Alembic through a93c4e125b87 | Pending live execution; offline compilation passed |
| Configure/live-test identity, including external Docker URL | Pending live execution; local startup safeguards tested |
| Populate/current core card data; full current MTGJSON sync; review failures/incomplete decks | Pending live execution |
| Verify `/mtg/api` and `/mtg/socket.io` proxy routes | Pending real proxy; fixture prefix worked |
| Real signed-in end-to-end browser smoke | Pending; fixture checks do not substitute |
| Real PostgreSQL concurrency and global resync/personal-origin check | Blocked: test URL unset |
| Production-scale catalog/statistics query measurements | Pending; operator probe supplied |
| Rollback procedure and evidence retention | Instructions supplied; old live artifacts/backup still need capture |

## Operator sequence on the reachable development server

Run with the existing service's `DATABASE_URL` and `KACHHAPA_AUTH_URL` exported securely. Do not paste passwords or session cookies into chat, commit them, or include them in reports. Use the deployed virtualenv path; the examples assume execution from `backend` with `python` bound to it.

1. Before overwriting deployed files, retain the deployed frontend directory and backend source/environment/service revision in a timestamped protected release directory. Record their paths and current Git/deployment revision. The local source snapshot does not replace these live artifacts.
2. Take and inspect a custom-format database backup **before migration**:

   ```sh
   python scripts/verifyPreconRelease.py --backup-dir /home/ijohnson/mtg-release-backups
   ```

   This requires `pg_dump` and `pg_restore`; credentials stay in the child environment. The helper checks the archive directory, which is not a restore test. Copy the backup off-server and test restoration into a separate disposable PostgreSQL database.

3. Deploy the code, configure the actual core identity origin, then upgrade with the existing ledger:

   ```sh
   python -m flask --app run:app db current
   python -m flask --app run:app db upgrade a93c4e125b87
   python -m flask --app run:app db current
   ```

   Stop on a schema/ledger conflict. Do not guess a stamp revision for a populated database. The catalog migration can adopt compatible pre-existing catalog tables, but it does not establish that the rest of an unversioned schema matches the ledger.

4. Ensure `mtgCore` is populated/current before sync. For an empty catalog use the existing card importer from the README. Do not rerun its initialization path against populated cards/decks without the existing reviewed merge/update procedure.
5. Capture pinned origins, perform the **full** existing catalog sync and retain its complete log:

   ```sh
   python scripts/verifyPreconRelease.py --origins-out /home/ijohnson/mtg-release-backups/before-origins.json
   python -m flask --app run:app sync-precons --report /home/ijohnson/mtg-release-backups/catalog-sync-report.json > /home/ijohnson/mtg-release-backups/catalog-sync.log 2>&1
   ```

   Review every failed/incomplete entry and its unresolved UUIDs/count/validation issues. Do not convert failures into playable lists or match by guessed names. Document any reviewed quarantined entries that intentionally remain visible but disabled. A nonzero sync exit must be investigated.

   `changed` and `unchanged` count successfully committed imports; `incomplete` is a subset of those imports, not an additional number of decks. `failed` counts separate imports that rolled back. The final error does not undo successful decks. Incomplete decks now print their exact saved issues. The JSON report is written before the nonzero exit and contains counts plus every incomplete deck's stable `fileName`, IDs/issues and every failed file's exception type/message. If `--report` is omitted it defaults to `precon-sync-results.json` in the current directory. Keep reports with the operator logs, since failure messages can include database details. A repeat sync is idempotent for unchanged source/resolution data; it does not erase personal decks or game history.

   After fixing the card catalog or a transient source failure, rerun only the
   reported problem decks. The new report contains only entries which still
   need another retry:

   ```sh
   python -m flask --app run:app sync-precons \
     --retry-report /home/ijohnson/mtg-release-backups/catalog-sync-report.json \
     --report /home/ijohnson/mtg-release-backups/catalog-sync-retry-report.json
   ```

   Unresolved card UUIDs indicate missing identities in `mtgCore` (including auxiliary boards), potentially because the card database and deck files came from different MTGJSON releases. Check the actual issues and source dates before planning a card-data update. The existing core initialization importer is not a safe in-place updater for populated data; do not use its wipe option to repair precons.

6. Run the real concurrency/resync test with a configured **test** PostgreSQL URL:

   ```sh
   PYTHONPATH=.:tests python -m unittest discover -s tests -p test_precon_concurrency.py -v
   ```

   `MTG_TEST_POSTGRES_URL` must be set. The test uses unique temporary schemas and cleans them up. Require a pass rather than a skip.

7. Restart the backend/deploy the matching frontend. With a signed-in test session cookie set locally as `MTG_SESSION_COOKIE`, run the live probes:

   ```sh
   python scripts/verifyPreconRelease.py \
     --base-url http://raspberrypii.local/mtg \
     --origins-before /home/ijohnson/mtg-release-backups/before-origins.json \
     --report /home/ijohnson/mtg-release-backups/live-evidence.json
   ```

   Substitute the reachable dev address. The helper verifies the migration head, live Kachhapa identity, API routes, Engine.IO polling handshake, personal origins and catalog state. It records actual card/precon/participant counts, endpoint timings and PostgreSQL EXPLAIN ANALYZE planning/execution times. Review whether the actual data distribution is production-representative. Queries have a transaction-local 30-second timeout. Reports contain no credentials or database URL.

   The report deliberately keeps `releaseReady: false`: automated probes do not certify the browser smoke test or review quarantined import failures.

8. In the real signed-in browser, at narrow and desktop widths:

   - Browse/filter/page and inspect an official deck.
   - Play Original without saving; record the returned deck ID/revision and verify the same values in game participation.
   - Complete an eligible PvP result using distinct real human accounts. Goldfish/simulation alone cannot demonstrate competitive Library Win Rate.
   - Confirm personal history includes the unlisted deck while Library Win Rate excludes it.
   - Save that same precon; confirm the same deck ID and earlier eligible result now contribute to Library Win Rate.
   - Edit its personal list; play original and current revisions and verify their separate statistics/history.
   - Compare returned revision totals and test draw/empty/unknown/invalidated/ambiguous labels with appropriate test records.
   - Verify identity failures/retry behavior and proxy/socket behavior in the actual environment.

9. Retain logs, report, screenshots taken by the operator if desired, backup/restore-test evidence, artifact hashes and an explicit human gate review. Only then mark Phase 4 release-complete.

## Rollback

Keep the pre-upgrade database dump and matching frontend/backend artifacts together. Stop the updated backend first so it cannot write during restore. Verify the backup restores into a separate rollback database before switching the service to that database; restore the previous backend/frontend/service environment as a matched set, then restart and smoke-test. Preserve the failed/new database for investigation rather than deleting its history. Do not replay catalog imports or use an automatic downgrade-to-base as a substitute for the known backup. Coordinate writes made after backup before any cutover, since restoring a backup omits later records.

For local source recovery, use the checkpoint manifest's HEAD in a clean checkout, overlay its archive and apply the recorded deletions after review. That restores the Phase 1–3 working state, including its then-uncommitted changes.

## Phase 4 files

New: `frontend/src/preconApi.js`, `frontend/src/DeckStatistics.js`, `frontend/src/Phase4.test.js`, `frontend/src/DirectPlay.test.js`, `backend/scripts/verifyPreconRelease.py`, `backend/tests/test_release_validation.py`, this runbook and source checkpoint files.

Updated: `PreconsPage.js`, `HistoryPage.js`, `DeckBuilder.js`, `App.js`, `GameLobby.js`, `MatchSetupModal.js`, `DeckRevisionSelect.js`, `Profile.js`, shared CSS; backend personal-instance validation/history metadata; optional PostgreSQL and statistics tests; Docker entrypoint/Compose; `run.py`; initial/catalog migration execution paths; backup ignore rules. Other pending changes were preserved.
