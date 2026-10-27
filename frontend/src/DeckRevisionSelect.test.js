import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import DeckRevisionSelect from "./DeckRevisionSelect";
import MatchSetupModal from "./MatchSetupModal";

test("precon stock/current choices use explicit selections; custom decks omit them", () => {
  const change = jest.fn();
  const { rerender } = render(<DeckRevisionSelect deck={{ sourcePreconId: 1 }} value="current" onChange={change} />);
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "stock" } });
  expect(change).toHaveBeenCalledWith("stock");
  expect(screen.getByRole("option", { name: "Play My Version" })).toBeTruthy();
  rerender(<DeckRevisionSelect deck={{ id: 1 }} value="current" onChange={change} />);
  expect(screen.queryByRole("combobox")).toBeNull();
});

test("match setup sends the selected original revision", async () => {
  const launch = jest.fn().mockResolvedValue({ id: 1 });
  render(<MatchSetupModal mode="goldfish" decks={[{ id: 3, name: "Dragons", format: "commander", cardCount: 100, sourcePreconId: 2 }]}
    initialDeckId="3" initialRevision="stock" onClose={() => {}} onLaunch={launch} />);
  fireEvent.submit(screen.getByRole("dialog"));
  expect(launch).toHaveBeenCalledWith(expect.objectContaining({ playerDeckId: 3, revision: "stock" }));
});
