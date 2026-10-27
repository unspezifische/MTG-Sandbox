"""Personal-instance integration tests using isolated offline databases."""
import json
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch, Mock

os.environ["SOCKETIO_ASYNC_MODE"] = "threading"
os.environ["DATABASE_URL"] = "sqlite://"
from sqlalchemy import event, select, func, BigInteger, ARRAY, JSON
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

@compiles(BigInteger, "sqlite")
def integer(type_, compiler, **kw):
    return "INTEGER"

@compiles(JSONB, "sqlite")
def jsonb(type_, compiler, **kw):
    return "JSON"

from app import create_app
from app.extensions import db
from app.models.mtgCore import Card, Printing
from app.models.mtgDecks import Deck, DeckCard, DeckTokenPreference, DeckVersion, DeckVersionCard
from app.models.mtgGames import Game, GamePlayer, CardInstance
from app.services.precons import import_deck, normalize_deck
from app.services.deck_identity import revision_entries


class IdentityTests(TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.ctx = self.app.app_context(); self.ctx.push()
        # Test-only storage adapters for pre-existing PostgreSQL arrays.
        for table in db.metadata.tables.values():
            for column in table.columns:
                if isinstance(column.type, ARRAY) and "sqlite" not in column.type._variant_mapping:
                    column.type = column.type.with_variant(JSON(), "sqlite")
        @event.listens_for(db.engine, "connect")
        def schemas(conn, _):
            for schema in ("mtgCore", "mtgDecks", "mtgGames", "mtgAnalysis"):
                conn.execute(f'ATTACH DATABASE ":memory:" AS "{schema}"')
        db.create_all()
        payload = json.loads((Path(__file__).parent / "fixtures/draconic_destruction.json").read_text())
        for i, entry in enumerate(normalize_deck(payload["data"]), 1):
            db.session.add(Card(id=i, uuid="canonical-" + entry["provider_uuid"], name=entry["name"],
                               typeLine="Legendary Creature — Dragon" if entry["board"] == "commander" else "Land"))
            db.session.add(Printing(id=i, uuid=entry["provider_uuid"], cardId=i))
        t, _ = import_deck({"fileName": "Draconic_Destruction_SCD", "code": "SCD"}, payload)
        db.session.commit()
        self.template_id = t.id
        self.client = self.app.test_client()
        self.client.set_cookie("kachhapa_session", "verified-by-core")
        self.auth = patch("app.auth.requests.get", return_value=Mock(status_code=200, json=lambda: {"id": 7}))
        self.auth.start()
        # Test client calls share this manually pushed app context, unlike real requests.
        self.app.before_request(self.clear_identity)

    @staticmethod
    def clear_identity():
        from flask import g
        g.pop("mtg_user_id", None)

    def tearDown(self):
        self.auth.stop(); db.session.remove(); db.engine.dispose(); self.ctx.pop()

    def test_default_kachhapa_auth_url_uses_local_nginx(self):
        self.assertEqual(self.app.config["KACHHAPA_AUTH_URL"], "http://127.0.0.1")

    def save(self):
        r = self.client.post(f"/api/precons/{self.template_id}/save", json={"user_id": 99})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json

    def count(self, cls):
        return db.session.scalar(select(func.count()).select_from(cls))

    def test_direct_play_reuse_and_promotion(self):
        a = self.client.post(f"/api/precons/{self.template_id}/play").json
        b = self.client.post(f"/api/precons/{self.template_id}/play").json
        self.assertEqual(a["deckId"], b["deckId"])
        self.assertEqual(a["revisionId"], b["revisionId"])
        self.assertEqual(self.client.get("/api/decks").json, [])
        self.assertEqual(self.count(DeckCard), 0)
        d = self.save()
        self.assertEqual(d["id"], a["deckId"])
        self.assertEqual(d["ownerUserId"], 7)
        self.assertEqual(self.save()["id"], d["id"])
        self.assertEqual(len(self.client.get("/api/decks").json), 1)
        self.assertEqual(self.count(Deck), 1)
        self.assertEqual(self.count(DeckCard), 0)
        self.assertEqual(d["cardCount"], 100)

    def test_copy_on_write_and_revision_isolation(self):
        d = self.save(); original = d["currentRevisionId"]
        entry = next(e for e in d["cards"] if not e["isCommander"])
        result = self.client.patch(f"/api/decks/{d['id']}/cards/{entry['id']}", json={"quantity": entry["quantity"] + 1})
        self.assertEqual(result.status_code, 200, result.text)
        edited = result.json
        self.assertNotEqual(original, edited["currentRevisionId"])
        self.assertEqual(edited["revisionType"], "custom")
        self.assertEqual(edited["sourcePreconId"], self.template_id)
        stock = self.client.get(f"/api/decks/{d['id']}/revisions/{original}").json
        self.assertEqual(sum(e["quantity"] for e in stock["cards"]), 100)
        self.assertEqual(self.client.get(f"/api/precons/{self.template_id}").json["playableCardCount"], 100)
        for mode, expected in (("stock", original), ("current", edited["currentRevisionId"])):
            r = self.client.post(f"/api/decks/{d['id']}/play", json={"revision": mode})
            self.assertEqual(r.json["revisionId"], expected)
        r = self.client.patch(f"/api/decks/{d['id']}", json={"name": "My dragons"})
        self.assertEqual(r.json["sourcePreconId"], self.template_id)
        self.assertEqual(r.json["currentRevisionId"], edited["currentRevisionId"])

    def test_ownership_and_untrusted_ids(self):
        d = self.save()
        with patch("app.auth.requests.get", return_value=Mock(status_code=200, json=lambda: {"id": 8})):
            self.assertEqual(self.client.get("/api/decks").json, [])
            for path, method in ((f"/api/decks/{d['id']}", "get"),
                                 (f"/api/decks/{d['id']}/cards", "post"),
                                 (f"/api/decks/{d['id']}/revisions", "get"),
                                 (f"/api/decks/{d['id']}/play", "post")):
                self.assertEqual(getattr(self.client, method)(path, json={}).status_code, 404)
        self.client.delete_cookie("kachhapa_session")
        self.assertEqual(self.client.post(f"/api/precons/{self.template_id}/save", json={"userId": 7}).status_code, 401)
        self.assertEqual(self.client.get(f"/api/decks/{d['id']}").status_code, 404)

    def test_history_association_survives_promotion_and_archive(self):
        a = self.client.post(f"/api/precons/{self.template_id}/play").json
        g = Game(gameMode="goldfish", status="completed")
        db.session.add(g); db.session.flush()
        p = GamePlayer(gameId=g.id, seatNumber=1, deckId=a["deckId"], deckVersionId=a["revisionId"], userId=7, result="win")
        db.session.add(p); db.session.commit()
        original = (p.id, p.deckId, p.deckVersionId)
        d = self.save()
        self.client.delete(f"/api/decks/{d['id']}")
        self.assertEqual(self.client.get("/api/decks").json, [])
        self.assertEqual((p.id, p.deckId, p.deckVersionId), original)
        self.assertEqual(self.client.post(f"/api/decks/{d['id']}/restore").json["id"], d["id"])

    def test_custom_decks_and_legacy_baselines(self):
        r = self.client.post("/api/decks", json={"name": "New custom", "ownerUserId": 99, "format": "none"})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json["ownerUserId"], 7)
        self.assertEqual(r.json["libraryStatus"], "saved")
        did = r.json["id"]; old = r.json["currentRevisionId"]
        card = db.session.scalar(select(Card))
        r = self.client.post(f"/api/decks/{did}/cards", json={"cardId": card.id, "quantity": 4})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertNotEqual(self.client.get(f"/api/decks/{did}").json["currentRevisionId"], old)
        legacy = Deck(name="Legacy", format="none")
        db.session.add(legacy); db.session.commit()
        self.assertIsNone(legacy.currentVersionId)
        self.assertEqual(self.client.get(f"/api/decks/{legacy.id}").status_code, 200)
        r = self.client.post(f"/api/decks/{legacy.id}/cards", json={"cardId": card.id})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(len(self.client.get(f"/api/decks/{legacy.id}/revisions").json["revisions"]), 2)

    def test_game_seeds_selected_stock_after_edit(self):
        d = self.save()
        entry = next(e for e in d["cards"] if not e["isCommander"])
        edited = self.client.patch(f"/api/decks/{d['id']}/cards/{entry['id']}", json={"quantity": entry["quantity"] + 2}).json
        for selection, total in (("stock", 100), ("current", 102)):
            r = self.client.post("/api/games", json={"gameMode": "goldfish", "playerCount": 1,
                "players": [{"deckId": d["id"], "revision": selection, "userId": 999}]})
            self.assertEqual(r.status_code, 201, r.text)
            gid = r.json["id"]
            from app.routes import _seed_game_from_decks
            game = db.session.get(Game, gid)
            _seed_game_from_decks(game); db.session.commit()
            self.assertEqual(db.session.scalar(select(func.count()).select_from(CardInstance).where(CardInstance.gameId == gid)), total)
            player = game.players[0]
            self.assertEqual(player.userId, 7)
            self.assertEqual(player.deckVersionId, d["currentRevisionId"] if selection == "stock" else edited["currentRevisionId"])

    def test_token_versions_are_selectable_copied_and_created_on_playmat(self):
        source_card = db.session.get(Card, 1)
        source_card.rawJson = {"relatedCards": {"tokens": ["token-printing-a"]}}
        token_a = Card(
            id=1001, uuid="token-printing-a", oracleId="token-oracle",
            name="Dragon", typeLine="Token Creature — Dragon", power="4", toughness="4",
            isToken=True, defaultSetCode="TST",
        )
        token_b = Card(
            id=1002, uuid="token-printing-b", oracleId="token-oracle",
            name="Dragon", typeLine="Token Creature — Dragon", power="4", toughness="4",
            isToken=True, defaultSetCode="ALT",
        )
        db.session.add_all([
            token_a,
            token_b,
            Printing(id=1001, uuid=token_a.uuid, cardId=token_a.id, collectorNumber="1"),
            Printing(id=1002, uuid=token_b.uuid, cardId=token_b.id, collectorNumber="2"),
        ])
        db.session.commit()

        deck = self.save()
        detail = self.client.get(f"/api/decks/{deck['id']}").json
        self.assertEqual(len(detail["tokens"]), 1)
        self.assertEqual({version["printingId"] for version in detail["tokens"][0]["versions"]}, {1001, 1002})

        chosen = self.client.put(
            f"/api/decks/{deck['id']}/tokens/token-oracle",
            json={"preferredPrintingId": 1002},
        )
        self.assertEqual(chosen.status_code, 200, chosen.text)
        self.assertEqual(chosen.json["preferredPrintingId"], 1002)
        self.assertEqual(self.count(DeckTokenPreference), 1)

        clone = self.client.post(f"/api/decks/{deck['id']}/duplicate").json
        self.assertEqual(clone["tokens"][0]["preferredPrintingId"], 1002)

        response = self.client.post("/api/games", json={
            "gameMode": "goldfish", "playerCount": 1,
            "players": [{"deckId": deck["id"], "revision": "current"}],
        })
        self.assertEqual(response.status_code, 201, response.text)
        game = db.session.get(Game, response.json["id"])
        from app.routes import _seed_game_from_decks
        _seed_game_from_decks(game)
        db.session.commit()
        player = game.players[0]
        # A started game keeps the token art it was seeded with even if the deck
        # preference changes later.
        self.client.put(
            f"/api/decks/{deck['id']}/tokens/token-oracle",
            json={"preferredPrintingId": 1001},
        )
        action = self.client.post(f"/api/games/{game.id}/actions", json={"action": {
            "type": "create_token", "gamePlayerId": player.id,
            "tokenOracleId": "token-oracle", "battlefieldX": 25, "battlefieldY": 50,
        }})
        self.assertEqual(action.status_code, 200, action.text)
        created = CardInstance.query.filter_by(gameId=game.id, instanceType="token").one()
        self.assertEqual((created.cardId, created.printingId, created.zone), (1002, 1002, "battlefield"))

    def test_incomplete_and_unlisted_cannot_edit(self):
        from app.models.mtgPrecons import PreconTemplate
        template = db.session.get(PreconTemplate, self.template_id)
        template.current_version.status = "incomplete"; db.session.commit()
        self.assertEqual(self.client.post(f"/api/precons/{self.template_id}/play").status_code, 409)
        template.current_version.status = "complete"; db.session.commit()
        d = self.client.post(f"/api/precons/{self.template_id}/play").json
        self.assertEqual(self.client.post(f"/api/decks/{d['deckId']}/cards", json={"cardId": 1}).status_code, 409)

    def test_duplicate_keeps_origin_without_copying_history(self):
        d = self.save()
        g = Game(gameMode="goldfish", status="completed")
        db.session.add(g); db.session.flush()
        db.session.add(GamePlayer(gameId=g.id, seatNumber=1, deckId=d["id"], deckVersionId=d["currentRevisionId"], result="win"))
        db.session.commit()
        r = self.client.post(f"/api/decks/{d['id']}/duplicate")
        self.assertEqual(r.status_code, 201, r.text)
        self.assertNotEqual(r.json["id"], d["id"])
        self.assertEqual(r.json["sourcePreconId"], d["sourcePreconId"])
        self.assertEqual(r.json["gamesPlayed"], 0)
        self.assertFalse(db.session.get(Deck, r.json["id"]).isPrimaryPreconInstance)
        self.assertEqual(self.save()["id"], d["id"])

    def test_bulk_edit_groups_changes_and_revision_stays_immutable(self):
        d = self.save()
        initial_versions = self.count(DeckVersion)
        r = self.client.post(f"/api/decks/{d['id']}/cards/bulk", json={"boardType": "main", "mode": "merge",
            "text": "2 Forest\n3 Mountain"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.count(DeckVersion), initial_versions + 1)
        version_id = r.json["deck"]["currentRevisionId"]
        snapshot = self.client.get(f"/api/decks/{d['id']}/revisions/{version_id}").json
        r = self.client.post(f"/api/decks/{d['id']}/boards/swap", json={"sourceBoard": "main", "targetBoard": "sideboard"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.client.get(f"/api/decks/{d['id']}/revisions/{version_id}").json, snapshot)

    def test_database_primary_uniqueness(self):
        from sqlalchemy.exc import IntegrityError
        d = self.save()
        clone = Deck(name="Conflicting primary", ownerUserId=7)
        clone.sourcePreconId = self.template_id
        clone.isPrimaryPreconInstance = True
        db.session.add(clone)
        with self.assertRaises(IntegrityError):
            db.session.flush()
        db.session.rollback()
        self.assertEqual(self.count(Deck), 1)

    def test_bearer_identity_and_unavailable_auth_fail_closed(self):
        self.client.delete_cookie("kachhapa_session")
        r = self.client.post("/api/decks", json={"name": "Bearer deck"}, headers={"Authorization": "Bearer verified"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json["ownerUserId"], 7)
        with patch("app.auth.requests.get", return_value=Mock(status_code=401)):
            r = self.client.post("/api/decks", json={"name": "Denied"}, headers={"Authorization": "Bearer bad"})
            self.assertEqual(r.status_code, 401)
        import requests
        with patch("app.auth.requests.get", side_effect=requests.ConnectionError()):
            r = self.client.post("/api/decks", json={"name": "Denied"}, headers={"Authorization": "Bearer unavailable"})
            self.assertEqual(r.status_code, 503)
            self.assertIn("error", r.json)

    def test_catalog_updates_do_not_rebase_personal_origin(self):
        from app.models.mtgPrecons import PreconTemplate
        d = self.save()
        original = d["sourcePreconVersionId"]
        payload = json.loads((Path(__file__).parent / "fixtures/draconic_destruction.json").read_text())
        payload["data"]["name"] = "Official renamed list"
        template, _ = import_deck({"fileName": "Draconic_Destruction_SCD", "code": "SCD"}, payload)
        db.session.commit()
        self.assertNotEqual(template.current_version_id, original)
        self.assertEqual(self.save()["sourcePreconVersionId"], original)
        self.assertEqual(self.client.post(f"/api/precons/{self.template_id}/play").json["revisionId"], d["currentRevisionId"])

    def test_revision_scope_and_cookie_origin(self):
        a = self.save()
        b = self.client.post("/api/decks", json={"name": "Other"}).json
        r = self.client.post(f"/api/decks/{b['id']}/play", json={"revision": a["currentRevisionId"]})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.client.post(f"/api/precons/{self.template_id}/save", headers={"Origin": "https://evil.example"}).status_code, 403)
