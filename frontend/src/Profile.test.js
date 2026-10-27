import React from "react";
import { render, screen } from "@testing-library/react";
import Profile from "./Profile";

afterEach(() => jest.restoreAllMocks());

function mockProfile({ library, history = [], fail = false }) {
  global.fetch = jest.fn((url) => {
    let payload = [];
    if (url.includes("/profile/stats")) payload = { library };
    else if (url.includes("/profile/history")) payload = { games: history, total: history.length };
    else if (!url.includes("recent=")) payload = [{ id: 2, name: "Saved deck", gamesPlayed: 999, wins: 999 }];
    return Promise.resolve({ ok: !fail, json: async () => payload });
  });
}

test("Profile uses API library win rate and shows unsaved deck history", async () => {
  mockProfile({ library: { gamesPlayed: 5, wins: 3, losses: 2, draws: 0, winRate: 60 },
    history: [{ id: 1, status: "completed", gameMode: "pvp", players: [{ id: 7, deckId: 3, deckName: "Unsaved Dragons" }],
      myParticipations: [{ gamePlayerId: 7, result: "loss", libraryStatus: "unlisted" }] }] });
  render(<Profile />);
  expect(await screen.findByText("60%")).toBeTruthy();
  expect(screen.getByText("Library Win Rate")).toBeTruthy();
  expect(screen.getByText("Unsaved Dragons")).toBeTruthy();
  expect(screen.getByText("loss")).toBeTruthy();
  expect(screen.queryByText("100%")).toBeNull();
  expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining("/profile/history"));
});

test("Profile leaves an empty or unavailable competitive win rate unset", async () => {
  mockProfile({ library: { gamesPlayed: 0, winRate: null } });
  render(<Profile />);
  await screen.findByText("Saved deck");
  expect(screen.queryByText("0%")).toBeNull();
});
