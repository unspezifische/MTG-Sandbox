import React from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import PreconsPage from "./PreconsPage";
import HistoryPage from "./HistoryPage";
import DeckStatistics from "./DeckStatistics";
import MatchSetupModal from "./MatchSetupModal";
import { mergePlayDecks, launchRevision } from "./preconApi";

const precon = { id: 7, name: "Draconic Destruction", gameplayAvailable: true, setCode: "SCD", releaseDate: "2022-12-02", format: "commander" };
const totals = { gamesPlayed: 5, wins: 3, losses: 2, draws: 0, winRate: 60, averageTurns: 8 };
const response = (data, status = 200) => Promise.resolve({ ok: status === 200, status, json: async () => data });
afterEach(() => {
  jest.restoreAllMocks();
  delete global.IntersectionObserver;
});

test("catalog filters and infinite scrolling append server batches", async () => {
  let intersectionCallback;
  const observe = jest.fn();
  const disconnect = jest.fn();
  global.IntersectionObserver = jest.fn((callback) => {
    intersectionCallback = callback;
    return { observe, disconnect };
  });
  global.fetch = jest.fn((url) => {
    const offset = new URL(url, "http://localhost").searchParams.get("offset");
    return response(offset === "50"
      ? { total: 60, limit: 50, offset: 50, precons: [{ ...precon, id: 8, name: "Second batch" }] }
      : { total: 60, limit: 50, offset: 0, precons: [precon] });
  });
  render(<PreconsPage />);
  await screen.findByText(precon.name);
  for (const [label, value] of [["Search preconstructed decks", "dragon"], ["Set code", "SCD"], ["Release year", "2022"], ["Commander", "Atarka"], ["Format", "commander"]]) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByText("Search"));
  await waitFor(() => expect(global.fetch).toHaveBeenLastCalledWith(expect.stringContaining("commander=Atarka"), expect.anything()));
  await waitFor(() => expect(observe).toHaveBeenCalled());
  act(() => intersectionCallback([{ isIntersecting: true }]));
  await waitFor(() => expect(global.fetch).toHaveBeenLastCalledWith(expect.stringContaining("offset=50"), expect.anything()));
  expect(await screen.findByText("Second batch")).toBeTruthy();
  const url = new URL(global.fetch.mock.calls.at(-1)[0], "http://localhost");
  expect(Object.fromEntries(url.searchParams)).toEqual({ q: "dragon", set: "SCD", year: "2022", commander: "Atarka", format: "commander", limit: "50", offset: "50" });
});

test("official details load from detail endpoint and incomplete lists disable both actions", async () => {
  global.fetch = jest.fn((url) => url.endsWith("/precons/7") ? response({ ...precon, gameplayAvailable: false, commanders: [{ name: "Atarka" }], boards: { main: [{ id: 1, quantity: 2, name: "Forest", card: null }] }, boardCounts: { main: 2 }, issues: ["Unresolved printing"], importStatus: "incomplete" }) : response({ precons: [{ ...precon, gameplayAvailable: false }], total: 1 }));
  render(<PreconsPage onPlay={jest.fn()} />);
  fireEvent.click(await screen.findByText("View Deck"));
  expect(await screen.findByText("Unresolved printing")).toBeTruthy();
  expect(screen.getByText(/2 × Forest/)).toBeTruthy();
  screen.getAllByText("Play Original").forEach((b) => expect(b).toBeDisabled());
  screen.getAllByText("Add to Your Decks").forEach((b) => expect(b).toBeDisabled());
  expect(global.fetch).toHaveBeenCalledWith(expect.stringMatching(/\/precons\/7$/), expect.anything());
});

test("resolver metadata makes an unlisted deck selectable with its exact original revision", async () => {
  const launch = jest.fn().mockResolvedValue({});
  function Harness() {
    const [selection, setSelection] = React.useState(null);
    return <><PreconsPage onPlay={(s) => setSelection(s)} />{selection && <MatchSetupModal mode="goldfish" decks={mergePlayDecks([], [selection])} initialDeckId={selection.deckId} initialRevision={selection.revisionId} onLaunch={launch} onClose={() => {}} />}</>;
  }
  const selection = { deckId: 42, revisionId: 77, deck: { id: 42, name: "Unlisted Dragons", cardCount: 100, libraryStatus: "unlisted", sourcePreconId: 7, currentRevisionId: 88 } };
  global.fetch = jest.fn((url) => url.endsWith("/play") ? response(selection) : response({ precons: [precon], total: 1 }));
  render(<Harness />);
  fireEvent.click(await screen.findByText("Play Original"));
  fireEvent.click(await screen.findByText("Start Goldfish"));
  expect(launch).toHaveBeenCalledWith(expect.objectContaining({ playerDeckId: 42, revision: 77 }));
});

