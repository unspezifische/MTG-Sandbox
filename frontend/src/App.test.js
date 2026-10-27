import { fireEvent, render, screen } from '@testing-library/react';
import App from './App';

beforeEach(() => {
  window.KachhapaAppearance = {
    mode: jest.fn(() => "dark"),
    snapshot: jest.fn(() => ({ username: "Jace Beleren" })),
    refresh: jest.fn(() => Promise.resolve()),
    setMode: jest.fn(() => Promise.resolve()),
  };
});

afterEach(() => {
  delete window.KachhapaAppearance;
});

test("renders the MTG Sandbox shell with a distinct Pod Bay", () => {
  render(<App />);
  expect(screen.getByText("MTG Sandbox")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Pod Bay" })).toBeInTheDocument();
  expect(screen.queryByText("Themes")).not.toBeInTheDocument();
});

test("opens account controls from the avatar", () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Open menu for Jace Beleren" }));
  expect(screen.getByRole("menuitem", { name: /Settings/ })).toBeInTheDocument();
  expect(screen.getByRole("menuitem", { name: /Switch to Light Mode/ })).toBeInTheDocument();
  expect(screen.getByRole("menuitem", { name: /Account Dashboard/ })).toHaveAttribute(
    "href",
    `${window.location.protocol}//${window.location.host}/accountProfile`
  );

  fireEvent.click(screen.getByRole("menuitem", { name: /Switch to Light Mode/ }));
  expect(window.KachhapaAppearance.setMode).toHaveBeenCalledWith("light");
});

test("opens Sandbox Settings from the avatar menu", () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Open menu for Jace Beleren" }));
  fireEvent.click(screen.getByRole("menuitem", { name: /Settings/ }));
  expect(screen.getByRole("heading", { name: "Settings" })).toBeInTheDocument();
});
