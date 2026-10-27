import React from "react";

const SYMBOL_NAMES = {
    W: "white mana",
    U: "blue mana",
    B: "black mana",
    R: "red mana",
    G: "green mana",
    C: "colorless mana",
    S: "snow mana",
    T: "tap",
    Q: "untap",
    E: "energy",
    P: "Phyrexian mana",
    X: "X generic mana",
    Y: "Y generic mana",
    Z: "Z generic mana",
};

const COLOR_SYMBOLS = new Set(["W", "U", "B", "R", "G", "C"]);

function ManaGlyph({ symbol }) {
    if (symbol === "W") {
        return (
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="4.2" />
                <path d="M12 1.9v4M12 18.1v4M1.9 12h4M18.1 12h4M4.85 4.85l2.82 2.82M16.33 16.33l2.82 2.82M19.15 4.85l-2.82 2.82M7.67 16.33l-2.82 2.82" />
            </svg>
        );
    }
    if (symbol === "U") {
        return (
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 2.1C9.2 6.2 5.6 9.5 5.6 14.2a6.4 6.4 0 0 0 12.8 0C18.4 9.5 14.8 6.2 12 2.1Z" />
                <path className="mana-glyph-cutout" d="M15.8 13.6c0 2.5-1.5 4.1-3.9 4.5 1.1.6 2.6.5 3.6-.4 1.2-1 1.6-2.7.9-4.2-.2-.5-.7-.4-.6.1Z" />
            </svg>
        );
    }
    if (symbol === "B") {
        return (
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 10.2A7 7 0 0 1 19 10c0 2.8-1.3 4.7-3.2 5.8v4.1l-2.3-1.4-1.5 2-1.5-2-2.3 1.4v-4.1A6.2 6.2 0 0 1 5 10.2Z" />
                <circle className="mana-glyph-cutout" cx="9.3" cy="10.5" r="1.55" />
                <circle className="mana-glyph-cutout" cx="14.7" cy="10.5" r="1.55" />
                <path className="mana-glyph-cutout" d="m12 12.2-1.3 2h2.6Z" />
            </svg>
        );
    }
    if (symbol === "R") {
        return (
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M13.7 2.1c.8 4.2-3.6 5.3-2.1 8.2 1.1-1.4 2.6-2.3 4.1-3.1.1 2.7 3.4 4.1 2.4 8.7A6.3 6.3 0 0 1 6 16.2c-1-3.6 1.3-6.3 3.5-8.3-.1 2 .5 3.3 1.4 3.9-.7-4.2 1.4-6.8 2.8-9.7Z" />
                <path className="mana-glyph-cutout" d="M12.9 13.3c2.6 2.3 1.1 5.8-1.2 6.3-1.7-1-2.3-3.5 1.2-6.3Z" />
            </svg>
        );
    }
    if (symbol === "G") {
        return (
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 1.8c1.3 1.1 2 2.3 2 3.7 2.5-.8 4.7.7 4.7 3.2 2.1.4 3.2 2 2.8 4-.4 2-2.2 3.1-4.2 2.9-.3 2.2-2.2 3.5-4.3 3v3.6H9v-2h1.5v-4.8l-3.3-2.5.9-1.2 2.4 1.7v-3.2H12v2.7l2.2-1.8 1 1.1-3.2 2.7v5.2h1v2H9c0-1.2.4-2.5 1-3.6-2.1.4-4-.8-4.4-2.9-2.1.1-3.6-1.3-3.5-3.3 0-2 1.3-3.3 3.2-3.7-.2-2.3 1.8-4.1 4.1-3.5.3-1.4 1.2-2.6 2.6-3.4Z" />
            </svg>
        );
    }
    if (symbol === "C") {
        return (
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path fillRule="evenodd" d="M12 1.5 22.5 12 12 22.5 1.5 12 12 1.5Zm0 5.1L6.6 12l5.4 5.4 5.4-5.4L12 6.6Z" />
            </svg>
        );
    }
    if (symbol === "S") return <span className="mana-symbol-character" aria-hidden="true">❄</span>;
    if (symbol === "T") return <span className="mana-symbol-character mana-symbol-rotate" aria-hidden="true">↷</span>;
    if (symbol === "Q") return <span className="mana-symbol-character mana-symbol-rotate" aria-hidden="true">↶</span>;
    if (symbol === "E") return <span className="mana-symbol-character" aria-hidden="true">ϟ</span>;
    if (symbol === "P") return <span className="mana-symbol-character" aria-hidden="true">Φ</span>;
    return <span className="mana-symbol-character" aria-hidden="true">{symbol}</span>;
}

