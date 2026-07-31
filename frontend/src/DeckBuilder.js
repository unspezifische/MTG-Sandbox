import React, { useEffect, useMemo, useRef, useState } from "react";
import { scryfallImageUrl } from "./cardImages";

const isMtgSubpath = window.location.pathname.startsWith("/mtg");
const API_BASE = isMtgSubpath ? "/mtg/api" : "/api";
const BOARD_OPTIONS = [
    ["main", "Main Deck"],
    ["sideboard", "Sideboard"],
    ["considering", "Considering"],
    ["attraction", "Attraction Deck"],
    ["contraption", "Contraption Deck"],
    ["stickers", "Sticker Sheets"],
    ["planar", "Planar Deck"],
    ["schemes", "Schemes"],
];
const FORMAT_OPTIONS = [
    ["commander", "Commander / EDH"],
    ["standard", "Standard"],
    ["modern", "Modern"],
    ["pioneer", "Pioneer"],
    ["legacy", "Legacy"],
    ["vintage", "Vintage"],
    ["pauper", "Pauper"],
    ["brawl", "Brawl"],
    ["standard-brawl", "Standard Brawl"],
    ["duel-commander", "Duel Commander"],
    ["pauper-edh", "Pauper EDH"],
    ["oathbreaker", "Oathbreaker"],
    ["historic", "Historic"],
    ["timeless", "Timeless"],
    ["none", "No format"],
];
const COMMANDER_FORMATS = new Set([
    "commander",
    "brawl",
    "standard-brawl",
    "duel-commander",
    "pauper-edh",
    "oathbreaker",
]);
const TYPE_GROUP_ORDER = [
    "Commander",
    "Creatures",
    "Instants",
    "Sorceries",
    "Artifacts",
    "Enchantments",
    "Planeswalkers",
    "Lands",
    "Other",
];

function getCardImageUrl(card, size = "small") {
    return scryfallImageUrl(card, size);
}

function isCommanderEligible(card) {
    const typeLine = card?.typeLine || "";
    const oracleText = (card?.oracleText || "").toLowerCase();
    return (
        typeLine.includes("Legendary Creature")
        || typeLine.includes("Legendary Background")
        || oracleText.includes("can be your commander")
    );
}

function commandersAreCompatible(first, second) {
    if (!first || !second) return true;
    if (first.partnerMode === "named") {
        return String(second.name || "").toLowerCase() === String(first.partnerName || "").toLowerCase();
    }
    if (second.partnerMode === "named") {
        return String(first.name || "").toLowerCase() === String(second.partnerName || "").toLowerCase();
    }
    if (first.partnerMode === "partner" && second.partnerMode === "partner") return true;
    if (first.partnerMode === "friends_forever" && second.partnerMode === "friends_forever") return true;
    if (first.partnerMode === "background") {
        return String(second.typeLine || "").toLowerCase().includes("background");
    }
    if (second.partnerMode === "background") {
        return String(first.typeLine || "").toLowerCase().includes("background");
    }
    if (first.partnerMode === "doctors_companion") {
        return String(second.typeLine || "").toLowerCase().includes("doctor");
    }
    if (second.partnerMode === "doctors_companion") {
        return String(first.typeLine || "").toLowerCase().includes("doctor");
    }
    return false;
}

function canHavePartner(card) {
    return Boolean(card?.partnerMode);
}

function getDeckGroup(cardEntry) {
    const typeLine = cardEntry?.card?.typeLine || "";

    if (cardEntry?.isCommander) return "Commander";
    if (typeLine.includes("Land")) return "Lands";
    if (typeLine.includes("Creature")) return "Creatures";
    if (typeLine.includes("Instant")) return "Instants";
    if (typeLine.includes("Sorcery")) return "Sorceries";
    if (typeLine.includes("Artifact")) return "Artifacts";
    if (typeLine.includes("Enchantment")) return "Enchantments";
    if (typeLine.includes("Planeswalker")) return "Planeswalkers";
    return "Other";
}

function getColorGroup(entry) {
    const colors = entry?.card?.colorIdentity || [];
    if (entry?.isCommander) return "Commander";
    if (!colors.length) return "Colorless";
    if (colors.length > 1) return "Multicolor";
    return { W: "White", U: "Blue", B: "Black", R: "Red", G: "Green" }[colors[0]] || "Other";
}

function getManaValueGroup(entry) {
    if (entry?.isCommander) return "Commander";
    const value = Number(entry?.card?.manaValue ?? 0);
    return value >= 7 ? "7+" : String(Math.max(0, Math.floor(value)));
}

function sortEntries(entries, sortMode) {
    return [...entries].sort((a, b) => {
        if (sortMode === "manaValueAsc") {
            return Number(a?.card?.manaValue ?? 0) - Number(b?.card?.manaValue ?? 0)
                || (a?.card?.name || "").localeCompare(b?.card?.name || "");
        }
        if (sortMode === "manaValueDesc") {
            return Number(b?.card?.manaValue ?? 0) - Number(a?.card?.manaValue ?? 0)
                || (a?.card?.name || "").localeCompare(b?.card?.name || "");
        }
        if (sortMode === "quantity") {
            return (b.quantity || 0) - (a.quantity || 0)
                || (a?.card?.name || "").localeCompare(b?.card?.name || "");
        }
        if (sortMode === "added") {
            return String(b.addedAt || "").localeCompare(String(a.addedAt || ""));
        }
        return (a?.card?.name || "").localeCompare(b?.card?.name || "");
    });
}

function buildDeckGroups(cards, groupMode, sortMode) {
    if (groupMode === "none") {
        return [["All cards", sortEntries(cards, sortMode)]];
    }

    const groups = new Map();
    cards.forEach((entry) => {
        const group = groupMode === "manaValue"
            ? getManaValueGroup(entry)
            : groupMode === "color"
                ? getColorGroup(entry)
                : getDeckGroup(entry);
        if (!groups.has(group)) groups.set(group, []);
        groups.get(group).push(entry);
    });

    const preferredOrder = groupMode === "type"
        ? TYPE_GROUP_ORDER
        : groupMode === "manaValue"
            ? ["Commander", "0", "1", "2", "3", "4", "5", "6", "7+"]
            : ["Commander", "White", "Blue", "Black", "Red", "Green", "Multicolor", "Colorless", "Other"];

    return [...groups.entries()]
        .sort(([a], [b]) => preferredOrder.indexOf(a) - preferredOrder.indexOf(b))
        .map(([title, entries]) => [title, sortEntries(entries, sortMode)]);
}

function countDeckCards(cards) {
    return cards.reduce((sum, entry) => sum + (entry.quantity || 0), 0);
}

const MANA_COLORS = [
    ["W", "White", "#f4f1d0"],
    ["U", "Blue", "#6ab7e8"],
    ["B", "Black", "#8b87a1"],
    ["R", "Red", "#e8795f"],
    ["G", "Green", "#67b98a"],
    ["C", "Colorless", "#aab4c3"],
];

function expandDeckEntries(entries) {
    return entries.flatMap((entry) => (
        Array.from({ length: Math.max(0, entry.quantity || 0) }, (_, copyIndex) => ({
            ...entry,
            copyKey: `${entry.id}-${copyIndex}`,
        }))
    ));
}

function median(values) {
    if (!values.length) return 0;
    const ordered = [...values].sort((a, b) => a - b);
    const middle = Math.floor(ordered.length / 2);
    return ordered.length % 2
        ? ordered[middle]
        : (ordered[middle - 1] + ordered[middle]) / 2;
}

function combination(n, k) {
    if (k < 0 || k > n) return 0;
    const safeK = Math.min(k, n - k);
    let result = 1;
    for (let index = 1; index <= safeK; index += 1) {
        result = (result * (n - safeK + index)) / index;
    }
    return result;
}

function hypergeometricProbability(population, successes, draws, hits) {
    const denominator = combination(population, draws);
    if (!denominator) return 0;
    return (
        combination(successes, hits)
        * combination(population - successes, draws - hits)
        / denominator
    );
}

function manaSymbolsForCard(card) {
    const counts = { W: 0, U: 0, B: 0, R: 0, G: 0, C: 0 };
    const symbols = String(card?.manaCost || "").match(/\{[^}]+\}/g) || [];
    symbols.forEach((rawSymbol) => {
        const symbol = rawSymbol.slice(1, -1).toUpperCase();
        ["W", "U", "B", "R", "G"].forEach((color) => {
            if (symbol.split("/").includes(color)) counts[color] += 1;
        });
        if (symbol === "C") counts.C += 1;
    });
    return counts;
}

