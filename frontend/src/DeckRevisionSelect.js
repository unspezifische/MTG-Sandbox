import React from "react";

export default function DeckRevisionSelect({ deck, value, onChange, label = "Deck version" }) {
  if (!deck?.sourcePreconId) return null;
  return (
    <label className="lobby-field">
      <span>{label}</span>
      <select className="modal-input" value={value} onChange={(event) => onChange(event.target.value)}>
        {deck.resolvedRevisionId && <option value={deck.resolvedRevisionId}>Resolved original · Revision #{deck.resolvedRevisionId}</option>}
        <option value="current">Play My Version</option>
        <option value="stock">Play Original Precon</option>
      </select>
    </label>
  );
}
