import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";

const isMtgSubpath = window.location.pathname.startsWith("/mtg");
const API_BASE = isMtgSubpath ? "/mtg/api" : "/api";
const SOCKET_PATH = isMtgSubpath ? "/mtg/socket.io" : "/socket.io";
const COMMANDER_FORMATS = new Set([
    "commander",
    "brawl",
    "standard-brawl",
    "duel-commander",
    "pauper-edh",
    "oathbreaker",
]);
const DEFAULT_PLAYMAT_LAYOUT = {
    leftRail: 154,
    hand: 210,
    opponent: 240,
};
const PLAYMAT_LAYOUT_KEY = "mtg-sandbox-playmat-layout";
const PLAYMAT_CANVAS_KEY = "mtg-sandbox-playmat-canvas";
const PLAYMAT_CANVAS_WIDTH = 2200;
const PLAYMAT_CANVAS_HEIGHT = 1200;
const DEFAULT_CANVAS_VIEW = {
    scale: 0.8,
    x: 24,
    y: 24,
};

function CardBack({ sleeveStyle = "classic", label = "Card back" }) {
    return (
        <div
            className={`playmat-card-back sleeve-${sleeveStyle}`}
            role="img"
            aria-label={label}
        >
            <div className="playmat-card-back-frame">
                <span>MAGIC</span>
                <small>THE GATHERING</small>
            </div>
        </div>
    );
}

function cardImage(cardInstance) {
    return (
        cardInstance?.card?.imageNormal ||
        cardInstance?.card?.imageSmall ||
        null
    );
}

function battlefieldCardStyle(card) {
    const x = Number(card?.battlefieldX ?? 40);
    const y = Number(card?.battlefieldY ?? 40);
    const rotation = Number(card?.rotationDeg ?? 0);

    return {
        position: "absolute",
        left: `${x}px`,
        top: `${y}px`,
        transform: `rotate(${rotation}deg)`,
        transformOrigin: "center center",
        width: "120px",
        cursor: "grab",
        userSelect: "none",
        touchAction: "none",
    };
}

function zoneArray(player, zoneName) {
    return player?.zones?.[zoneName] || [];
}

function libraryCount(player) {
    return player?.zones?.libraryCount || 0;
}

const TYPE_ORDER = [
    "Land",
    "Creature",
    "Artifact",
    "Enchantment",
    "Planeswalker",
    "Instant",
    "Sorcery",
    "Battle",
];

function cardTypeSortValue(card) {
    const typeLine = String(card?.card?.typeLine || "");
    const index = TYPE_ORDER.findIndex((type) => typeLine.includes(type));
    return `${String(index < 0 ? TYPE_ORDER.length : index).padStart(2, "0")}:${typeLine}`;
}

function BattlefieldCard({
    card,
    sleeveStyle,
    isSelected,
    onSelect,
    onDragStart,
    onContextMenu,
    onHover,
}) {
    const imageUrl = cardImage(card);
    const showingBack = card?.isFaceDown || card?.displayFace === "back";

    return (
        <div
            className="playmat-battlefield-card"
            style={battlefieldCardStyle(card)}
            onPointerDown={(event) => onDragStart(event, card)}
            onClick={(event) => onSelect(card, event)}
            onContextMenu={(event) => onContextMenu(event, card)}
            onMouseEnter={(event) => onHover(card, event)}
            onMouseMove={(event) => onHover(card, event)}
            onMouseLeave={() => onHover(null)}
            title={card?.card?.name || "Card"}
        >
            <div
                style={{
                    border: isSelected ? "2px solid #60a5fa" : "1px solid #334155",
                    borderRadius: "10px",
                    overflow: "hidden",
                    background: "#111827",
                    boxShadow: isSelected
                        ? "0 0 0 2px rgba(96,165,250,0.25)"
                        : "0 4px 12px rgba(0,0,0,0.35)",
                }}
            >
                {showingBack ? (
                    <CardBack
                        sleeveStyle={sleeveStyle}
                        label={`${card?.card?.name || "Card"} face down`}
                    />
                ) : imageUrl ? (
                    <img
                        src={imageUrl}
                        alt={card?.card?.name || "Card"}
                        style={{ display: "block", width: "100%" }}
                        draggable={false}
                    />
                ) : (
                    <div
                        style={{
                            aspectRatio: "63 / 88",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            padding: "12px",
                            color: "#cbd5e1",
                            fontSize: "0.8rem",
                            textAlign: "center",
                        }}
                    >
                        {card?.card?.name || "Unknown Card"}
                    </div>
                )}

            </div>
        </div>
    );
}

function opponentCardStyle(card, index) {
    const x = Number(card?.battlefieldX);
    const y = Number(card?.battlefieldY);
    const hasPosition = Number.isFinite(x) && Number.isFinite(y);

    return {
        left: hasPosition ? `${Math.max(2, Math.min(88, x / 12))}%` : `${8 + ((index * 9) % 72)}%`,
        top: hasPosition ? `${Math.max(18, Math.min(62, y / 8))}%` : `${30 + ((index % 2) * 12)}%`,
        transform: `translate(-50%, -50%) rotate(${180 + Number(card?.rotationDeg || 0)}deg)`,
    };
}

function OpponentBoards({ players, onCardClick, onCardHover }) {
    if (!players.length) {
        return (
            <section className="playmat-opponent-boards empty">
                <span>Waiting for an opponent…</span>
            </section>
        );
    }

    return (
        <section
            className="playmat-opponent-boards"
            aria-label="Opponent tables"
            style={{ "--opponent-count": players.length }}
        >
            {players.map((player) => {
                const battlefield = zoneArray(player, "battlefield");
                const handCount = zoneArray(player, "hand").length;
                return (
                    <article className="playmat-opponent-board" key={player.id}>
                        <header>
                            <strong>Player {player.seatNumber}</strong>
                            <div className="playmat-opponent-stats">
                                <span>Hand {handCount}</span>
                                <span>Field {battlefield.length}</span>
                                <span>GY {zoneArray(player, "graveyard").length}</span>
                                <span>Exile {zoneArray(player, "exile").length}</span>
                            </div>
                        </header>
                        <div className="playmat-opponent-surface">
                            <div className="playmat-opponent-hand" aria-label={`${handCount} hidden cards in hand`}>
                                {Array.from({ length: Math.min(handCount, 10) }).map((_, index) => (
                                    <div key={index} style={{ marginLeft: index ? "-30px" : 0 }}>
                                        <CardBack sleeveStyle={player.sleeveStyle} />
                                    </div>
                                ))}
                                {handCount > 10 ? <strong>+{handCount - 10}</strong> : null}
                            </div>
                            <div className="playmat-opponent-command">
                                {zoneArray(player, "command").map((card) => (
                                    <button
                                        type="button"
                                        key={card.id}
                                        onClick={(event) => onCardClick(event, card, "command", true)}
                                        onContextMenu={(event) => onCardClick(event, card, "command", true)}
                                        onMouseEnter={(event) => onCardHover(card, event, Boolean(card?.isFaceDown || card?.displayFace === "back"))}
                                        onMouseMove={(event) => onCardHover(card, event, Boolean(card?.isFaceDown || card?.displayFace === "back"))}
                                        onMouseLeave={() => onCardHover(null)}
                                    >
                                        {card?.isFaceDown || card?.displayFace === "back" ? (
                                            <CardBack sleeveStyle={player.sleeveStyle} />
                                        ) : cardImage(card) ? (
                                            <img src={cardImage(card)} alt={card?.card?.name || "Commander"} />
                                        ) : (
                                            <span>{card?.card?.name || "Commander"}</span>
                                        )}
                                    </button>
                                ))}
                            </div>
                            {battlefield.map((card, index) => (
                                <button
                                    type="button"
                                    className={`playmat-opponent-card ${card?.isTapped ? "tapped" : ""}`}
                                    key={card.id}
                                    style={opponentCardStyle(card, index)}
                                    onClick={(event) => onCardClick(event, card, "battlefield", true)}
                                    onContextMenu={(event) => onCardClick(event, card, "battlefield", true)}
                                    onMouseEnter={(event) => onCardHover(card, event, Boolean(card?.isFaceDown || card?.displayFace === "back"))}
                                    onMouseMove={(event) => onCardHover(card, event, Boolean(card?.isFaceDown || card?.displayFace === "back"))}
                                    onMouseLeave={() => onCardHover(null)}
                                >
                                    {card?.isFaceDown || card?.displayFace === "back" ? (
                                        <CardBack sleeveStyle={player.sleeveStyle} />
                                    ) : cardImage(card) ? (
                                        <img src={cardImage(card)} alt={card?.card?.name || "Card"} />
                                    ) : (
                                        <span>{card?.card?.name || "Card"}</span>
                                    )}
                                </button>
                            ))}
                            <div className="playmat-opponent-library" aria-label={`${libraryCount(player)} cards in library`}>
                                <CardBack sleeveStyle={player.sleeveStyle} />
                                <strong>{libraryCount(player)}</strong>
                            </div>
                            {!battlefield.length ? (
                                <div className="playmat-opponent-empty">Player {player.seatNumber}'s battlefield</div>
                            ) : null}
                        </div>
                    </article>
                );
            })}
        </section>
    );
}

function CommandZone({ cards, sleeveStyle, onCardClick, onCardHover }) {
    return (
        <section className="playmat-command-zone" aria-label="Command Zone">
            <div>
                <strong>Command Zone</strong>
                <span>{cards.length} commander{cards.length === 1 ? "" : "s"}</span>
            </div>
            <div className="playmat-command-cards">
                {cards.length ? cards.map((card) => (
                    <button
                        type="button"
                        className="playmat-command-card"
                        key={card.id}
                        onClick={(event) => onCardClick(event, card, "command")}
                        onContextMenu={(event) => onCardClick(event, card, "command")}
                        onMouseEnter={(event) => onCardHover(card, event)}
                        onMouseMove={(event) => onCardHover(card, event)}
                        onMouseLeave={() => onCardHover(null)}
                        title="Hover to preview · click for actions"
                    >
                        {card?.isFaceDown || card?.displayFace === "back" ? (
                            <CardBack sleeveStyle={sleeveStyle} />
                        ) : cardImage(card) ? (
                            <img src={cardImage(card)} alt={card?.card?.name || "Commander"} />
                        ) : (
                            <span>{card?.card?.name || "Commander"}</span>
                        )}
                    </button>
                )) : <em>No commander in the Command Zone</em>}
            </div>
        </section>
    );
}

