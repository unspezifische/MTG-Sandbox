import React, { useMemo, useState } from "react";

const FORMAT_OPTIONS = [
    ["commander", "Commander"],
    ["standard", "Standard"],
    ["modern", "Modern"],
    ["pioneer", "Pioneer"],
    ["legacy", "Legacy"],
    ["vintage", "Vintage"],
    ["pauper", "Pauper"],
];

const GAME_MODE_OPTIONS = [
    ["multiplayer", "Multiplayer free-for-all"],
    ["one-v-one", "One versus one"],
    ["two-headed-giant", "Two-Headed Giant"],
];

const RULESET_OPTIONS = [
    ["casual", "Casual"],
    ["tournament", "Tournament"],
    ["playtest", "Playtest / house rules"],
];

function optionLabel(options, value) {
    return options.find(([key]) => key === value)?.[1] || value || "—";
}

function CreateLobbyModal({ decks, onClose, onCreate, busy, preferredDeckId = "" }) {
    const playableDecks = decks.filter((deck) => Number(deck.cardCount) > 0);
    const [name, setName] = useState("");
    const [format, setFormat] = useState("commander");
    const [gameMode, setGameMode] = useState("multiplayer");
    const [ruleset, setRuleset] = useState("casual");
    const [playerCount, setPlayerCount] = useState(4);
    const [hostDeckId, setHostDeckId] = useState(
        playableDecks.some((deck) => String(deck.id) === String(preferredDeckId))
            ? preferredDeckId
            : (playableDecks[0]?.id || "")
    );
    const [password, setPassword] = useState("");
    const [notes, setNotes] = useState("");
    const [localError, setLocalError] = useState("");

    async function submit(event) {
        event.preventDefault();
        if (!name.trim()) {
            setLocalError("Give the lobby a name.");
            return;
        }
        if (!hostDeckId) {
            setLocalError("Choose the deck you want to bring.");
            return;
        }
        if (password && password.length < 4) {
            setLocalError("Passwords must be at least 4 characters.");
            return;
        }
        setLocalError("");
        const created = await onCreate({
            lobbyName: name.trim(),
            format,
            gameMode,
            ruleset,
            playerCount: Number(playerCount),
            hostDeckId: Number(hostDeckId),
            password,
            notes: notes.trim(),
            userId: 1,
        });
        if (created?.error) setLocalError(created.error);
        else if (created) onClose();
    }

    return (
        <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
            <form
                className="deck-modal lobby-modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="create-lobby-title"
                onSubmit={submit}
                onMouseDown={(event) => event.stopPropagation()}
            >
                <div className="deck-modal-header">
                    <div>
                        <div className="eyebrow">Host a table</div>
                        <h2 id="create-lobby-title">Create new game</h2>
                    </div>
                    <button type="button" className="modal-close" onClick={onClose} aria-label="Close">×</button>
                </div>

                <div className="deck-modal-body">
                    <label className="lobby-field">
                        <span>Lobby name</span>
                        <input
                            className="modal-input"
                            value={name}
                            maxLength={80}
                            onChange={(event) => setName(event.target.value)}
                            placeholder="Friday night Commander"
                            autoFocus
                        />
                    </label>

                    <div className="lobby-form-grid">
                        <label className="lobby-field">
                            <span>Format</span>
                            <select className="modal-input" value={format} onChange={(event) => setFormat(event.target.value)}>
                                {FORMAT_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                            </select>
                        </label>
                        <label className="lobby-field">
                            <span>Game mode</span>
                            <select className="modal-input" value={gameMode} onChange={(event) => setGameMode(event.target.value)}>
                                {GAME_MODE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                            </select>
                        </label>
                        <label className="lobby-field">
                            <span>Ruleset</span>
                            <select className="modal-input" value={ruleset} onChange={(event) => setRuleset(event.target.value)}>
                                {RULESET_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                            </select>
                            {ruleset === "playtest" && (
                                <strong className="rules-engine-disabled-warning">
                                    The playtest / house rules option disables MTG Sandbox&apos;s MTG Rules Engine for this game. ILLEGAL MOVES MAY BE PERMITTED.
                                </strong>
                            )}
                        </label>
                        <label className="lobby-field">
                            <span>Seats</span>
                            <select className="modal-input" value={playerCount} onChange={(event) => setPlayerCount(event.target.value)}>
                                {[2, 3, 4, 5, 6, 7, 8].map((count) => <option key={count} value={count}>{count} players</option>)}
                            </select>
                        </label>
                    </div>

                    <label className="lobby-field">
                        <span>Your deck</span>
                        <select className="modal-input" value={hostDeckId} onChange={(event) => setHostDeckId(event.target.value)}>
                            <option value="">Choose a saved deck…</option>
                            {playableDecks.map((deck) => (
                                <option key={deck.id} value={deck.id}>
                                    {deck.name} · {deck.format} · {deck.cardCount} cards
                                </option>
                            ))}
                        </select>
                    </label>

                    <label className="lobby-field">
                        <span>Password <small>Optional</small></span>
                        <input
                            className="modal-input"
                            type="password"
                            value={password}
                            maxLength={128}
                            onChange={(event) => setPassword(event.target.value)}
                            placeholder="Leave blank for a public lobby"
                            autoComplete="new-password"
                        />
                    </label>

                    <label className="lobby-field">
                        <span>Table notes <small>Optional</small></span>
                        <textarea
                            className="modal-input lobby-notes"
                            value={notes}
                            onChange={(event) => setNotes(event.target.value)}
                            placeholder="Power level, house rules, expected game length…"
                        />
                    </label>

                    {!playableDecks.length && (
                        <div className="play-page-error">Create a deck with cards before hosting a game.</div>
                    )}
                    {localError && <div className="play-page-error">{localError}</div>}
                </div>

                <div className="deck-modal-footer">
                    <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
                    <button type="submit" className="button-primary" disabled={busy || !playableDecks.length}>
                        {busy ? "Creating…" : "Create lobby"}
                    </button>
                </div>
            </form>
        </div>
    );
}

function JoinLobbyModal({ game, decks, onClose, onJoin, onReloadDecks, decksLoading, decksError, busy }) {
    const playableDecks = useMemo(
        () => decks.filter((deck) => Number(deck.cardCount) > 0),
        [decks]
    );
    const [deckId, setDeckId] = useState(playableDecks[0]?.id || "");
    const [password, setPassword] = useState("");
    const [localError, setLocalError] = useState("");

    React.useEffect(() => {
        if (!playableDecks.length) {
            setDeckId("");
            return;
        }
        if (!playableDecks.some((deck) => String(deck.id) === String(deckId))) {
            setDeckId(String(playableDecks[0].id));
        }
    }, [deckId, playableDecks]);

    async function submit(event) {
        event.preventDefault();
        if (!deckId) {
            setLocalError("Choose a deck before joining.");
            return;
        }
        setLocalError("");
        const joined = await onJoin(game.id, Number(deckId), password);
        if (joined?.error) setLocalError(joined.error);
        else if (joined) onClose();
    }

    return (
        <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
            <form
                className="deck-modal join-lobby-modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="join-lobby-title"
                onSubmit={submit}
                onMouseDown={(event) => event.stopPropagation()}
            >
                <div className="deck-modal-header">
                    <div>
                        <div className="eyebrow">Join table</div>
                        <h2 id="join-lobby-title">{game.lobbyName}</h2>
                    </div>
                    <button type="button" className="modal-close" onClick={onClose} aria-label="Close">×</button>
                </div>
                <div className="deck-modal-body">
                    <div className="join-lobby-summary">
                        <span>{game.format}</span>
                        <span>{optionLabel(GAME_MODE_OPTIONS, game.gameMode)}</span>
                        <span>{optionLabel(RULESET_OPTIONS, game.ruleset)}</span>
                    </div>
                    {game.ruleset === "playtest" && (
                        <strong className="rules-engine-disabled-warning">
                            This game disables MTG Sandbox&apos;s MTG Rules Engine. ILLEGAL MOVES MAY BE PERMITTED.
                        </strong>
                    )}
                    <label className="lobby-field">
                        <span>Your deck</span>
                        <select className="modal-input" value={deckId} onChange={(event) => setDeckId(event.target.value)} disabled={decksLoading}>
                            <option value="">{decksLoading ? "Loading saved decks…" : "Choose a saved deck…"}</option>
                            {playableDecks.map((deck) => (
                                <option key={deck.id} value={deck.id}>{deck.name} · {deck.cardCount} cards</option>
                            ))}
                        </select>
                    </label>
                    {!decksLoading && !playableDecks.length && (
                        <div className="join-deck-load-state">
                            <span>{decksError || "No saved decks with cards were found."}</span>
                            <button type="button" className="button-secondary" onClick={onReloadDecks}>Retry saved decks</button>
                        </div>
                    )}
                    {game.isPasswordProtected && (
                        <label className="lobby-field">
                            <span>Lobby password</span>
                            <input
                                className="modal-input"
                                type="password"
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                autoComplete="current-password"
                                autoFocus
                            />
                        </label>
                    )}
                    {localError && <div className="play-page-error">{localError}</div>}
                </div>
                <div className="deck-modal-footer">
                    <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
                    <button type="submit" className="button-primary" disabled={busy || decksLoading || !playableDecks.length}>
                        {busy ? "Joining…" : "Join lobby"}
                    </button>
                </div>
            </form>
        </div>
    );
}

export default function GameLobby({
    games,
    decks,
    selectedGameId,
    busy,
    onRefresh,
    onSelect,
    onCreate,
    onJoin,
    onRefreshDecks,
    decksLoading = false,
    decksError = "",
    createRequestId = 0,
    preferredDeckId = "",
}) {
    const [search, setSearch] = useState("");
    const [gameMode, setGameMode] = useState("all");
    const [ruleset, setRuleset] = useState("all");
    const [showCreate, setShowCreate] = useState(false);
    const [joinGame, setJoinGame] = useState(null);
    const [copyMessage, setCopyMessage] = useState("");

    React.useEffect(() => {
        if (createRequestId > 0) setShowCreate(true);
    }, [createRequestId]);

    const availableGames = useMemo(() => {
        const query = search.trim().toLowerCase();
        return games
            .filter((game) => game.status === "pending")
            .filter((game) => !query || String(game.lobbyName || "").toLowerCase().includes(query))
            .filter((game) => gameMode === "all" || game.gameMode === gameMode)
            .filter((game) => ruleset === "all" || game.ruleset === ruleset);
    }, [gameMode, games, ruleset, search]);

    async function copyInvite(game) {
        const url = new URL(window.location.href);
        url.searchParams.set("lobby", game.id);
        try {
            await navigator.clipboard.writeText(url.toString());
            setCopyMessage(`Invite link copied for ${game.lobbyName}.`);
        } catch {
            setCopyMessage(`Lobby ID: ${game.id}`);
        }
    }

    return (
        <section className="game-lobby-browser">
            <div className="lobby-browser-heading">
                <div>
                    <div className="eyebrow">Multiplayer</div>
                    <h2>Game lobbies</h2>
                    <p>Find an open table or create one and invite your friends.</p>
                </div>
                <div className="play-page-actions">
                    <button type="button" className="button-secondary" onClick={onRefresh}>Refresh</button>
                    <button type="button" className="button-primary" onClick={() => setShowCreate(true)}>
                        Create new game
                    </button>
                </div>
            </div>

            <div className="lobby-filters">
                <label className="lobby-search">
                    <span className="sr-only">Search lobby names</span>
                    <input
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        placeholder="Search lobby names…"
                    />
                </label>
                <select value={gameMode} onChange={(event) => setGameMode(event.target.value)} aria-label="Filter by game mode">
                    <option value="all">All game modes</option>
                    {GAME_MODE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
                <select value={ruleset} onChange={(event) => setRuleset(event.target.value)} aria-label="Filter by ruleset">
                    <option value="all">All rulesets</option>
                    {RULESET_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
            </div>

            {copyMessage && <div className="lobby-copy-message">{copyMessage}</div>}

            <div className="lobby-results-heading">
                <strong>{availableGames.length} available game{availableGames.length === 1 ? "" : "s"}</strong>
                <span>Open seats update when players join.</span>
            </div>

            {availableGames.length ? (
                <div className="lobby-card-grid">
                    {availableGames.map((game) => (
                        <article
                            key={game.id}
                            className={`lobby-card ${String(game.id) === String(selectedGameId) ? "selected" : ""}`}
                        >
                            <div className="lobby-card-top">
                                <div>
                                    <span className={`ruleset-badge ${game.ruleset}`}>{game.ruleset}</span>
                                    {game.isPasswordProtected && <span className="lobby-lock" title="Password protected">🔒</span>}
                                </div>
                                <span className="lobby-game-id">#{game.id}</span>
                            </div>
                            <h3>{game.lobbyName}</h3>
                            <p>{game.notes || "No table notes provided."}</p>
                            <div className="lobby-card-meta">
                                <span><b>{game.format}</b> format</span>
                                <span>{optionLabel(GAME_MODE_OPTIONS, game.gameMode)}</span>
                                <span>{game.occupiedPlayerCount}/{game.maxPlayers} players</span>
                            </div>
                            <div className="lobby-seat-meter" aria-label={`${game.occupiedPlayerCount} of ${game.maxPlayers} seats occupied`}>
                                {Array.from({ length: game.maxPlayers }, (_, index) => (
                                    <i key={index} className={index < game.occupiedPlayerCount ? "filled" : ""} />
                                ))}
                            </div>
                            <div className="lobby-card-actions">
                                <button type="button" className="button-secondary" onClick={() => copyInvite(game)}>Copy invite</button>
                                <button
                                    type="button"
                                    className="button-primary"
                                    onClick={async () => {
                                        onSelect(game.id);
                                        await onRefreshDecks?.();
                                        setJoinGame(game);
                                    }}
                                    disabled={game.openSeatCount < 1}
                                >
                                    {game.openSeatCount > 0 ? "Join game" : "Full"}
                                </button>
                            </div>
                        </article>
                    ))}
                </div>
            ) : (
                <div className="lobby-empty">
                    <strong>No open lobbies match those filters.</strong>
                    <span>Create a new game or clear the search to see more tables.</span>
                </div>
            )}

            {showCreate && (
                <CreateLobbyModal
                    decks={decks}
                    busy={busy}
                    onCreate={onCreate}
                    onClose={() => setShowCreate(false)}
                    preferredDeckId={preferredDeckId}
                />
            )}
            {joinGame && (
                <JoinLobbyModal
                    game={joinGame}
                    decks={decks}
                    busy={busy}
                    onJoin={onJoin}
                    onReloadDecks={onRefreshDecks}
                    decksLoading={decksLoading}
                    decksError={decksError}
                    onClose={() => setJoinGame(null)}
                />
            )}
        </section>
    );
}