function describeSymbol(symbol) {
    if (SYMBOL_NAMES[symbol]) return SYMBOL_NAMES[symbol];
    if (/^\d+$/.test(symbol)) return `${symbol} generic mana`;
    if (symbol.includes("/")) {
        return symbol.split("/").map((part) => SYMBOL_NAMES[part] || part).join(" or ");
    }
    return symbol;
}

function symbolClass(symbol) {
    const parts = symbol.split("/");
    const colors = parts.filter((part) => COLOR_SYMBOLS.has(part));
    if (colors.length === 1 && parts.length === 1) return `mana-symbol--${colors[0].toLowerCase()}`;
    if (colors.length) return `mana-symbol--hybrid mana-symbol--hybrid-${colors.join("").toLowerCase()}`;
    if (symbol === "T" || symbol === "Q") return "mana-symbol--action";
    if (symbol === "S") return "mana-symbol--snow";
    if (symbol === "E") return "mana-symbol--energy";
    return "mana-symbol--generic";
}

export function ManaSymbol({ symbol, size = "md" }) {
    const normalized = String(symbol || "").replace(/^\{|\}$/g, "").toUpperCase();
    if (!normalized) return null;
    const parts = normalized.split("/");

    return (
        <span
            className={`mana-symbol mana-symbol--${size} ${symbolClass(normalized)}`}
            role="img"
            aria-label={describeSymbol(normalized)}
            title={describeSymbol(normalized)}
            data-mana-symbol={normalized}
        >
            {parts.map((part, index) => (
                <span className="mana-symbol-part" key={`${part}-${index}`}>
                    <ManaGlyph symbol={part} />
                </span>
            ))}
        </span>
    );
}

export function ManaCost({ cost, size = "md", empty = "—", className = "" }) {
    const symbols = String(cost || "").match(/\{([^}]+)\}/g) || [];
    if (!symbols.length) return <span className={className}>{empty}</span>;

    return (
        <span className={`mana-cost ${className}`.trim()} aria-label={symbols.map((symbol) => describeSymbol(symbol.slice(1, -1).toUpperCase())).join(", ")}>
            {symbols.map((symbol, index) => (
                <ManaSymbol key={`${symbol}-${index}`} symbol={symbol} size={size} />
            ))}
        </span>
    );
}

export function ManaText({ children, size = "sm", className = "" }) {
    const text = String(children ?? "");
    const segments = text.split(/(\{[^}]+\})/g);

    return (
        <span className={`mana-text ${className}`.trim()}>
            {segments.map((segment, index) => {
                const match = segment.match(/^\{([^}]+)\}$/);
                return match
                    ? <ManaSymbol key={`${segment}-${index}`} symbol={match[1]} size={size} />
                    : <React.Fragment key={`text-${index}`}>{segment}</React.Fragment>;
            })}
        </span>
    );
}

export function ColorIdentitySymbols({ colors, size = "md", empty = "Colorless" }) {
    if (!Array.isArray(colors) || colors.length === 0) {
        return <span className="deck-colorless">{empty}</span>;
    }
    return (
        <span className="mana-cost mana-color-identity">
            {colors.map((color) => <ManaSymbol key={color} symbol={color} size={size} />)}
        </span>
    );
}