function HandFan({
    cards,
    onCardClick,
    onCardHover,
    onDragStart,
    onDragEnd,
    selectedCardId,
    highlightedCardIds,
}) {
    return (
        <div
            style={{
                display: "flex",
                gap: "10px",
                overflowX: "auto",
                padding: "8px 4px 12px",
            }}
        >
            {cards.map((card) => {
                const imageUrl = cardImage(card);
                const isSelected = selectedCardId === card.id;
                const isNew = highlightedCardIds.has(card.id);

                return (
                    <div
                        key={card.id}
                        className="playmat-hand-card"
                        draggable
                        onDragStart={(event) => onDragStart(event, card)}
                        onDragEnd={onDragEnd}
                        style={{
                            minWidth: "112px",
                            width: "112px",
                            border: isNew
                                ? "3px solid #facc15"
                                : isSelected ? "2px solid #60a5fa" : "1px solid #334155",
                            borderRadius: "10px",
                            background: "#111827",
                            overflow: "hidden",
                            boxShadow: isNew
                                ? "0 0 0 3px rgba(250,204,21,0.24), 0 4px 16px rgba(0,0,0,0.4)"
                                : "0 4px 12px rgba(0,0,0,0.3)",
                            animation: isNew ? "new-card-glow 1.1s ease-in-out infinite alternate" : "none",
                        }}
                        onClick={(event) => onCardClick(event, card, "hand")}
                        onContextMenu={(event) => onCardClick(event, card, "hand")}
                        onMouseEnter={(event) => onCardHover(card, event)}
                        onMouseMove={(event) => onCardHover(card, event)}
                        onMouseLeave={() => onCardHover(null)}
                    >
                        {imageUrl ? (
                            <img
                                src={imageUrl}
                                alt={card?.card?.name || "Card"}
                                style={{ display: "block", width: "100%" }}
                                draggable={false}
                            />
                        ) : (
                            <div
                                style={{
                                    aspectRatio: "63 / 88",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    padding: "10px",
                                    color: "#cbd5e1",
                                    fontSize: "0.8rem",
                                    textAlign: "center",
                                }}
                            >
                                {card?.card?.name || "Unknown Card"}
                            </div>
                        )}

                    </div>
                );
            })}
        </div>
    );
}

function ZonePanel({ player, onDrawOne, onOpenTools, onDropToZone }) {
    const dropZone = (event, zone) => {
        event.preventDefault();
        const cardId = Number(event.dataTransfer.getData("application/x-mtg-card-id"));
        if (cardId) onDropToZone(cardId, zone);
    };
    return (
        <aside className="playmat-zone-rail">
            <div className="playmat-player-chip">
                <strong>{`Player ${player?.seatNumber ?? "?"}`}</strong>
                <span>{player?.playerType || "human"}</span>
            </div>

            <div className="playmat-zone-counts">
                <div><span>Library</span><strong>{libraryCount(player)}</strong></div>
                <div><span>Hand</span><strong>{zoneArray(player, "hand").length}</strong></div>
                <div><span>Battlefield</span><strong>{zoneArray(player, "battlefield").length}</strong></div>
                {[
                    ["graveyard", "Graveyard"],
                    ["exile", "Exile"],
                    ["command", "Command"],
                ].map(([zone, label]) => (
                    <div
                        key={zone}
                        className="playmat-zone-drop"
                        onDragOver={(event) => event.preventDefault()}
                        onDrop={(event) => dropZone(event, zone)}
                        title={`Drop a card here to move it to ${label}`}
                    >
                        <span>{label}</span>
                        <strong>{zoneArray(player, zone).length}</strong>
                    </div>
                ))}
            </div>

            <button type="button" onClick={onDrawOne}>Draw</button>
            <button type="button" onClick={onOpenTools}>Tools</button>
        </aside>
    );
}

function HoverCardPreview({ preview }) {
    if (!preview?.card) return null;
    const card = preview.card;
    const concealed = Boolean(preview.concealed);
    const imageUrl = concealed ? null : cardImage(card);

    return (
        <aside
            className="playmat-hover-preview"
            style={{ left: preview.x, top: preview.y }}
            aria-live="polite"
        >
            <div className="playmat-hover-preview-image">
                {concealed ? (
                    <CardBack label="Face-down card" />
                ) : imageUrl ? (
                    <img src={imageUrl} alt={card?.card?.name || "Card"} />
                ) : (
                    <span>{card?.card?.name || "Unknown card"}</span>
                )}
            </div>
            <div className="playmat-hover-preview-copy">
                <strong>{concealed ? "Face-down card" : card?.card?.name || "Unknown card"}</strong>
                {!concealed ? (
                    <>
                        <div className="playmat-hover-meta">
                            <span>{card?.card?.manaCost || "No mana cost"}</span>
                            {card?.card?.manaValue != null ? <small>MV {card.card.manaValue}</small> : null}
                        </div>
                        <small>{card?.card?.typeLine || "—"}</small>
                        <p>{card?.card?.oracleText || "No Oracle text."}</p>
                    </>
                ) : (
                    <p>This card's identity is hidden.</p>
                )}
                <em>Click for actions</em>
            </div>
        </aside>
    );
}

