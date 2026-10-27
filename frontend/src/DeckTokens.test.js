import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { TokenPreferences } from "./DeckBuilder";


test("chooses and saves the Play Mat printing for a deck token", async () => {
  const token = {
    tokenOracleId: "dragon-token",
    name: "Dragon",
    typeLine: "Token Creature — Dragon",
    power: "4",
    toughness: "4",
    createdBy: ["Dragon Roost"],
    preferredPrintingId: 11,
    preferred: { printingId: 11, setCode: "TST", collectorNumber: "1" },
    versions: [
      { printingId: 11, setCode: "TST", collectorNumber: "1" },
      { printingId: 12, setCode: "ALT", collectorNumber: "2", artist: "Token Artist" },
    ],
  };
  const updated = { ...token, preferredPrintingId: 12, preferred: token.versions[1] };
  const onTokenUpdated = jest.fn();
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => updated }));

  render(<TokenPreferences deck={{ id: 7, tokens: [token] }} onTokenUpdated={onTokenUpdated} />);
  expect(screen.getByText("Tokens this deck can create")).toBeInTheDocument();
  expect(screen.getByText("Created by Dragon Roost")).toBeInTheDocument();

  fireEvent.change(screen.getByRole("combobox", { name: "Preferred version" }), {
    target: { value: "12" },
  });
  await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
    "/api/decks/7/tokens/dragon-token",
    expect.objectContaining({ method: "PUT" })
  ));
  expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({ preferredPrintingId: 12 });
  await waitFor(() => expect(onTokenUpdated).toHaveBeenCalledWith(updated));
});
