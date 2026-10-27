import React, { useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";
import "./App.css";

import { mergePlayDecks, apiErrorMessage } from "./preconApi";
import Profile from "./Profile";
import DeckBuilder from "./DeckBuilder";
import DecksPage from "./DecksPage";
import PreconsPage from "./PreconsPage";
import GameLobby from "./GameLobby";
import PlayMat from "./PlayMat";
import MatchSetupModal from "./MatchSetupModal";
import HistoryPage from "./HistoryPage";
import SettingsPage from "./SettingsPage";

const isMtgSubpath = window.location.pathname.startsWith("/mtg");
const API_BASE = isMtgSubpath ? "/mtg/api" : "/api";
const SOCKET_PATH = isMtgSubpath ? "/mtg/socket.io" : "/socket.io";
const LOBBY_TOKEN_KEY = "mtg-sandbox-lobby-token";
const SLEEVE_OPTIONS = [
  ["classic", "Classic MTG"],
  ["obsidian-matte", "Obsidian · Matte"],
  ["sapphire-glossy", "Sapphire · Glossy"],
  ["crimson-semi-gloss", "Crimson · Semi-gloss"],
  ["emerald-matte", "Emerald · Matte"],
  ["arcane-swirl", "Arcane Swirl · Animated"],
  ["dragon-scale", "Dragon Scale"],
];

function getLobbyParticipantToken() {
  const existing = window.localStorage.getItem(LOBBY_TOKEN_KEY);
  if (existing) return existing;
  const token = window.crypto?.randomUUID
    ? `${window.crypto.randomUUID()}-${window.crypto.randomUUID()}`
    : `${Date.now()}-${Math.random()}-${Math.random()}`;
  window.localStorage.setItem(LOBBY_TOKEN_KEY, token);
  return token;
}

function getAccountDashboardHref() {
  const accountHost = /^mtg\./i.test(window.location.hostname)
    ? window.location.host.replace(/^mtg\./i, "")
    : window.location.host;
  return `${window.location.protocol}//${accountHost}/accountProfile`;
}

function getAvatarInitials(username) {
  const parts = String(username || "Planeswalker")
    .trim()
    .split(/[\s._-]+/)
    .filter(Boolean);
  return parts.slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "P";
}

function App() {
  const invitedLobbyId = new URLSearchParams(window.location.search).get("lobby") || "";
  const [activePage, setActivePage] = useState(invitedLobbyId ? "play" : "profile");
  const [selectedDeckId, setSelectedDeckId] = useState(null);
  const [createDeckRequestId, setCreateDeckRequestId] = useState(0);
  const [createLobbyRequestId, setCreateLobbyRequestId] = useState(0);
  const [preferredLobbyDeckId, setPreferredLobbyDeckId] = useState("");
  const [matchSetup, setMatchSetup] = useState(null);
  const [directSelections, setDirectSelections] = useState([]);
  const [preferredLobbyRevision, setPreferredLobbyRevision] = useState("current");

  const [socket, setSocket] = useState(null);

  const [games, setGames] = useState([]);
  const [decks, setDecks] = useState([]);
  const playDecks = useMemo(() => mergePlayDecks(decks, directSelections), [decks, directSelections]);
  const [selectedGameId, setSelectedGameId] = useState(invitedLobbyId);
  const [currentGame, setCurrentGame] = useState(null);
  const [currentGamePlayerId, setCurrentGamePlayerId] = useState("");

  const [playLoading, setPlayLoading] = useState(false);
  const [playError, setPlayError] = useState("");
  const [decksLoading, setDecksLoading] = useState(true);
  const [decksError, setDecksError] = useState("");
  const [participantToken] = useState(getLobbyParticipantToken);
  const [signedInUser, setSignedInUser] = useState("");
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef(null);

  const [appearanceMode,setAppearanceMode]=useState(()=>window.KachhapaAppearance?.mode()||'dark');
  useEffect(() => {
    const update=()=>{const runtime=window.KachhapaAppearance;setSignedInUser(runtime?.snapshot()?.username||'');setAppearanceMode(runtime?.mode()||'dark');};
    update();
    window.KachhapaAppearance?.refresh().catch(()=>{});
    window.addEventListener('appearance-changed',update);
    return()=>window.removeEventListener('appearance-changed',update);
  }, []);

  useEffect(() => {
    if (!userMenuOpen) return undefined;
    const closeOnOutsideClick = (event) => {
      if (!userMenuRef.current?.contains(event.target)) setUserMenuOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setUserMenuOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [userMenuOpen]);

  useEffect(() => {
    const socketClient = io({
      path: SOCKET_PATH,
      transports: ["websocket", "polling"],
      autoConnect: true,
    });

    setSocket(socketClient);

    return () => {
      socketClient.disconnect();
    };
  }, []);

  useEffect(() => {
    async function loadPlayData() {
      const gamesRequest = fetch(`${API_BASE}/games`)
        .then(async (response) => {
          if (!response.ok) throw new Error(`Failed to load games (${response.status})`);
          const payload = await response.json();
          setGames(Array.isArray(payload) ? payload : []);
        })
        .catch((error) => {
          console.error("Failed to load games:", error);
          setPlayError("Game lobbies could not be loaded. Use Refresh to try again.");
        });
      const decksRequest = fetch(`${API_BASE}/decks`)
        .then(async (response) => {
          if (!response.ok) throw new Error(`Failed to load decks (${response.status})`);
          const payload = await response.json();
          setDecks(Array.isArray(payload) ? payload : []);
          setDecksError("");
        })
        .catch((error) => {
          console.error("Failed to load decks:", error);
          setDecksError("Saved decks could not be loaded.");
        })
        .finally(() => setDecksLoading(false));
      try {
        await Promise.allSettled([gamesRequest, decksRequest]);
      } catch {
        // Each independent request reports its own failure.
      }
    }

    loadPlayData();
  }, []);

  useEffect(() => {
    if (!selectedGameId) {
      setCurrentGame(null);
      return;
    }

    async function loadGame() {
      setPlayLoading(true);
      setPlayError("");

      try {
        const response = await fetch(`${API_BASE}/games/${selectedGameId}`, {
          headers: { "X-Lobby-Token": participantToken },
        });
        if (!response.ok) {
          throw new Error(`Failed to load game (${response.status})`);
        }

        const payload = await response.json();
        setCurrentGame(payload);
        setCurrentGamePlayerId(payload.currentPlayerId ? String(payload.currentPlayerId) : "");
      } catch (error) {
        console.error("Failed to load game:", error);
        setPlayError("Failed to load the selected game.");
        setCurrentGame(null);
      } finally {
        setPlayLoading(false);
      }
    }

    loadGame();
  }, [participantToken, selectedGameId]);

  useEffect(() => {
    if (!selectedGameId || currentGame?.status !== "pending") return undefined;

    let cancelled = false;
    const refreshSelectedLobby = async () => {
      try {
        const response = await fetch(`${API_BASE}/games/${selectedGameId}`, {
          headers: { "X-Lobby-Token": participantToken },
        });
        if (response.status === 404) {
          if (!cancelled) {
            setGames((previous) => previous.filter(
              (game) => Number(game.id) !== Number(selectedGameId)
            ));
            setCurrentGame(null);
            setCurrentGamePlayerId("");
            setSelectedGameId("");
          }
          return;
        }
        if (!response.ok) return;
        const payload = await response.json();
        if (!cancelled) {
          setCurrentGame(payload);
          setCurrentGamePlayerId(payload.currentPlayerId ? String(payload.currentPlayerId) : "");
          setGames((previous) => previous.map((game) => (
            Number(game.id) === Number(payload.id) ? payload : game
          )));
        }
      } catch {
        // Socket updates remain primary; the poll is only a recovery path.
      }
    };

    const intervalId = window.setInterval(refreshSelectedLobby, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [currentGame?.status, participantToken, selectedGameId]);

  useEffect(() => {
    if (!socket || !selectedGameId) return undefined;

    const numericGameId = Number(selectedGameId);
    const joinSelectedRoom = () => {
      socket.emit("game:join", { gameId: numericGameId });
      socket.emit("lobby:presence", {
        gameId: numericGameId,
        participantToken,
      });
    };
    if (socket.connected) joinSelectedRoom();
    socket.on("connect", joinSelectedRoom);

    const handleLobbyUpdated = (payload) => {
      if (Number(payload?.gameId) !== numericGameId || !payload?.game) return;
      setCurrentGame((previous) => ({
        ...payload.game,
        currentPlayerId: previous?.currentPlayerId || null,
        currentUserIsHost: previous?.currentUserIsHost || false,
      }));
      setGames((previous) => previous.map((game) => (
        Number(game.id) === numericGameId ? payload.game : game
      )));
    };

    const handleStateUpdated = (payload) => {
      if (Number(payload?.gameId) !== numericGameId) return;
      if (payload?.state?.game?.status === "completed") {
        setCurrentGame(null);
        setCurrentGamePlayerId("");
        setSelectedGameId("");
        window.history.replaceState(null, "", window.location.pathname);
        setPlayError("Game complete. You have returned to the lobby browser.");
        handleRefreshGames();
        return;
      }
      setCurrentGame((previous) => (
        previous ? { ...previous, status: payload?.state?.game?.status || previous.status } : previous
      ));
      setGames((previous) => previous.map((game) => (
        Number(game.id) === numericGameId
          ? { ...game, status: payload?.state?.game?.status || game.status }
          : game
      )));
    };

    const handleLobbyClosed = (payload) => {
      if (Number(payload?.gameId) !== numericGameId) return;
      setCurrentGame(null);
      setCurrentGamePlayerId("");
      setSelectedGameId("");
      window.history.replaceState(null, "", window.location.pathname);
      setPlayError("This lobby was closed by its host.");
    };

    socket.on("game:lobby_updated", handleLobbyUpdated);
    socket.on("game:state_updated", handleStateUpdated);
    socket.on("game:lobby_closed", handleLobbyClosed);
    return () => {
      socket.off("connect", joinSelectedRoom);
      socket.off("game:lobby_updated", handleLobbyUpdated);
      socket.off("game:state_updated", handleStateUpdated);
      socket.off("game:lobby_closed", handleLobbyClosed);
    };
  }, [participantToken, socket, selectedGameId]);

  useEffect(() => {
    if (!socket) return undefined;

    const handleLobbiesUpdated = async (payload) => {
      const changedGameId = Number(payload?.gameId);
      if (!changedGameId) return;

      if (payload.action === "closed") {
        setGames((previous) => previous.filter((game) => Number(game.id) !== changedGameId));
        if (Number(selectedGameId) === changedGameId) {
          setCurrentGame(null);
          setCurrentGamePlayerId("");
          setSelectedGameId("");
          window.history.replaceState(null, "", window.location.pathname);
          setPlayError("This lobby was closed by its host.");
        }
        return;
      }

      if (payload.game) {
        setGames((previous) => {
          const found = previous.some((game) => Number(game.id) === changedGameId);
          return found
            ? previous.map((game) => Number(game.id) === changedGameId ? payload.game : game)
            : [payload.game, ...previous];
        });
      }

      if (Number(selectedGameId) === changedGameId && payload.action !== "started") {
        try {
          const response = await fetch(`${API_BASE}/games/${changedGameId}`, {
            headers: { "X-Lobby-Token": participantToken },
          });
          if (!response.ok) return;
          const personalizedGame = await response.json();
          setCurrentGame(personalizedGame);
          setCurrentGamePlayerId(
            personalizedGame.currentPlayerId ? String(personalizedGame.currentPlayerId) : ""
          );
        } catch (error) {
          console.error("Failed to refresh updated lobby:", error);
        }
      }
    };

    socket.on("lobbies:updated", handleLobbiesUpdated);
    return () => socket.off("lobbies:updated", handleLobbiesUpdated);
  }, [participantToken, selectedGameId, socket]);

  const selectedPlayer = useMemo(() => {
    if (!currentGame || !currentGamePlayerId) return null;
    return (
      currentGame.players?.find(
        (player) => String(player.id) === String(currentGamePlayerId)
      ) || null
    );
  }, [currentGame, currentGamePlayerId]);

  async function handleRefreshGames() {
    try {
      const response = await fetch(`${API_BASE}/games`);
      if (!response.ok) {
        throw new Error(`Failed to load games (${response.status})`);
      }

      const payload = await response.json();
      setGames(Array.isArray(payload) ? payload : []);
    } catch (error) {
      console.error("Failed to refresh games:", error);
    }
  }

  async function handleRefreshDecks() {
    setDecksLoading(true);
    setDecksError("");
    try {
      const response = await fetch(`${API_BASE}/decks`, { cache: "no-store" });
      if (!response.ok) throw new Error(`Failed to load decks (${response.status})`);
      const payload = await response.json();
      const refreshedDecks = Array.isArray(payload) ? payload : [];
      setDecks(refreshedDecks);
      return refreshedDecks;
    } catch (error) {
      console.error("Failed to refresh decks:", error);
      setDecksError("Saved decks could not be loaded. Check the connection and try again.");
      return [];
    } finally {
      setDecksLoading(false);
    }
  }

  async function handlePreconPlay(selection, mode) {
    if (!selection.deck || !selection.deckId || !selection.revisionId) throw new Error("The precon resolver returned an incomplete selection. Refresh details and retry.");
    setDirectSelections((previous) => [...previous.filter((p) => p.deckId !== selection.deckId), selection]);
    if (mode === "pvp") {
      setPreferredLobbyRevision(selection.revisionId);
      handleStartMatchShortcut(selection.deckId, selection.revisionId);
    } else {
      setMatchSetup({ mode, initialDeckId: String(selection.deckId), initialRevision: selection.revisionId });
    }
  }

  async function handleCreateLobby(lobby) {
    setPlayLoading(true);
    setPlayError("");
    try {
      const response = await fetch(`${API_BASE}/games`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...lobby, participantToken }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiErrorMessage(response.status, payload?.error || "Failed to create lobby."));
      if (!payload.id) throw new Error("The game service returned an invalid response. Check the API proxy and retry.");

      setCurrentGame(payload);
      setSelectedGameId(String(payload.id));
      setCurrentGamePlayerId(payload.currentPlayerId ? String(payload.currentPlayerId) : "");
      setGames((previous) => [payload, ...previous.filter((game) => game.id !== payload.id)]);
      window.history.replaceState(null, "", `${window.location.pathname}?lobby=${payload.id}`);
      return payload;
    } catch (error) {
      const message = error.message || "Failed to create lobby.";
      setPlayError(message);
      return { error: message };
    } finally {
      setPlayLoading(false);
    }
  }

  async function handleJoinLobby(gameId, deckId, password, revision = "current") {
    setPlayLoading(true);
    setPlayError("");
    try {
      const response = await fetch(`${API_BASE}/games/${gameId}/join`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ deckId, password, participantToken, revision,
          ...(Number.isInteger(Number(revision)) ? { deckVersionId: Number(revision) } : {}) }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiErrorMessage(response.status, payload?.error || "Failed to join lobby."));
      if (!payload.id) throw new Error("The game service returned an invalid response. Check the API proxy and retry.");

      setCurrentGame(payload);
      setSelectedGameId(String(gameId));
      setCurrentGamePlayerId(payload.currentPlayerId ? String(payload.currentPlayerId) : "");
      setGames((previous) => previous.map((game) => (
        Number(game.id) === Number(gameId) ? payload : game
      )));
      window.history.replaceState(null, "", `${window.location.pathname}?lobby=${gameId}`);
      return payload;
    } catch (error) {
      const message = error.message || "Failed to join lobby.";
      setPlayError(message);
      return { error: message };
    } finally {
      setPlayLoading(false);
    }
  }

  async function handleReadyChange(ready) {
    setPlayLoading(true);
    setPlayError("");
    try {
      const response = await fetch(`${API_BASE}/games/${selectedGameId}/ready`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ participantToken, ready }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.error || "Failed to update readiness.");
      setCurrentGame(payload);
      setGames((previous) => previous.map((game) => (
        Number(game.id) === Number(selectedGameId) ? payload : game
      )));
    } catch (error) {
      setPlayError(error.message || "Failed to update readiness.");
    } finally {
      setPlayLoading(false);
    }
  }

  async function handleSleeveChange(sleeveStyle) {
    setPlayError("");
    try {
      const response = await fetch(`${API_BASE}/games/${selectedGameId}/sleeve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ participantToken, sleeveStyle }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.error || "Failed to update sleeve.");
      setCurrentGame(payload);
    } catch (error) {
      setPlayError(error.message || "Failed to update sleeve.");
    }
  }

  async function requestStartGame(force = false) {
    const response = await fetch(`${API_BASE}/games/${selectedGameId}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ participantToken, force }),
    });
    const payload = await response.json();
    if (
      response.status === 409
      && payload?.requiresConfirmation
      && !force
    ) {
      const reasons = (payload.reasons || []).join("\n");
      const confirmed = window.confirm(
        `${reasons}\n\nDo you truly want to start the game anyway?`
      );
      if (confirmed) return requestStartGame(true);
      return null;
    }
    if (!response.ok) throw new Error(payload?.error || "Failed to start game.");
    return payload;
  }

  async function handleStartGame() {
    setPlayLoading(true);
    setPlayError("");
    try {
      const payload = await requestStartGame(false);
      if (!payload) return;
      setCurrentGame(payload.game);
      await handleRefreshGames();
    } catch (error) {
      setPlayError(error.message || "Failed to start game.");
    } finally {
      setPlayLoading(false);
    }
  }

  async function handleLeaveLobby() {
    if (!window.confirm("Leave this lobby and reopen your seat?")) return;
    setPlayLoading(true);
    setPlayError("");
    try {
      const response = await fetch(`${API_BASE}/games/${selectedGameId}/leave`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ participantToken }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.error || "Failed to leave lobby.");
      setCurrentGame(null);
      setCurrentGamePlayerId("");
      setSelectedGameId("");
      window.history.replaceState(null, "", window.location.pathname);
      await handleRefreshGames();
    } catch (error) {
      setPlayError(error.message || "Failed to leave lobby.");
    } finally {
      setPlayLoading(false);
    }
  }

  async function handleCloseLobby() {
    if (!window.confirm("Close this lobby for every player? This cannot be undone.")) return;
    setPlayLoading(true);
    setPlayError("");
    try {
      const response = await fetch(`${API_BASE}/games/${selectedGameId}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ participantToken }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.error || "Failed to close lobby.");
      setGames((previous) => previous.filter((game) => Number(game.id) !== Number(selectedGameId)));
      setCurrentGame(null);
      setCurrentGamePlayerId("");
      setSelectedGameId("");
      window.history.replaceState(null, "", window.location.pathname);
    } catch (error) {
      setPlayError(error.message || "Failed to close lobby.");
    } finally {
      setPlayLoading(false);
    }
  }

  async function handleOpenDeck(deckId) {
    try {
      await fetch(`${API_BASE}/decks/${deckId}/used`, { method: "POST" });
    } catch {
      // Opening the editor should still work if usage tracking is temporarily unavailable.
    }
    setSelectedDeckId(deckId);
    setActivePage("deckBuilder");
  }

  function handleCreateDeckShortcut() {
    setSelectedDeckId(null);
    setActivePage("decks");
    setCreateDeckRequestId((value) => value + 1);
  }

  function handleStartMatchShortcut(deckId = "", revision = "current") {
    setCurrentGame(null);
    setCurrentGamePlayerId("");
    setSelectedGameId("");
    setPreferredLobbyDeckId(deckId ? String(deckId) : "");
    setPreferredLobbyRevision(revision);
    setActivePage("play");
    setCreateLobbyRequestId((value) => value + 1);
    window.history.replaceState(null, "", window.location.pathname);
  }

  function handleGameComplete() {
    setCurrentGame(null);
    setCurrentGamePlayerId("");
    setSelectedGameId("");
    setActivePage("play");
    setPlayError("Game complete. You have returned to the lobby browser.");
    window.history.replaceState(null, "", window.location.pathname);
    handleRefreshGames();
  }

  function handleExitGame(message = "You returned to the lobby browser.") {
    setCurrentGame(null);
    setCurrentGamePlayerId("");
    setSelectedGameId("");
    setActivePage("play");
    setPlayError(message);
    window.history.replaceState(null, "", window.location.pathname);
    handleRefreshGames();
  }

  async function launchConfiguredMatch({
    mode,
    playerDeckId,
    computerDeckId = null,
    strategy = "adaptive",
    revision = "current",
    computerRevision = "current",
  }) {
    setPlayLoading(true);
    setPlayError("");
    try {
      const selectedDeck = playDecks.find((deck) => Number(deck.id) === Number(playerDeckId));
      const players = [{
        seatNumber: 1,
        playerType: "human",
        deckId: Number(playerDeckId),
        revision,
        ...(Number.isInteger(Number(revision)) ? { deckVersionId: Number(revision) } : {}),
      }];
      if (mode === "simulation") {
        players.push({
          seatNumber: 2,
          playerType: "computer",
          deckId: Number(computerDeckId),
          aiProfile: strategy,
          revision: computerRevision,
          ...(Number.isInteger(Number(computerRevision)) ? { deckVersionId: Number(computerRevision) } : {}),
        });
      }
      const response = await fetch(`${API_BASE}/games`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gameMode: mode,
          format: selectedDeck?.format || "commander",
          ruleset: "playtest",
          playerCount: players.length,
          players,
          participantToken,
          notes: mode === "simulation" ? `Computer strategy: ${strategy}` : "Solo Goldfish playtest",
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiErrorMessage(response.status, payload?.error || "Could not start the match."));
      if (!payload.id) throw new Error("The game service returned an invalid response. Check the API proxy and retry.");
      setCurrentGame(payload);
      setSelectedGameId(String(payload.id));
      setCurrentGamePlayerId(String(payload.currentPlayerId || payload.players?.[0]?.id || ""));
      setGames((previous) => [payload, ...previous]);
      setActivePage("play");
      window.history.replaceState(null, "", `${window.location.pathname}?lobby=${payload.id}`);
      return payload;
    } catch (error) {
      const message = error.message || "Could not start the match.";
      setPlayError(message);
      return { error: message };
    } finally {
      setPlayLoading(false);
    }
  }

  function handleGoldfish(deckId = "", revision = "current") {
    if (deckId) {
      launchConfiguredMatch({ mode: "goldfish", playerDeckId: Number(deckId), revision });
      return;
    }
    setMatchSetup({ mode: "goldfish", initialDeckId: "" });
  }

  function handleSimulation(deckId = "", revision = "current") {
    setMatchSetup({ mode: "simulation", initialDeckId: deckId ? String(deckId) : "", initialRevision: revision });
  }

  function handlePvP() {
    setCurrentGame(null);
    setCurrentGamePlayerId("");
    setSelectedGameId("");
    setActivePage("play");
    window.history.replaceState(null, "", window.location.pathname);
  }

  function renderPlayPage() {
    if (!playLoading && currentGame?.status === "active" && currentGamePlayerId) {
      return (
        <PlayMat
          gameId={Number(selectedGameId)}
          activePlayerId={Number(currentGamePlayerId)}
          participantToken={participantToken}
          onGameComplete={handleGameComplete}
          onExitGame={handleExitGame}
        />
      );
    }

    return (
      <div className="page-shell">
        <div className="page-card play-page-shell">
          <GameLobby
            games={games}
            decks={playDecks}
            selectedGameId={selectedGameId}
            busy={playLoading}
            onRefresh={handleRefreshGames}
            onRefreshDecks={handleRefreshDecks}
            decksLoading={decksLoading}
            decksError={decksError}
            onSelect={(gameId) => setSelectedGameId(String(gameId))}
            onCreate={handleCreateLobby}
            onJoin={handleJoinLobby}
            createRequestId={createLobbyRequestId}
            preferredDeckId={preferredLobbyDeckId}
            preferredRevision={preferredLobbyRevision}
          />

          {currentGame?.status === "pending" && (
            <div className="lobby-seats selected-lobby">
              <div className="selected-lobby-heading">
                <div>
                  <div className="eyebrow">Waiting room</div>
                  <h3>{currentGame.lobbyName || `Game #${currentGame.id}`}</h3>
                  <p>
                    {currentGame.format} · {currentGame.gameMode} · {currentGame.ruleset}
                    {currentGame.isPasswordProtected ? " · Password protected" : ""}
                  </p>
                </div>
                <strong>{currentGame.occupiedPlayerCount}/{currentGame.maxPlayers} seated</strong>
              </div>
              {currentGame.players?.map((player) => (
                <div className="lobby-seat" key={player.id}>
                  <span>
                    <i className={player.isReady ? "ready" : player.deckId ? "seated" : ""} />
                    Seat {player.seatNumber}
                    {player.isHost ? <small>Host</small> : null}
                  </span>
                  {player.deckId ? (
                    <div className="lobby-player-status">
                      <strong>{player.deckName}</strong>
                      <span className={
                        !player.isConnected
                          ? "disconnected"
                          : player.isReady ? "ready" : "not-ready"
                      }>
                        {!player.isConnected
                          ? player.disconnectedAt ? "Reconnecting…" : "Connecting…"
                          : player.isReady ? "Ready" : "Not ready"}
                      </span>
                    </div>
                  ) : (
                    <em>Waiting for a player…</em>
                  )}
                </div>
              ))}
              {selectedPlayer && (
                <div className="selected-lobby-actions">
                  <label className="lobby-sleeve-picker">
                    <span>Deck sleeve</span>
                    <select
                      value={selectedPlayer.sleeveStyle || "classic"}
                      onChange={(event) => handleSleeveChange(event.target.value)}
                      disabled={playLoading}
                    >
                      {SLEEVE_OPTIONS.map(([value, label]) => (
                        <option value={value} key={value}>{label}</option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    className={selectedPlayer.isReady ? "button-secondary" : "button-primary"}
                    onClick={() => handleReadyChange(!selectedPlayer.isReady)}
                    disabled={playLoading}
                  >
                    {selectedPlayer.isReady ? "Mark not ready" : "I'm ready"}
                  </button>
                  {currentGame.currentUserIsHost ? (
                    <>
                      <button
                        type="button"
                        className="button-primary"
                        onClick={handleStartGame}
                        disabled={playLoading || currentGame.occupiedPlayerCount < 2}
                      >
                        Start game
                      </button>
                      <button
                        type="button"
                        className="button-danger"
                        onClick={handleCloseLobby}
                        disabled={playLoading}
                      >
                        Close lobby
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      className="button-danger"
                      onClick={handleLeaveLobby}
                      disabled={playLoading}
                    >
                      Leave lobby
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {playLoading && (
            <div className="play-page-message">Loading play data...</div>
          )}

          {playError && (
            <div className="play-page-error">{playError}</div>
          )}

          {!playLoading && !currentGame && (
            <div className="play-page-message">
              Choose an available lobby or create a new game.
            </div>
          )}

          {!playLoading && currentGame && !currentGamePlayerId && (
            <div className="play-page-message">
              Join this lobby with one of your saved decks to claim a seat.
            </div>
          )}

          {selectedPlayer && (
            <div className="play-page-footer-note">
              Controlling seat {selectedPlayer.seatNumber}
              {selectedPlayer.deckName ? ` · ${selectedPlayer.deckName}` : ""}
            </div>
          )}
        </div>
      </div>
    );
  }

  function renderPage() {
    switch (activePage) {
      case "profile":
        return (
          <Profile
            onNavigate={setActivePage}
            onOpenDeck={handleOpenDeck}
            onCreateDeck={handleCreateDeckShortcut}
            onStartMatch={handleStartMatchShortcut}
            onGoldfish={handleGoldfish}
            onSimulation={handleSimulation}
            onPvP={handlePvP}
          />
        );

      case "decks":
      case "deckBuilder":
        if (selectedDeckId) {
          return (
            <DeckBuilder
              deckId={selectedDeckId}
              onBack={() => {
                setSelectedDeckId(null);
                setActivePage("decks");
              }}
              onLaunchGame={(mode, launchDeckId, revision) => (
                mode === "goldfish"
                  ? handleGoldfish(launchDeckId, revision)
                  : handleSimulation(launchDeckId, revision)
              )}
            />
          );
        }
        return (
          <DecksPage
            onOpenDeck={handleOpenDeck}
            createRequestId={createDeckRequestId}
            onCreateRequestHandled={() => setCreateDeckRequestId(0)}
          />
        );

      case "precons":
        return <PreconsPage onOpenDeck={handleOpenDeck} onSaved={handleRefreshDecks} onPlay={handlePreconPlay} />;

      case "play":
        return renderPlayPage();

      case "history":
        return <HistoryPage onOpenDeck={handleOpenDeck} />;

      case "settings":
        return <SettingsPage />;

      default:
        return (
          <Profile
            onNavigate={setActivePage}
            onOpenDeck={handleOpenDeck}
            onCreateDeck={handleCreateDeckShortcut}
            onStartMatch={handleStartMatchShortcut}
            onGoldfish={handleGoldfish}
            onSimulation={handleSimulation}
            onPvP={handlePvP}
          />
        );
    }
  }

  const showingActivePlaymat = (
    activePage === "play"
    && currentGame?.status === "active"
    && Boolean(currentGamePlayerId)
  );

  return (
    <div className={`app-root ${showingActivePlaymat ? "playmat-active" : ""}`}>
      {!showingActivePlaymat && <header className="topbar">
        <div className="topbar-left">
          <div className="app-brand">MTG Sandbox</div>
        </div>

        <nav className="topbar-nav">
          <button
            className={`nav-button ${activePage === "profile" ? "active" : ""}`}
            onClick={() => setActivePage("profile")}
            type="button"
          >
            Pod Bay
          </button>

          <button
            className={`nav-button ${["decks", "deckBuilder"].includes(activePage) ? "active" : ""}`}
            onClick={() => {
              setSelectedDeckId(null);
              setActivePage("decks");
            }}
            type="button"
          >
            Your Decks
          </button>

          <button type="button" className={`nav-button ${activePage === "precons" ? "active" : ""}`} onClick={() => setActivePage("precons")}>Precons</button>
          <button
            className={`nav-button ${activePage === "play" ? "active" : ""}`}
            onClick={() => setActivePage("play")}
            type="button"
          >
            Play
          </button>

          <button
            className={`nav-button ${activePage === "history" ? "active" : ""}`}
            onClick={() => setActivePage("history")}
            type="button"
          >
            History
          </button>
        </nav>

        <div className="topbar-right">
          {signedInUser ? (
            <div className="topbar-welcome">Welcome back, <strong>{signedInUser}</strong></div>
          ) : null}
          <div className="user-menu" ref={userMenuRef}>
            <button
              className={`user-avatar ${activePage === "settings" ? "active" : ""}`}
              type="button"
              aria-label={signedInUser ? `Open menu for ${signedInUser}` : "Open user menu"}
              aria-haspopup="menu"
              aria-expanded={userMenuOpen}
              onClick={() => setUserMenuOpen((open) => !open)}
            >
              <span aria-hidden="true">{getAvatarInitials(signedInUser)}</span>
            </button>
            {userMenuOpen ? (
              <div className="user-menu-popover" role="menu" aria-label="User menu">
                <div className="user-menu-heading">
                  <span>MTG Sandbox</span>
                  <strong>{signedInUser || "Planeswalker"}</strong>
                </div>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setActivePage("settings");
                    setUserMenuOpen(false);
                  }}
                >
                  <span>Settings</span>
                  <small>Sandbox preferences</small>
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    window.KachhapaAppearance
                      ?.setMode(appearanceMode === "dark" ? "light" : "dark")
                      .catch(() => {});
                    setUserMenuOpen(false);
                  }}
                >
                  <span>Switch to {appearanceMode === "dark" ? "Light" : "Dark"} Mode</span>
                  <small>Shared appearance</small>
                </button>
                <a href={getAccountDashboardHref()} role="menuitem">
                  <span>Account Dashboard</span>
                  <small>Kachhapa account &amp; campaigns</small>
                </a>
              </div>
            ) : null}
          </div>
        </div>
      </header>}

      <main className={`app-content ${showingActivePlaymat ? "playmat-active-content" : ""}`}>
        {renderPage()}
      </main>
      {matchSetup ? (
        <MatchSetupModal
          mode={matchSetup.mode}
          decks={playDecks}
          initialDeckId={matchSetup.initialDeckId}
          initialRevision={matchSetup.initialRevision}
          busy={playLoading}
          onClose={() => setMatchSetup(null)}
          onLaunch={launchConfiguredMatch}
        />
      ) : null}
    </div>
  );
}

export default App;
