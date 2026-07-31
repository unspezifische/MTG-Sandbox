import React, { useEffect, useMemo, useState } from "react";

const isMtgSubpath = window.location.pathname.startsWith("/mtg");
const API_BASE = isMtgSubpath ? "/mtg/api" : "/api";

function formatDate(value) {
  if (!value) return "In progress";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function HistoryPage({ onOpenDeck }) {
  const [games, setGames] = useState([]);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/games`)
      .then((response) => {
        if (!response.ok) throw new Error(`Could not load history (${response.status}).`);
        return response.json();
      })
      .then((payload) => setGames(Array.isArray(payload) ? payload : []))
      .catch((loadError) => setError(loadError.message));
  }, []);

  const visible = useMemo(
    () => games.filter((game) => filter === "all" || game.status === filter),
    [filter, games]
  );

  return (
    <div className="page-shell">
      <section className="page-card history-page">
        <div className="section-header">
          <div>
            <div className="eyebrow">Match archive</div>
            <h1>Game History</h1>
            <p>Completed matches, active playtests, decks, results, and AI strategies.</p>
          </div>
          <select value={filter} onChange={(event) => setFilter(event.target.value)}>
            <option value="all">All games</option>
            <option value="completed">Completed</option>
            <option value="active">Active</option>
            <option value="pending">Pending lobbies</option>
          </select>
        </div>
        {error ? <div className="error-box">{error}</div> : null}
        {!error && !visible.length ? <div className="deck-empty-state">No games match this filter.</div> : null}
        {visible.length ? (
          <div className="deck-table-wrap">
            <table className="deck-table history-table">
              <thead>
                <tr><th>Date</th><th>Mode</th><th>Decks</th><th>Result</th><th>Status</th></tr>
              </thead>
              <tbody>
                {visible.map((game) => {
                  const winner = game.players?.find((player) => player.id === game.winnerGamePlayerId);
                  return (
                    <tr key={game.id}>
                      <td>{formatDate(game.endedAt || game.startedAt || game.createdAt)}</td>
                      <td><strong>{game.gameMode}</strong><small>{game.ruleset}</small></td>
                      <td>
                        {(game.players || []).filter((player) => player.deckId).map((player) => (
                          <button type="button" className="history-deck-link" key={player.id} onClick={() => onOpenDeck(player.deckId)}>
                            P{player.seatNumber}: {player.deckName}
                            {player.aiProfile ? ` · ${player.aiProfile} AI` : ""}
                          </button>
                        ))}
                      </td>
                      <td>{winner ? `Player ${winner.seatNumber} · ${winner.deckName}` : "—"}</td>
                      <td><span className={`history-status ${game.status}`}>{game.status}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  );
}
