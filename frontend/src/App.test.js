import { render, screen } from '@testing-library/react';
import App from './App';

test("renders the MTG Sandbox application shell", () => {
  render(<App />);
  expect(screen.getByText("MTG Sandbox")).toBeInTheDocument();
});