function producedColorsForCard(card) {
    const typeLine = String(card?.typeLine || "");
    const oracleText = String(card?.oracleText || "");
    const colors = new Set();
    const basicTypes = {
        Plains: "W",
        Island: "U",
        Swamp: "B",
        Mountain: "R",
        Forest: "G",
    };

    Object.entries(basicTypes).forEach(([landType, color]) => {
        if (typeLine.includes(landType)) colors.add(color);
    });
    oracleText.split(/[\n.]+/).forEach((sentence) => {
        if (!/\badd\b/i.test(sentence)) return;
        const symbols = sentence.match(/\{[WUBRGC]\}/gi) || [];
        symbols.forEach((symbol) => colors.add(symbol.slice(1, -1).toUpperCase()));
    });
    if (/add one mana of any color/i.test(oracleText)) {
        ["W", "U", "B", "R", "G"].forEach((color) => colors.add(color));
    }
    if (/add one mana of any type/i.test(oracleText)) {
        MANA_COLORS.forEach(([color]) => colors.add(color));
    }
    if (colors.size === 0 && typeLine.includes("Land")) colors.add("C");
    return [...colors];
}

function calculateDeckAnalytics(entries) {
    const copies = expandDeckEntries(entries);
    const lands = copies.filter((entry) => String(entry.card?.typeLine || "").includes("Land"));
    const nonlands = copies.filter((entry) => !String(entry.card?.typeLine || "").includes("Land"));
    const manaValues = copies.map((entry) => Number(entry.card?.manaValue || 0));
    const nonlandManaValues = nonlands.map((entry) => Number(entry.card?.manaValue || 0));
    const curve = Array.from({ length: 8 }, (_, index) => ({
        label: index === 7 ? "7+" : String(index),
        permanent: 0,
        spell: 0,
        cards: [],
    }));
    const typeCounts = {};
    const colorIdentityCounts = { W: 0, U: 0, B: 0, R: 0, G: 0, C: 0, M: 0 };
    const pipCounts = { W: 0, U: 0, B: 0, R: 0, G: 0, C: 0 };
    const sourceCounts = { W: 0, U: 0, B: 0, R: 0, G: 0, C: 0 };

    nonlands.forEach((entry) => {
        const value = Math.min(7, Math.max(0, Math.floor(Number(entry.card?.manaValue || 0))));
        const typeLine = String(entry.card?.typeLine || "");
        const isSpell = typeLine.includes("Instant") || typeLine.includes("Sorcery");
        curve[value][isSpell ? "spell" : "permanent"] += 1;
        curve[value].cards.push(entry);
    });

    copies.forEach((entry) => {
        const group = getDeckGroup(entry);
        typeCounts[group] = (typeCounts[group] || 0) + 1;

        const identity = entry.card?.colorIdentity || [];
        if (identity.length === 0) colorIdentityCounts.C += 1;
        else if (identity.length > 1) colorIdentityCounts.M += 1;
        else colorIdentityCounts[identity[0]] = (colorIdentityCounts[identity[0]] || 0) + 1;

        const cardPips = manaSymbolsForCard(entry.card);
        Object.keys(pipCounts).forEach((color) => {
            pipCounts[color] += cardPips[color];
        });
        if (String(entry.card?.typeLine || "").includes("Land")) {
            producedColorsForCard(entry.card).forEach((color) => {
                sourceCounts[color] += 1;
            });
        }
    });

    const openingHandSize = Math.min(7, copies.length);
    const landOdds = Array.from({ length: openingHandSize + 1 }, (_, landCount) => ({
        landCount,
        probability: hypergeometricProbability(copies.length, lands.length, openingHandSize, landCount),
    }));
    const average = manaValues.length
        ? manaValues.reduce((sum, value) => sum + value, 0) / manaValues.length
        : 0;
    const nonlandAverage = nonlandManaValues.length
        ? nonlandManaValues.reduce((sum, value) => sum + value, 0) / nonlandManaValues.length
        : 0;

    return {
        copies,
        lands,
        nonlands,
        curve,
        typeCounts,
        colorIdentityCounts,
        pipCounts,
        sourceCounts,
        landOdds,
        average,
        nonlandAverage,
        median: median(manaValues),
        nonlandMedian: median(nonlandManaValues),
        totalManaValue: manaValues.reduce((sum, value) => sum + value, 0),
    };
}

function drawSampleHand(copies, size = 7) {
    const pool = [...copies];
    for (let index = pool.length - 1; index > 0; index -= 1) {
        const swapIndex = Math.floor(Math.random() * (index + 1));
        [pool[index], pool[swapIndex]] = [pool[swapIndex], pool[index]];
    }
    return pool.slice(0, Math.min(size, pool.length));
}

function ManaCurveChart({ curve, selectedValue, onSelect }) {
    const maxTotal = Math.max(1, ...curve.map((bucket) => bucket.permanent + bucket.spell));

    return (
        <div className="analytics-chart" aria-label="Mana curve by mana value">
            <div className="mana-curve-bars">
                {curve.map((bucket) => {
                    const total = bucket.permanent + bucket.spell;
                    return (
                        <button
                            type="button"
                            className={`mana-curve-column ${selectedValue === bucket.label ? "selected" : ""}`}
                            key={bucket.label}
                            onClick={() => onSelect(selectedValue === bucket.label ? null : bucket.label)}
                            aria-pressed={selectedValue === bucket.label}
                        >
                            <span className="mana-curve-value">{total || ""}</span>
                            <div className="mana-curve-track">
                                <div
                                    className="mana-curve-segment permanent"
                                    style={{ height: `${(bucket.permanent / maxTotal) * 100}%` }}
                                    title={`${bucket.permanent} permanents`}
                                />
                                <div
                                    className="mana-curve-segment spell"
                                    style={{ height: `${(bucket.spell / maxTotal) * 100}%` }}
                                    title={`${bucket.spell} instants and sorceries`}
                                />
                            </div>
                            <strong>{bucket.label}</strong>
                        </button>
                    );
                })}
            </div>
            <div className="analytics-legend">
                <span><i className="legend-swatch permanent" />Permanents</span>
                <span><i className="legend-swatch spell" />Instants & sorceries</span>
            </div>
        </div>
    );
}

function DistributionRows({ values, labels, colors, total }) {
    const maximum = Math.max(1, ...Object.values(values));
    return (
        <div className="analytics-distribution">
            {Object.entries(values).map(([key, count]) => (
                <div className="distribution-row" key={key}>
                    <span className="distribution-label">
                        <i style={{ background: colors?.[key] || "#7e8da3" }} />
                        {labels?.[key] || key}
                    </span>
                    <div className="distribution-track">
                        <span
                            style={{
                                width: `${(count / maximum) * 100}%`,
                                background: colors?.[key] || "#7e8da3",
                            }}
                        />
                    </div>
                    <strong>{count}</strong>
                    {typeof total === "number" && (
                        <small>{total ? Math.round((count / total) * 100) : 0}%</small>
                    )}
                </div>
            ))}
        </div>
    );
}

function OpeningHandOdds({ odds }) {
    const maximum = Math.max(0.01, ...odds.map((item) => item.probability));
    return (
        <div className="opening-odds" aria-label="Opening hand land count probabilities">
            {odds.map((item) => (
                <div className="opening-odds-column" key={item.landCount}>
                    <span>{Math.round(item.probability * 100)}%</span>
                    <div>
                        <i style={{ height: `${(item.probability / maximum) * 100}%` }} />
                    </div>
                    <strong>{item.landCount}</strong>
                </div>
            ))}
        </div>
    );
}

