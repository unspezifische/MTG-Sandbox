"""Optional real-PostgreSQL save/play race test, confined to unique temporary schemas."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest import TestCase, skipUnless
from unittest.mock import Mock, patch
from uuid import uuid4

from sqlalchemy import text, select, func
from app import create_app
from app.extensions import db
from app.models.mtgCore import Card, Printing
from app.models.mtgDecks import Deck
from app.services.precons import import_deck, normalize_deck


@skipUnless(os.environ.get("MTG_TEST_POSTGRES_URL"), "Set MTG_TEST_POSTGRES_URL to run PostgreSQL race test")
class PostgresConcurrencyTests(TestCase):
    def test_concurrent_save_and_play_share_one_primary(self):
        prefix = "mtg_test_" + uuid4().hex
        schemas = {s: prefix + "_" + str(i) for i, s in enumerate(("mtgCore", "mtgDecks", "mtgGames", "mtgAnalysis"))}
        app = create_app({"TESTING": True,
            "SQLALCHEMY_DATABASE_URI": os.environ["MTG_TEST_POSTGRES_URL"],
            "SQLALCHEMY_ENGINE_OPTIONS": {"execution_options": {"schema_translate_map": schemas}}})
        try:
            with app.app_context():
                with db.engine.begin() as conn:
                    for schema in schemas.values():
                        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
                db.create_all()
                payload = json.loads((Path(__file__).parent / "fixtures/draconic_destruction.json").read_text())
                for i, entry in enumerate(normalize_deck(payload["data"]), 1):
                    db.session.add(Card(id=i, uuid="canonical-" + entry["provider_uuid"], name=entry["name"]))
                    db.session.add(Printing(id=i, cardId=i, uuid=entry["provider_uuid"]))
                template, _ = import_deck({"fileName": "Draconic_Destruction_SCD", "code": "SCD"}, payload)
                db.session.commit(); template_id = template.id
            barrier = Barrier(2)
            def request(action):
                with app.test_client() as client:
                    client.set_cookie("kachhapa_session", "verified-by-test-upstream")
                    barrier.wait(timeout=10)
                    response = client.post(f"/api/precons/{template_id}/{action}")
                    if response.status_code != 200:
                        raise AssertionError(response.text)
                    return response.json["id"] if action == "save" else response.json["deckId"]
            with patch("app.auth.requests.get", return_value=Mock(status_code=200, json=lambda: {"id": 7})):
                with ThreadPoolExecutor(max_workers=2) as workers:
                    a = workers.submit(request, "save"); b = workers.submit(request, "play")
                    self.assertEqual(a.result(timeout=30), b.result(timeout=30))
            with app.app_context():
                self.assertEqual(db.session.scalar(select(func.count()).select_from(Deck)), 1)
                self.assertEqual(db.session.scalar(select(Deck.libraryStatus)), "saved")
                # A valid changed official cardlist creates a global version while
                # the existing personal source and stock revision stay pinned.
                deck = db.session.scalar(select(Deck))
                origin, revision = deck.sourcePreconVersionId, deck.currentVersionId
                payload["data"]["mainBoard"][0]["count"] += 1
                payload["data"]["mainBoard"].pop(1)
                template, changed = import_deck({"fileName": "Draconic_Destruction_SCD", "code": "SCD"}, payload)
                db.session.commit()
                self.assertTrue(changed)
                self.assertEqual(template.current_version.status, "complete")
                self.assertNotEqual(template.current_version_id, origin)
                self.assertEqual((deck.sourcePreconVersionId, deck.currentVersionId), (origin, revision))
        finally:
            with app.app_context():
                db.session.remove()
                with db.engine.begin() as conn:
                    for schema in schemas.values():
                        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
                db.engine.dispose()
