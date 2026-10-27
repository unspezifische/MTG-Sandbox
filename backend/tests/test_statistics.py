"""Phase 3 historical attribution and participant-level statistics acceptance tests."""
from unittest import TestCase
from unittest.mock import patch, Mock
from sqlalchemy import select

import test_deck_identity as identity
from app.extensions import db
from app.models.mtgDecks import Deck, DeckVersion
from app.models.mtgGames import Game, GamePlayer


class StatisticsTests(TestCase):
    setUp = identity.IdentityTests.setUp
    tearDown = identity.IdentityTests.tearDown
    clear_identity = staticmethod(identity.IdentityTests.clear_identity)
    save = identity.IdentityTests.save
    count = identity.IdentityTests.count

    def add_game(self, deck_id, revision_id, result="win", *, mode="pvp", status="completed", invalid=False,
                 computer=False, user_id=7, turns=6):
        game = Game(gameMode=mode, status=status, turnNumber=turns)
        game.isInvalidated = invalid
        db.session.add(game); db.session.flush()
        player = GamePlayer(gameId=game.id, seatNumber=1, userId=user_id, playerType="human",
                          deckId=deck_id, deckVersionId=revision_id, result=result)
        opponent = GamePlayer(gameId=game.id, seatNumber=2, userId=user_id if computer else 8,
            playerType="computer" if computer else "human", deckId=deck_id,
            deckVersionId=revision_id, result="loss" if result == "win" else "win")
        db.session.add_all([player, opponent]); db.session.commit()
        return game, player

    def stats(self):
        response = self.client.get("/api/profile/stats")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json

    def test_unsaved_games_and_retroactive_promotion(self):
        p = self.client.post(f"/api/precons/{self.template_id}/play").json
        games = [self.add_game(p["deckId"], p["revisionId"], result) for result in ("win", "win", "win", "loss", "loss")]
        before = [(g.id, player.id, player.deckId, player.deckVersionId) for g, player in games]
        self.assertEqual(self.stats()["library"]["gamesPlayed"], 0)
        overall = self.stats()["overallCompetitive"]
        self.assertEqual((overall["wins"], overall["losses"], overall["winRate"]), (3, 2, 60.0))
        history = self.client.get("/api/profile/history").json
        self.assertEqual(history["total"], 5)
        self.assertTrue(all(g["myParticipations"][0]["libraryStatus"] == "unlisted" for g in history["games"]))
        self.assertEqual(self.client.get("/api/decks").json, [])
        deck = self.save()
        self.assertEqual(deck["id"], p["deckId"])
        self.assertEqual(self.stats()["library"]["winRate"], 60.0)
        self.assertEqual(self.stats()["library"]["gamesPlayed"], 5)
        self.assertEqual([(g.id, player.id, player.deckId, player.deckVersionId) for g, player in games], before)
        self.assertEqual(self.client.get(f"/api/decks/{deck['id']}/stats").json["stats"]["wins"], 3)

    def test_revisions_keep_five_stock_and_three_custom_games(self):
        deck = self.save()
        for result in ("win", "win", "win", "loss", "loss"):
            self.add_game(deck["id"], deck["currentRevisionId"], result)
        entry = next(e for e in deck["cards"] if not e["isCommander"])
        edited = self.client.patch(f"/api/decks/{deck['id']}/cards/{entry['id']}", json={"quantity": entry["quantity"] + 12}).json
        for result in ("loss", "win", "loss"):
            self.add_game(deck["id"], edited["currentRevisionId"], result)
        detail = self.client.get(f"/api/decks/{deck['id']}/stats").json
        self.assertEqual(detail["scopes"]["all"]["gamesPlayed"], 8)
        self.assertEqual(detail["scopes"]["stock"]["gamesPlayed"], 5)
        self.assertEqual(detail["scopes"]["current"]["gamesPlayed"], 3)
        self.assertEqual(self.client.get(f"/api/decks/{deck['id']}/stats?revision=stock").json["stats"]["winRate"], 60.0)
        self.assertEqual(self.client.get(f"/api/decks/{deck['id']}/stats?revision=current").json["stats"]["gamesPlayed"], 3)
        selected = f"{deck['currentRevisionId']},{edited['currentRevisionId']}"
        self.assertEqual(self.client.get(f"/api/decks/{deck['id']}/stats?revision={selected}").json["stats"]["gamesPlayed"], 8)
        rows = db.session.scalars(select(GamePlayer).where(GamePlayer.userId == 7).order_by(GamePlayer.id)).all()
        self.assertEqual([p.deckVersionId for p in rows], [deck["currentRevisionId"]] * 5 + [edited["currentRevisionId"]] * 3)

    def test_modes_statuses_validity_and_draw_denominator(self):
        deck = self.save(); did, rid = deck["id"], deck["currentRevisionId"]
        self.add_game(did, rid, "win")
        self.add_game(did, rid, "loss")
        self.add_game(did, rid, "draw")
        for mode in ("goldfish", "simulation", "pvai"):
            self.add_game(did, rid, "win", mode=mode, computer=mode != "goldfish")
        self.add_game(did, rid, "win", computer=True)  # PvAI despite legacy pvp label
        for status in ("pending", "active", "aborted", "invalidated"):
            self.add_game(did, rid, "win", status=status)
        self.add_game(did, rid, "win", invalid=True)
        self.add_game(did, rid, None)
        stats = self.stats()
        self.assertEqual((stats["library"]["wins"], stats["library"]["losses"], stats["library"]["draws"]), (1, 1, 1))
        self.assertEqual(stats["library"]["winRate"], 50)
        self.assertEqual(stats["library"]["gamesPlayed"], 3)
        self.assertEqual(stats["pvai"]["gamesPlayed"], 2)
        self.assertEqual({(r["mode"], r["category"]) for r in stats["byMode"]},
                         {("pvp", "competitive"), ("pvp", "pvai"), ("pvai", "pvai"), ("goldfish", "goldfish"), ("simulation", "simulation")})
        response = self.client.get(f"/api/decks/{did}").json
        self.assertEqual((response["gamesPlayed"], response["winRate"], response["draws"]), (3, 50, 1))
        self.assertEqual(self.client.get(f"/api/decks/{did}/stats?mode=simulation").json["stats"]["gamesPlayed"], 1)
        self.assertEqual(self.client.get(f"/api/decks/{did}/stats?mode=pvai").json["stats"]["gamesPlayed"], 2)

    def test_duplicate_archive_restore_and_result_corrections(self):
        deck = self.save()
        game, participant = self.add_game(deck["id"], deck["currentRevisionId"])
        clone = self.client.post(f"/api/decks/{deck['id']}/duplicate").json
        self.assertEqual(self.stats()["library"]["gamesPlayed"], 1)
        self.assertEqual(self.client.get(f"/api/decks/{clone['id']}/stats").json["stats"]["gamesPlayed"], 0)
        self.client.delete(f"/api/decks/{deck['id']}")
        self.assertEqual(self.stats()["library"]["gamesPlayed"], 0)
        self.assertEqual(self.stats()["overallCompetitive"]["gamesPlayed"], 1)
        self.assertEqual(self.client.get("/api/profile/history").json["total"], 1)
        self.client.post(f"/api/decks/{deck['id']}/restore")
        self.assertEqual(self.stats()["library"]["gamesPlayed"], 1)
        participant.result = "loss"; db.session.commit()
        self.assertEqual(self.stats()["library"]["winRate"], 0)
        game.isInvalidated = True; game.invalidationReason = "Corrected invalid game"; db.session.commit()
        self.assertIsNone(self.stats()["library"]["winRate"])
        self.assertTrue(self.client.get("/api/profile/history").json["games"][0]["isInvalidated"])

    def test_multiplayer_uses_participant_result_and_excludes_ambiguous_seats(self):
        deck = self.save()
        game, player = self.add_game(deck["id"], deck["currentRevisionId"], "loss", mode="multiplayer")
        third = GamePlayer(gameId=game.id, seatNumber=3, userId=9, deckId=deck["id"], result="loss")
        db.session.add(third); game.winnerGamePlayerId = game.players[1].id; db.session.commit()
        self.assertEqual(self.stats()["library"]["losses"], 1)
        self.assertEqual(self.stats()["library"]["wins"], 0)
        # Repeated legacy hardcoded IDs must not manufacture a second result for the account.
        third.userId = 7; db.session.commit()
        self.assertEqual(self.stats()["library"]["gamesPlayed"], 0)
        self.assertEqual(self.client.get("/api/profile/history").json["total"], 1)

    def test_unknown_legacy_revision_and_account_isolation(self):
        deck = self.save()
        self.add_game(deck["id"], None)
        self.add_game(deck["id"], deck["currentRevisionId"], user_id=77)
        self.assertEqual(self.stats()["overallCompetitive"]["gamesPlayed"], 1)
        response = self.client.get(f"/api/decks/{deck['id']}/stats").json
        self.assertEqual(response["scopes"]["all"]["gamesPlayed"], 1)
        self.assertEqual(response["scopes"]["stock"]["gamesPlayed"], 0)
        self.assertIsNone(response["revisions"][0]["revisionId"])
        self.assertFalse(self.client.get("/api/profile/history").json["games"][0]["myParticipations"][0]["configurationKnown"])
        with patch("app.auth.requests.get", return_value=Mock(status_code=200, json=lambda: {"id": 8})):
            self.assertEqual(self.client.get(f"/api/decks/{deck['id']}/stats").status_code, 404)
        self.client.delete_cookie("kachhapa_session")
        for path in ("/api/profile/stats", "/api/profile/history", f"/api/decks/{deck['id']}/stats"):
            self.assertEqual(self.client.get(path).status_code, 401)

    def test_completion_route_makes_finalized_result_eligible(self):
        from werkzeug.security import generate_password_hash
        deck = self.save()
        game, participant = self.add_game(deck["id"], deck["currentRevisionId"], "loss", status="active")
        participant.lobbyTokenHash = generate_password_hash("test-participant-token")
        db.session.commit()
        self.assertEqual(self.stats()["library"]["gamesPlayed"], 0)
        response = self.client.post(f"/api/games/{game.id}/concede", json={"participantToken": "test-participant-token"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.stats()["library"]["losses"], 1)
        self.assertEqual(game.status, "completed")

    def test_pending_game_pins_configuration_before_later_edits(self):
        deck = self.save()
        response = self.client.post("/api/games", json={"gameMode": "goldfish", "playerCount": 1,
            "players": [{"deckId": deck["id"]}]})
        self.assertEqual(response.status_code, 201, response.text)
        game = db.session.get(Game, response.json["id"])
        entry = next(e for e in deck["cards"] if not e["isCommander"])
        self.client.patch(f"/api/decks/{deck['id']}/cards/{entry['id']}", json={"quantity": entry["quantity"] + 2})
        from app.routes import _seed_game_from_decks
        from app.models.mtgGames import CardInstance
        from sqlalchemy import func
        _seed_game_from_decks(game); db.session.commit()
        self.assertEqual(game.players[0].deckVersionId, deck["currentRevisionId"])
        self.assertEqual(db.session.scalar(select(func.count()).select_from(CardInstance).where(CardInstance.gameId == game.id)), 100)

    def test_unavailable_current_catalog_disables_save_and_play_for_existing_instance(self):
        deck = self.save()
        from app.models.mtgPrecons import PreconTemplate
        template = db.session.get(PreconTemplate, self.template_id)
        template.current_version.status = "incomplete"
        db.session.commit()
        for action in ("save", "play"):
            response = self.client.post(f"/api/precons/{self.template_id}/{action}")
            self.assertEqual(response.status_code, 409)

    def test_filters_pagination_empty_and_normalization(self):
        deck = self.save()
        self.assertIsNone(self.stats()["library"]["winRate"])
        self.add_game(deck["id"], deck["currentRevisionId"], " WON ", turns=8)
        self.add_game(deck["id"], deck["currentRevisionId"], "draw", turns=10)
        self.assertEqual(self.stats()["library"]["averageTurns"], 9)
        self.assertEqual(self.stats()["library"]["winRate"], 100)
        self.assertEqual(len(self.client.get("/api/profile/history?limit=1&offset=1").json["games"]), 1)
        for query in ("limit=0", "limit=101", "offset=-1", "limit=bad"):
            self.assertEqual(self.client.get("/api/profile/history?" + query).status_code, 400)
        for query in ("revision=nope", "revision=0", "mode=banana"):
            self.assertEqual(self.client.get(f"/api/decks/{deck['id']}/stats?" + query).status_code, 400)
        other = self.client.post("/api/decks", json={"name": "Other deck"}).json
        self.assertEqual(self.client.get(f"/api/decks/{other['id']}/stats?revision={deck['currentRevisionId']}").status_code, 404)