function HypergeometricCalculator({ initialDeckSize, initialHits, onClose }) {
    const [deckSize, setDeckSize] = useState(Math.max(1, initialDeckSize || 100));
    const [cardsSeen, setCardsSeen] = useState(Math.min(7, Math.max(1, initialDeckSize || 100)));
    const [successes, setSuccesses] = useState(Math.min(initialHits || 1, Math.max(1, initialDeckSize || 100)));
    const [wanted, setWanted] = useState(1);
    const [mulligans, setMulligans] = useState(0);
    const [result, setResult] = useState(null);

    function calculate() {
        const population = Math.max(1, Math.floor(Number(deckSize) || 1));
        const draws = Math.min(population, Math.max(0, Math.floor(Number(cardsSeen) || 0)));
        const hitsInDeck = Math.min(population, Math.max(0, Math.floor(Number(successes) || 0)));
        const target = Math.max(0, Math.floor(Number(wanted) || 0));
        const retries = Math.min(20, Math.max(0, Math.floor(Number(mulligans) || 0)));
        const maximumHits = Math.min(draws, hitsInDeck);
        const exactly = hypergeometricProbability(population, hitsInDeck, draws, target);
        let atLeast = 0;
        let atMost = 0;
        for (let hitCount = 0; hitCount <= maximumHits; hitCount += 1) {
            const probability = hypergeometricProbability(
                population,
                hitsInDeck,
                draws,
                hitCount
            );
            if (hitCount >= target) atLeast += probability;
            if (hitCount <= target) atMost += probability;
        }
        const zero = hypergeometricProbability(population, hitsInDeck, draws, 0);
        const attempts = retries + 1;
        setDeckSize(population);
        setCardsSeen(draws);
        setSuccesses(hitsInDeck);
        setWanted(target);
        setMulligans(retries);
        setResult({
            exactly,
            atLeast,
            atMost,
            zero,
            attempts,
            findAcrossAttempts: 1 - ((1 - atLeast) ** attempts),
            missEveryAttempt: (1 - atLeast) ** attempts,
        });
    }

    const percentage = (value) => `${(value * 100).toFixed(2)}%`;

    return (
        <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
            <section
                className="deck-modal hypergeometric-modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="hypergeometric-title"
                onMouseDown={(event) => event.stopPropagation()}
            >
                <div className="deck-modal-header">
                    <div>
                        <div className="eyebrow">Probability tool</div>
                        <h2 id="hypergeometric-title">Hypergeometric calculator</h2>
                    </div>
                    <button type="button" className="modal-close" onClick={onClose} aria-label="Close">×</button>
                </div>
                <div className="deck-modal-body">
                    <div className="hypergeometric-fields">
                        <label>
                            <span>Size of the deck</span>
                            <input className="modal-input" type="number" min="1" value={deckSize} onChange={(event) => setDeckSize(event.target.value)} />
                        </label>
                        <label>
                            <span>Number of cards to look at</span>
                            <input className="modal-input" type="number" min="0" value={cardsSeen} onChange={(event) => setCardsSeen(event.target.value)} />
                        </label>
                        <label>
                            <span>How many matching cards are in the deck?</span>
                            <input className="modal-input" type="number" min="0" value={successes} onChange={(event) => setSuccesses(event.target.value)} />
                        </label>
                        <label>
                            <span>How many do you want to draw?</span>
                            <input className="modal-input" type="number" min="0" value={wanted} onChange={(event) => setWanted(event.target.value)} />
                        </label>
                        <label>
                            <span>How many mulligans do you want to take?</span>
                            <input className="modal-input" type="number" min="0" max="20" value={mulligans} onChange={(event) => setMulligans(event.target.value)} />
                        </label>
                    </div>

                    <button type="button" className="button-primary hypergeometric-calculate" onClick={calculate}>
                        Calculate
                    </button>

                    {result && (
                        <div className="hypergeometric-result" aria-live="polite">
                            <strong>Single hand</strong>
                            <span>Chance of drawing {wanted} or more: <b>{percentage(result.atLeast)}</b></span>
                            <span>Chance of drawing exactly {wanted}: <b>{percentage(result.exactly)}</b></span>
                            <span>Chance of drawing {wanted} or less: <b>{percentage(result.atMost)}</b></span>
                            <span>Chance of drawing zero: <b>{percentage(result.zero)}</b></span>
                            {result.attempts > 1 && (
                                <>
                                    <strong>Across {result.attempts} hands</strong>
                                    <span>
                                        Chance of finding {wanted} or more at least once:{" "}
                                        <b>{percentage(result.findAcrossAttempts)}</b>
                                    </span>
                                    <span>
                                        Chance every hand misses that goal:{" "}
                                        <b>{percentage(result.missEveryAttempt)}</b>
                                    </span>
                                </>
                            )}
                        </div>
                    )}

                    <p className="analytics-method-note">
                        Mulligan odds treat each full hand as an independent look and assume you mulligan whenever the
                        target is missed. London-mulligan bottoming decisions are not modeled.
                    </p>
                </div>
                <div className="deck-modal-footer">
                    <button type="button" className="button-secondary" onClick={onClose}>Close</button>
                </div>
            </section>
        </div>
    );
}

