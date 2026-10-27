export const API_BASE = window.location.pathname.startsWith("/mtg") ? "/mtg/api" : "/api";

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  let payload;
  try { payload = await response.json(); }
  catch {
    if (response.ok) throw new Error("The service returned an unreadable response. Check the API proxy and retry.");
    payload = {};
  }
  if (!response.ok) {
    throw new Error(apiErrorMessage(response.status, payload.error));
  }
  return payload;
}

export function mergePlayDecks(saved, selections) {
  const decks = new Map(saved.map((deck) => [Number(deck.id), deck]));
  selections.forEach((selection) => decks.set(Number(selection.deckId), {
    ...selection.deck, ...decks.get(Number(selection.deckId)), id: selection.deckId,
    resolvedRevisionId: selection.revisionId,
  }));
  return [...decks.values()];
}

export function launchRevision(deck, value = "current") {
  if (deck?.resolvedRevisionId && (value === "stock" || (value === "current" && deck.libraryStatus === "unlisted"))) {
    return deck.resolvedRevisionId;
  }
  return deck?.sourcePreconId ? value : "current";
}

export function apiErrorMessage(status, message) {
  const guidance = {
    401: "Sign in to Kachhapa, then retry this action.",
    409: "This selection is unavailable or has changed. Refresh its details and try again.",
    503: "The identity service is unavailable. Try again shortly; an administrator may need to check KACHHAPA_AUTH_URL.",
  }[status];
  return [message || `Request failed (${status}).`, guidance].filter(Boolean).join(" ");
}
