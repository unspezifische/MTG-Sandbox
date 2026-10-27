"""Offline catalog tests. SQLite exercises services/API, not PostgreSQL migrations."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ["SOCKETIO_ASYNC_MODE"] = "threading"
os.environ["DATABASE_URL"] = "sqlite://"
from sqlalchemy import event, select, func, ARRAY
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

# Existing core models are PostgreSQL-specific. Test only the relevant tables.
@compiles(ARRAY, "sqlite")
def sqlite_array(type_, compiler, **kw):
    return "JSON"

@compiles(JSONB, "sqlite")
def sqlite_jsonb(type_, compiler, **kw):
    return "JSON"

from app import create_app
from app.extensions import db
from app.models.mtgCore import Card, Printing, Set
from app.models.mtgPrecons import PreconTemplate, PreconTemplateVersion, PreconTemplateCard, PreconAlias
from app.services.precons import import_deck, normalize_deck, playable_count, require_playable

FIXTURE = Path(__file__).parent / "fixtures" / "draconic_destruction.json"


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        @event.listens_for(db.engine, "connect")
        def schemas(conn, _):
            conn.execute('ATTACH DATABASE ":memory:" AS "mtgCore"')
            conn.execute('ATTACH DATABASE ":memory:" AS "mtgDecks"')
        for cls in (Card, Set, Printing, PreconTemplate, PreconAlias, PreconTemplateVersion, PreconTemplateCard):
            cls.__table__.create(db.engine)
        self.payload = json.loads(FIXTURE.read_text())
        self.index = dict(fileName="Draconic_Destruction_SCD", name="Draconic Destruction", code="SCD")
        for i, entry in enumerate(normalize_deck(self.payload["data"]), 1):
            db.session.add(Card(id=i, uuid="canonical-" + entry["provider_uuid"], name=entry["name"]))
            db.session.add(Printing(id=i, cardId=i, uuid=entry["provider_uuid"]))
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.ctx.pop()

    def imported(self, payload=None):
        template, changed = import_deck(self.index, payload or self.payload)
        db.session.commit()
        return template, changed

    def count(self, cls):
        return db.session.scalar(select(func.count()).select_from(cls))

    def test_known_commander_import_and_detail(self):
        t, changed = self.imported()
        self.assertTrue(changed)
        self.assertEqual(t.current_version.status, "complete")
        result = self.client.get(f"/api/precons/{t.id}")
        self.assertEqual(result.status_code, 200)
        d = result.get_json()
        self.assertEqual(d["playableCardCount"], 100)
        self.assertEqual(d["boardCounts"], {"main": 99, "commander": 1})
        self.assertEqual(d["commanders"][0]["name"], "Atarka, World Render")
        self.assertTrue(d["commanders"][0]["printingId"])
        self.assertIsNotNone(d["commanders"][0]["card"])
        self.assertTrue(d["gameplayAvailable"])
        self.assertTrue(any(e["quantity"] == 5 for e in d["boards"]["main"]))

    def test_idempotence_order_and_source_meta(self):
        t, _ = self.imported()
        old = t.current_version_id
        self.payload["data"]["mainBoard"].reverse()
        self.payload["meta"]["date"] = "2099-01-01"
        t, changed = self.imported()
        self.assertFalse(changed)
        self.assertEqual(t.current_version_id, old)
        self.assertEqual(self.count(PreconTemplate), 1)
        self.assertEqual(self.count(PreconTemplateVersion), 1)

    def test_changed_content_preserves_old_version(self):
        t, _ = self.imported()
        old = t.current_version_id
        entry = self.payload["data"]["mainBoard"][0]
        old_qty = entry["count"]
        entry["count"] += 1
        t, changed = self.imported()
        self.assertTrue(changed)
        self.assertNotEqual(old, t.current_version_id)
        saved = db.session.scalar(select(PreconTemplateCard).filter_by(version_id=old, provider_uuid=entry["uuid"]))
        self.assertEqual(saved.quantity, old_qty)
        self.assertEqual(self.count(PreconTemplateVersion), 2)
        self.assertEqual(t.current_version.status, "incomplete")

    def test_unresolved_and_repair(self):
        uuid = self.payload["data"]["mainBoard"][0]["uuid"]
        printing = db.session.scalar(select(Printing).filter_by(uuid=uuid))
        printing.uuid = "temporarily-unavailable"
        db.session.commit()
        t, _ = self.imported()
        old = t.current_version_id
        with self.assertRaises(ValueError):
            require_playable(t.current_version)
        self.assertFalse(self.client.get(f"/api/precons/{t.id}").json["gameplayAvailable"])
        printing.uuid = uuid
        db.session.commit()
        t, _ = self.imported()
        self.assertNotEqual(t.current_version_id, old)
        require_playable(t.current_version)
        self.assertEqual(db.session.get(PreconTemplateVersion, old).status, "incomplete")

    def test_board_distinctions_and_overlap(self):
        d = copy.deepcopy(self.payload["data"])
        d["mainBoard"].extend(d["commander"])
        d["tokens"] = [dict(uuid="token", name="Dragon Token", count=3)]
        d["planes"] = [dict(uuid="plane", name="Plane", count=1)]
        entries = normalize_deck(d)
        self.assertEqual(playable_count(entries), 100)
        self.assertIn("planes", {c["board"] for c in entries})
        d["mainBoard"][0]["count"] = -1
        with self.assertRaises(ValueError):
            normalize_deck(d)

    def test_search_filters_pagination_and_read_only(self):
        t, _ = self.imported()
        for query in ("q=draconic", "commander=atarka", "format=commander&set=scd&year=2022"):
            response = self.client.get("/api/precons?" + query)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["total"], 1)
            self.assertNotIn("boards", response.json["precons"][0])
        for query in ("year=oops", "limit=101", "offset=-1", "limit=0"):
            self.assertEqual(self.client.get("/api/precons?" + query).status_code, 400)
        self.assertEqual(self.client.get("/api/precons?offset=1").json["precons"], [])
        self.assertEqual(self.client.get("/api/precons?q=%25").json["total"], 0)
        self.assertEqual(self.client.get("/api/precons?commander=missing").json["total"], 0)
        self.assertEqual(self.client.get("/api/precons/999999").status_code, 404)
        for method in ("post", "patch", "delete"):
            self.assertEqual(getattr(self.client, method)(f"/api/precons/{t.id}").status_code, 405)

    def test_explicit_alias_preserves_identity(self):
        t, _ = self.imported()
        original_id = t.id
        self.index["fileName"] = "Renamed_Deck_SCD"
        renamed, changed = import_deck(self.index, self.payload, alias_of=original_id)
        db.session.commit()
        self.assertEqual(renamed.id, original_id)
        self.assertFalse(changed)
        self.assertEqual(self.count(PreconAlias), 2)

    def test_transaction_rollback(self):
        import_deck(self.index, self.payload)
        db.session.rollback()
        self.assertEqual(self.count(PreconTemplate), 0)
        self.assertEqual(self.count(PreconTemplateVersion), 0)

    def test_local_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / "index.json").write_text(json.dumps({"data": [self.index]}))
            (path / (self.index["fileName"] + ".json")).write_text(json.dumps(self.payload))
            args = ["sync-precons", "--index", str(path / "index.json"), "--deck-dir", folder,
                    "--report", str(path / "report.json")]
            for _ in range(2):
                result = self.app.test_cli_runner().invoke(args=args)
                self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(self.count(PreconTemplateVersion), 1)

    def test_multiple_commanders_and_direct_card_uuid(self):
        extra = self.payload["data"]["mainBoard"].pop(0)
        self.payload["data"]["commander"].append(extra)
        uuid = extra["uuid"]
        printing = db.session.scalar(select(Printing).filter_by(uuid=uuid))
        card = db.session.get(Card, printing.cardId)
        card.uuid = uuid
        printing.uuid = "other-printing-" + uuid
        db.session.commit()
        t, _ = self.imported()
        result = self.client.get(f"/api/precons/{t.id}").json
        self.assertEqual(len(result["commanders"]), 2)
        self.assertEqual(result["playableCardCount"], 100)
        self.assertTrue(result["gameplayAvailable"])
        direct = next(c for c in result["commanders"] if c["providerUuid"] == uuid)
        self.assertIsNone(direct["printingId"])
        self.assertEqual(direct["cardId"], card.id)

    def test_cli_report_explains_problems_and_preserves_successful_imports(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            incomplete = dict(self.index, fileName="Incomplete", name="Incomplete")
            failed = dict(self.index, fileName="Failed", name="Failed")
            payload = copy.deepcopy(self.payload)
            payload["data"]["mainBoard"][0]["uuid"] = "missing-card-uuid"
            (path / "Incomplete.json").write_text(json.dumps(payload))
            (path / (self.index["fileName"] + ".json")).write_text(json.dumps(self.payload))
            # A missing deck file fails independently of both successful imports.
            (path / "index.json").write_text(json.dumps({"data": [self.index, incomplete, failed]}))
            args = ["sync-precons", "--index", str(path / "index.json"),
                    "--deck-dir", folder, "--report", str(path / "report.json")]
            for attempt in range(2):
                result = self.app.test_cli_runner().invoke(args=args)
                self.assertNotEqual(result.exit_code, 0)
                report = json.loads((path / "report.json").read_text())
                self.assertEqual(report["counts"], dict(changed=2 if attempt == 0 else 0,
                    unchanged=0 if attempt == 0 else 2, incomplete=1, failed=1))
                self.assertEqual(report["schemaVersion"], 1)
                self.assertEqual(report["selectedCount"], 3)
                self.assertEqual(report["retry"], report["problems"])
                issues, failure = report["problems"]
                self.assertEqual(issues["status"], "incomplete")
                self.assertIn("missing-card-uuid", issues["issues"][0])
                self.assertIn(issues["issues"][0], result.output)
                self.assertEqual(failure["fileName"], "Failed")
                self.assertEqual(failure["errorType"], "FileNotFoundError")
                self.assertIn("successful decks were committed", result.output)

            # Once the failed source becomes available, the prior report limits
            # the next run to only that deck and the still-incomplete one.
            (path / "Failed.json").write_text(json.dumps(self.payload))
            retry_path = path / "retry-results.json"
            retry_result = self.app.test_cli_runner().invoke(args=[
                "sync-precons", "--index", str(path / "index.json"),
                "--deck-dir", folder, "--retry-report", str(path / "report.json"),
                "--report", str(retry_path),
            ])
            self.assertNotEqual(retry_result.exit_code, 0)
            retry_report = json.loads(retry_path.read_text())
            self.assertEqual(retry_report["selectedCount"], 2)
            self.assertEqual(retry_report["counts"], dict(
                changed=1, unchanged=1, incomplete=1, failed=0,
            ))
            self.assertEqual([entry["fileName"] for entry in retry_report["retry"]], ["Incomplete"])
            self.assertNotIn("Draconic Destruction: complete", retry_result.output)
            self.assertEqual(self.count(PreconTemplate), 3)
            self.assertEqual(self.count(PreconTemplateVersion), 3)

    def test_invalid_input_does_not_replace_current_version(self):
        t, _ = self.imported()
        original = t.current_version_id
        self.payload["data"]["mainBoard"][0]["count"] = 0
        with self.assertRaises(ValueError):
            import_deck(self.index, self.payload)
        db.session.rollback()
        self.assertEqual(db.session.get(PreconTemplate, t.id).current_version_id, original)
        self.assertEqual(self.count(PreconTemplateVersion), 1)

    def test_existing_routes_remain_registered(self):
        routes = {str(r) for r in self.app.url_map.iter_rules()}
        for route in ("/api/cards", "/api/decks", "/api/decks/<int:deck_id>"):
            self.assertIn(route, routes)


if __name__ == "__main__":
    unittest.main()