test.each([401, 409, 503])("catalog action status %i has actionable guidance", async (status) => {
  global.fetch = jest.fn((url, opts) => opts?.method === "POST" ? response({ error: "Action unavailable" }, status) : response({ precons: [precon], total: 1 }));
  render(<PreconsPage onPlay={jest.fn()} />);
  fireEvent.click(await screen.findByText("Play Original"));
  const alert = await screen.findByRole("alert");
  expect(alert.textContent).toMatch(status === 401 ? /Sign in to Kachhapa/ : status === 503 ? /identity service is unavailable/ : /Refresh its details/);
});

test("personal history shows own result, invalidation, unknown configuration and ambiguity", async () => {
  const participation = { gamePlayerId: 1, deckId: 42, result: "loss", configurationKnown: false, libraryStatus: "unlisted" };
  global.fetch = jest.fn(() => response({ total: 30, games: [{ id: 1, gameMode: "multiplayer", status: "completed", isInvalidated: true, invalidationReason: "Invalid result", players: [{ id: 1, deckName: "My Dragons" }, { id: 2, deckName: "Opponent", result: "win" }], myParticipations: [participation, { ...participation, gamePlayerId: 3, libraryStatus: "archived" }] }] }));
  render(<HistoryPage />);
  expect(await screen.findByText(/result attribution is ambiguous/)).toBeTruthy();
  expect(screen.getAllByText("Participant result: loss")).toHaveLength(2);
  expect(screen.getAllByText("Unknown historical configuration")).toHaveLength(2);
  expect(screen.getByText(/Invalidated — excluded/)).toBeTruthy();
  expect(screen.getByText("Library: archived")).toBeTruthy();
  fireEvent.click(screen.getByText("Next"));
  await waitFor(() => expect(global.fetch).toHaveBeenLastCalledWith(expect.stringMatching(/profile\/history\?.*offset=25/), expect.anything()));
  expect(global.fetch.mock.calls.every(([url]) => !url.includes("/api/games"))).toBe(true);
});

test("statistics scopes, returned revision IDs and modes are requested from the server", async () => {
  global.fetch = jest.fn(() => response({ stats: totals, scopes: { all: totals, stock: totals, current: totals }, revisions: [{ ...totals, revisionId: 11, revisionType: "stock", configurationKnown: true }, { ...totals, revisionId: 12, revisionType: "custom", configurationKnown: true }, { ...totals, revisionId: null, configurationKnown: false }] }));
  render(<DeckStatistics deck={{ id: 42 }} />);
  await screen.findByText("Compare revisions");
  for (const scope of ["stock", "current", "all"]) {
    fireEvent.change(screen.getByLabelText("Revision scope"), { target: { value: scope } });
    await waitFor(() => expect(global.fetch).toHaveBeenLastCalledWith(expect.stringContaining(`revision=${scope}`), expect.anything()));
  }
  fireEvent.click(await screen.findByLabelText("Revision #11 · stock"));
  fireEvent.click(screen.getByLabelText("Revision #12 · custom"));
  fireEvent.click(screen.getByText("Compare selected revisions"));
  await waitFor(() => expect(global.fetch).toHaveBeenLastCalledWith(expect.stringContaining("revision=11%2C12"), expect.anything()));
  for (const mode of ["pvai", "goldfish", "simulation", "pvp", "competitive"]) {
    fireEvent.change(screen.getByLabelText("Statistics mode"), { target: { value: mode } });
    await waitFor(() => expect(global.fetch).toHaveBeenLastCalledWith(expect.stringContaining(`mode=${mode}`), expect.anything()));
  }
  expect(within(await screen.findByRole("region", { name: "Revision comparison" })).getByText("Unknown historical configuration")).toBeTruthy();
});

test("empty personal history explains how to begin", async () => {
  global.fetch = jest.fn(() => response({ games: [], total: 0 }));
  render(<HistoryPage />);
  expect(await screen.findByText(/saving it is optional/)).toBeTruthy();
});

