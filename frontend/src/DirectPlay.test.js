import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "./App";

jest.mock("socket.io-client", () => ({ io: () => ({ on: jest.fn(), off: jest.fn(), emit: jest.fn(), disconnect: jest.fn() }) }));
jest.mock("./Profile", () => ({ onNavigate }) => <button onClick={() => onNavigate("precons")}>Browse catalog</button>);
jest.mock("./PlayMat", () => ({ onExitGame }) => <div>Live game<button onClick={() => onExitGame()}>Leave game</button></div>);
jest.mock("./DeckBuilder", () => ({ deckId }) => <div>Editing deck {deckId}</div>);

test("App submits the resolver's unlisted deck and exact revision then saves that same deck", async () => {
  window.history.replaceState({}, "", "/");
  let saved = false;
  const deck = { id: 42, name: "Unlisted Dragons", sourcePreconId: 7, libraryStatus: "unlisted", cardCount: 100, currentRevisionId: 88 };
  const game = { id: 9, status: "active", players: [{ id: 1, deckId: 42 }], currentPlayerId: 1 };
  global.fetch = jest.fn(async (url, options = {}) => {
    let data = [];
    if (url.includes("/precons?")) data = { total: 1, precons: [{ id: 7, name: "Draconic Destruction", gameplayAvailable: true }] };
    else if (url.endsWith("/precons/7/play")) data = { deckId: 42, revisionId: 77, deck };
    else if (url.endsWith("/precons/7/save")) { saved = true; data = { ...deck, libraryStatus: "saved" }; }
    else if (url.endsWith("/decks")) data = saved ? [{ ...deck, libraryStatus: "saved" }] : [];
    else if ((url.endsWith("/games") && options.method === "POST") || url.endsWith("/games/9")) data = game;
    return { ok: true, status: 200, json: async () => data };
  });
  render(<App />);
  fireEvent.click(screen.getByText("Browse catalog"));
  fireEvent.click(await screen.findByText("Play Original"));
  fireEvent.click(await screen.findByText("Start Goldfish"));
  await screen.findByText("Live game");
  const post = global.fetch.mock.calls.find(([url, options]) => url.endsWith("/games") && options?.method === "POST");
  expect(JSON.parse(post[1].body).players[0]).toEqual(expect.objectContaining({ deckId: 42, deckVersionId: 77 }));
  expect(JSON.parse(post[1].body).players[0].userId).toBeUndefined();
  fireEvent.click(screen.getByText("Leave game"));
  fireEvent.click(await screen.findByRole("button", { name: "Precons" }));
  fireEvent.click(await screen.findByText("Add to Your Decks"));
  await screen.findByText("Editing deck 42");
  await waitFor(() => expect(saved).toBe(true));
  expect(global.fetch.mock.calls.some(([url]) => url.endsWith("/decks"))).toBe(true);
});
