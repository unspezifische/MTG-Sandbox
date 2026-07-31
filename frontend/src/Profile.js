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
  const losses = Math.max(0, Number(deck.gamesPlayed || 0) - Number(deck.wins || 0));
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
  const human = game.players?.find((player) => player.playerType === "human" && player.deckId)
    || game.players?.find((player) => player.deckId);
  const winner = game.players?.find((player) => player.id === game.winnerGamePlayerId);
  return (
    <div className="list-row">
      <div className="list-row-main">
        <div className="list-row-title">{human?.deckName || game.lobbyName || `Game #${game.id}`}</div>
        <div className="list-row-subtitle">
          {game.gameMode} • {(game.players || []).filter((player) => player.deckId).length} player game
        </div>
      </div>

      <div className="list-row-meta">
        <div>{winner ? (winner.id === human?.id ? "Win" : "Loss") : game.status}</div>
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
  const [deckError, setDeckError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(`${API_BASE}/decks`),
      fetch(`${API_BASE}/decks?recent=true`),
      fetch(`${API_BASE}/games`),
    ])
      .then(async ([allResponse, recentResponse, gamesResponse]) => {
        if (!allResponse.ok || !recentResponse.ok || !gamesResponse.ok) {
          throw new Error("Could not load profile activity.");
        }
        return Promise.all([allResponse.json(), recentResponse.json(), gamesResponse.json()]);
      })
      .then(([allPayload, recentPayload, gamesPayload]) => {
        if (!cancelled) {
          setDecks(Array.isArray(allPayload) ? allPayload : []);
          setRecentDecks(Array.isArray(recentPayload) ? recentPayload.slice(0, 3) : []);
          setRecentGames(
            Array.isArray(gamesPayload)
              ? gamesPayload.filter((game) => game.status === "completed").slice(0, 3)
              : []
          );
        }
      })
      .catch((error) => {
        if (!cancelled) setDeckError(error.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const deckStats = useMemo(() => {
    const games = decks.reduce((total, deck) => total + Number(deck.gamesPlayed || 0), 0);
    const wins = decks.reduce((total, deck) => total + Number(deck.wins || 0), 0);
    const best = [...decks].sort((a, b) => Number(b.wins || 0) - Number(a.wins || 0))[0];
    return {
      games,
      wins,
      best,
      winRate: games ? Math.round((wins / games) * 100) : 0,
    };
  }, [decks]);

  return (
    <div className="page-shell">
      <section className="hero-card">
        <div>
          <h1>Welcome back</h1>
          <p>
            Jump back into deck refinement, launch a game mode, or review recent
            performance.
          </p>
        </div>

        <div className="hero-actions">
          <button type="button" onClick={onCreateDeck}>
            Create New Deck
          </button>
          <button type="button" onClick={() => onNavigate("decks")}>
            Open Deck Builder
          </button>
          <button type="button" onClick={() => onStartMatch()}>
            Start a Match
          </button>
        </div>
      </section>

      <section className="stats-grid">
        <StatCard label="Decks" value={decks.length} subtext="Saved deck lists" />
        <StatCard label="Games" value={deckStats.games} subtext="Across all decks" />
        <StatCard label="Win Rate" value={`${deckStats.winRate}%`} subtext="Completed games" />
        <StatCard label="Best Deck" value={deckStats.best?.name || "—"} subtext="Most recorded wins" />
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