function AdvancedInteractionPanel({
    players,
    activePlayer,
    selectedCard,
    peekCards,
    onPeek,
    onDrawFromPlayer,
    onTransfer,
    onSwap,
    onClose,
}) {
    const otherPlayers = players.filter((player) => player.id !== activePlayer?.id);
    const exchangeCards = players.flatMap((player) => (
        ["hand", "graveyard"].flatMap((zone) => (
            zoneArray(player, zone).map((card) => ({
                ...card,
                ownerSeat: player.seatNumber,
                exchangeZone: zone,
            }))
        ))
    )).filter((card) => card.id !== selectedCard?.id && !card.isCommander);
    const [sourcePlayerId, setSourcePlayerId] = useState(String(otherPlayers[0]?.id || ""));
    const [targetPlayerId, setTargetPlayerId] = useState(String(otherPlayers[0]?.id || ""));
    const [targetZone, setTargetZone] = useState("hand");
    const [swapCardId, setSwapCardId] = useState("");

    return (
        <div className="playmat-tools-backdrop" onMouseDown={onClose}>
            <section className="playmat-tools-panel" onMouseDown={(event) => event.stopPropagation()}>
                <header>
                    <div>
                        <strong>Deck & player tools</strong>
                        <span>Manual controls for card-driven interactions</span>
                    </div>
                    <button type="button" onClick={onClose}>Close</button>
                </header>

                <div className="playmat-tools-grid">
                    <div>
                        <h3>Peek at your Library</h3>
                        <button type="button" onClick={() => onPeek(5)}>Peek at top 5</button>
                        <div className="playmat-peek-cards">
                            {peekCards.map((card, index) => (
                                <div key={card.id}>
                                    <span>{index + 1}</span>
                                    {cardImage(card) ? (
                                        <img src={cardImage(card)} alt={card?.card?.name || "Card"} />
                                    ) : null}
                                    <strong>{card?.card?.name || "Unknown card"}</strong>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div>
                        <h3>Draw from another Library</h3>
                        <select
                            value={sourcePlayerId}
                            onChange={(event) => setSourcePlayerId(event.target.value)}
                        >
                            {otherPlayers.map((player) => (
                                <option key={player.id} value={player.id}>Player {player.seatNumber}</option>
                            ))}
                        </select>
                        <button
                            type="button"
                            disabled={!sourcePlayerId}
                            onClick={() => onDrawFromPlayer(Number(sourcePlayerId))}
                        >
                            Draw their top card
                        </button>
                    </div>

                    <div>
                        <h3>Give the selected card</h3>
                        <p>{selectedCard?.card?.name || "Select a visible card first."}</p>
                        <select
                            value={targetPlayerId}
                            onChange={(event) => setTargetPlayerId(event.target.value)}
                        >
                            {otherPlayers.map((player) => (
                                <option key={player.id} value={player.id}>Player {player.seatNumber}</option>
                            ))}
                        </select>
                        <select value={targetZone} onChange={(event) => setTargetZone(event.target.value)}>
                            <option value="hand">Hand</option>
                            <option value="graveyard">Graveyard</option>
                            <option value="exile">Exile</option>
                            <option value="battlefield">Battlefield</option>
                        </select>
                        <button
                            type="button"
                            disabled={!selectedCard || !targetPlayerId}
                            onClick={() => onTransfer(Number(targetPlayerId), targetZone)}
                        >
                            Transfer card
                        </button>
                    </div>

                    <div>
                        <h3>Swap cards</h3>
                        <p>Swap the selected card with a card in a hand or graveyard.</p>
                        <select value={swapCardId} onChange={(event) => setSwapCardId(event.target.value)}>
                            <option value="">Choose the other card…</option>
                            {exchangeCards.map((card) => (
                                <option key={card.id} value={card.id}>
                                    P{card.ownerSeat} {card.exchangeZone}: {card?.card?.name || "Unknown"}
                                </option>
                            ))}
                        </select>
                        <button
                            type="button"
                            disabled={!selectedCard || !swapCardId}
                            onClick={() => onSwap(Number(swapCardId))}
                        >
                            Swap cards
                        </button>
                    </div>
                </div>
            </section>
        </div>
    );
}

const LIBRARY_CONDITIONS = [
    ["land", "Land"],
    ["nonland", "Nonland card"],
    ["creature", "Creature"],
    ["instant", "Instant"],
    ["sorcery", "Sorcery"],
    ["instant-or-sorcery", "Instant or sorcery"],
    ["artifact", "Artifact"],
    ["enchantment", "Enchantment"],
    ["planeswalker", "Planeswalker"],
];

function LibraryActionModal({
    cards,
    onInspect,
    onScry,
    onExileUntil,
    onClose,
}) {
    const [mode, setMode] = useState("scry");
    const [count, setCount] = useState(1);
    const [condition, setCondition] = useState("land");
    const [placements, setPlacements] = useState({});
    const [orderedIds, setOrderedIds] = useState([]);
    const [busy, setBusy] = useState(false);

    useEffect(() => {
        setOrderedIds(cards.map((card) => card.id));
        setPlacements(Object.fromEntries(cards.map((card) => [card.id, "top"])));
    }, [cards]);

    const orderedCards = orderedIds
        .map((id) => cards.find((card) => card.id === id))
        .filter(Boolean);

    function move(cardId, direction) {
        setOrderedIds((ids) => {
            const index = ids.indexOf(cardId);
            const nextIndex = index + direction;
            if (index < 0 || nextIndex < 0 || nextIndex >= ids.length) return ids;
            const next = [...ids];
            [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
            return next;
        });
    }

    async function inspect() {
        setBusy(true);
        try {
            await onInspect(mode === "scry" ? Number(count) : null, mode === "scry-until" ? condition : null);
        } finally {
            setBusy(false);
        }
    }

    async function applyScry() {
        const topIds = orderedIds.filter((id) => placements[id] !== "bottom");
        const bottomIds = orderedIds.filter((id) => placements[id] === "bottom");
        setBusy(true);
        try {
            await onScry(orderedIds, topIds, bottomIds);
            onClose();
        } finally {
            setBusy(false);
        }
    }

    async function exileUntil() {
        if (!window.confirm(`Exile cards from the top through the first ${LIBRARY_CONDITIONS.find(([value]) => value === condition)?.[1].toLowerCase()}?`)) return;
        setBusy(true);
        try {
            await onExileUntil(condition);
            onClose();
        } finally {
            setBusy(false);
        }
    }

    return (
        <div className="playmat-tools-backdrop" onMouseDown={onClose}>
            <section className="library-action-modal" onMouseDown={(event) => event.stopPropagation()}>
                <header>
                    <div>
                        <strong>Library actions</strong>
                        <span>Inspect privately, then apply the result to the shared game state.</span>
                    </div>
                    <button type="button" onClick={onClose}>Close</button>
                </header>
                <div className="library-action-controls">
                    <label>
                        Action
                        <select value={mode} onChange={(event) => setMode(event.target.value)}>
                            <option value="scry">Scry a number of cards</option>
                            <option value="scry-until">Scry until a card type</option>
                            <option value="exile-until">Exile until a card type</option>
                        </select>
                    </label>
                    {mode === "scry" ? (
                        <label>
                            Cards
                            <input type="number" min="1" max="20" value={count} onChange={(event) => setCount(event.target.value)} />
                        </label>
                    ) : (
                        <label>
                            Stop at
                            <select value={condition} onChange={(event) => setCondition(event.target.value)}>
                                {LIBRARY_CONDITIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                            </select>
                        </label>
                    )}
                    {mode === "exile-until" ? (
                        <button type="button" className="danger-button" disabled={busy} onClick={exileUntil}>
                            Exile until…
                        </button>
                    ) : (
                        <button type="button" disabled={busy} onClick={inspect}>
                            {busy ? "Inspecting…" : mode === "scry" ? `Look at top ${count}` : "Find matching card"}
                        </button>
                    )}
                </div>
                {mode !== "exile-until" && cards.length > 0 && (
                    <>
                        <p className="library-action-help">
                            Arrange the cards, mark each for the top or bottom, then apply the scry.
                            Other players see only the counts—not the private card identities.
                        </p>
                        <div className="library-scry-list">
                            {orderedCards.map((card, index) => (
                                <div key={card.id}>
                                    <span className="library-scry-position">{index + 1}</span>
                                    {cardImage(card) ? <img src={cardImage(card)} alt="" /> : null}
                                    <span>
                                        <strong>{card?.card?.name || "Unknown card"}</strong>
                                        <small>{card?.card?.typeLine || ""}</small>
                                    </span>
                                    <div className="library-order-buttons">
                                        <button type="button" onClick={() => move(card.id, -1)} disabled={index === 0} aria-label="Move earlier">↑</button>
                                        <button type="button" onClick={() => move(card.id, 1)} disabled={index === orderedCards.length - 1} aria-label="Move later">↓</button>
                                    </div>
                                    <select
                                        value={placements[card.id] || "top"}
                                        onChange={(event) => setPlacements((current) => ({ ...current, [card.id]: event.target.value }))}
                                    >
                                        <option value="top">Top</option>
                                        <option value="bottom">Bottom</option>
                                    </select>
                                </div>
                            ))}
                        </div>
                        <footer>
                            <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
                            <button type="button" className="button-primary" disabled={busy} onClick={applyScry}>
                                {busy ? "Applying…" : "Apply scry"}
                            </button>
                        </footer>
                    </>
                )}
            </section>
        </div>
    );
}

function RuleViolationModal({ violation, ruleset, onAllow, onClose }) {
    if (!violation) return null;
    const canOverride = ruleset !== "tournament";
    return (
        <div className="playmat-tools-backdrop" onMouseDown={onClose}>
            <section className="rule-violation-modal" role="alertdialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}>
                <div className="rule-violation-icon">!</div>
                <div>
                    <div className="eyebrow">{ruleset === "tournament" ? "Illegal tournament action" : "Rules warning"}</div>
                    <h2>{violation.title || "That action is against the rules"}</h2>
                    <p>{violation.message || "The requested action is not legal in the current game state."}</p>
                    {violation.rule ? <blockquote>{violation.rule}</blockquote> : null}
                    {violation.citation ? <strong>{violation.citation}</strong> : null}
                </div>
                <footer>
                    <button type="button" className="button-secondary" onClick={onClose}>
                        {canOverride ? "Cancel" : "Close"}
                    </button>
                    {canOverride ? (
                        <button type="button" className="danger-button" onClick={onAllow}>Allow anyway</button>
                    ) : null}
                </footer>
            </section>
        </div>
    );
}

export default function PlayMat({
    gameId,
    activePlayerId = null,
    participantToken = "",
    onGameComplete = null,
    onExitGame = null,
}) {
    const preferences = useMemo(() => {
        try {
            return JSON.parse(window.localStorage.getItem("mtg-sandbox-preferences") || "{}");
        } catch {
            return {};
        }
    }, []);
    const [gameState, setGameState] = useState(null);
    const [selectedCard, setSelectedCard] = useState(null);
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [handSort, setHandSort] = useState("type");
    const [highlightedCardIds, setHighlightedCardIds] = useState(new Set());
    const [toolsOpen, setToolsOpen] = useState(false);
    const [peekCards, setPeekCards] = useState([]);
    const [deckMenuOpen, setDeckMenuOpen] = useState(false);
    const [libraryActionsOpen, setLibraryActionsOpen] = useState(false);
    const [hotkeyHelpOpen, setHotkeyHelpOpen] = useState(false);
    const [contextMenu, setContextMenu] = useState(null);
    const [hoveredCard, setHoveredCard] = useState(null);
    const [hoverPreview, setHoverPreview] = useState(null);
    const [selectedCardIds, setSelectedCardIds] = useState(new Set());
    const [selectionBox, setSelectionBox] = useState(null);
    const [randomizerOpen, setRandomizerOpen] = useState(false);
    const [customDieSides, setCustomDieSides] = useState(6);
    const [randomCount, setRandomCount] = useState(1);
    const [draggingHandCardId, setDraggingHandCardId] = useState(null);
    const [ruleViolation, setRuleViolation] = useState(null);
    const [layout, setLayout] = useState(() => {
        try {
            return {
                ...DEFAULT_PLAYMAT_LAYOUT,
                ...JSON.parse(window.localStorage.getItem(PLAYMAT_LAYOUT_KEY) || "{}"),
            };
        } catch {
            return DEFAULT_PLAYMAT_LAYOUT;
        }
    });
    const [canvasView, setCanvasView] = useState(() => {
        try {
            return {
                ...DEFAULT_CANVAS_VIEW,
                ...JSON.parse(window.localStorage.getItem(PLAYMAT_CANVAS_KEY) || "{}"),
            };
        } catch {
            return DEFAULT_CANVAS_VIEW;
        }
    });

    const socketRef = useRef(null);
    const battlefieldRef = useRef(null);
    const dragRef = useRef(null);
    const panRef = useRef(null);
    const canvasViewRef = useRef(canvasView);
    const previousHandIdsRef = useRef(null);
    const highlightTimerRef = useRef(null);
    const selectionRef = useRef(null);
    const requestedAiTurnRef = useRef("");
    const layoutResizeRef = useRef(null);

    const activePlayer = useMemo(() => {
        if (!gameState?.players?.length) return null;
        if (activePlayerId) {
            return gameState.players.find((p) => p.id === activePlayerId) || gameState.players[0];
        }
        return gameState.players[0];
    }, [gameState, activePlayerId]);

    const battlefieldCards = useMemo(() => {
        return zoneArray(activePlayer, "battlefield");
    }, [activePlayer]);
    const opponentPlayers = useMemo(
        () => (gameState?.players || []).filter((player) => player.id !== activePlayer?.id),
        [activePlayer?.id, gameState?.players]
    );

    useEffect(() => {
        window.localStorage.setItem(PLAYMAT_LAYOUT_KEY, JSON.stringify(layout));
    }, [layout]);

    useEffect(() => {
        canvasViewRef.current = canvasView;
        window.localStorage.setItem(PLAYMAT_CANVAS_KEY, JSON.stringify(canvasView));
    }, [canvasView]);

    const beginLayoutResize = useCallback((kind, event) => {
        event.preventDefault();
        event.stopPropagation();
        layoutResizeRef.current = {
            kind,
            startX: event.clientX,
            startY: event.clientY,
            startLayout: layout,
        };
        document.body.classList.add("playmat-is-resizing");
    }, [layout]);

    useEffect(() => {
        const clamp = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));
        const handleLayoutPointerMove = (event) => {
            const resize = layoutResizeRef.current;
            if (!resize) return;
            const deltaX = event.clientX - resize.startX;
            const deltaY = event.clientY - resize.startY;

            setLayout((current) => {
                if (resize.kind === "left") {
                    return { ...current, leftRail: clamp(resize.startLayout.leftRail + deltaX, 104, 320) };
                }
                if (resize.kind === "hand") {
                    return { ...current, hand: clamp(resize.startLayout.hand - deltaY, 130, 430) };
                }
                if (resize.kind === "opponent") {
                    return { ...current, opponent: clamp(resize.startLayout.opponent + deltaY, 110, 440) };
                }
                return current;
            });
        };
        const handleLayoutPointerUp = () => {
            if (!layoutResizeRef.current) return;
            layoutResizeRef.current = null;
            document.body.classList.remove("playmat-is-resizing");
        };

        window.addEventListener("pointermove", handleLayoutPointerMove);
        window.addEventListener("pointerup", handleLayoutPointerUp);
        return () => {
            window.removeEventListener("pointermove", handleLayoutPointerMove);
            window.removeEventListener("pointerup", handleLayoutPointerUp);
            document.body.classList.remove("playmat-is-resizing");
        };
    }, []);

    const handCards = useMemo(() => {
        const cards = [...zoneArray(activePlayer, "hand")];
        return cards.sort((first, second) => {
            if (handSort === "name") {
                return String(first?.card?.name || "").localeCompare(second?.card?.name || "");
            }
            if (handSort === "mana-asc" || handSort === "mana-desc") {
                const manaDifference = Number(first?.card?.manaValue ?? 0)
                    - Number(second?.card?.manaValue ?? 0);
                const directedDifference = handSort === "mana-desc"
                    ? -manaDifference
                    : manaDifference;
                return directedDifference || String(first?.card?.name || "")
                    .localeCompare(second?.card?.name || "");
            }
            return cardTypeSortValue(first).localeCompare(cardTypeSortValue(second))
                || Number(first?.card?.manaValue ?? 0) - Number(second?.card?.manaValue ?? 0)
                || String(first?.card?.name || "").localeCompare(second?.card?.name || "");
        });
    }, [activePlayer, handSort]);

    useEffect(() => {
        const currentIds = new Set(handCards.map((card) => card.id));
        if (previousHandIdsRef.current === null) {
            previousHandIdsRef.current = currentIds;
            return undefined;
        }

        const newIds = [...currentIds].filter((id) => !previousHandIdsRef.current.has(id));
        previousHandIdsRef.current = currentIds;
        if (!newIds.length) return undefined;

        if (preferences.animateCards === false) return undefined;
        setHighlightedCardIds(new Set(newIds));
        window.clearTimeout(highlightTimerRef.current);
        highlightTimerRef.current = window.setTimeout(() => {
            setHighlightedCardIds(new Set());
        }, 5000);
        return undefined;
    }, [handCards, preferences.animateCards]);

    useEffect(() => () => {
        window.clearTimeout(highlightTimerRef.current);
    }, []);

    const commandCards = useMemo(() => {
        return zoneArray(activePlayer, "command");
    }, [activePlayer]);

    const usesCommandZone = COMMANDER_FORMATS.has(
        String(gameState?.game?.format || "").toLowerCase()
    );
    const isMyTurn = Boolean(
        activePlayer
        && activePlayer.seatNumber === gameState?.game?.activeSeatNumber
    );

    const fetchState = useCallback(async () => {
        if (!gameId) return;
        setIsLoading(true);
        setError("");

        try {
            const response = await fetch(`${API_BASE}/games/${gameId}/state`);
            if (!response.ok) {
                throw new Error(`Failed to fetch game state: ${response.status}`);
            }
            const data = await response.json();
            setGameState(data);
        } catch (err) {
            setError(err?.message || "Failed to fetch game state.");
        } finally {
            setIsLoading(false);
        }
    }, [gameId]);

    useEffect(() => {
        fetchState();
    }, [fetchState]);

    useEffect(() => {
        if (gameState?.game?.status !== "completed" || !onGameComplete) return undefined;
        const timeoutId = window.setTimeout(onGameComplete, 1200);
        return () => window.clearTimeout(timeoutId);
    }, [gameState?.game?.status, onGameComplete]);

    useEffect(() => {
        if (!gameId) return;

        const socket = io({
            path: SOCKET_PATH,
            transports: ["websocket", "polling"],
        });

        socketRef.current = socket;

        socket.on("connect", () => {
            socket.emit("game:join", { gameId });
        });

        socket.on("game:state_updated", (payload) => {
            if (payload?.gameId === gameId && payload?.state) {
                setGameState(payload.state);
            }
        });

        socket.on("game:error", (payload) => {
            setError(payload?.message || "Game socket error.");
        });

        return () => {
            socket.disconnect();
            socketRef.current = null;
        };
    }, [gameId]);

    const postAction = useCallback(
        async (action) => {
            setError("");
            const response = await fetch(`${API_BASE}/games/${gameId}/actions`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action }),
            });

            if (!response.ok) {
                let detail = `Action failed with status ${response.status}`;
                try {
                    const json = await response.json();
                    if (response.status === 409 && json?.ruleViolation) {
                        setRuleViolation({ ...json.ruleViolation, action });
                        return { blockedByRules: true };
                    }
                    if (json?.message) detail = json.message;
                } catch {
                    // ignore json parse failure
                }
                throw new Error(detail);
            }

            const payload = await response.json();
            if (payload?.state) {
                setGameState(payload.state);
            }
            return payload;
        },
        [gameId]
    );

    useEffect(() => {
        const computer = (gameState?.players || []).find(
            (player) => player.seatNumber === gameState?.game?.activeSeatNumber
                && ["computer", "ai"].includes(player.playerType)
        );
        if (!computer || gameState?.game?.status !== "active") return undefined;
        const turnKey = `${gameState.game.turnNumber}:${computer.id}`;
        if (requestedAiTurnRef.current === turnKey) return undefined;
        requestedAiTurnRef.current = turnKey;
        const timeoutId = window.setTimeout(() => {
            postAction({
                type: "ai_take_turn",
                gamePlayerId: computer.id,
            }).catch((err) => {
                setError(err?.message || "The computer could not complete its turn.");
                requestedAiTurnRef.current = "";
            });
        }, 900);
        return () => window.clearTimeout(timeoutId);
    }, [
        gameState?.game?.activeSeatNumber,
        gameState?.game?.status,
        gameState?.game?.turnNumber,
        gameState?.players,
        postAction,
    ]);

    const handleDrawOne = useCallback(async () => {
        if (!activePlayer) return;
        try {
            await postAction({
                type: "draw_cards",
                gamePlayerId: activePlayer.id,
                count: 1,
            });
        } catch (err) {
            setError(err?.message || "Failed to draw card.");
        }
    }, [activePlayer, postAction]);

    const handleBottomDraw = useCallback(async () => {
        if (!activePlayer) return;
        try {
            await postAction({
                type: "draw_bottom",
                gamePlayerId: activePlayer.id,
                count: 1,
            });
        } catch (err) {
            setError(err?.message || "Failed to draw from the bottom.");
        }
    }, [activePlayer, postAction]);

    const handleShuffleLibrary = useCallback(async () => {
        if (!activePlayer) return;
        try {
            await postAction({
                type: "shuffle_library",
                gamePlayerId: activePlayer.id,
            });
        } catch (err) {
            setError(err?.message || "Failed to shuffle the Library.");
        }
    }, [activePlayer, postAction]);

    const handleRollDice = useCallback(async (sides, count = randomCount) => {
        if (!activePlayer) return;
        try {
            await postAction({
                type: "roll_dice",
                gamePlayerId: activePlayer.id,
                sides: Number(sides),
                count: Number(count),
            });
        } catch (err) {
            setError(err?.message || "Failed to roll dice.");
        }
    }, [activePlayer, postAction, randomCount]);

    const handleFlipCoins = useCallback(async (count = randomCount) => {
        if (!activePlayer) return;
        try {
            await postAction({
                type: "flip_coins",
                gamePlayerId: activePlayer.id,
                count: Number(count),
            });
        } catch (err) {
            setError(err?.message || "Failed to flip coins.");
        }
    }, [activePlayer, postAction, randomCount]);

    const handleConcede = useCallback(async () => {
        if (gameState?.game?.status !== "active") {
            onExitGame?.("The game is no longer active.");
            return;
        }
        if (
            preferences.confirmConcede !== false
            && !window.confirm("Concede this game? This may end the game for every remaining player.")
        ) return;
        try {
            const response = await fetch(`${API_BASE}/games/${gameId}/concede`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ participantToken }),
            });
            const payload = await response.json();
            if (!response.ok) {
                if (response.status === 400 && /only active games/i.test(payload?.error || "")) {
                    onExitGame?.("The game had already ended.");
                    return;
                }
                throw new Error(payload?.error || "Failed to concede.");
            }
            setGameState(payload.state);
        } catch (err) {
            setError(err?.message || "Failed to concede.");
        }
    }, [gameId, gameState?.game?.status, onExitGame, participantToken, preferences.confirmConcede]);

    const handleExitTable = useCallback(() => {
        if (
            gameState?.game?.status === "active"
            && !window.confirm("Return to the Games Lobby without conceding? The game will remain active.")
        ) return;
        onExitGame?.("You left the table without conceding.");
    }, [gameState?.game?.status, onExitGame]);

    const handleCardHover = useCallback((card, event = null, concealed = false) => {
        setHoveredCard(card);
        if (!card || !event) {
            setHoverPreview(null);
            return;
        }
        const previewWidth = 520;
        const previewHeight = 420;
        const x = event.clientX + previewWidth + 24 > window.innerWidth
            ? Math.max(12, event.clientX - previewWidth - 18)
            : event.clientX + 18;
        const y = Math.max(12, Math.min(event.clientY - 70, window.innerHeight - previewHeight - 12));
        setHoverPreview({ card, concealed, x, y });
    }, []);

    const handleCardMenu = useCallback((event, card, zone = "battlefield", readOnly = false) => {
        event?.preventDefault?.();
        event?.stopPropagation?.();
        setHoverPreview(null);
        setSelectedCard(card);
        setSelectedCardIds((previous) => {
            if (event?.shiftKey || event?.metaKey || event?.ctrlKey) {
                const next = new Set(previous);
                if (next.has(card.id)) next.delete(card.id);
                else next.add(card.id);
                return next;
            }
            return new Set([card.id]);
        });
        const x = Math.max(8, Math.min(event?.clientX || 20, window.innerWidth - 240));
        const y = Math.max(8, Math.min(event?.clientY || 20, window.innerHeight - 440));
        setContextMenu({ x, y, card, zone, readOnly });
    }, []);

    const handleCardContextMenu = useCallback((event, card) => {
        handleCardMenu(event, card, "battlefield");
    }, [handleCardMenu]);

    const handlePassTurn = useCallback(async () => {
        if (!activePlayer || !isMyTurn) return;
        try {
            await postAction({
                type: "pass_turn",
                gamePlayerId: activePlayer.id,
            });
        } catch (err) {
            setError(err?.message || "Failed to pass the turn.");
        }
    }, [activePlayer, isMyTurn, postAction]);

    const defaultBattlefieldPosition = useCallback((card) => {
        const width = PLAYMAT_CANVAS_WIDTH;
        const height = PLAYMAT_CANVAS_HEIGHT;
        const cardWidth = 120;
        const cardHeight = 205;
        const typeLine = String(card?.card?.typeLine || "");
        const isBasicLand = typeLine.includes("Basic Land");
        const isFancyLand = typeLine.includes("Land")
            && !isBasicLand
            && (card?.card?.colorIdentity || []).length > 1;
        const relatedCards = battlefieldCards.filter((entry) => {
            if (card?.isCommander) return entry.isCommander;
            const entryType = String(entry?.card?.typeLine || "");
            if (typeLine.includes("Land")) {
                const entryBasic = entryType.includes("Basic Land");
                const entryFancy = entryType.includes("Land")
                    && !entryBasic
                    && (entry?.card?.colorIdentity || []).length > 1;
                return isBasicLand ? entryBasic : isFancyLand ? entryFancy : (
                    entryType.includes("Land") && !entryBasic && !entryFancy
                );
            }
            if (typeLine.includes("Artifact")) return entryType.includes("Artifact");
            if (typeLine.includes("Enchantment")) return entryType.includes("Enchantment");
            return entryType.includes("Creature");
        });
        const relatedCount = relatedCards.length;
        const offset = (relatedCount % 5) * 34;
        const clamp = (value, maximum) => Math.max(10, Math.min(maximum - 10, value));

        if (card?.isCommander) {
            return {
                x: clamp(width - cardWidth - 18 - offset, width - cardWidth),
                y: 18,
            };
        }
        if (typeLine.includes("Land")) {
            const centerLeft = (width - cardWidth) / 2;
            const x = isBasicLand
                ? centerLeft - (relatedCount * 36)
                : isFancyLand
                    ? centerLeft + 72 + (relatedCount * 36)
                    : centerLeft + (relatedCount * 24);
            return {
                x: clamp(x, width - cardWidth),
                y: clamp(height - cardHeight - 18, height - cardHeight),
            };
        }
        if (typeLine.includes("Artifact")) {
            return {
                x: clamp(width * 0.78 - offset, width - cardWidth),
                y: clamp(56 + offset / 2, height - cardHeight),
            };
        }
        if (typeLine.includes("Enchantment")) {
            return {
                x: clamp(width * 0.58 - offset, width - cardWidth),
                y: clamp(42 + offset / 2, height - cardHeight),
            };
        }
        return {
            x: clamp(28 + offset, width - cardWidth),
            y: clamp(height * 0.32 + offset / 2, height - cardHeight),
        };
    }, [battlefieldCards]);

    const handleHandDragStart = useCallback((event, card) => {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("application/x-mtg-card-id", String(card.id));
        event.dataTransfer.setData("text/plain", String(card.id));
        setDraggingHandCardId(card.id);
    }, []);

    const handleHandDropOnBattlefield = useCallback(async (event) => {
        event.preventDefault();
        const cardId = Number(
            event.dataTransfer.getData("application/x-mtg-card-id")
            || event.dataTransfer.getData("text/plain")
            || draggingHandCardId
        );
        const card = handCards.find((candidate) => candidate.id === cardId);
        setDraggingHandCardId(null);
        if (!card || !battlefieldRef.current) return;
        const rect = battlefieldRef.current.getBoundingClientRect();
        const view = canvasViewRef.current;
        const worldX = (event.clientX - rect.left - view.x) / view.scale;
        const worldY = (event.clientY - rect.top - view.y) / view.scale;
        const x = Math.max(8, Math.min(PLAYMAT_CANVAS_WIDTH - 128, worldX - 60));
        const y = Math.max(8, Math.min(PLAYMAT_CANVAS_HEIGHT - 180, worldY - 85));
        try {
            await postAction({
                type: "move_card",
                cardInstanceId: card.id,
                zone: "battlefield",
                zoneIndex: null,
                battlefieldX: x,
                battlefieldY: y,
                stackIndex: null,
            });
        } catch (err) {
            setError(err?.message || "Failed to play the dragged card.");
        }
    }, [draggingHandCardId, handCards, postAction]);

    const handleDropToZone = useCallback(async (cardId, zone) => {
        const card = gameState?.players
            ?.flatMap((player) => (
                ["hand", "battlefield", "graveyard", "exile", "command", "stack"]
                    .flatMap((zoneName) => zoneArray(player, zoneName))
            ))
            .find((candidate) => candidate.id === Number(cardId));
        setDraggingHandCardId(null);
        if (!card) return;
        try {
            await postAction({
                type: "move_card",
                cardInstanceId: card.id,
                zone,
                zoneIndex: null,
                battlefieldX: null,
                battlefieldY: null,
                stackIndex: null,
            });
        } catch (err) {
            setError(err?.message || `Failed to move card to ${zone}.`);
        }
    }, [gameState?.players, postAction]);

    const handleMoveToZone = useCallback(
        async (card, zone) => {
            const position = zone === "battlefield"
                ? defaultBattlefieldPosition(card)
                : { x: null, y: null };
            try {
                await postAction({
                    type: "move_card",
                    cardInstanceId: card.id,
                    zone,
                    zoneIndex: null,
                    battlefieldX: position.x,
                    battlefieldY: position.y,
                    stackIndex: null,
                });
            } catch (err) {
                setError(err?.message || "Failed to move card.");
            }
        },
        [defaultBattlefieldPosition, postAction]
    );

    const handleReturnToLibrary = useCallback(async (card, position) => {
        try {
            await postAction({
                type: "return_to_library",
                cardInstanceId: card.id,
                position,
            });
            setSelectedCard(null);
        } catch (err) {
            setError(err?.message || "Failed to return card to the Library.");
        }
    }, [postAction]);

    const handlePeekLibrary = useCallback(async (count, untilCondition = null) => {
        try {
            const response = await fetch(`${API_BASE}/games/${gameId}/library/peek`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ participantToken, count, untilCondition }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload?.error || "Failed to peek at the Library.");
            setPeekCards(payload.cards || []);
            return payload.cards || [];
        } catch (err) {
            setError(err?.message || "Failed to peek at the Library.");
            throw err;
        }
    }, [gameId, participantToken]);

    const handleScryLibrary = useCallback(async (inspectedCardIds, topCardIds, bottomCardIds) => {
        if (!activePlayer) return;
        try {
            await postAction({
                type: "scry_library",
                gamePlayerId: activePlayer.id,
                inspectedCardIds,
                topCardIds,
                bottomCardIds,
            });
            setPeekCards([]);
        } catch (err) {
            setError(err?.message || "Failed to apply the scry.");
            throw err;
        }
    }, [activePlayer, postAction]);

    const handleExileUntil = useCallback(async (condition) => {
        if (!activePlayer) return;
        try {
            await postAction({
                type: "exile_until",
                gamePlayerId: activePlayer.id,
                condition,
            });
        } catch (err) {
            setError(err?.message || "Failed to exile cards.");
            throw err;
        }
    }, [activePlayer, postAction]);

    const handleDrawFromPlayer = useCallback(async (sourceGamePlayerId) => {
        if (!activePlayer) return;
        try {
            await postAction({
                type: "draw_from_player",
                sourceGamePlayerId,
                targetGamePlayerId: activePlayer.id,
                count: 1,
            });
        } catch (err) {
            setError(err?.message || "Failed to draw from that player's Library.");
        }
    }, [activePlayer, postAction]);

    const handleTransferSelected = useCallback(async (targetGamePlayerId, targetZone) => {
        if (!selectedCard) return;
        try {
            await postAction({
                type: "transfer_card",
                cardInstanceId: selectedCard.id,
                targetGamePlayerId,
                targetZone,
            });
            setSelectedCard(null);
        } catch (err) {
            setError(err?.message || "Failed to transfer that card.");
        }
    }, [postAction, selectedCard]);

    const handleSwapSelected = useCallback(async (secondCardInstanceId) => {
        if (!selectedCard) return;
        try {
            await postAction({
                type: "swap_cards",
                firstCardInstanceId: selectedCard.id,
                secondCardInstanceId,
            });
            setSelectedCard(null);
        } catch (err) {
            setError(err?.message || "Failed to swap those cards.");
        }
    }, [postAction, selectedCard]);

    const handleTapToggle = useCallback(
        async (card) => {
            const nextTapped = !card.isTapped;
            setGameState((previous) => previous ? {
                ...previous,
                players: previous.players.map((player) => ({
                    ...player,
                    zones: {
                        ...player.zones,
                        battlefield: zoneArray(player, "battlefield").map((entry) => (
                            entry.id === card.id
                                ? { ...entry, isTapped: nextTapped, rotationDeg: nextTapped ? 90 : 0 }
                                : entry
                        )),
                    },
                })),
            } : previous);
            try {
                await postAction({
                    type: "tap_card",
                    cardInstanceId: card.id,
                    isTapped: nextTapped,
                });
            } catch (err) {
                setError(err?.message || "Failed to tap card.");
                fetchState();
            }
        },
        [fetchState, postAction]
    );

    const handleFaceToggle = useCallback(
        async (card) => {
            const nextFace = card?.displayFace === "back" ? "front" : "back";
            setGameState((previous) => previous ? {
                ...previous,
                players: previous.players.map((player) => ({
                    ...player,
                    zones: {
                        ...player.zones,
                        battlefield: zoneArray(player, "battlefield").map((entry) => (
                            entry.id === card.id
                                ? {
                                    ...entry,
                                    displayFace: nextFace,
                                    isFaceDown: nextFace === "back",
                                }
                                : entry
                        )),
                    },
                })),
            } : previous);
            try {
                await postAction({
                    type: "set_display_face",
                    cardInstanceId: card.id,
                    displayFace: nextFace,
                    isFaceDown: nextFace === "back",
                });
            } catch (err) {
                setError(err?.message || "Failed to flip card.");
                fetchState();
            }
        },
        [fetchState, postAction]
    );

    const handleDragStart = useCallback((event, card) => {
        if (event.button !== 0) return;
        if (!battlefieldRef.current) return;

        const boardRect = battlefieldRef.current.getBoundingClientRect();
        const view = canvasViewRef.current;
        const pointerX = (event.clientX - boardRect.left - view.x) / view.scale;
        const pointerY = (event.clientY - boardRect.top - view.y) / view.scale;
        const currentX = Number(card?.battlefieldX ?? 40);
        const currentY = Number(card?.battlefieldY ?? 40);

        dragRef.current = {
            card,
            pointerId: event.pointerId,
            offsetX: pointerX - currentX,
            offsetY: pointerY - currentY,
        };

        event.currentTarget.setPointerCapture?.(event.pointerId);
    }, []);

    const handleSelectionStart = useCallback((event) => {
        if (![0, 1].includes(event.button) || !battlefieldRef.current) return;
        if (event.target?.closest?.(
            ".playmat-battlefield-card, .playmat-deck-anchor, .playmat-canvas-controls"
        )) return;

        event.preventDefault();
        const rect = battlefieldRef.current.getBoundingClientRect();
        const view = canvasViewRef.current;
        if (event.button === 0 && event.shiftKey) {
            const startX = (event.clientX - rect.left - view.x) / view.scale;
            const startY = (event.clientY - rect.top - view.y) / view.scale;
            selectionRef.current = { startX, startY };
            setSelectionBox({ left: startX, top: startY, width: 0, height: 0 });
            setSelectedCardIds(new Set());
        } else {
            panRef.current = {
                pointerId: event.pointerId,
                startClientX: event.clientX,
                startClientY: event.clientY,
                startX: view.x,
                startY: view.y,
            };
        }
        event.currentTarget.setPointerCapture?.(event.pointerId);
    }, []);

    const handlePointerMove = useCallback((event) => {
        if (!battlefieldRef.current) return;

        const boardRect = battlefieldRef.current.getBoundingClientRect();
        if (panRef.current) {
            setCanvasView((current) => ({
                ...current,
                x: panRef.current.startX + event.clientX - panRef.current.startClientX,
                y: panRef.current.startY + event.clientY - panRef.current.startClientY,
            }));
            return;
        }

        const view = canvasViewRef.current;
        if (selectionRef.current) {
            const currentX = (event.clientX - boardRect.left - view.x) / view.scale;
            const currentY = (event.clientY - boardRect.top - view.y) / view.scale;
            const left = Math.min(selectionRef.current.startX, currentX);
            const top = Math.min(selectionRef.current.startY, currentY);
            const right = Math.max(selectionRef.current.startX, currentX);
            const bottom = Math.max(selectionRef.current.startY, currentY);
            setSelectionBox({ left, top, width: right - left, height: bottom - top });
            setSelectedCardIds(new Set(
                battlefieldCards
                    .filter((card) => {
                        const x = Number(card.battlefieldX ?? 40);
                        const y = Number(card.battlefieldY ?? 40);
                        return x + 120 >= left && x <= right && y + 170 >= top && y <= bottom;
                    })
                    .map((card) => card.id)
            ));
            return;
        }

        if (!dragRef.current) return;
        const pointerX = (event.clientX - boardRect.left - view.x) / view.scale;
        const pointerY = (event.clientY - boardRect.top - view.y) / view.scale;
        const nextX = pointerX - dragRef.current.offsetX;
        const nextY = pointerY - dragRef.current.offsetY;

        setGameState((prev) => {
            if (!prev) return prev;

            const next = {
                ...prev,
                players: prev.players.map((player) => ({
                    ...player,
                    zones: {
                        ...player.zones,
                        battlefield: zoneArray(player, "battlefield").map((card) =>
                            card.id === dragRef.current.card.id
                                ? { ...card, battlefieldX: nextX, battlefieldY: nextY }
                                : card
                        ),
                    },
                })),
            };

            return next;
        });
    }, [battlefieldCards]);

    const handlePointerUp = useCallback(
        async () => {
            if (panRef.current) {
                panRef.current = null;
                return;
            }
            if (selectionRef.current) {
                selectionRef.current = null;
                setSelectionBox(null);
                return;
            }
            if (!dragRef.current) return;

            const card = dragRef.current.card;
            dragRef.current = null;

            const latestCard =
                gameState?.players
                    ?.flatMap((player) => zoneArray(player, "battlefield"))
                    .find((c) => c.id === card.id) || card;

            try {
                await postAction({
                    type: "move_card",
                    cardInstanceId: latestCard.id,
                    zone: "battlefield",
                    zoneIndex: null,
                    battlefieldX: Number(latestCard.battlefieldX ?? 40),
                    battlefieldY: Number(latestCard.battlefieldY ?? 40),
                    stackIndex: null,
                });
            } catch (err) {
                setError(err?.message || "Failed to update card position.");
                fetchState();
            }
        },
        [gameState, postAction, fetchState]
    );

    const handleCanvasWheel = useCallback((event) => {
        if (!battlefieldRef.current) return;
        event.preventDefault();
        const rect = battlefieldRef.current.getBoundingClientRect();
        const current = canvasViewRef.current;
        const cursorX = event.clientX - rect.left;
        const cursorY = event.clientY - rect.top;
        const worldX = (cursorX - current.x) / current.scale;
        const worldY = (cursorY - current.y) / current.scale;
        const nextScale = Math.max(
            0.35,
            Math.min(2.25, current.scale * Math.exp(-event.deltaY * 0.0015))
        );
        setCanvasView({
            scale: nextScale,
            x: cursorX - worldX * nextScale,
            y: cursorY - worldY * nextScale,
        });
    }, []);

    const zoomCanvas = useCallback((factor) => {
        if (!battlefieldRef.current) return;
        const rect = battlefieldRef.current.getBoundingClientRect();
        const current = canvasViewRef.current;
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        const worldX = (centerX - current.x) / current.scale;
        const worldY = (centerY - current.y) / current.scale;
        const nextScale = Math.max(0.35, Math.min(2.25, current.scale * factor));
        setCanvasView({
            scale: nextScale,
            x: centerX - worldX * nextScale,
            y: centerY - worldY * nextScale,
        });
    }, []);

    const fitCanvas = useCallback(() => {
        if (!battlefieldRef.current) return;
        const rect = battlefieldRef.current.getBoundingClientRect();
        const nextScale = Math.max(
            0.35,
            Math.min(1, Math.min(
                (rect.width - 32) / PLAYMAT_CANVAS_WIDTH,
                (rect.height - 32) / PLAYMAT_CANVAS_HEIGHT
            ))
        );
        setCanvasView({
            scale: nextScale,
            x: (rect.width - PLAYMAT_CANVAS_WIDTH * nextScale) / 2,
            y: (rect.height - PLAYMAT_CANVAS_HEIGHT * nextScale) / 2,
        });
    }, []);

    useEffect(() => {
        window.addEventListener("pointermove", handlePointerMove);
        window.addEventListener("pointerup", handlePointerUp);

        return () => {
            window.removeEventListener("pointermove", handlePointerMove);
            window.removeEventListener("pointerup", handlePointerUp);
        };
    }, [handlePointerMove, handlePointerUp]);

    useEffect(() => {
        const closeMenus = () => setContextMenu(null);
        window.addEventListener("click", closeMenus);
        return () => window.removeEventListener("click", closeMenus);
    }, []);

    useEffect(() => {
        const handleHotkey = (event) => {
            const tagName = event.target?.tagName?.toLowerCase();
            if (["input", "select", "textarea"].includes(tagName)) return;
            const key = event.key.toLowerCase();
            const card = hoveredCard || selectedCard;
            if (event.code === "Backquote") {
                if (event.shiftKey) handleRollDice(20, 1);
                else handleRollDice(6, 1);
                event.preventDefault();
                return;
            }
            if (key === "?") {
                setHotkeyHelpOpen((open) => !open);
                return;
            }
            const canMoveCard = !card || Number(card.gamePlayerId) === Number(activePlayer?.id);
            if (event.code === "Space") {
                if (!card || !canMoveCard || event.repeat) return;
                const cardZone = ["battlefield", "hand", "command"].find((zone) => (
                    zoneArray(activePlayer, zone).some((entry) => entry.id === card.id)
                ));
                if (cardZone === "battlefield") handleTapToggle(card);
                else if (cardZone === "hand" || cardZone === "command") {
                    handleMoveToZone(card, "battlefield");
                } else {
                    return;
                }
                event.preventDefault();
            } else if (key === "c") handleDrawOne();
            else if (key === "v") handleShuffleLibrary();
            else if (key === "e" || key === "n") handlePassTurn();
            else if (card && canMoveCard && key === "d") handleMoveToZone(card, "graveyard");
            else if (card && canMoveCard && key === "s") handleMoveToZone(card, "exile");
            else if (card && canMoveCard && key === "r") handleMoveToZone(card, "hand");
            else if (card && canMoveCard && key === "t") handleReturnToLibrary(card, "top");
            else if (card && canMoveCard && key === "y") handleReturnToLibrary(card, "bottom");
            else if (card && canMoveCard && key === "j") handleFaceToggle(card);
            else return;
            event.preventDefault();
        };
        window.addEventListener("keydown", handleHotkey);
        return () => window.removeEventListener("keydown", handleHotkey);
    }, [
        handleDrawOne,
        handleFaceToggle,
        handleMoveToZone,
        handlePassTurn,
        handleRollDice,
        handleReturnToLibrary,
        handleShuffleLibrary,
        handleTapToggle,
        hoveredCard,
        selectedCard,
        activePlayer,
    ]);

    const contextTargets = contextMenu
        && !contextMenu.readOnly
        && contextMenu.zone === "battlefield"
        && selectedCardIds.has(contextMenu.card.id)
        ? battlefieldCards.filter((card) => selectedCardIds.has(card.id))
        : (contextMenu ? [contextMenu.card] : []);
    const contextCardConcealed = Boolean(
        contextMenu?.readOnly
        && (contextMenu.card?.isFaceDown || contextMenu.card?.displayFace === "back")
    );
    const runContextAction = async (action, { excludeCommanders = false } = {}) => {
        for (const card of contextTargets) {
            if (excludeCommanders && card.isCommander) continue;
            await action(card);
        }
        setContextMenu(null);
    };

    return (
        <div
            className="playmat-runtime"
            style={{
                "--playmat-left-rail": `${layout.leftRail}px`,
                "--playmat-hand": `${layout.hand}px`,
            }}
        >
            <ZonePanel
                player={activePlayer}
                onDrawOne={handleDrawOne}
                onOpenTools={() => setToolsOpen(true)}
                onDropToZone={handleDropToZone}
            />

            <main className="playmat-table">
                <div className="playmat-toolbar">
                    <div className="playmat-match-meta">
                        <span className={`ruleset-badge ${gameState?.game?.ruleset || "casual"}`}>
                            {gameState?.game?.ruleset === "playtest" ? "House rules" : gameState?.game?.ruleset || "Casual"}
                        </span>
                        <span>{gameState?.game?.format || "—"}</span>
                        <span>{gameState?.game?.gameMode || "—"}</span>
                    </div>
                    <div className="playmat-turn-controls">
                        <span>
                            Turn {gameState?.game?.turnNumber || 1}
                            {" · "}
                            Player {gameState?.game?.activeSeatNumber || 1}
                        </span>
                        <button
                            type="button"
                            className="playmat-pass-button"
                            disabled={!isMyTurn || isLoading}
                            onClick={handlePassTurn}
                        >
                            {isMyTurn ? "Pass turn" : "Waiting…"}
                        </button>
                        <button type="button" onClick={() => setHotkeyHelpOpen(true)}>Hotkeys</button>
                        <button type="button" onClick={() => setRandomizerOpen(true)}>Dice & coins</button>
                        <button
                            type="button"
                            className="playmat-reset-layout"
                            onClick={() => setLayout(DEFAULT_PLAYMAT_LAYOUT)}
                            title="Reset adjustable PlayMat sections"
                        >
                            Reset layout
                        </button>
                        <button type="button" className="playmat-exit-button" onClick={handleExitTable}>
                            Return to lobby
                        </button>
                        <button type="button" className="playmat-concede-button" onClick={handleConcede}>
                            Concede
                        </button>
                    </div>
                </div>

                {gameState?.game?.ruleset === "playtest" ? (
                    <div className="playmat-rules-policy disabled">
                        Rules engine disabled · illegal moves may be permitted.
                    </div>
                ) : (
                    <div className={`playmat-rules-policy ${gameState?.game?.ruleset || "casual"}`}>
                        {gameState?.game?.ruleset === "tournament"
                            ? "Tournament rules · illegal actions will be blocked when rules enforcement is available."
                            : "Casual rules · future legality warnings may be overridden."}
                    </div>
                )}

                {gameState?.game?.status === "completed" ? (
                    <div className="playmat-game-over">
                        Game complete · Player {
                            gameState.players.find((player) => player.result === "win")?.seatNumber || "—"
                        } wins
                    </div>
                ) : null}

                {error ? (
                    <div
                        style={{
                            background: "#451a1a",
                            border: "1px solid #7f1d1d",
                            color: "#fecaca",
                            borderRadius: "10px",
                            padding: "10px 12px",
                        }}
                    >
                        {error}
                    </div>
                ) : null}

                <div style={{ height: `${layout.opponent}px`, minHeight: 0, flex: "0 0 auto" }}>
                    <OpponentBoards
                        players={opponentPlayers}
                        onCardClick={handleCardMenu}
                        onCardHover={handleCardHover}
                    />
                </div>
                <div
                    className="playmat-opponent-resizer"
                    role="separator"
                    aria-label="Resize opponent table"
                    aria-orientation="horizontal"
                    onPointerDown={(event) => beginLayoutResize("opponent", event)}
                >
                    <span />
                </div>

                {gameState?.randomResults?.length ? (
                    <div className="playmat-random-results" aria-live="polite">
                        {gameState.randomResults.slice(-4).reverse().map((result) => (
                            <span key={result.eventId}>
                                P{result.seatNumber} {result.type === "flip_coins" ? "flipped" : "rolled"}{" "}
                                <strong>{result.values.join(", ")}</strong>
                                {result.type === "roll_dice" ? ` (${result.label})` : ""}
                            </span>
                        ))}
                    </div>
                ) : null}

                {gameState?.alternateWinConditions?.length ? (
                    <div className="playmat-alt-win-watch">
                        <strong>Alternate win conditions</strong>
                        {gameState.alternateWinConditions.map((condition) => (
                            <span key={condition.cardInstanceId}>
                                P{condition.seatNumber} · {condition.cardName} · {condition.status}
                            </span>
                        ))}
                    </div>
                ) : null}

                {usesCommandZone ? (
                    <CommandZone
                        cards={commandCards}
                        sleeveStyle={activePlayer?.sleeveStyle}
                        onCardClick={handleCardMenu}
                        onCardHover={handleCardHover}
                    />
                ) : null}

                <div
                    ref={battlefieldRef}
                    className={`playmat-battlefield ${draggingHandCardId ? "accepting-drop" : ""}`}
                    onPointerDown={handleSelectionStart}
                    onWheel={handleCanvasWheel}
                    onDragOver={(event) => {
                        event.preventDefault();
                        event.dataTransfer.dropEffect = "move";
                    }}
                    onDrop={handleHandDropOnBattlefield}
                    style={{
                        position: "relative",
                        flex: 1,
                        minHeight: 0,
                        background:
                            "radial-gradient(circle at center, rgba(30,41,59,0.9), rgba(15,23,42,1))",
                        border: "1px solid #334155",
                        borderRadius: "16px",
                        overflow: "hidden",
                    }}
                >
                    <div
                        className="playmat-canvas-controls"
                        onPointerDown={(event) => event.stopPropagation()}
                    >
                        <button type="button" onClick={() => zoomCanvas(0.8)} aria-label="Zoom out">−</button>
                        <output>{Math.round(canvasView.scale * 100)}%</output>
                        <button type="button" onClick={() => zoomCanvas(1.25)} aria-label="Zoom in">+</button>
                        <button type="button" onClick={fitCanvas}>Fit table</button>
                    </div>
                    <div
                        className="playmat-canvas-layer"
                        style={{
                            width: `${PLAYMAT_CANVAS_WIDTH}px`,
                            height: `${PLAYMAT_CANVAS_HEIGHT}px`,
                            transform: `translate(${canvasView.x}px, ${canvasView.y}px) scale(${canvasView.scale})`,
                        }}
                    >
                        {preferences.showPlacementGuides !== false ? (
                        <div className="playmat-placement-guides" aria-hidden="true">
                            <div className="guide-creatures">Creatures · front line</div>
                            <div className="guide-enchantments">Enchantments</div>
                            <div className="guide-artifacts">Artifacts</div>
                            <div className="guide-commanders">Commander</div>
                            <div className="guide-lands">
                                <span>Basic lands</span>
                                <strong>Lands</strong>
                                <span>Multicolor lands</span>
                            </div>
                        </div>
                        ) : null}
                        {battlefieldCards.map((card) => (
                            <BattlefieldCard
                                key={card.id}
                                card={card}
                                sleeveStyle={activePlayer?.sleeveStyle}
                                isSelected={selectedCardIds.has(card.id)}
                                onSelect={(cardEntry, event) => handleCardMenu(event, cardEntry, "battlefield")}
                                onDragStart={handleDragStart}
                                onContextMenu={handleCardContextMenu}
                                onHover={handleCardHover}
                            />
                        ))}
                        {selectionBox ? (
                            <div className="playmat-selection-box" style={selectionBox} />
                        ) : null}
                        <div className="playmat-deck-anchor">
                            <button
                                type="button"
                                className="playmat-deck-stack"
                                onClick={(event) => {
                                    event.stopPropagation();
                                    setDeckMenuOpen((open) => !open);
                                }}
                            >
                                <CardBack sleeveStyle={activePlayer?.sleeveStyle} />
                                <strong>{libraryCount(activePlayer)}</strong>
                            </button>
                            {deckMenuOpen ? (
                                <div className="playmat-deck-menu" onClick={(event) => event.stopPropagation()}>
                                    <button type="button" onClick={handleDrawOne}>Draw top card <kbd>C</kbd></button>
                                    <button type="button" onClick={handleBottomDraw}>Draw bottom card</button>
                                    <button type="button" onClick={() => {
                                        setToolsOpen(true);
                                        handlePeekLibrary(5);
                                    }}>Peek at top 5</button>
                                    <button type="button" onClick={() => {
                                        setPeekCards([]);
                                        setLibraryActionsOpen(true);
                                        setDeckMenuOpen(false);
                                    }}>Scry / exile until…</button>
                                    <button type="button" onClick={handleShuffleLibrary}>Shuffle <kbd>V</kbd></button>
                                    <button type="button" onClick={() => setToolsOpen(true)}>More…</button>
                                </div>
                            ) : null}
                        </div>
                    </div>
                    <div className="playmat-canvas-hint" aria-hidden="true">
                        Drag empty space to pan · Scroll to zoom · Shift-drag to select
                    </div>
                </div>
            </main>

            <div className="playmat-hand-dock">
                <div className="playmat-hand-heading">
                    <strong>Hand</strong>
                    <label>
                        <span>Sort</span>
                        <select value={handSort} onChange={(event) => setHandSort(event.target.value)}>
                            <option value="type">Card type</option>
                            <option value="mana-asc">Mana value · low to high</option>
                            <option value="mana-desc">Mana value · high to low</option>
                            <option value="name">Name</option>
                        </select>
                    </label>
                </div>
                <HandFan
                    cards={handCards}
                    onCardClick={handleCardMenu}
                    onCardHover={handleCardHover}
                    onDragStart={handleHandDragStart}
                    onDragEnd={() => setDraggingHandCardId(null)}
                    selectedCardId={selectedCard?.id}
                    highlightedCardIds={highlightedCardIds}
                />
            </div>
            <div
                className="playmat-layout-resizer playmat-resizer-left"
                role="separator"
                aria-label="Resize player sidebar"
                aria-orientation="vertical"
                onPointerDown={(event) => beginLayoutResize("left", event)}
            />
            <div
                className="playmat-layout-resizer playmat-resizer-hand"
                role="separator"
                aria-label="Resize hand"
                aria-orientation="horizontal"
                onPointerDown={(event) => beginLayoutResize("hand", event)}
            />
            {toolsOpen ? (
                <AdvancedInteractionPanel
                    players={gameState?.players || []}
                    activePlayer={activePlayer}
                    selectedCard={selectedCard}
                    peekCards={peekCards}
                    onPeek={handlePeekLibrary}
                    onDrawFromPlayer={handleDrawFromPlayer}
                    onTransfer={handleTransferSelected}
                    onSwap={handleSwapSelected}
                    onClose={() => setToolsOpen(false)}
                />
            ) : null}
            {libraryActionsOpen ? (
                <LibraryActionModal
                    cards={peekCards}
                    onInspect={handlePeekLibrary}
                    onScry={handleScryLibrary}
                    onExileUntil={handleExileUntil}
                    onClose={() => {
                        setLibraryActionsOpen(false);
                        setPeekCards([]);
                    }}
                />
            ) : null}
            {ruleViolation ? (
                <RuleViolationModal
                    violation={ruleViolation}
                    ruleset={gameState?.game?.ruleset || "casual"}
                    onClose={() => setRuleViolation(null)}
                    onAllow={async () => {
                        const action = ruleViolation.action;
                        setRuleViolation(null);
                        try {
                            await postAction({ ...action, allowIllegalMove: true });
                        } catch (err) {
                            setError(err?.message || "The action could not be overridden.");
                        }
                    }}
                />
            ) : null}
            {randomizerOpen ? (
                <div className="playmat-tools-backdrop" onMouseDown={() => setRandomizerOpen(false)}>
                    <section className="playmat-randomizer" onMouseDown={(event) => event.stopPropagation()}>
                        <header>
                            <div>
                                <div className="eyebrow">Public game action</div>
                                <strong>Dice & coins</strong>
                            </div>
                            <button type="button" onClick={() => setRandomizerOpen(false)}>Close</button>
                        </header>
                        <label>
                            Number to roll or flip
                            <input
                                type="number"
                                min="1"
                                max="20"
                                value={randomCount}
                                onChange={(event) => setRandomCount(event.target.value)}
                            />
                        </label>
                        <div className="playmat-randomizer-presets">
                            {[6, 10, 20, 100].map((sides) => (
                                <button type="button" key={sides} onClick={() => handleRollDice(sides)}>
                                    Roll d{sides}
                                </button>
                            ))}
                            <button type="button" onClick={() => handleFlipCoins()}>Flip coin</button>
                        </div>
                        <div className="playmat-randomizer-custom">
                            <label>
                                Custom die sides
                                <input
                                    type="number"
                                    min="2"
                                    max="1000"
                                    value={customDieSides}
                                    onChange={(event) => setCustomDieSides(event.target.value)}
                                />
                            </label>
                            <button type="button" onClick={() => handleRollDice(customDieSides)}>
                                Roll custom die
                            </button>
                        </div>
                        <small>Results are broadcast to every player and retained in the game event log.</small>
                    </section>
                </div>
            ) : null}
            {contextMenu ? (
                <div
                    className="playmat-card-context"
                    style={{ left: contextMenu.x, top: contextMenu.y }}
                    onClick={(event) => event.stopPropagation()}
                >
                    <strong>
                        {contextTargets.length > 1
                            ? `${contextTargets.length} selected cards`
                            : contextCardConcealed ? "Face-down card" : (contextMenu.card?.card?.name || "Card")}
                    </strong>
                    {contextMenu.readOnly ? (
                        <>
                            {!contextCardConcealed ? (
                                <button
                                    type="button"
                                    onClick={() => {
                                        navigator.clipboard?.writeText(contextMenu.card?.card?.name || "");
                                        setContextMenu(null);
                                    }}
                                >
                                    Copy card name
                                </button>
                            ) : null}
                            {!contextCardConcealed ? (
                                <button
                                    type="button"
                                    onClick={() => {
                                        setSelectedCard(contextMenu.card);
                                        setToolsOpen(true);
                                        setContextMenu(null);
                                    }}
                                >
                                    Open interaction tools
                                </button>
                            ) : null}
                        </>
                    ) : (
                        <>
                            {contextMenu.zone === "battlefield" ? (
                                <>
                                    <button type="button" onClick={() => runContextAction(handleTapToggle)}>Tap / Untap</button>
                                    <button type="button" onClick={() => runContextAction(handleFaceToggle)}>Face down / up</button>
                                </>
                            ) : (
                                <button type="button" onClick={() => runContextAction(
                                    (card) => handleMoveToZone(card, "battlefield")
                                )}>
                                    Play to Battlefield
                                </button>
                            )}
                            <button type="button" onClick={() => runContextAction((card) => handleMoveToZone(card, "graveyard"))}>
                                Send to Graveyard <kbd>D</kbd>
                            </button>
                            <button type="button" onClick={() => runContextAction((card) => handleMoveToZone(card, "exile"))}>
                                Send to Exile <kbd>S</kbd>
                            </button>
                            {contextMenu.zone !== "hand" ? (
                                <button type="button" onClick={() => runContextAction((card) => handleMoveToZone(card, "hand"))}>
                                    Return to Hand <kbd>R</kbd>
                                </button>
                            ) : null}
                            {contextTargets.some((card) => !card.isCommander) ? (
                                <>
                                    <button type="button" onClick={() => runContextAction(
                                        (card) => handleReturnToLibrary(card, "top"),
                                        { excludeCommanders: true }
                                    )}>
                                        Top of Library <kbd>T</kbd>
                                    </button>
                                    <button type="button" onClick={() => runContextAction(
                                        (card) => handleReturnToLibrary(card, "bottom"),
                                        { excludeCommanders: true }
                                    )}>
                                        Bottom of Library <kbd>Y</kbd>
                                    </button>
                                    <button type="button" onClick={() => runContextAction(
                                        (card) => handleReturnToLibrary(card, "random"),
                                        { excludeCommanders: true }
                                    )}>
                                        Shuffle into Library
                                    </button>
                                </>
                            ) : null}
                            <button
                                type="button"
                                onClick={() => {
                                    navigator.clipboard?.writeText(contextMenu.card?.card?.name || "");
                                    setContextMenu(null);
                                }}
                            >
                                Copy card name
                            </button>
                        </>
                    )}
                </div>
            ) : null}
            <HoverCardPreview preview={hoverPreview} />
            {hotkeyHelpOpen ? (
                <div className="playmat-tools-backdrop" onMouseDown={() => setHotkeyHelpOpen(false)}>
                    <section className="playmat-hotkey-help" onMouseDown={(event) => event.stopPropagation()}>
                        <header>
                            <strong>Hotkey Help</strong>
                            <button type="button" onClick={() => setHotkeyHelpOpen(false)}>Close</button>
                        </header>
                        <div>
                            <span><kbd>Space</kbd> Default action for hovered card</span>
                            <span><kbd>C</kbd> Draw top card</span>
                            <span><kbd>V</kbd> Shuffle Library</span>
                            <span><kbd>E</kbd> / <kbd>N</kbd> Pass turn</span>
                            <span><kbd>D</kbd> Hovered card to Graveyard</span>
                            <span><kbd>S</kbd> Hovered card to Exile</span>
                            <span><kbd>R</kbd> Hovered card to Hand</span>
                            <span><kbd>T</kbd> Hovered card to top of Library</span>
                            <span><kbd>Y</kbd> Hovered card to bottom of Library</span>
                            <span><kbd>J</kbd> Face down / up</span>
                            <span><kbd>?</kbd> Toggle this help</span>
                            <span><kbd>`</kbd> Roll d6</span>
                            <span><kbd>Shift</kbd> + <kbd>`</kbd> Roll d20</span>
                        </div>
                    </section>
                </div>
            ) : null}
        </div>
    );
}
