export function localCardImage(url) {
  return typeof url==='string'&&url.startsWith('/card-images/')&&window.location.pathname.startsWith('/mtg/')?'/mtg'+url:url;
}
export function scryfallImageUrl(card, size = "small") {
  if (!card) return null;

  const existing = size === "normal"
    ? card.imageNormal || card.imageSmall
    : card.imageSmall;
  if (existing) return localCardImage(existing);

  const id = card.scryfallId;
  if (typeof id !== "string" || id.length < 2) return null;

  return `https://cards.scryfall.io/${size}/front/${id[0]}/${id[1]}/${id}.jpg`;
}
