import React, { useEffect, useRef, useState } from "react";
import { apiRequest } from "./preconApi";

const EMPTY = { q: "", format: "", set: "", year: "", commander: "" };
const LIMIT = 50;

export default function PreconsPage({ onOpenDeck, onSaved, onPlay }) {
  const [filters, setFilters] = useState(EMPTY);
  const [applied, setApplied] = useState(EMPTY);
  const [offset, setOffset] = useState(0);
  const [nextOffset, setNextOffset] = useState(0);
  const [catalog, setCatalog] = useState({ precons: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState("");
  const [busy, setBusy] = useState(null);
  const [mode, setMode] = useState("goldfish");
  const detailRef = useRef(null);
  const loadMoreRef = useRef(null);
  useEffect(() => {
    if (selectedId) {
      detailRef.current?.focus();
      detailRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
    }
  }, [selectedId]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    const params = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) });
    Object.entries(applied).forEach(([key, value]) => { if (value.trim()) params.set(key, value.trim()); });
    apiRequest(`/precons?${params}`, { signal: controller.signal })
      .then((value) => {
        if (controller.signal.aborted) return;
        setNextOffset(Number(value.offset ?? offset) + Number(value.limit ?? value.precons.length));
        setCatalog((current) => {
          if (offset === 0) return value;
          const byId = new Map(current.precons.map((precon) => [precon.id, precon]));
          value.precons.forEach((precon) => byId.set(precon.id, precon));
          return { ...value, precons: [...byId.values()] };
        });
      })
      .catch((e) => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [applied, offset, retry]);

  const hasMore = nextOffset < catalog.total;
  useEffect(() => {
    const target = loadMoreRef.current;
    if (!target || loading || error || !hasMore || typeof IntersectionObserver === "undefined") return undefined;
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) setOffset(nextOffset);
    }, { rootMargin: "600px 0px" });
    observer.observe(target);
    return () => observer.disconnect();
  }, [error, hasMore, loading, nextOffset]);

  useEffect(() => {
    if (!selectedId) return undefined;
    const controller = new AbortController();
    setDetail(null); setDetailError("");
    apiRequest(`/precons/${selectedId}`, { signal: controller.signal })
      .then((value) => { if (!controller.signal.aborted) setDetail(value); })
      .catch((e) => { if (!controller.signal.aborted) setDetailError(e.message); });
    return () => controller.abort();
  }, [selectedId, retry]);

  async function act(precon, action) {
    setBusy({ id: precon.id, action }); setError("");
    try {
      const payload = await apiRequest(`/precons/${precon.id}/${action}`, { method: "POST" });
      if (action === "save") {
        await onSaved?.(payload);
        onOpenDeck?.(payload.id);
      } else {
        await onPlay?.(payload, mode);
      }
    } catch (e) { setError(e.message); }
    finally { setBusy(null); }
  }

  function actions(precon) {
    const unavailable = !precon.gameplayAvailable;
    const playBusy = busy?.id === precon.id && busy.action === "play";
    const saveBusy = busy?.id === precon.id && busy.action === "save";
    const unavailableTitle = unavailable ? "Unavailable until this deck's import issues are resolved." : undefined;
    return <div className="precon-actions">
      <button type="button" className={`button-primary ${playBusy ? "is-busy" : ""}`} title={unavailableTitle} disabled={unavailable || busy !== null || !onPlay} onClick={() => act(precon, "play")}>{playBusy ? "Starting…" : "Play Original"}</button>
      <button type="button" className={`button-secondary ${saveBusy ? "is-busy" : ""}`} title={unavailableTitle} disabled={unavailable || busy !== null} onClick={() => act(precon, "save")}>{saveBusy ? "Adding…" : "Add to Your Decks"}</button>
    </div>;
  }

  return <div className="page-shell precons-page">
    <section className="page-card">
      <div className="eyebrow">Official deck catalog</div><h1>Browse precons</h1>
      <p>Inspect an official list, play the original without saving, or add it to your decks.</p>
      <form role="search" className="precon-filters" onSubmit={(e) => { e.preventDefault(); setApplied({ ...filters }); setOffset(0); setNextOffset(0); setCatalog({ precons: [], total: 0 }); setSelectedId(null); }}>
        {[["q", "Search preconstructed decks"], ["set", "Set code"], ["year", "Release year"], ["commander", "Commander"]].map(([key, label]) =>
          <label key={key}>{label}<input value={filters[key]} type={key === "year" ? "number" : "text"} min={key === "year" ? 1 : undefined} max={key === "year" ? 9998 : undefined} onChange={(e) => setFilters({ ...filters, [key]: e.target.value })} /></label>)}
        <label>Format<select value={filters.format} onChange={(e) => setFilters({ ...filters, format: e.target.value })}>
          <option value="">All formats</option>{["commander", "brawl", "standard", "modern", "pioneer", "legacy", "vintage", "pauper"].map((f) => <option key={f}>{f}</option>)}
        </select></label>
        <button type="submit">Search</button>
        <button type="button" onClick={() => { setFilters(EMPTY); setApplied({ ...EMPTY }); setOffset(0); setNextOffset(0); setCatalog({ precons: [], total: 0 }); setSelectedId(null); }}>Clear filters</button>
      </form>
      <label className="precon-mode">Play mode<select value={mode} onChange={(e) => setMode(e.target.value)}><option value="goldfish">Goldfish</option><option value="simulation">Simulation</option><option value="pvp">PvP lobby</option></select></label>
    </section>
    <section className="page-card" aria-busy={loading}>
      <h2>Preconstructed decks</h2><p>{catalog.total} {catalog.total === 1 ? "deck" : "decks"}</p>
      {loading && !catalog.precons.length && <p role="status">Loading the precon catalog…</p>}
      {error && <div role="alert" className="error-box">{error}<button onClick={() => setRetry(retry + 1)}>Retry</button></div>}
      {!loading && !error && !catalog.precons.length && <p>No precons match these filters. Clear filters to browse all decks. An empty catalog may need synchronization by an administrator.</p>}
      {!!catalog.precons.length && <div className="precon-grid">{catalog.precons.map((p) => <article className="precon-card" key={p.id}>
        <h3>{p.name}</h3><p>{p.setCode} · {p.format || p.deckType} · {p.releaseDate || "Release date unavailable"}</p>
        <p>{p.gameplayAvailable ? "Ready to play" : "Incomplete decklist — view details for import issues."}</p>
        <button className="button-secondary" onClick={() => setSelectedId(p.id)}>View Deck</button>{actions(p)}
      </article>)}</div>}
      <div ref={loadMoreRef} className="catalog-load-more" aria-live="polite">
        {loading && catalog.precons.length > 0 && <span role="status">Loading more decks…</span>}
        {!loading && !error && hasMore && <button type="button" onClick={() => setOffset(nextOffset)}>Load more decks</button>}
        {!loading && !error && catalog.precons.length > 0 && !hasMore && <span>All {catalog.total} decks loaded.</span>}
      </div>
    </section>
    {selectedId && <section ref={detailRef} tabIndex={-1} className="page-card precon-detail" aria-label="Official deck details" aria-busy={!detail && !detailError}>
      <button onClick={() => { setSelectedId(null); setDetail(null); }}>Close details</button>
      {detailError && <div role="alert" className="error-box">{detailError}<button onClick={() => setRetry(retry + 1)}>Retry details</button></div>}
      {!detail && !detailError && <p role="status">Loading official decklist…</p>}
      {detail && <><h2>{detail.name}</h2><p>{detail.setCode} · {detail.deckType} · {detail.releaseDate || "Release date unavailable"}</p>
        <p>Commanders: {detail.commanders.map((c) => c.name).join(" + ") || "None"}</p>
        <p>Playable cards: {detail.playableCardCount ?? "Unknown"} · Catalog version {detail.templateVersionId} · {detail.importStatus}</p>
        {detail.issues?.length > 0 && <div role="status" className="error-box"><strong>Import issues</strong><ul>{detail.issues.map((issue, i) => <li key={i}>{issue}</li>)}</ul></div>}
        {!detail.gameplayAvailable && <p>Saving and playing are disabled until the catalog import is complete.</p>}
        <label className="precon-mode">Detail play mode<select value={mode} onChange={(e) => setMode(e.target.value)}><option value="goldfish">Goldfish</option><option value="simulation">Simulation</option><option value="pvp">PvP lobby</option></select></label>{actions(detail)}
        <div className="precon-boards">{Object.entries(detail.boards).map(([board, cards]) => <section key={board}><h3>{board} ({detail.boardCounts[board] || 0})</h3><ul>{cards.map((c) => <li key={c.id}>{c.quantity} × {c.card?.name || c.name}{!c.card && " (unresolved)"}{c.isCommander && " · Commander"}</li>)}</ul></section>)}</div>
      </>}
    </section>}
  </div>;
}
