import React, { useEffect, useState } from "react";
import { apiRequest } from "./preconApi";

const LIMIT = 25;
function formatDate(value) {
  const date = new Date(value);
  return !value || Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleString();
}

export default function HistoryPage({ onOpenDeck }) {
  const [history, setHistory] = useState({ games: [], total: 0 });
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    const params = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) });
    if (status) params.set("status", status);
    apiRequest(`/profile/history?${params}`, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setHistory(data); })
      .catch((e) => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [status, offset, retry]);
  return <div className="page-shell"><section className="page-card history-page" aria-busy={loading}>
    <h1>Game History</h1><p>Your results, including unlisted and archived decks.</p>
    <label>Game status<select value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0); }}><option value="">All games</option>{["completed", "active", "pending", "aborted", "invalidated"].map((s) => <option key={s}>{s}</option>)}</select></label>
    {loading && <p role="status">Loading personal history…</p>}
    {error && <div className="error-box" role="alert">{error}<button onClick={() => setRetry(retry + 1)}>Retry</button></div>}
    {!loading && !error && !history.games.length && <p>No personal games match this filter. Play a deck to begin recording your history; saving it is optional.</p>}
    {!loading && !error && <div className="personal-history-grid">{history.games.map((game) => <article className="history-record" key={game.id}>
      <h2>Game #{game.id} · {game.gameMode}</h2><p>{formatDate(game.endedAt || game.startedAt || game.createdAt)} · {game.status}</p>
      {game.isInvalidated && <p className="error-box">Invalidated — excluded from statistics. {game.invalidationReason}</p>}
      {game.myParticipations.length > 1 && <p className="error-box">Multiple human seats for your account: result attribution is ambiguous and excluded from statistics.</p>}
      {game.myParticipations.map((p) => {
        const player = game.players.find((row) => row.id === p.gamePlayerId);
        return <div className="history-participation" key={p.gamePlayerId}>
          <p>{p.deckId ? <button className="history-deck-link" onClick={() => onOpenDeck?.(p.deckId)}>{p.deckName || player?.deckName || `Deck #${p.deckId}`}</button> : "Unknown deck"}</p>
          <p>Participant result: {p.result || "Not finalized"}</p>
          <p>{p.configurationKnown && ["stock", "custom"].includes(p.revisionType) ? `${p.revisionType === "stock" ? "Original stock" : "Custom"} · Revision #${p.revisionId}` : "Unknown historical configuration"}</p>
          <p>Library: {p.libraryStatus || "Unknown"}</p>
        </div>;
      })}
    </article>)}</div>}
    <nav className="catalog-pagination" aria-label="History pages"><button disabled={loading || offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>Previous</button><span>Page {Math.floor(offset / LIMIT) + 1} · {history.total} games</span><button disabled={loading || offset + LIMIT >= history.total} onClick={() => setOffset(offset + LIMIT)}>Next</button></nav>
  </section></div>;
}
