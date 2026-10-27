import { render, screen } from "@testing-library/react";
import { ColorIdentitySymbols, ManaCost, ManaText } from "./ManaSymbols";

describe("mana symbol rendering", () => {
    test("renders a mana cost as accessible icon pips", () => {
        const { container } = render(<ManaCost cost="{2}{U}{R}" />);

        expect(screen.getByTitle("2 generic mana")).toBeInTheDocument();
        expect(screen.getByTitle("blue mana")).toBeInTheDocument();
        expect(screen.getByTitle("red mana")).toBeInTheDocument();
        expect(container).not.toHaveTextContent("{U}");
        expect(container).not.toHaveTextContent("{R}");
    });

    test("replaces symbols embedded in Oracle text", () => {
        const { container } = render(<ManaText>{"{T}: Add {G}."}</ManaText>);

        expect(screen.getByTitle("tap")).toBeInTheDocument();
        expect(screen.getByTitle("green mana")).toBeInTheDocument();
        expect(container).toHaveTextContent(": Add");
        expect(container).not.toHaveTextContent("{T}");
    });

    test("uses icons for deck color identity", () => {
        render(<ColorIdentitySymbols colors={["W", "B"]} />);

        expect(screen.getByTitle("white mana")).toBeInTheDocument();
        expect(screen.getByTitle("black mana")).toBeInTheDocument();
    });
});
