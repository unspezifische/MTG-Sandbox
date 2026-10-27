import React, { useEffect, useState } from "react";
import { apiRequest } from "./preconApi";

function TotalsTable({ rows, label }) {
  return <div className="statistics-table-scroll" role="region" aria-label={label} tabIndex="0"><table className="deck-table"><thead><tr><th>Configuration</th><th>Games</th><th>Wins</th><th>Losses</th><th>Draws</th><th>Win rate</th><th>Average turns</th></tr></thead>
    <tbody>{rows.map(([name, s]) => <tr key={name}><th scope="row">{name}</th><td>{s.gamesPlayed}</td><td>{s.wins}</td><td>{s.losses}</td><td>{s.draws}</td><td>{s.winRate == null ? "—" : `${s.winRate}%`}</td><td>{s.averageTurns ?? "—"}</td></tr>)}</tbody></table></div>;
}

export default function DeckStatistics({ deck }) {
  const [mode, setMode] = useState("competitive");
  const [revision, setRevision] = useState("all");
  const [selected, setSelected] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    const params = new URLSearchParams({ mode, revision });
    apiRequest(`/decks/${deck.id}/stats?${params}`, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setStatistics(data); })
      .catch((e) => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [deck.id, deck.currentRevisionId, mode, revision, retry]);
  return <section className="page-card deck-statistics" aria-label="Deck performance" aria-busy={loading}>
    <h2>Deck statistics</h2><p>Results from recorded games. Win rate excludes draws; unfinished and invalidated games are excluded.</p>
    <div className="statistics-controls">
      <label>Statistics mode<select value={mode} onChange={(e) => setMode(e.target.value)}>{["competitive", "pvai", "goldfish", "simulation", "all", "pvp", "multiplayer", "one-v-one", "two-headed-giant", "pv-ai"].map((m) => <option value={m} key={m}>{m === "pvai" ? "PvAI" : m}</option>)}</select></label>
      <label>Revision scope<select value={["all", "stock", "current"].includes(revision) ? revision : "selected"} onChange={(e) => { if (e.target.value !== "selected") setRevision(e.target.value); }}><option value="all">All revisions</option><option value="stock">Original stock</option><option value="current">Current version</option>{!['all', 'stock', 'current'].includes(revision) && <option value="selected">Selected revisions</option>}</select></label>
    </div>
    {loading && <p role="status">Loading deck statistics…</p>}
    {error && <div role="alert" className="error-box">{error}<button onClick={() => setRetry(retry + 1)}>Retry statistics</button></div>}
    {!loading && !error && statistics && <>
      {!statistics.stats.gamesPlayed && <p>No finalized games qualify for this selection.</p>}
      <TotalsTable label="Selected statistics" rows={[["Selected scope", statistics.stats]]} />
      <TotalsTable label="Configuration totals" rows={[["All revisions", statistics.scopes.all], ["Original stock", statistics.scopes.stock], ["Current version", statistics.scopes.current]]} />
      <h3>Compare revisions</h3>
      <p>Unknown historical configurations remain separate and cannot be assigned to a revision.</p>
      <fieldset className="revision-options"><legend>Revisions to compare</legend>{statistics.revisions.map((r) => <label key={r.revisionId ?? "unknown"}>
        {r.configurationKnown && <input type="checkbox" checked={selected.includes(r.revisionId)} onChange={(e) => setSelected(e.target.checked ? [...selected, r.revisionId] : selected.filter((id) => id !== r.revisionId))} />}
        {r.configurationKnown ? `Revision #${r.revisionId} · ${r.revisionType}` : "Unknown historical configuration"}
      </label>)}<button disabled={!selected.length} onClick={() => setRevision(selected.join(","))}>Compare selected revisions</button></fieldset>
      <TotalsTable label="Revision comparison" rows={statistics.revisions.filter((r) => !selected.length || selected.includes(r.revisionId) || !r.configurationKnown).map((r) => [r.configurationKnown ? `Revision #${r.revisionId} · ${r.revisionType}` : "Unknown historical configuration", r])} />
    </>}
  </section>;
}