function DeckAnalytics({ entries, deckId, onLaunchGame }) {
    const analytics = useMemo(() => calculateDeckAnalytics(entries), [entries]);
    const [sampleHand, setSampleHand] = useState(() => drawSampleHand(analytics.copies));
    const [showCalculator, setShowCalculator] = useState(false);
    const [selectedManaValue, setSelectedManaValue] = useState(null);
    const [hoveredCurveCard, setHoveredCurveCard] = useState(null);
    const deckSignature = entries.map((entry) => `${entry.id}:${entry.quantity}`).join("|");

    useEffect(() => {
        setSampleHand(drawSampleHand(analytics.copies));
    }, [analytics.copies, deckSignature]);

    const typeLabels = TYPE_GROUP_ORDER
        .filter((type) => type !== "Commander" && analytics.typeCounts[type])
        .reduce((result, type) => ({ ...result, [type]: type }), {});
    const typeValues = Object.keys(typeLabels)
        .reduce((result, type) => ({ ...result, [type]: analytics.typeCounts[type] }), {});
    const colorLabels = {
        W: "White",
        U: "Blue",
        B: "Black",
        R: "Red",
        G: "Green",
        M: "Multicolor",
        C: "Colorless",
    };
    const colorStyles = {
        W: "#f4f1d0",
        U: "#6ab7e8",
        B: "#8b87a1",
        R: "#e8795f",
        G: "#67b98a",
        M: "#b87be4",
        C: "#aab4c3",
    };
    const landPercentage = analytics.copies.length
        ? Math.round((analytics.lands.length / analytics.copies.length) * 100)
        : 0;
    const twoToFourLandOdds = analytics.landOdds
        .filter((item) => item.landCount >= 2 && item.landCount <= 4)
        .reduce((sum, item) => sum + item.probability, 0);
    const highCurveCount = analytics.curve
        .slice(5)
        .reduce((sum, item) => sum + item.permanent + item.spell, 0);
    const diagnoses = [];
    const expectedOpeningLands = analytics.copies.length
        ? (Math.min(7, analytics.copies.length) * analytics.lands.length) / analytics.copies.length
        : 0;
    const selectedCurveCards = useMemo(() => {
        const bucket = analytics.curve.find((item) => item.label === selectedManaValue);
        if (!bucket) return [];
        const grouped = new Map();
        bucket.cards.forEach((entry) => {
            const key = entry.id || entry.card?.id || entry.card?.name;
            const existing = grouped.get(key);
            if (existing) existing.count += 1;
            else grouped.set(key, { entry, count: 1 });
        });
        return [...grouped.values()].sort((a, b) => (
            String(a.entry.card?.typeLine || "").localeCompare(String(b.entry.card?.typeLine || ""))
            || String(a.entry.card?.name || "").localeCompare(String(b.entry.card?.name || ""))
        ));
    }, [analytics.curve, selectedManaValue]);

    function drawAnotherCard() {
        const inHand = new Set(sampleHand.map((entry) => entry.copyKey));
        const remaining = analytics.copies.filter((entry) => !inHand.has(entry.copyKey));
        if (!remaining.length) return;
        const drawn = remaining[Math.floor(Math.random() * remaining.length)];
        setSampleHand((previous) => [...previous, drawn]);
    }
    if (analytics.copies.length < 7) {
        diagnoses.push("Add at least seven main-deck cards to make opening-hand analysis meaningful.");
    } else {
        diagnoses.push(
            `${Math.round(twoToFourLandOdds * 100)}% of opening hands contain two to four lands.`
        );
        if (landPercentage < 30) diagnoses.push("The land share is low; early land drops may be inconsistent.");
        if (landPercentage > 45) diagnoses.push("The land share is high; watch for mana-heavy opening hands.");
        if (analytics.nonlandAverage > 4) diagnoses.push("The nonland curve is top-heavy; consider more early plays or ramp.");
        if (highCurveCount > analytics.nonlands.length * 0.3) {
            diagnoses.push("More than 30% of nonlands cost five or more mana.");
        }
    }

    return (
        <section className="deck-analytics" aria-labelledby="deck-analytics-title">
            <div className="analytics-heading">
                <div>
                    <div className="eyebrow">Deck intelligence</div>
                    <h2 id="deck-analytics-title">Statistics & analytics</h2>
                    <p>Calculated from the current main deck. Commander, sideboard, and considering cards are excluded.</p>
                </div>
                <span className="analytics-live-badge">Updates with your list</span>
            </div>

            <div className="analytics-stat-grid">
                <div><span>Main deck</span><strong>{analytics.copies.length}</strong><small>cards</small></div>
                <div><span>Lands</span><strong>{analytics.lands.length}</strong><small>{landPercentage}% of deck</small></div>
                <div><span>Average MV</span><strong>{analytics.average.toFixed(2)}</strong><small>{analytics.nonlandAverage.toFixed(2)} without lands</small></div>
                <div><span>Median MV</span><strong>{analytics.median.toFixed(1)}</strong><small>{analytics.nonlandMedian.toFixed(1)} without lands</small></div>
                <div><span>Total MV</span><strong>{analytics.totalManaValue}</strong><small>main deck</small></div>
            </div>

            <div className="analytics-grid">
                <article className="analytics-panel analytics-panel-wide">
                    <div className="analytics-panel-heading">
                        <div><span>Curve</span><h3>Mana value</h3></div>
                        <small>Nonland cards</small>
                    </div>
                    <ManaCurveChart
                        curve={analytics.curve}
                        selectedValue={selectedManaValue}
                        onSelect={(value) => {
                            setSelectedManaValue(value);
                            setHoveredCurveCard(null);
                        }}
                    />
                    {selectedManaValue !== null ? (
                        <div className="mana-curve-drilldown">
                            <div className="mana-curve-card-list">
                                <strong>Mana value {selectedManaValue}</strong>
                                {selectedCurveCards.map(({ entry, count }) => (
                                    <button
                                        type="button"
                                        key={entry.id || entry.card?.id || entry.card?.name}
                                        onMouseEnter={() => setHoveredCurveCard(entry)}
                                        onFocus={() => setHoveredCurveCard(entry)}
                                    >
                                        <span>{count}× {entry.card?.name}</span>
                                        <small>{entry.card?.typeLine}</small>
                                    </button>
                                ))}
                            </div>
                            <div className="mana-curve-preview">
                                {hoveredCurveCard ? (
                                    <>
                                        {getCardImageUrl(hoveredCurveCard.card, "normal") ? (
                                            <img
                                                src={getCardImageUrl(hoveredCurveCard.card, "normal")}
                                                alt={hoveredCurveCard.card?.name || "Card"}
                                            />
                                        ) : null}
                                        <strong>{hoveredCurveCard.card?.name}</strong>
                                    </>
                                ) : (
                                    <span>Hover or focus a card to preview it.</span>
                                )}
                            </div>
                        </div>
                    ) : null}
                    <button
                        type="button"
                        className="button-secondary hypergeometric-open"
                        onClick={() => setShowCalculator(true)}
                    >
                        Hypergeometric calculator
                    </button>
                </article>

                <article className="analytics-panel">
                    <div className="analytics-panel-heading">
                        <div><span>Composition</span><h3>Card types</h3></div>
                    </div>
                    <DistributionRows
                        values={typeValues}
                        labels={typeLabels}
                        total={analytics.copies.length}
                    />
                </article>

                <article className="analytics-panel">
                    <div className="analytics-panel-heading">
                        <div><span>Identity</span><h3>Color distribution</h3></div>
                    </div>
                    <DistributionRows
                        values={analytics.colorIdentityCounts}
                        labels={colorLabels}
                        colors={colorStyles}
                        total={analytics.copies.length}
                    />
                </article>

                <article className="analytics-panel">
                    <div className="analytics-panel-heading">
                        <div><span>Demand</span><h3>Colored mana symbols</h3></div>
                    </div>
                    <DistributionRows
                        values={analytics.pipCounts}
                        labels={colorLabels}
                        colors={colorStyles}
                    />
                </article>

                <article className="analytics-panel">
                    <div className="analytics-panel-heading">
                        <div><span>Supply</span><h3>Land color sources</h3></div>
                        <small>A land can count for multiple colors</small>
                    </div>
                    <DistributionRows
                        values={analytics.sourceCounts}
                        labels={colorLabels}
                        colors={colorStyles}
                    />
                </article>

                <article className="analytics-panel analytics-panel-wide">
                    <div className="analytics-panel-heading">
                        <div><span>Consistency</span><h3>Opening hand land count</h3></div>
                        <small>Exact probability for a random seven-card hand</small>
                    </div>
                    <OpeningHandOdds odds={analytics.landOdds} />
                    <div className="opening-odds-axis">Number of lands in opening hand</div>
                    <p className="opening-land-expectation">
                        Expected lands in an opening hand: <strong>{expectedOpeningLands.toFixed(2)}</strong>
                    </p>
                </article>

                <article className="analytics-panel analytics-diagnosis">
                    <div className="analytics-panel-heading">
                        <div><span>Readout</span><h3>Deck diagnosis</h3></div>
                    </div>
                    <ul>
                        {diagnoses.map((diagnosis) => <li key={diagnosis}>{diagnosis}</li>)}
                    </ul>
                </article>
            </div>

            <article className="sample-hand-panel">
                <div className="analytics-panel-heading">
                    <div><span>Playtest</span><h3>Sample starting hand</h3></div>
                    <div className="sample-hand-actions">
                        <span>
                            {sampleHand.filter((entry) => String(entry.card?.typeLine || "").includes("Land")).length} lands
                        </span>
                        <button
                            type="button"
                            className="button-secondary"
                            onClick={() => setSampleHand(drawSampleHand(analytics.copies))}
                            disabled={analytics.copies.length === 0}
                        >
                            Deal a new hand
                        </button>
                        <button
                            type="button"
                            className="button-secondary"
                            onClick={drawAnotherCard}
                            disabled={sampleHand.length >= analytics.copies.length}
                        >
                            Draw
                        </button>
                        <button
                            type="button"
                            className="button-primary"
                            onClick={() => onLaunchGame?.("goldfish", deckId)}
                            disabled={!deckId}
                        >
                            Playtest · Goldfish
                        </button>
                        <button
                            type="button"
                            className="button-secondary"
                            onClick={() => onLaunchGame?.("simulation", deckId)}
                            disabled={!deckId}
                        >
                            Play vs computer
                        </button>
                    </div>
                </div>
                {sampleHand.length ? (
                    <div className="sample-hand-cards">
                        {sampleHand.map((entry) => {
                            const imageUrl = getCardImageUrl(entry.card, "normal");
                            return (
                                <div className="sample-hand-card" key={entry.copyKey}>
                                    {imageUrl ? (
                                        <img src={imageUrl} alt={entry.card?.name || "Card"} loading="lazy" />
                                    ) : (
                                        <div className="sample-hand-placeholder">No image</div>
                                    )}
                                    <strong>{entry.card?.name || "Unknown card"}</strong>
                                    <small>{entry.card?.manaCost || entry.card?.typeLine || "—"}</small>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="sample-hand-empty">Add cards to the main deck to deal a sample hand.</div>
                )}
                <p className="analytics-method-note">
                    Sample hands are drawn without replacement from the current main deck. Probability bars are exact
                    hypergeometric calculations, not simulated estimates.
                </p>
            </article>

            {showCalculator && (
                <HypergeometricCalculator
                    initialDeckSize={analytics.copies.length}
                    initialHits={analytics.lands.length}
                    onClose={() => setShowCalculator(false)}
                />
            )}
        </section>
    );
}

function SearchDropdown({ results, onAddCard, onHoverCard, onClose, isVisible }) {
    if (!isVisible) return null;

    return (
        <div className="builder-search-dropdown">
            <div className="builder-search-dropdown-header">
                <span>{results.length} result{results.length === 1 ? "" : "s"}</span>
                <button type="button" onClick={onClose} aria-label="Close search results">×</button>
            </div>
            {results.length === 0 ? (
                <div className="builder-search-empty">No results.</div>
            ) : (
                results.map((card) => {
                    const imageUrl = getCardImageUrl(card, "small");

                    return (
                        <div
                            key={card.uuid}
                            className="builder-search-result"
                            onMouseEnter={() => onHoverCard(card)}
                        >
                            <div className="builder-search-result-image">
                                {imageUrl ? (
                                    <img src={imageUrl} alt={card.name} className="builder-thumb" loading="lazy" />
                                ) : (
                                    <div className="builder-thumb builder-thumb-placeholder">No Image</div>
                                )}
                            </div>

                            <div className="builder-search-result-main">
                                <div className="builder-search-result-title">
                                    <strong>{card.name}</strong>
                                    <span className="builder-search-mv">MV {card.manaValue ?? "-"}</span>
                                </div>
                                <div className="builder-search-result-meta">
                                    {card.manaCost || "—"} • {card.typeLine || "—"}
                                </div>
                            </div>

                            <div className="builder-search-result-actions">
                                <button type="button" onClick={() => onAddCard(card)}>
                                    Add
                                </button>
                            </div>
                        </div>
                    );
                })
            )}
        </div>
    );
}

function CardPreviewPane({ card }) {
    if (!card) {
        return (
            <aside className="builder-preview-pane">
                <div className="builder-preview-empty">Hover a card to preview it.</div>
            </aside>
        );
    }

    const imageUrl = getCardImageUrl(card, "normal");

    return (
        <aside className="builder-preview-pane">
            {imageUrl ? (
                <img src={imageUrl} alt={card.name} className="builder-preview-image" />
            ) : (
                <div className="builder-preview-image builder-preview-placeholder">No Image</div>
            )}

            <div className="builder-preview-info">
                <h2>{card.name}</h2>
                <div className="builder-preview-type">{card.typeLine || "—"}</div>
                <div className="builder-preview-line">
                    <strong>Mana Cost:</strong> {card.manaCost || "—"}
                </div>
                <div className="builder-preview-line">
                    <strong>Set:</strong> {card.defaultSetName || "—"}{" "}
                    {card.defaultSetCode ? `(${card.defaultSetCode})` : ""}
                </div>

                <div className="builder-preview-oracle">
                    <strong>Oracle Text</strong>
                    <p>{card.oracleText || "—"}</p>
                </div>
            </div>
        </aside>
    );
}

function CardActionMenu({
    entry,
    onAddOne,
    onSetQuantity,
    onMove,
    onSetCommander,
    onRemove,
    onViewDetails,
}) {
    const [open, setOpen] = useState(false);
    const menuRef = useRef(null);

    useEffect(() => {
        if (!open) return undefined;
        function closeOnOutsideClick(event) {
            if (menuRef.current && !menuRef.current.contains(event.target)) setOpen(false);
        }
        function closeOnEscape(event) {
            if (event.key === "Escape") setOpen(false);
        }
        document.addEventListener("mousedown", closeOnOutsideClick);
        document.addEventListener("keydown", closeOnEscape);
        return () => {
            document.removeEventListener("mousedown", closeOnOutsideClick);
            document.removeEventListener("keydown", closeOnEscape);
        };
    }, [open]);

    function run(action) {
        setOpen(false);
        action();
    }

    return (
        <div className="builder-card-actions" ref={menuRef}>
            <button
                type="button"
                className="builder-card-menu-button"
                onClick={() => setOpen((value) => !value)}
                aria-haspopup="menu"
                aria-expanded={open}
                aria-label={`Options for ${entry.card?.name || "card"}`}
            >
                •••
            </button>
            {open && (
                <div className="builder-card-menu" role="menu">
                    <button type="button" onClick={() => run(onAddOne)}>Add one</button>
                    <button
                        type="button"
                        onClick={() => {
                            const next = window.prompt("Quantity", String(entry.quantity || 1));
                            if (next !== null) run(() => onSetQuantity(next));
                        }}
                    >
                        Set quantity…
                    </button>
                    <div className="builder-card-menu-divider" />
                    {entry.boardType !== "main" && (
                        <button type="button" onClick={() => run(() => onMove("main"))}>Move to main deck</button>
                    )}
                    {entry.boardType !== "sideboard" && !entry.isCommander && (
                        <button type="button" onClick={() => run(() => onMove("sideboard"))}>Move to sideboard</button>
                    )}
                    {entry.boardType !== "considering" && !entry.isCommander && (
                        <button type="button" onClick={() => run(() => onMove("considering"))}>Move to considering</button>
                    )}
                    {!entry.isCommander && isCommanderEligible(entry.card) && (
                        <button type="button" onClick={() => run(onSetCommander)}>Set as commander</button>
                    )}
                    <div className="builder-card-menu-divider" />
                    <button type="button" onClick={() => run(onViewDetails)}>View details</button>
                    <button
                        type="button"
                        onClick={() => run(() => navigator.clipboard?.writeText(entry.card?.name || ""))}
                    >
                        Copy card name
                    </button>
                    <button type="button" className="danger-menu-item" onClick={() => run(onRemove)}>Remove</button>
                </div>
            )}
        </div>
    );
}

function DeckGroupColumn({
    title,
    entries,
    viewMode,
    onHoverCard,
    onAddOne,
    onSetQuantity,
    onMove,
    onSetCommander,
    onRemoveCard,
}) {
    if (!entries.length) return null;

    return (
        <section className={`builder-group-column view-${viewMode}`}>
            <div className="builder-group-header">
                <h3>{title}</h3>
                <span>{entries.reduce((sum, entry) => sum + (entry.quantity || 0), 0)}</span>
            </div>

            <div className="builder-group-list">
                {entries.map((entry) => (
                    <div
                        key={entry.id}
                        className="builder-card-row"
                        onMouseEnter={() => onHoverCard(entry.card)}
                    >
                        {viewMode === "images" && (
                            <img
                                className="builder-card-tile-image"
                                src={getCardImageUrl(entry.card, "normal")}
                                alt={entry.card?.name || "Card"}
                                loading="lazy"
                            />
                        )}
                        <div className="builder-card-qty">{entry.quantity}</div>
                        <div className="builder-card-name">{entry.card?.name || "Unknown Card"}</div>
                        {viewMode !== "compact" && (
                            <div className="builder-card-cost">{entry.card?.manaCost || "—"}</div>
                        )}
                        <CardActionMenu
                            entry={entry}
                            onAddOne={() => onAddOne(entry)}
                            onSetQuantity={(quantity) => onSetQuantity(entry, quantity)}
                            onMove={(boardType) => onMove(entry, boardType)}
                            onSetCommander={() => onSetCommander(entry)}
                            onRemove={() => onRemoveCard(entry)}
                            onViewDetails={() => onHoverCard(entry.card)}
                        />
                    </div>
                ))}
            </div>
        </section>
    );
}

function DeckSettingsModal({ deck, onClose, onDeckUpdated }) {
    const [name, setName] = useState(deck.name || "");
    const [notes, setNotes] = useState(deck.notes || "");
    const [isPublic, setIsPublic] = useState(Boolean(deck.isPublic));
    const [folderName, setFolderName] = useState(deck.folderName || "");
    const [commanderBracket, setCommanderBracket] = useState(String(deck.commanderBracket || ""));
    const [format, setFormat] = useState(deck.format || "none");
    const [commanderQuery, setCommanderQuery] = useState("");
    const [results, setResults] = useState([]);
    const [commanderSelection, setCommanderSelection] = useState(
        () => (deck.cards || []).filter((entry) => entry.isCommander).map((entry) => entry.card).filter(Boolean)
    );
    const [busy, setBusy] = useState(false);
    const [commanderSearching, setCommanderSearching] = useState(false);
    const [message, setMessage] = useState("");
    const requiresCommander = COMMANDER_FORMATS.has(format);
    const allCommanderCards = commanderSelection;
    const primaryCommander = allCommanderCards[0] || null;
    const hasCommander = allCommanderCards.length > 0;
    const canAddCommander = requiresCommander && allCommanderCards.length < 2;
    const partnerExpected = allCommanderCards.length === 1 && canHavePartner(primaryCommander);
    const canSearchCommander = canAddCommander && (!hasCommander || partnerExpected);

    useEffect(() => {
        if (!canSearchCommander || commanderQuery.trim().length < 2) {
            setResults([]);
            return undefined;
        }
        const controller = new AbortController();
        const timer = window.setTimeout(async () => {
            setCommanderSearching(true);
            try {
                const response = await fetch(
                    `${API_BASE}/cards?q=${encodeURIComponent(commanderQuery.trim())}&limit=10&commanderOnly=true`,
                    { signal: controller.signal }
                );
                const payload = await response.json();
                if (!response.ok) throw new Error(payload?.error || "Commander search failed.");
                const excludedIds = new Set(allCommanderCards.map((card) => card.id));
                const candidates = (Array.isArray(payload) ? payload : [])
                    .filter((card) => !excludedIds.has(card.id))
                    .filter((card) => !primaryCommander || commandersAreCompatible(primaryCommander, card));
                setResults(candidates);
            } catch (searchError) {
                if (searchError.name !== "AbortError") setMessage(searchError.message);
            } finally {
                setCommanderSearching(false);
            }
        }, 250);
        return () => {
            window.clearTimeout(timer);
            controller.abort();
        };
    }, [allCommanderCards, canSearchCommander, commanderQuery, primaryCommander]);

    async function handleSave() {
        if (!name.trim()) {
            setMessage("Deck name is required.");
            return;
        }
        if (requiresCommander && !hasCommander) {
            setMessage("Choose a commander before saving this format.");
            return;
        }
        setBusy(true);
        setMessage("");
        try {
            const formatResponse = await fetch(`${API_BASE}/decks/${deck.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: name.trim(),
                    notes: notes.trim() || null,
                    isPublic,
                    folderName: folderName.trim() || null,
                    commanderBracket: commanderBracket || null,
                    format,
                }),
            });
            let updatedDeck = await formatResponse.json();
            if (!formatResponse.ok) throw new Error(updatedDeck?.error || "Could not update deck format.");

            if (requiresCommander || allCommanderCards.length) {
                const commanderResponse = await fetch(`${API_BASE}/decks/${deck.id}/commanders`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        commanderCardIds: allCommanderCards.map((card) => card.id),
                    }),
                });
                updatedDeck = await commanderResponse.json();
                if (!commanderResponse.ok) {
                    throw new Error(updatedDeck?.error || "Could not update commanders.");
                }
            }

            onDeckUpdated(updatedDeck);
            onClose();
        } catch (saveError) {
            setMessage(saveError.message || "Could not update deck settings.");
        } finally {
            setBusy(false);
        }
    }

    return (
        <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
            <section
                className="deck-modal deck-settings-modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="deck-settings-title"
                onMouseDown={(event) => event.stopPropagation()}
            >
                <div className="deck-modal-header">
                    <div>
                        <div className="eyebrow">Deck setup</div>
                        <h2 id="deck-settings-title">Deck settings</h2>
                    </div>
                    <button type="button" className="modal-close" onClick={onClose} aria-label="Close">×</button>
                </div>
                <div className="deck-modal-body">
                    <label className="field-label" htmlFor="builder-deck-name">Name</label>
                    <input
                        id="builder-deck-name"
                        className="modal-input"
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                    />
                    <label className="field-label" htmlFor="builder-deck-notes">Description</label>
                    <textarea
                        id="builder-deck-notes"
                        className="modal-input"
                        rows="3"
                        maxLength="500"
                        value={notes}
                        onChange={(event) => setNotes(event.target.value)}
                    />
                    <div className="deck-settings-field-row">
                        <div>
                            <span className="field-label">Visibility</span>
                            <div className="visibility-options">
                                <label><input type="radio" checked={isPublic} onChange={() => setIsPublic(true)} /> Visible</label>
                                <label><input type="radio" checked={!isPublic} onChange={() => setIsPublic(false)} /> Private</label>
                            </div>
                        </div>
                        <div>
                            <label className="field-label" htmlFor="builder-folder-name">Folder</label>
                            <input
                                id="builder-folder-name"
                                className="modal-input"
                                value={folderName}
                                onChange={(event) => setFolderName(event.target.value)}
                                placeholder="No folder"
                            />
                        </div>
                    </div>
                    <label className="field-label" htmlFor="builder-format">Format</label>
                    <select
                        id="builder-format"
                        className="modal-input"
                        value={format}
                        onChange={(event) => setFormat(event.target.value)}
                    >
                        {FORMAT_OPTIONS.map(([value, label]) => (
                            <option key={value} value={value}>{label}</option>
                        ))}
                    </select>

                    <fieldset className="commander-bracket-fieldset">
                        <legend className="field-label">Commander bracket</legend>
                        {[
                            ["", "Unsure / use estimate"],
                            ["1", "Bracket 1 — Exhibition"],
                            ["2", "Bracket 2 — Core"],
                            ["3", "Bracket 3 — Upgraded"],
                            ["4", "Bracket 4 — Optimized"],
                            ["5", "Bracket 5 — cEDH"],
                        ].map(([value, label]) => (
                            <label key={value || "auto"}>
                                <input
                                    type="radio"
                                    name="commander-bracket"
                                    value={value}
                                    checked={commanderBracket === value}
                                    onChange={(event) => setCommanderBracket(event.target.value)}
                                />
                                {label}
                            </label>
                        ))}
                        <div className="bracket-estimate">
                            <strong>
                                Estimated bracket: {deck.estimatedCommanderBracket?.bracket || "—"}
                            </strong>
                            <span>
                                {(deck.estimatedCommanderBracket?.reasons || []).join("; ")}.
                                This estimate is advisory and will improve as synergy data grows.
                            </span>
                        </div>
                    </fieldset>

                    {requiresCommander && (
                        <div className="missing-commander-picker">
                            {!hasCommander && (
                                <div className="missing-commander-callout">
                                    This format requires a commander. Choose one to finish updating the deck.
                                </div>
                            )}

                            {allCommanderCards.length > 0 && (
                                <div className="selected-commanders">
                                    <span className="field-label">
                                        Commander{allCommanderCards.length === 1 ? "" : "s"}
                                    </span>
                                    {allCommanderCards.map((card) => (
                                            <div className="selected-commander-row" key={card.id}>
                                                <img src={getCardImageUrl(card, "small")} alt="" loading="lazy" />
                                                <span>
                                                    <strong>{card.name}</strong>
                                                    <small>
                                                        {card.partnerMode
                                                            ? card.partnerMode === "named"
                                                                ? `Partners with ${card.partnerName}`
                                                                : "Supports a paired commander"
                                                            : card.typeLine}
                                                    </small>
                                                </span>
                                                <button
                                                    type="button"
                                                    onClick={() => {
                                                        setCommanderSelection((cards) => (
                                                            cards.filter((selected) => selected.id !== card.id)
                                                        ));
                                                        setCommanderQuery("");
                                                        setResults([]);
                                                    }}
                                                >
                                                    Change
                                                </button>
                                            </div>
                                    ))}
                                    <small className="commander-search-hint">
                                        Replaced commanders are removed from the deck; every other card stays unchanged.
                                    </small>
                                </div>
                            )}

                            {canAddCommander && !canSearchCommander && (
                                <div className="missing-commander-callout">
                                    {primaryCommander.name} cannot be paired with a second commander.
                                </div>
                            )}

                            {canSearchCommander && (
                                <>
                                    <div className={`missing-commander-callout ${partnerExpected ? "partner" : ""}`}>
                                        {partnerExpected
                                            ? `${primaryCommander.name} supports a paired commander. Search for the partner below.`
                                            : hasCommander
                                                ? "This commander does not advertise a supported partner pairing."
                                                : "Search for an eligible commander."}
                                    </div>
                                    <label className="field-label" htmlFor="builder-commander">
                                        {hasCommander ? "Add paired commander" : "Commander"}
                                    </label>
                                <input
                                    id="builder-commander"
                                    className="modal-input"
                                    value={commanderQuery}
                                    onChange={(event) => setCommanderQuery(event.target.value)}
                                        placeholder={partnerExpected
                                            ? `Search for ${primaryCommander.partnerName || "a compatible partner"}…`
                                            : "Search legendary creatures…"}
                                />
                                    {commanderQuery.trim().length >= 2 && !commanderSearching && results.length === 0 && (
                                        <div className="commander-search-hint">
                                            No compatible commanders found for this search.
                                        </div>
                                    )}
                                    {commanderSearching && (
                                        <div className="commander-search-hint">Searching compatible commanders…</div>
                                    )}
                                    {results.length > 0 && (
                                        <div className="settings-commander-results">
                                            {results.map((card) => (
                                                <button
                                                    key={card.uuid}
                                                    type="button"
                                                    onClick={() => {
                                                        setCommanderSelection((cards) => [...cards, card]);
                                                        setCommanderQuery("");
                                                        setResults([]);
                                                    }}
                                                >
                                                    <img src={getCardImageUrl(card, "small")} alt="" loading="lazy" />
                                                    <span>
                                                        <strong>{card.name}</strong>
                                                        <small>
                                                            {card.partnerMode === "named"
                                                                ? `Partner with ${card.partnerName}`
                                                                : card.typeLine}
                                                        </small>
                                                    </span>
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    )}
                    {message && <div className="modal-error">{message}</div>}
                </div>
                <div className="deck-modal-footer">
                    <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
                    <button type="button" className="button-primary" onClick={handleSave} disabled={busy}>
                        {busy ? "Saving…" : "Save changes"}
                    </button>
                </div>
            </section>
        </div>
    );
}

function BulkEditModal({ deck, initialBoard, onClose, onDeckUpdated }) {
    const startingBoard = initialBoard === "command" ? "main" : initialBoard;
    const serializeBoard = (selectedBoard) => (deck.cards || [])
        .filter((entry) => entry.boardType === selectedBoard && !entry.isCommander)
        .sort((first, second) => String(first.card?.name || "").localeCompare(String(second.card?.name || "")))
        .map((entry) => `${entry.quantity} ${entry.card?.name || "Unknown card"}`)
        .join("\n");
    const [boardType, setBoardType] = useState(startingBoard);
    const [mode, setMode] = useState("replace");
    const [text, setText] = useState(() => serializeBoard(startingBoard));
    const [swapTarget, setSwapTarget] = useState(
        BOARD_OPTIONS.find(([value]) => value !== initialBoard)?.[0] || "considering"
    );
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState("");
    const [issues, setIssues] = useState([]);

    async function handleImport() {
        setBusy(true);
        setMessage("");
        setIssues([]);
        try {
            const response = await fetch(`${API_BASE}/decks/${deck.id}/cards/bulk`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ boardType, mode, text }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload?.error || `Import failed (${response.status}).`);
            onDeckUpdated(payload.deck);
            setIssues(payload.issues || []);
            setMessage(
                `Imported ${payload.importedQuantity} cards from ${payload.resolvedLines} lines into ${
                    BOARD_OPTIONS.find(([value]) => value === boardType)?.[1] || boardType
                }.`
            );
        } catch (importError) {
            setMessage(importError.message || "Bulk import failed.");
        } finally {
            setBusy(false);
        }
    }

    async function handleSwapBoard() {
        if (boardType === swapTarget) return;
        setBusy(true);
        setMessage("");
        try {
            const response = await fetch(`${API_BASE}/decks/${deck.id}/boards/swap`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ sourceBoard: boardType, targetBoard: swapTarget }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload?.error || `Board move failed (${response.status}).`);
            onDeckUpdated(payload.deck);
            setMessage(`Moved ${payload.movedQuantity} cards to ${
                BOARD_OPTIONS.find(([value]) => value === swapTarget)?.[1] || swapTarget
            }.`);
        } catch (swapError) {
            setMessage(swapError.message || "Board move failed.");
        } finally {
            setBusy(false);
        }
    }

    function handleFile(event) {
        const file = event.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            setText(typeof reader.result === "string" ? reader.result : "");
            setMessage(`Loaded ${file.name}. Review the list, then import it.`);
        };
        reader.onerror = () => setMessage(`Could not read ${file.name}.`);
        reader.readAsText(file);
    }

    return (
        <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
            <section
                className="deck-modal bulk-modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="bulk-edit-title"
                onMouseDown={(event) => event.stopPropagation()}
            >
                <div className="deck-modal-header">
                    <div>
                        <div className="eyebrow">Deck tools</div>
                        <h2 id="bulk-edit-title">Bulk edit cards</h2>
                    </div>
                    <button type="button" className="modal-close" onClick={onClose} aria-label="Close">×</button>
                </div>

                <div className="deck-modal-body">
                    <div className="bulk-controls">
                        <div>
                            <label className="field-label" htmlFor="bulk-board">Board</label>
                            <select
                                id="bulk-board"
                                className="modal-input"
                                value={boardType}
                                onChange={(event) => {
                                    const nextBoard = event.target.value;
                                    setBoardType(nextBoard);
                                    setText(serializeBoard(nextBoard));
                                    setMode("replace");
                                    setMessage("");
                                    setIssues([]);
                                }}
                            >
                                {BOARD_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                            </select>
                        </div>
                        <div>
                            <span className="field-label">Import behavior</span>
                            <div className="visibility-options">
                                <label>
                                    <input
                                        type="radio"
                                        checked={mode === "replace"}
                                        onChange={() => {
                                            setMode("replace");
                                            setText(serializeBoard(boardType));
                                        }}
                                    />
                                    Save as complete board
                                </label>
                                <label>
                                    <input
                                        type="radio"
                                        checked={mode === "merge"}
                                        onChange={() => {
                                            setMode("merge");
                                            setText("");
                                        }}
                                    />
                                    Only add listed quantities
                                </label>
                            </div>
                        </div>
                    </div>

                    <div className="bulk-list-heading">
                        <div>
                            <label className="field-label" htmlFor="bulk-list">Card list</label>
                            <small>
                                Existing cards are included below. Append cards at the bottom, or press Cmd+A / Ctrl+A to replace the entire list.
                            </small>
                        </div>
                        <label className="file-import-button">
                            Import from file
                            <input type="file" accept=".txt,.dec,.dek,.csv,text/plain" onChange={handleFile} />
                        </label>
                    </div>
                    <textarea
                        id="bulk-list"
                        className="modal-input bulk-textarea"
                        value={text}
                        onChange={(event) => setText(event.target.value)}
                        placeholder={"1 Sol Ring (TDC) 106\n1 Arcane Signet (DSC) 92\n4 Island (ZEN) 236"}
                    />

                    <div className="board-move-panel">
                        <div>
                            <strong>Move an entire board</strong>
                            <small>Cards already in the destination are merged by quantity.</small>
                        </div>
                        <div className="board-move-actions">
                            <span>Move to</span>
                            <select className="modal-input" value={swapTarget} onChange={(event) => setSwapTarget(event.target.value)}>
                                {BOARD_OPTIONS.filter(([value]) => value !== boardType).map(([value, label]) => (
                                    <option key={value} value={value}>{label}</option>
                                ))}
                            </select>
                            <button type="button" className="button-secondary" onClick={handleSwapBoard} disabled={busy}>Move board</button>
                        </div>
                    </div>

                    {message && <div className="bulk-message">{message}</div>}
                    {issues.length > 0 && (
                        <div className="bulk-issues">
                            <strong>{issues.length} line{issues.length === 1 ? "" : "s"} need attention</strong>
                            {issues.map((issue) => (
                                <div key={`${issue.line}-${issue.text}`}>Line {issue.line}: {issue.error}</div>
                            ))}
                        </div>
                    )}
                </div>

                <div className="deck-modal-footer">
                    <button type="button" className="button-secondary" onClick={onClose}>Done</button>
                    <button type="button" className="button-primary" onClick={handleImport} disabled={busy || !text.trim()}>
                        {busy ? "Working…" : "Import cards"}
                    </button>
                </div>
            </section>
        </div>
    );
}

function DeckBuilder({ deckId, onBack, onLaunchGame }) {
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState([]);
    const [currentDeck, setCurrentDeck] = useState(null);
    const [hoveredCard, setHoveredCard] = useState(null);
    const [error, setError] = useState("");
    const [isSearching, setIsSearching] = useState(false);
    const [isLoadingDeck, setIsLoadingDeck] = useState(true);
    const [showSearchDropdown, setShowSearchDropdown] = useState(false);
    const [selectedBoard, setSelectedBoard] = useState("main");
    const [showBulkEdit, setShowBulkEdit] = useState(false);
    const [showDeckSettings, setShowDeckSettings] = useState(false);
    const [viewMode, setViewMode] = useState("text");
    const [groupMode, setGroupMode] = useState("type");
    const [sortMode, setSortMode] = useState("name");
    const searchAreaRef = useRef(null);

    const boardCards = useMemo(() => {
        const cards = currentDeck?.cards || [];
        if (selectedBoard === "main") {
            return cards.filter((entry) => entry.boardType === "main" || entry.boardType === "command");
        }
        return cards.filter((entry) => entry.boardType === selectedBoard);
    }, [currentDeck, selectedBoard]);

    const groupedCards = useMemo(
        () => buildDeckGroups(boardCards, groupMode, sortMode),
        [boardCards, groupMode, sortMode]
    );

    const analyticsCards = useMemo(
        () => (currentDeck?.cards || []).filter((entry) => entry.boardType === "main" && !entry.isCommander),
        [currentDeck]
    );

    const totalCards = useMemo(() => {
        return countDeckCards(currentDeck?.cards || []);
    }, [currentDeck]);

    useEffect(() => {
        async function loadDeck() {
            setIsLoadingDeck(true);
            setError("");
            try {
                await refreshDeck(deckId);
            } catch (err) {
                setError(err instanceof Error ? err.message : "Failed to load this deck.");
            } finally {
                setIsLoadingDeck(false);
            }
        }
        if (deckId) loadDeck();
        else setIsLoadingDeck(false);
    }, [deckId]);

    useEffect(() => {
        function handleOutsideClick(event) {
            if (
                showSearchDropdown
                && searchAreaRef.current
                && !searchAreaRef.current.contains(event.target)
            ) {
                setShowSearchDropdown(false);
            }
        }
        function handleEscape(event) {
            if (event.key === "Escape") setShowSearchDropdown(false);
        }
        document.addEventListener("mousedown", handleOutsideClick);
        document.addEventListener("keydown", handleEscape);
        return () => {
            document.removeEventListener("mousedown", handleOutsideClick);
            document.removeEventListener("keydown", handleEscape);
        };
    }, [showSearchDropdown]);

    async function handleSearch() {
        const trimmed = searchQuery.trim();
        if (!trimmed) {
            setSearchResults([]);
            setShowSearchDropdown(false);
            return;
        }

        setIsSearching(true);
        setError("");

        try {
            const response = await fetch(
                `${API_BASE}/cards?q=${encodeURIComponent(trimmed)}&limit=25`
            );

            if (!response.ok) {
                throw new Error(`Search failed with status ${response.status}`);
            }

            const data = await response.json();
            setSearchResults(Array.isArray(data) ? data : []);
            setShowSearchDropdown(true);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to search cards.");
        } finally {
            setIsSearching(false);
        }
    }

    async function refreshDeck(deckId) {
        const response = await fetch(`${API_BASE}/decks/${deckId}`);
        if (!response.ok) {
            throw new Error(`Failed to refresh deck ${deckId}`);
        }
        const data = await response.json();
        setCurrentDeck(data);
    }

    async function handleAddCard(card) {
        if (!currentDeck) {
            setError("Create a deck before adding cards.");
            return;
        }

        setError("");

        try {
            const response = await fetch(`${API_BASE}/decks/${currentDeck.id}/cards`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    cardId: card.id,
                    quantity: 1,
                    boardType: selectedBoard === "command" ? "main" : selectedBoard,
                    isCommander: false,
                }),
            });

            if (!response.ok) {
                throw new Error(`Add card failed with status ${response.status}`);
            }

            await refreshDeck(currentDeck.id);
            setHoveredCard(card);
            setShowSearchDropdown(false);
            setSearchResults([]);
            setSearchQuery("");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to add card.");
        }
    }

    async function updateCardEntry(entry, changes) {
        setError("");
        try {
            const response = await fetch(
                `${API_BASE}/decks/${currentDeck.id}/cards/${entry.id}`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(changes),
                }
            );
            const payload = await response.json();
            if (!response.ok) throw new Error(payload?.error || `Card update failed (${response.status}).`);
            setCurrentDeck(payload);
        } catch (updateError) {
            setError(updateError.message || "Failed to update card.");
        }
    }

    async function handleAddOne(entry) {
        await updateCardEntry(entry, { quantity: (entry.quantity || 0) + 1 });
    }

    async function handleSetQuantity(entry, rawQuantity) {
        const quantity = Number(rawQuantity);
        if (!Number.isInteger(quantity) || quantity < 1) {
            setError("Quantity must be a whole number of at least 1.");
            return;
        }
        await updateCardEntry(entry, { quantity });
    }

    async function handleMoveCard(entry, boardType) {
        await updateCardEntry(entry, { boardType, isCommander: false });
        if (entry.boardType === selectedBoard && boardType !== selectedBoard) {
            setHoveredCard(null);
        }
    }

    async function handleSetCommander(entry) {
        await updateCardEntry(entry, { boardType: "command", isCommander: true, quantity: 1 });
    }

    async function handleRemoveCard(entry) {
        if (!currentDeck) return;

        setError("");

        try {
            const response = await fetch(
                `${API_BASE}/decks/${currentDeck.id}/cards/${entry.id}`,
                {
                    method: "DELETE",
                }
            );

            if (!response.ok) {
                throw new Error(`Remove card failed with status ${response.status}`);
            }

            await refreshDeck(currentDeck.id);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to remove card.");
        }
    }

    if (isLoadingDeck) {
        return <div className="builder-loading">Loading deck…</div>;
    }

    if (!currentDeck) {
        return (
            <div className="builder-loading">
                <h2>Deck not found</h2>
                <p>{error || "Choose a deck from your library."}</p>
                <button type="button" onClick={onBack}>Back to your decks</button>
            </div>
        );
    }

    const commanderNames = currentDeck.commanderNames || [];

    return (
        <div className="builder-page">
            <section className="builder-deck-hero">
                <button type="button" className="builder-back-button" onClick={onBack}>← Your decks</button>
                <div className="builder-hero-content">
                    <div>
                        <div className="eyebrow">Deck builder</div>
                        <h1>{currentDeck.name}</h1>
                        <div className="builder-deck-meta">
                            <span className="format-pill">{currentDeck.format}</span>
                            <span>{totalCards} cards</span>
                            <span>{currentDeck.isPublic ? "Public" : "Private"}</span>
                        </div>
                    </div>
                    <div className="builder-commander-summary">
                        <span>{commanderNames.length ? "Commander" : "Format"}</span>
                        <strong>{commanderNames.join(" + ") || currentDeck.format}</strong>
                        <button type="button" onClick={() => setShowDeckSettings(true)}>
                            Deck settings
                        </button>
                    </div>
                </div>
                {currentDeck.notes && <p className="builder-description">{currentDeck.notes}</p>}
            </section>

            {currentDeck.requiresCommander && !currentDeck.hasRequiredCommander && (
                <button
                    type="button"
                    className="missing-commander-banner"
                    onClick={() => setShowDeckSettings(true)}
                >
                    <span>
                        <strong>This deck needs a commander</strong>
                        Choose an eligible legendary card to complete the {currentDeck.format} setup.
                    </span>
                    <span>Add commander →</span>
                </button>
            )}

            <div className="builder-header">
                <div className="builder-header-left">
                    <div>
                        <div className="eyebrow">Add cards</div>
                        <h2>Find the next piece</h2>
                        <p>Search the full card catalog and add cards directly to this list.</p>
                    </div>
                </div>
                <div className="builder-header-right">
                    <div className="builder-search-row" ref={searchAreaRef}>
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(event) => {
                                const value = event.target.value;
                                setSearchQuery(value);
                                if (!value.trim()) {
                                    setSearchResults([]);
                                    setShowSearchDropdown(false);
                                }
                            }}
                            onKeyDown={(event) => {
                                if (event.key === "Enter") handleSearch();
                                if (event.key === "Escape") setShowSearchDropdown(false);
                            }}
                            onFocus={() => {
                                if (searchResults.length > 0) setShowSearchDropdown(true);
                            }}
                            placeholder="Find and add cards..."
                            className="builder-input builder-search-input"
                        />
                        <button type="button" onClick={handleSearch}>
                            Search
                        </button>

                        <SearchDropdown
                            results={searchResults}
                            onAddCard={handleAddCard}
                            onHoverCard={setHoveredCard}
                            onClose={() => setShowSearchDropdown(false)}
                            isVisible={showSearchDropdown}
                        />
                    </div>
                </div>
            </div>

            {error ? <div className="error-box">{error}</div> : null}
            {isSearching ? <div className="muted-text">Searching…</div> : null}

            <div className="board-toolbar">
                <div className="board-tabs" role="tablist" aria-label="Deck boards">
                    {BOARD_OPTIONS.slice(0, 3).map(([value, label]) => (
                        <button
                            key={value}
                            type="button"
                            role="tab"
                            aria-selected={selectedBoard === value}
                            className={selectedBoard === value ? "active" : ""}
                            onClick={() => setSelectedBoard(value)}
                        >
                            {label}
                            <span>{(currentDeck.cards || []).filter((entry) => entry.boardType === value).reduce((sum, entry) => sum + entry.quantity, 0)}</span>
                        </button>
                    ))}
                    <select
                        className="board-other-select"
                        value={BOARD_OPTIONS.slice(3).some(([value]) => value === selectedBoard) ? selectedBoard : ""}
                        onChange={(event) => event.target.value && setSelectedBoard(event.target.value)}
                        aria-label="Other deck board"
                    >
                        <option value="">Other boards…</option>
                        {BOARD_OPTIONS.slice(3).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                    </select>
                </div>
                <button type="button" className="button-secondary" onClick={() => setShowBulkEdit(true)}>Bulk edit / Import</button>
            </div>

            <div className="builder-layout">
                <CardPreviewPane card={hoveredCard} />

                <main className="builder-main">
                    <div className="builder-toolbar">
                        <label className="builder-toolbar-item">
                            <strong>View</strong>
                            <select value={viewMode} onChange={(event) => setViewMode(event.target.value)}>
                                <option value="text">Text</option>
                                <option value="images">Images</option>
                                <option value="compact">Compact</option>
                            </select>
                        </label>
                        <label className="builder-toolbar-item">
                            <strong>Group</strong>
                            <select value={groupMode} onChange={(event) => setGroupMode(event.target.value)}>
                                <option value="type">Type</option>
                                <option value="manaValueAsc">Mana value — low to high</option>
                                <option value="manaValueDesc">Mana value — high to low</option>
                                <option value="color">Color identity</option>
                                <option value="none">No grouping</option>
                            </select>
                        </label>
                        <label className="builder-toolbar-item">
                            <strong>Sort</strong>
                            <select value={sortMode} onChange={(event) => setSortMode(event.target.value)}>
                                <option value="name">Name</option>
                                <option value="manaValue">Mana value</option>
                                <option value="quantity">Quantity</option>
                                <option value="added">Recently added</option>
                            </select>
                        </label>
                    </div>

                    <div className={`builder-groups-grid view-${viewMode} group-${groupMode}`}>
                        {groupedCards.map(([groupName, entries]) => (
                            <DeckGroupColumn
                                key={groupName}
                                title={groupName}
                                entries={entries}
                                viewMode={viewMode}
                                onHoverCard={setHoveredCard}
                                onAddOne={handleAddOne}
                                onSetQuantity={handleSetQuantity}
                                onMove={handleMoveCard}
                                onSetCommander={handleSetCommander}
                                onRemoveCard={handleRemoveCard}
                            />
                        ))}
                    </div>
                </main>
            </div>

            <DeckAnalytics
                entries={analyticsCards}
                deckId={deckId}
                onLaunchGame={onLaunchGame}
            />

            {showBulkEdit && (
                <BulkEditModal
                    deck={currentDeck}
                    initialBoard={selectedBoard}
                    onClose={() => setShowBulkEdit(false)}
                    onDeckUpdated={setCurrentDeck}
                />
            )}
            {showDeckSettings && (
                <DeckSettingsModal
                    deck={currentDeck}
                    onClose={() => setShowDeckSettings(false)}
                    onDeckUpdated={setCurrentDeck}
                />
            )}
        </div>
    );
}

export default DeckBuilder;
