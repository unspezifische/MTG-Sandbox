import React, { useEffect, useMemo, useState } from "react";
import { scryfallImageUrl } from "./cardImages";

const isMtgSubpath = window.location.pathname.startsWith("/mtg");
const API_BASE = isMtgSubpath ? "/mtg/api" : "/api";

const FORMATS = [
  ["commander", "Commander / EDH"],
  ["standard", "Standard"],
  ["modern", "Modern"],
  ["pioneer", "Pioneer"],
  ["legacy", "Legacy"],
  ["vintage", "Vintage"],
  ["pauper", "Pauper"],
  ["brawl", "Brawl"],
  ["standard-brawl", "Standard Brawl"],
  ["duel-commander", "Duel Commander"],
  ["pauper-edh", "Pauper EDH"],
  ["oathbreaker", "Oathbreaker"],
  ["historic", "Historic"],
  ["timeless", "Timeless"],
  ["old-school", "Old School"],
  ["premodern", "Premodern"],
  ["none", "No format"],
];

const COMMANDER_FORMATS = new Set([
  "commander",
  "brawl",
  "standard-brawl",
  "duel-commander",
  "pauper-edh",
  "oathbreaker",
]);

const COLOR_LABELS = {
  W: "White",
  U: "Blue",
  B: "Black",
  R: "Red",
  G: "Green",
};

function isCommanderEligible(card) {
  const typeLine = card?.typeLine || "";
  const oracleText = card?.oracleText || "";
  return (
    typeLine.includes("Legendary Creature") ||
    typeLine.includes("Legendary Background") ||
    oracleText.toLowerCase().includes("can be your commander")
  );
}

function uniqueCommanderCards(cards) {
  const seen = new Set();
  return cards.filter((card) => {
    const key = (card?.name || "").trim().toLowerCase();
    if (!key || seen.has(key) || !isCommanderEligible(card)) return false;
    seen.add(key);
    return true;
  });
}

function isCompatiblePartner(primary, candidate) {
  if (!primary || !candidate || primary.id === candidate.id) return false;
  if (primary.partnerMode === "named") {
    return String(candidate.name || "").toLowerCase() === String(primary.partnerName || "").toLowerCase();
  }
  if (candidate.partnerMode === "named") {
    return String(primary.name || "").toLowerCase() === String(candidate.partnerName || "").toLowerCase();
  }
  if (primary.partnerMode === "partner") return candidate.partnerMode === "partner";
  if (primary.partnerMode === "friends_forever") return candidate.partnerMode === "friends_forever";
  if (primary.partnerMode === "background") {
    return (candidate.typeLine || "").toLowerCase().includes("background");
  }
  if (primary.partnerMode === "doctors_companion") {
    return (candidate.typeLine || "").toLowerCase().includes("doctor");
  }
  return false;
}

function ColorIdentity({ colors }) {
  if (!Array.isArray(colors) || colors.length === 0) {
    return <span className="deck-colorless">Colorless</span>;
  }

  return (
    <span className="deck-color-row" aria-label={colors.map((color) => COLOR_LABELS[color]).join(", ")}>
      {colors.map((color) => (
        <span key={color} className={`mana-dot mana-${color.toLowerCase()}`} title={COLOR_LABELS[color]}>
          {color}
        </span>
      ))}
    </span>
  );
}

function CreateDeckModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [format, setFormat] = useState("commander");
  const [commanderQuery, setCommanderQuery] = useState("");
  const [commanderResults, setCommanderResults] = useState([]);
  const [commander, setCommander] = useState(null);
  const [partnerQuery, setPartnerQuery] = useState("");
  const [partnerResults, setPartnerResults] = useState([]);
  const [partner, setPartner] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isPublic, setIsPublic] = useState(false);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const requiresCommander = COMMANDER_FORMATS.has(format);

  useEffect(() => {
    if (!requiresCommander) {
      setCommander(null);
      setCommanderQuery("");
      setCommanderResults([]);
      setPartner(null);
      setPartnerQuery("");
      setPartnerResults([]);
    }
  }, [requiresCommander]);

  useEffect(() => {
    if (!requiresCommander || commander || commanderQuery.trim().length < 2) {
      setCommanderResults([]);
      return undefined;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(
          `${API_BASE}/cards?q=${encodeURIComponent(commanderQuery.trim())}&limit=12&commanderOnly=true`,
          { signal: controller.signal }
        );
        if (!response.ok) throw new Error("Commander search failed.");
        const payload = await response.json();
        setCommanderResults(Array.isArray(payload) ? uniqueCommanderCards(payload).slice(0, 8) : []);
      } catch (searchError) {
        if (searchError.name !== "AbortError") setError(searchError.message);
      }
    }, 180);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [commanderQuery, commander, requiresCommander]);

  useEffect(() => {
    setPartner(null);
    setPartnerResults([]);
    setPartnerQuery(commander?.partnerMode === "named" ? commander.partnerName || "" : "");
  }, [commander]);

  useEffect(() => {
    if (!commander?.partnerMode || partner || partnerQuery.trim().length < 2) {
      setPartnerResults([]);
      return undefined;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(
          `${API_BASE}/cards?q=${encodeURIComponent(partnerQuery.trim())}&limit=20&commanderOnly=true`,
          { signal: controller.signal }
        );
        if (!response.ok) throw new Error("Partner search failed.");
        const payload = await response.json();
        const options = Array.isArray(payload) ? uniqueCommanderCards(payload) : [];
        setPartnerResults(options.filter((card) => isCompatiblePartner(commander, card)).slice(0, 8));
      } catch (searchError) {
        if (searchError.name !== "AbortError") setError(searchError.message);
      }
    }, commander.partnerMode === "named" ? 0 : 180);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [commander, partner, partnerQuery]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!name.trim()) {
      setError("Give your deck a name.");
      return;
    }
    if (requiresCommander && !commander) {
      setError("Choose a commander for this format.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/decks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          format,
          commanderCardIds: [commander?.id, partner?.id].filter(Boolean),
          commanderCount: requiresCommander ? (partner ? 2 : 1) : 0,
          colorIdentity: Array.from(
            new Set([...(commander?.colorIdentity || []), ...(partner?.colorIdentity || [])])
          ),
          isPublic,
          notes: notes.trim() || null,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.error || `Deck creation failed (${response.status}).`);
      onCreated(payload);
    } catch (submitError) {
      setError(submitError.message || "Deck creation failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="deck-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-deck-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="deck-modal-header">
          <div>
            <div className="eyebrow">Deck library</div>
            <h2 id="create-deck-title">Create a new deck</h2>
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="deck-modal-body">
            <label className="field-label" htmlFor="deck-name">Deck name</label>
            <input
              id="deck-name"
              className="modal-input"
              autoFocus
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. Pirate Tribal, Mono-Red Aggro, or My First EDH Deck"
            />

            <div className={`modal-field-grid ${requiresCommander ? "" : "single"}`}>
              <div>
                <label className="field-label" htmlFor="deck-format">Format</label>
                <select
                  id="deck-format"
                  className="modal-input"
                  value={format}
                  onChange={(event) => setFormat(event.target.value)}
                >
                  {FORMATS.map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>

              {requiresCommander && (
                <div className="commander-field">
                  <label className="field-label" htmlFor="commander-search">Commander</label>
                  {commander ? (
                    <button type="button" className="commander-selected" onClick={() => setCommander(null)}>
                      <span>{commander.name}</span>
                      <span>Change</span>
                    </button>
                  ) : (
                    <input
                      id="commander-search"
                      className="modal-input"
                      value={commanderQuery}
                      onChange={(event) => setCommanderQuery(event.target.value)}
                      placeholder="Search for a commander…"
                    />
                  )}
                  {commanderResults.length > 0 && (
                    <div className="commander-results">
                      {commanderResults.map((card) => (
                        <button
                          key={card.uuid}
                          type="button"
                          onClick={() => {
                            setCommander(card);
                            setCommanderQuery(card.name);
                            setCommanderResults([]);
                          }}
                        >
                          {scryfallImageUrl(card, "small") && (
                            <img src={scryfallImageUrl(card, "small")} alt="" loading="lazy" />
                          )}
                          <span>
                            <strong>{card.name}</strong>
                            <small>{card.typeLine}</small>
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {requiresCommander && commander?.partnerMode && (
              <div className="partner-picker">
                <div className="partner-picker-heading">
                  <div>
                    <span className="field-label">Partner commander</span>
                    <small>
                      {commander.partnerMode === "named"
                        ? `${commander.name} partners specifically with ${commander.partnerName}.`
                        : "This commander supports a paired commander. Only compatible choices are shown."}
                    </small>
                  </div>
                  <span className="optional-badge">Optional</span>
                </div>
                <div className="commander-field">
                  {partner ? (
                    <button type="button" className="commander-selected" onClick={() => setPartner(null)}>
                      <span>{partner.name}</span>
                      <span>Change</span>
                    </button>
                  ) : (
                    <input
                      className="modal-input"
                      value={partnerQuery}
                      onChange={(event) => setPartnerQuery(event.target.value)}
                      placeholder="Search compatible partners…"
                      aria-label="Partner commander"
                    />
                  )}
                  {partnerResults.length > 0 && (
                    <div className="commander-results partner-results">
                      {partnerResults.map((card) => (
                        <button
                          key={card.uuid}
                          type="button"
                          onClick={() => {
                            setPartner(card);
                            setPartnerQuery(card.name);
                            setPartnerResults([]);
                          }}
                        >
                          {scryfallImageUrl(card, "small") && (
                            <img src={scryfallImageUrl(card, "small")} alt="" loading="lazy" />
                          )}
                          <span><strong>{card.name}</strong><small>{card.typeLine}</small></span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            <button
              type="button"
              className="advanced-toggle"
              onClick={() => setShowAdvanced((value) => !value)}
              aria-expanded={showAdvanced}
            >
              <span>{showAdvanced ? "−" : "+"}</span> Advanced options
            </button>

            {showAdvanced && (
              <div className="advanced-panel">
                <div>
                  <span className="field-label">Visibility</span>
                  <div className="visibility-options">
                    <label><input type="radio" checked={!isPublic} onChange={() => setIsPublic(false)} /> Private</label>
                    <label><input type="radio" checked={isPublic} onChange={() => setIsPublic(true)} /> Public</label>
                  </div>
                </div>
                <div>
                  <label className="field-label" htmlFor="deck-notes">Description</label>
                  <textarea
                    id="deck-notes"
                    className="modal-input"
                    rows="3"
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    placeholder="What is this deck trying to do?"
                  />
                </div>
              </div>
            )}

            {error && <div className="modal-error">{error}</div>}
          </div>

          <div className="deck-modal-footer">
            <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="button-primary" disabled={submitting}>
              {submitting ? "Creating…" : "Create deck"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function CommanderEditorModal({ deck, onClose, onSaved }) {
  const [selection, setSelection] = useState(
    () => (deck.cards || []).filter((entry) => entry.isCommander).map((entry) => entry.card).filter(Boolean)
  );
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const primary = selection[0] || null;
  const partnerExpected = selection.length === 1 && Boolean(primary?.partnerMode);
  const canSearch = selection.length === 0 || (selection.length === 1 && partnerExpected);

  useEffect(() => {
    if (!canSearch || query.trim().length < 2) {
      setResults([]);
      return undefined;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setSearching(true);
      try {
        const response = await fetch(
          `${API_BASE}/cards?q=${encodeURIComponent(query.trim())}&limit=12&commanderOnly=true`,
          { signal: controller.signal }
        );
        const payload = await response.json();
        if (!response.ok) throw new Error(payload?.error || "Commander search failed.");
        const excluded = new Set(selection.map((card) => card.id));
        const candidates = uniqueCommanderCards(Array.isArray(payload) ? payload : [])
          .filter((card) => !excluded.has(card.id))
          .filter((card) => !primary || isCompatiblePartner(primary, card));
        setResults(candidates.slice(0, 10));
      } catch (searchError) {
        if (searchError.name !== "AbortError") setError(searchError.message);
      } finally {
        setSearching(false);
      }
    }, 220);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [canSearch, primary, query, selection]);

  async function save() {
    if (COMMANDER_FORMATS.has(deck.format) && selection.length === 0) {
      setError("Choose a commander before saving.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/decks/${deck.id}/commanders`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ commanderCardIds: selection.map((card) => card.id) }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.error || "Could not update commanders.");
      onSaved(payload);
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="deck-modal commander-editor-modal" role="dialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}>
        <div className="deck-modal-header">
          <div><div className="eyebrow">Deck setup</div><h2>Change commander</h2></div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <div className="deck-modal-body">
          <p className="commander-editor-intro">
            Swap the commander without rebuilding the deck. The former commander is removed; every other card remains unchanged.
          </p>
          {selection.length > 0 && (
            <div className="selected-commanders">
              {selection.map((card) => (
                <div className="selected-commander-row" key={card.id}>
                  {scryfallImageUrl(card, "small") ? <img src={scryfallImageUrl(card, "small")} alt="" /> : <span />}
                  <span><strong>{card.name}</strong><small>{card.typeLine}</small></span>
                  <button
                    type="button"
                    onClick={() => {
                      setSelection((cards) => cards.filter((selected) => selected.id !== card.id));
                      setQuery("");
                      setResults([]);
                    }}
                  >
                    Change
                  </button>
                </div>
              ))}
            </div>
          )}
          {canSearch ? (
            <div className="commander-field">
              <label className="field-label" htmlFor="library-commander-search">
                {partnerExpected ? "Paired commander" : "New commander"}
              </label>
              <input
                id="library-commander-search"
                className="modal-input"
                autoFocus={selection.length === 0}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={partnerExpected ? "Search compatible partners…" : "Search eligible commanders…"}
              />
              {searching ? <div className="commander-search-hint">Searching…</div> : null}
              {query.trim().length >= 2 && !searching && results.length === 0 ? (
                <div className="commander-search-hint">No compatible commanders found.</div>
              ) : null}
              {results.length > 0 && (
                <div className="settings-commander-results">
                  {results.map((card) => (
                    <button
                      type="button"
                      key={card.uuid || card.id}
                      onClick={() => {
                        setSelection((cards) => [...cards, card]);
                        setQuery("");
                        setResults([]);
                      }}
                    >
                      {scryfallImageUrl(card, "small") ? <img src={scryfallImageUrl(card, "small")} alt="" /> : <span />}
                      <span><strong>{card.name}</strong><small>{card.typeLine}</small></span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="missing-commander-callout">
              {primary?.name} does not support a second commander. Click Change to replace it.
            </div>
          )}
          {error ? <div className="modal-error">{error}</div> : null}
        </div>
        <div className="deck-modal-footer">
          <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
          <button type="button" className="button-primary" onClick={save} disabled={busy || selection.length === 0}>
            {busy ? "Saving…" : "Save commander"}
          </button>
        </div>
      </section>
    </div>
  );
}

function LibraryDeckSettingsModal({ deck, onClose, onSaved }) {
  const [name, setName] = useState(deck.name || "");
  const [notes, setNotes] = useState(deck.notes || "");
  const [format, setFormat] = useState(deck.format || "none");
  const [isPublic, setIsPublic] = useState(Boolean(deck.isPublic));
  const [folderName, setFolderName] = useState(deck.folderName || "");
  const [commanderBracket, setCommanderBracket] = useState(String(deck.commanderBracket || ""));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function save(event) {
    event.preventDefault();
    if (!name.trim()) {
      setError("Deck name is required.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/decks/${deck.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          notes: notes.trim() || null,
          format,
          isPublic,
          folderName: folderName.trim() || null,
          commanderBracket: commanderBracket || null,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.error || "Could not save deck settings.");
      onSaved(payload);
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="deck-modal deck-settings-modal" role="dialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}>
        <div className="deck-modal-header">
          <div><div className="eyebrow">Deck library</div><h2>Deck settings</h2></div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <form onSubmit={save}>
          <div className="deck-modal-body">
            <label className="field-label" htmlFor="library-deck-name">Name</label>
            <input id="library-deck-name" className="modal-input" value={name} onChange={(event) => setName(event.target.value)} />
            <label className="field-label" htmlFor="library-deck-description">Description</label>
            <textarea id="library-deck-description" className="modal-input" rows="3" maxLength="500" value={notes} onChange={(event) => setNotes(event.target.value)} />
            <div className="deck-settings-field-row">
              <div>
                <span className="field-label">Visibility</span>
                <div className="visibility-options">
                  <label><input type="radio" checked={isPublic} onChange={() => setIsPublic(true)} /> Visible</label>
                  <label><input type="radio" checked={!isPublic} onChange={() => setIsPublic(false)} /> Private</label>
                </div>
              </div>
              <div>
                <label className="field-label" htmlFor="library-deck-folder">Folder</label>
                <input id="library-deck-folder" className="modal-input" value={folderName} onChange={(event) => setFolderName(event.target.value)} placeholder="No folder" />
              </div>
            </div>
            <label className="field-label" htmlFor="library-deck-format">Format</label>
            <select id="library-deck-format" className="modal-input" value={format} onChange={(event) => setFormat(event.target.value)}>
              {FORMATS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <fieldset className="commander-bracket-fieldset">
              <legend className="field-label">Commander bracket</legend>
              {[
                ["", "Unsure / use estimate"],
                ["1", "Bracket 1 — Exhibition"],
                ["2", "Bracket 2 — Core"],
                ["3", "Bracket 3 — Upgraded"],
                ["4", "Bracket 4 — Optimized"],
                ["5", "Bracket 5 — cEDH"],
              ].map(([value, label]) => (
                <label key={value || "auto"}>
                  <input type="radio" name="library-bracket" value={value} checked={commanderBracket === value} onChange={(event) => setCommanderBracket(event.target.value)} />
                  {label}
                </label>
              ))}
              <div className="bracket-estimate">
                <strong>Estimated bracket: {deck.estimatedCommanderBracket?.bracket || "—"}</strong>
                <span>{(deck.estimatedCommanderBracket?.reasons || []).join("; ")}. Advisory estimate only.</span>
              </div>
            </fieldset>
            {COMMANDER_FORMATS.has(format) && !deck.hasRequiredCommander && (
              <div className="modal-error">This format requires a commander. Save, then open the deck to select one.</div>
            )}
            {error && <div className="modal-error">{error}</div>}
          </div>
          <div className="deck-modal-footer">
            <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="button-primary" disabled={busy}>{busy ? "Saving…" : "Save settings"}</button>
          </div>
        </form>
      </section>
    </div>
  );
}

function DecksPage({ onOpenDeck, createRequestId = 0 }) {
  const [decks, setDecks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [filter, setFilter] = useState("");
  const [openMenuId, setOpenMenuId] = useState(null);
  const [settingsDeck, setSettingsDeck] = useState(null);
  const [commanderDeck, setCommanderDeck] = useState(null);

  useEffect(() => {
    if (createRequestId > 0) setShowCreate(true);
  }, [createRequestId]);

  useEffect(() => {
    async function loadDecks() {
      try {
        const response = await fetch(`${API_BASE}/decks`);
        if (!response.ok) throw new Error(`Could not load decks (${response.status}).`);
        const payload = await response.json();
        setDecks(Array.isArray(payload) ? payload : []);
      } catch (loadError) {
        setError(loadError.message);
      } finally {
        setLoading(false);
      }
    }
    loadDecks();
  }, []);

  const visibleDecks = useMemo(() => {
    const query = filter.trim().toLowerCase();
    if (!query) return decks;
    return decks.filter((deck) =>
      [deck.name, deck.format, ...(deck.commanderNames || [])]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query))
    );
  }, [decks, filter]);

  async function patchDeck(deck, changes) {
    const response = await fetch(`${API_BASE}/decks/${deck.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(changes),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload?.error || "Could not update deck.");
    setDecks((current) => current.map((candidate) => candidate.id === deck.id ? payload : candidate));
    setOpenMenuId(null);
    return payload;
  }

  async function moveToFolder(deck) {
    const folderName = window.prompt("Move this deck to which folder? Leave blank for no folder.", deck.folderName || "");
    if (folderName === null) return;
    try {
      await patchDeck(deck, { folderName: folderName.trim() || null });
    } catch (actionError) {
      setError(actionError.message);
    }
  }

  async function deleteDeck(deck) {
    if (!window.confirm(`Delete “${deck.name}”? This cannot be undone.`)) return;
    try {
      const response = await fetch(`${API_BASE}/decks/${deck.id}`, { method: "DELETE" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.error || "Could not delete deck.");
      setDecks((current) => current.filter((candidate) => candidate.id !== deck.id));
      setOpenMenuId(null);
    } catch (actionError) {
      setError(actionError.message);
    }
  }

  async function openCommanderEditor(deck) {
    setOpenMenuId(null);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/decks/${deck.id}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.error || "Could not load deck commanders.");
      setCommanderDeck(payload);
    } catch (loadError) {
      setError(loadError.message);
    }
  }

  return (
    <div className="decks-page">
      <section className="decks-hero">
        <div>
          <div className="eyebrow">Collection</div>
          <h1>Your decks</h1>
          <p>Build, tune, and track every list in one place.</p>
        </div>
        <button type="button" className="button-primary create-deck-button" onClick={() => setShowCreate(true)}>
          <span>＋</span> Create new deck
        </button>
      </section>

      <section className="decks-panel">
        <div className="decks-panel-toolbar">
          <div>
            <h2>Deck library</h2>
            <span>{decks.length} {decks.length === 1 ? "deck" : "decks"}</span>
          </div>
          <input
            className="deck-filter"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="Search your decks…"
            aria-label="Search your decks"
          />
        </div>

        {loading && <div className="deck-empty-state">Loading your decks…</div>}
        {error && <div className="error-box">{error}</div>}

        {!loading && !error && visibleDecks.length === 0 && (
          <div className="deck-empty-state">
            <div className="empty-icon">◇</div>
            <h3>{decks.length ? "No decks match that search" : "Your first deck starts here"}</h3>
            <p>{decks.length ? "Try a different name, format, or commander." : "Create a list and start shaping your game plan."}</p>
            {!decks.length && (
              <button type="button" className="button-primary" onClick={() => setShowCreate(true)}>Create new deck</button>
            )}
          </div>
        )}

        {visibleDecks.length > 0 && (
          <div className="deck-table-wrap">
            <table className="deck-table">
              <thead>
                <tr>
                  <th>Deck</th>
                  <th>Format</th>
                  <th>Colors</th>
                  <th>Cards</th>
                  <th>Games</th>
                  <th>Win rate</th>
                  <th><span className="sr-only">Open</span></th>
                </tr>
              </thead>
              <tbody>
                {visibleDecks.map((deck) => (
                  <tr key={deck.id} onClick={() => onOpenDeck(deck.id)} tabIndex="0">
                    <td>
                      <strong>{deck.name}</strong>
                      <small>{deck.commanderNames?.join(" + ") || "No commander"}</small>
                    </td>
                    <td><span className="format-pill">{deck.format || "none"}</span></td>
                    <td><ColorIdentity colors={deck.colorIdentity} /></td>
                    <td>{deck.cardCount || 0}</td>
                    <td>{deck.gamesPlayed || 0}</td>
                    <td>
                      {deck.winRate == null ? <span className="muted-value">—</span> : `${deck.winRate}%`}
                    </td>
                    <td className="deck-row-actions" onClick={(event) => event.stopPropagation()}>
                      <button
                        type="button"
                        className="deck-overflow-button"
                        aria-label={`Actions for ${deck.name}`}
                        aria-expanded={openMenuId === deck.id}
                        onClick={() => setOpenMenuId((current) => current === deck.id ? null : deck.id)}
                      >
                        ⋮
                      </button>
                      {openMenuId === deck.id && (
                        <div className="deck-overflow-menu">
                          <button type="button" onClick={() => patchDeck(deck, { isPublic: !deck.isPublic }).catch((actionError) => setError(actionError.message))}>
                            Make deck {deck.isPublic ? "private" : "publicly visible"}
                          </button>
                          {COMMANDER_FORMATS.has(deck.format) && (
                            <button type="button" onClick={() => openCommanderEditor(deck)}>
                              Change commander…
                            </button>
                          )}
                          <button type="button" onClick={() => { setSettingsDeck(deck); setOpenMenuId(null); }}>Settings</button>
                          <button type="button" onClick={() => moveToFolder(deck)}>Move to folder…</button>
                          <button type="button" className="danger" onClick={() => deleteDeck(deck)}>Delete deck…</button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {showCreate && (
        <CreateDeckModal
          onClose={() => setShowCreate(false)}
          onCreated={(deck) => onOpenDeck(deck.id)}
        />
      )}
      {settingsDeck && (
        <LibraryDeckSettingsModal
          deck={settingsDeck}
          onClose={() => setSettingsDeck(null)}
          onSaved={(updated) => {
            setDecks((current) => current.map((deck) => deck.id === updated.id ? updated : deck));
            setSettingsDeck(null);
          }}
        />
      )}
      {commanderDeck && (
        <CommanderEditorModal
          deck={commanderDeck}
          onClose={() => setCommanderDeck(null)}
          onSaved={(updated) => {
            setDecks((current) => current.map((deck) => deck.id === updated.id ? updated : deck));
            setCommanderDeck(null);
          }}
        />
      )}
    </div>
  );
}

export default DecksPage;
