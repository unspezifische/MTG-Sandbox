import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import PlayMat from "./PlayMat";


jest.mock("socket.io-client", () => ({
  io: () => ({ on: jest.fn(), emit: jest.fn(), disconnect: jest.fn() }),
}));


test("creates the deck-selected token from the Play Mat token tray", async () => {
  const token = {
    tokenOracleId: "dragon-token",
    name: "Dragon",
    typeLine: "Token Creature — Dragon",
    power: "4",
    toughness: "4",
    preferred: { cardId: 51, printingId: 61, typeLine: "Token Creature — Dragon" },
  };
  const state = {
    game: { id: 9, status: "active", format: "commander", gameMode: "goldfish", turnNumber: 1, activeSeatNumber: 1 },
    players: [{
      id: 4, seatNumber: 1, playerType: "human", startingLife: 40,
      zones: { hand: [], battlefield: [], graveyard: [], exile: [], command: [], stack: [], libraryCount: 93 },
      tokenOptions: [token],
    }],
    alternateWinConditions: [],
    randomResults: [],
  };
  global.fetch = jest.fn(async (_url, options = {}) => ({
    ok: true,
    json: async () => options.method === "POST" ? { state } : state,
  }));

  render(<PlayMat gameId={9} activePlayerId={4} />);
  fireEvent.click(await screen.findByRole("button", { name: "Tokens (1)" }));
  fireEvent.click(screen.getByRole("button", { name: /Dragon.*Create/ }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
    "/api/games/9/actions",
    expect.objectContaining({ method: "POST" })
  ));
  const actionCall = global.fetch.mock.calls.find(([, options]) => options?.method === "POST");
  expect(JSON.parse(actionCall[1].body).action).toEqual(expect.objectContaining({
    type: "create_token",
    gamePlayerId: 4,
    tokenOracleId: "dragon-token",
  }));
});
