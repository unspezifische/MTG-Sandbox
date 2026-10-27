import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import PreconsPage from "./PreconsPage";

afterEach(() => {
  jest.restoreAllMocks();
});

test("loads, searches, and saves a playable precon", async () => {
  const openDeck = jest.fn();
  global.fetch = jest.fn((url, options = {}) => {
    if (options.method === "POST") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ id: 42 }) });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        total: 1,
        precons: [{ id: 7, name: "Draconic Destruction", setCode: "CLB", format: "commander", releaseDate: "2022-06-10", gameplayAvailable: true }],
      }),
    });
  });

  render(<PreconsPage onOpenDeck={openDeck} />);
  expect(await screen.findByText("Draconic Destruction")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Search preconstructed decks"), { target: { value: "dragon" } });
  fireEvent.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining("q=dragon"), expect.any(Object)));

  fireEvent.click(await screen.findByRole("button", { name: "Add to Your Decks" }));
  await waitFor(() => expect(openDeck).toHaveBeenCalledWith(42));
});
