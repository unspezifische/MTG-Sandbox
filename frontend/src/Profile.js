import { apiErrorMessage } from "./preconApi";
import React, { useEffect, useMemo, useState } from "react";

const isMtgSubpath = window.location.pathname.startsWith("/mtg");
const API_BASE = isMtgSubpath ? "/mtg/api" : "/api";

function StatCard({ label, value, subtext }) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {subtext ? <div className="stat-subtext">{subtext}</div> : null}
    </div>
  );
}

function relativeTimestamp(value) {
  if (!value) return "Not used yet";
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return "Recently";
  const seconds = Math.round((timestamp - Date.now()) / 1000);
  const ranges = [
    ["year", 31536000],
    ["month", 2592000],
    ["week", 604800],
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  for (const [unit, size] of ranges) {
    if (Math.abs(seconds) >= size) return formatter.format(Math.round(seconds / size), unit);
  }
  return "just now";
}

function DeckRow({ deck, onOpenDeck, onGoldfish }) {
  const losses = Number(deck.losses || 0);
  return (
    <div className="list-row">
      <div className="list-row-main">
        <div className="list-row-title">{deck.name}</div>
        <div className="list-row-subtitle">
          {deck.format || "none"} • {deck.commanderNames?.join(" + ") || "No commander"}
        </div>
      </div>

      <div className="list-row-meta">
        <div>{Number(deck.wins || 0)}-{losses}</div>
        <div className="muted-text">Used {relativeTimestamp(deck.lastUsedAt || deck.updatedAt)}</div>
      </div>

      <div className="list-row-actions">
        <button type="button" onClick={() => onOpenDeck(deck.id)}>
          Open
        </button>
        <button type="button" onClick={() => onGoldfish(deck.id)}>
          Goldfish
        </button>
      </div>
    </div>
  );
}

function GameRow({ game, onNavigate }) {
  const mine = game.myParticipations?.[0];
  const human = game.players?.find((player) => player.id === mine?.gamePlayerId)
    || game.players?.find((player) => player.playerType === "human" && player.deckId)
    || game.players?.find((player) => player.deckId);
  const outcome = game.isInvalidated ? "Invalidated"
    : game.myParticipations?.length > 1 ? "Multiple seats" : (mine?.result || game.status);
  return (
    <div className="list-row">
      <div className="list-row-main">
        <div className="list-row-title">{human?.deckName || game.lobbyName || `Game #${game.id}`}</div>
        <div className="list-row-subtitle">
          {game.gameMode} • {(game.players || []).filter((player) => player.deckId).length} player game
        </div>
      </div>

      <div className="list-row-meta">
        <div>{outcome}</div>
        <div className="muted-text">{relativeTimestamp(game.endedAt || game.startedAt || game.createdAt)}</div>
      </div>

      <div className="list-row-actions">
        <button type="button" onClick={() => onNavigate("history")}>
          View
        </button>
      </div>
    </div>
  );
}

function ModeCard({ title, description, onClick, buttonLabel }) {
  return (
    <div className="mode-card">
      <h3>{title}</h3>
      <p>{description}</p>
      <button type="button" onClick={onClick}>
        {buttonLabel}
      </button>
    </div>
  );
}

function Profile({
  onNavigate,
  onOpenDeck,
  onCreateDeck,
  onStartMatch,
  onGoldfish,
  onSimulation,
  onPvP,
}) {
  const [decks, setDecks] = useState([]);
  const [recentDecks, setRecentDecks] = useState([]);
  const [recentGames, setRecentGames] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [deckError, setDeckError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(`${API_BASE}/decks`),
      fetch(`${API_BASE}/decks?recent=true`),
      fetch(`${API_BASE}/profile/history?status=completed&limit=3`),
      fetch(`${API_BASE}/profile/stats`),
    ])
      .then(async ([allResponse, recentResponse, gamesResponse, statsResponse]) => {
        if (!allResponse.ok || !recentResponse.ok || !gamesResponse.ok || !statsResponse.ok) {
          const failed = [allResponse, recentResponse, gamesResponse, statsResponse].find((response) => !response.ok);
          throw new Error(apiErrorMessage(failed.status, "Could not load profile activity."));
        }
        return Promise.all([allResponse.json(), recentResponse.json(), gamesResponse.json(), statsResponse.json()]);
      })
      .then(([allPayload, recentPayload, gamesPayload, statsPayload]) => {
        if (!cancelled) {
          setDecks(Array.isArray(allPayload) ? allPayload : []);
          setRecentDecks(Array.isArray(recentPayload) ? recentPayload.slice(0, 3) : []);
          setRecentGames(Array.isArray(gamesPayload.games) ? gamesPayload.games : []);
          setStatistics(statsPayload);
        }
      })
      .catch((error) => {
        if (!cancelled) setDeckError(error.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const bestDeck = useMemo(
    () => [...decks].sort((a, b) => Number(b.wins || 0) - Number(a.wins || 0))[0],
    [decks]
  );
  const library = statistics?.library;
  const winRateLabel = library?.winRate == null ? "—" : `${library.winRate}%`;


  return (
    <div className="page-shell">
      <section className="hero-card">
        <div>
          <div className="eyebrow">Pod Bay</div>
          <h1>Welcome back</h1>
          <p>
            Your command center for career stats and game history. Jump back into
            deck refinement, launch a game mode, or review recent performance.
          </p>
        </div>

        <div className="hero-actions">
          <button type="button" onClick={onCreateDeck}>
            Create New Deck
          </button>
          <button type="button" onClick={() => onNavigate("precons")}>
            Browse Precons
          </button>
          <button type="button" onClick={() => onStartMatch()}>
            Start a Match
          </button>
        </div>
      </section>

      <section className="stats-grid">
        <StatCard label="Decks" value={decks.length} subtext="Saved deck lists" />
        <StatCard label="Games" value={library?.gamesPlayed ?? "—"} subtext="Competitive games with saved decks" />
        <StatCard label="Library Win Rate" value={winRateLabel} subtext="Completed PvP; draws excluded" />
        <StatCard label="Best Deck" value={bestDeck?.name || "—"} subtext="Most recorded wins" />
      </section>

      <section className="content-grid">
        <div className="page-card">
          <div className="section-header">
            <h2>Recently Used Decks</h2>
            <button type="button" onClick={() => onNavigate("decks")}>
              View All
            </button>
          </div>

          <div className="list-stack">
            {recentDecks.map((deck) => (
              <DeckRow
                key={deck.id}
                deck={deck}
                onOpenDeck={onOpenDeck}
                onGoldfish={onGoldfish}
              />
            ))}
            {!recentDecks.length && !deckError ? (
              <div className="muted-text">No decks have been used yet.</div>
            ) : null}
            {deckError ? <div className="error-box">{deckError}</div> : null}
          </div>
        </div>

        <div className="page-card">
          <div className="section-header">
            <h2>Game Modes</h2>
          </div>

          <div className="mode-grid">
            <ModeCard
              title="Goldfish"
              description="Test lines, opening hands, and sequencing without an opponent."
              buttonLabel="Launch"
              onClick={() => onGoldfish()}
            />
            <ModeCard
              title="Simulation"
              description="Run automated tests, batch comparisons, and alternate lines."
              buttonLabel="Open"
              onClick={() => onSimulation()}
            />
            <ModeCard
              title="PvP"
              description="Start or join a multiplayer match."
              buttonLabel="Enter"
              onClick={onPvP}
            />
          </div>
        </div>
      </section>

      <section className="page-card">
        <div className="section-header">
          <h2>Recent Games</h2>
          <button type="button" onClick={() => onNavigate("history")}>
            Full History
          </button>
        </div>

        <div className="list-stack">
          {recentGames.map((game) => (
            <GameRow key={game.id} game={game} onNavigate={onNavigate} />
          ))}
        </div>
      </section>
    </div>
  );
}

export default Profile;
