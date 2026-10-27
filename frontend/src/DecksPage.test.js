import { fireEvent, render, screen } from "@testing-library/react";
import DecksPage from "./DecksPage";

beforeEach(() => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve([]) }));
});

afterEach(() => {
  jest.restoreAllMocks();
});

test("consumes a create request so returning to Your Decks does not reopen the modal", async () => {
  const handled = jest.fn();
  const firstVisit = render(
    <DecksPage onOpenDeck={jest.fn()} createRequestId={1} onCreateRequestHandled={handled} />
  );

  expect(screen.getByRole("dialog", { name: "Create a new deck" })).toBeInTheDocument();
  expect(handled).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.queryByRole("dialog", { name: "Create a new deck" })).not.toBeInTheDocument();
  firstVisit.unmount();

  render(<DecksPage onOpenDeck={jest.fn()} createRequestId={0} onCreateRequestHandled={handled} />);
  expect(screen.queryByRole("dialog", { name: "Create a new deck" })).not.toBeInTheDocument();
  expect(await screen.findByText("Your first deck starts here")).toBeInTheDocument();
});