test("promotion refreshes selection metadata without dropping the pinned original", () => {
  const [deck] = mergePlayDecks([{ id: 42, sourcePreconId: 7, libraryStatus: "saved", currentRevisionId: 99 }],
    [{ deckId: 42, revisionId: 77, deck: { id: 42, libraryStatus: "unlisted", currentRevisionId: 77 } }]);
  expect(deck.libraryStatus).toBe("saved");
  expect(deck.currentRevisionId).toBe(99);
  expect(deck.resolvedRevisionId).toBe(77);
  expect(launchRevision(deck, "current")).toBe("current");
  expect(launchRevision(deck, "stock")).toBe(77);
});

test("simulation uses the resolved unlisted original for both selected decks", async () => {
  const launch = jest.fn().mockResolvedValue({});
  const decks = mergePlayDecks([], [{ deckId: 42, revisionId: 77, deck: { id: 42, sourcePreconId: 7, cardCount: 100, name: "Unlisted Dragons", libraryStatus: "unlisted" } }]);
  render(<MatchSetupModal mode="simulation" decks={decks} initialDeckId={42} initialRevision={77} onLaunch={launch} onClose={() => {}} />);
  fireEvent.click(screen.getByText("Play against computer"));
  expect(launch).toHaveBeenCalledWith(expect.objectContaining({ playerDeckId: 42, revision: 77, computerDeckId: 42, computerRevision: 77 }));
});

test("PvP hosting retains a resolver selection omitted by the saved library", async () => {
  const { default: GameLobby } = await import("./GameLobby");
  const create = jest.fn().mockResolvedValue({ id: 1 });
  const decks = mergePlayDecks([], [{ deckId: 42, revisionId: 77, deck: { id: 42, sourcePreconId: 7, cardCount: 100, name: "Unlisted Dragons", libraryStatus: "unlisted" } }]);
  render(<GameLobby decks={decks} games={[]} busy={false} createRequestId={1} preferredDeckId="42" preferredRevision={77} onCreate={create} />);
  const dialog = await screen.findByRole("dialog");
  fireEvent.change(within(dialog).getByLabelText("Lobby name"), { target: { value: "Test table" } });
  fireEvent.click(within(dialog).getByRole("button", { name: "Create lobby" }));
  await waitFor(() => expect(create).toHaveBeenCalledWith(expect.objectContaining({ hostDeckId: 42, hostDeckVersionId: 77 })));
});

test("saving the previously played primary refreshes the API-backed library record", async () => {
  const { default: Profile } = await import("./Profile");
  let saved = false;
  const open = jest.fn();
  function Harness() {
    const [showProfile, setShowProfile] = React.useState(false);
    return showProfile ? <Profile /> : <PreconsPage onPlay={jest.fn()} onSaved={() => setShowProfile(true)} onOpenDeck={open} />;
  }
  global.fetch = jest.fn((url) => {
    if (url.endsWith("/play")) return response({ deckId: 42, revisionId: 77, deck: { id: 42 } });
    if (url.endsWith("/save")) { saved = true; return response({ id: 42 }); }
    if (url.includes("/profile/stats")) return response({ library: saved ? totals : { ...totals, gamesPlayed: 0, winRate: null } });
    if (url.includes("/profile/history")) return response({ games: [], total: 5 });
    if (url.includes("/decks")) return response(saved ? [{ id: 42, name: "Saved Dragons", gamesPlayed: 5, wins: 3, losses: 2 }] : []);
    return response({ precons: [precon], total: 1 });
  });
  render(<Harness />);
  fireEvent.click(await screen.findByText("Play Original"));
  await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining("/precons/7/play"), expect.anything()));
  await waitFor(() => expect(screen.getByText("Add to Your Decks")).not.toBeDisabled());
  fireEvent.click(screen.getByText("Add to Your Decks"));
  expect(await screen.findByText("60%")).toBeTruthy();
  expect(screen.getByText("Library Win Rate")).toBeTruthy();
  expect(open).toHaveBeenCalledWith(42);
});

test.each([401, 503])("personal history and statistics explain identity status %i", async (status) => {
  global.fetch = jest.fn(() => response({ error: "Identity check failed" }, status));
  const view = render(<HistoryPage />);
  expect((await screen.findByRole("alert")).textContent).toMatch(status === 401 ? /Sign in to Kachhapa/ : /identity service is unavailable/);
  view.unmount();
  render(<DeckStatistics deck={{ id: 42 }} />);
  expect((await screen.findByRole("alert")).textContent).toMatch(status === 401 ? /Sign in to Kachhapa/ : /identity service is unavailable/);
});
