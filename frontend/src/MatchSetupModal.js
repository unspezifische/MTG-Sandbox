import React, { useMemo, useState } from "react";

const STRATEGIES = [
  ["relaxed", "Relaxed", "Plays fewer spells and favors a slower practice game."],
  ["adaptive", "Adaptive", "Balances creatures, utility cards, and mana curve."],
  ["aggressive", "Aggressive", "Prioritizes creatures and inexpensive pressure."],
  ["defensive", "Defensive", "Prioritizes interaction, artifacts, and enchantments."],
  ["random", "Unpredictable", "Selects legal-looking actions at random."],
];

export default function MatchSetupModal({
  mode,
  decks,
  initialDeckId = "",
  busy = false,
  onClose,
  onLaunch,
}) {
  const playableDecks = useMemo(
    () => decks.filter((deck) => Number(deck.cardCount || 0) > 0),
    [decks]
  );
  const preferred = playableDecks.some((deck) => String(deck.id) === String(initialDeckId))
    ? String(initialDeckId)
    : String(playableDecks[0]?.id || "");
  const [playerDeckId, setPlayerDeckId] = useState(preferred);
  const [computerDeckId, setComputerDeckId] = useState(
    String(playableDecks.find((deck) => String(deck.id) !== preferred)?.id || preferred)
  );
  const [strategy, setStrategy] = useState("adaptive");
  const [error, setError] = useState("");
  const isSimulation = mode === "simulation";

  async function submit(event) {
    event.preventDefault();
    if (!playerDeckId || (isSimulation && !computerDeckId)) {
      setError("Choose every required deck.");
      return;
    }
    setError("");
    const result = await onLaunch({
      mode,
      playerDeckId: Number(playerDeckId),
      computerDeckId: isSimulation ? Number(computerDeckId) : null,
      strategy,
    });
    if (result?.error) setError(result.error);
    else onClose();
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="deck-modal match-setup-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="match-setup-title"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={submit}
      >
        <div className="deck-modal-header">
          <div>
            <div className="eyebrow">{isSimulation ? "Player versus computer" : "Solo playtest"}</div>
            <h2 id="match-setup-title">{isSimulation ? "Set up a simulation" : "Choose a Goldfish deck"}</h2>
          </div>
          <button type="button" className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="deck-modal-body match-setup-fields">
          <label>
            <span>Your deck</span>
            <select className="modal-input" value={playerDeckId} onChange={(event) => setPlayerDeckId(event.target.value)}>
              {playableDecks.map((deck) => (
                <option value={deck.id} key={deck.id}>{deck.name} · {deck.format}</option>
              ))}
            </select>
          </label>
          {isSimulation ? (
            <>
              <label>
                <span>Computer deck</span>
                <select className="modal-input" value={computerDeckId} onChange={(event) => setComputerDeckId(event.target.value)}>
                  {playableDecks.map((deck) => (
                    <option value={deck.id} key={deck.id}>{deck.name} · {deck.format}</option>
                  ))}
                </select>
              </label>
              <fieldset className="strategy-options">
                <legend>Computer strategy</legend>
                {STRATEGIES.map(([value, label, description]) => (
                  <label className={strategy === value ? "selected" : ""} key={value}>
                    <input
                      type="radio"
                      name="strategy"
                      value={value}
                      checked={strategy === value}
                      onChange={() => setStrategy(value)}
                    />
                    <span><strong>{label}</strong><small>{description}</small></span>
                  </label>
                ))}
              </fieldset>
            </>
          ) : null}
          {error ? <div className="modal-error">{error}</div> : null}
        </div>
        <div className="deck-modal-footer">
          <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="button-primary" disabled={busy || !playableDecks.length}>
            {busy ? "Starting…" : isSimulation ? "Play against computer" : "Start Goldfish"}
          </button>
        </div>
      </form>
    </div>
  );
}
