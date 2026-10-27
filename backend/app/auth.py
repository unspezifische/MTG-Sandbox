"""Verify identity with the existing Kachhapa backend, never client user IDs."""
from urllib.parse import urlsplit

import requests
from flask import abort, current_app, g, request


def current_user_id(required=False):
    if not hasattr(g, "mtg_user_id"):
        cookie = request.cookies.get("kachhapa_session")
        bearer = request.headers.get("Authorization", "")
        g.mtg_user_id = None
        if cookie or bearer:
            base = current_app.config["KACHHAPA_AUTH_URL"].rstrip("/")
            try:
                # Fixed configured upstream; no client URLs, redirects or arbitrary identity headers.
                if bearer:
                    response = requests.get(base + "/api/profile", headers={"Authorization": bearer},
                                            timeout=(3, 5), allow_redirects=False)
                else:
                    response = requests.get(base + "/api/session", cookies={"kachhapa_session": cookie},
                                            timeout=(3, 5), allow_redirects=False)
                if response.status_code == 200:
                    uid = response.json().get("id")
                    if not isinstance(uid, int) or isinstance(uid, bool) or uid <= 0:
                        abort(503, description="Identity service returned an invalid account")
                    g.mtg_user_id = uid
                elif response.status_code not in (401, 403):
                    abort(503, description="Identity service unavailable")
            except (requests.RequestException, ValueError):
                abort(503, description="Identity service unavailable")
        if cookie and not bearer and request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("Origin")
            if origin and urlsplit(origin).netloc != request.host:
                abort(403, description="Cross-origin deck changes are not allowed")
    if required and g.mtg_user_id is None:
        abort(401, description="Sign in to Kachhapa to use your personal library")
    return g.mtg_user_id


def check_deck_access(deck, *, edit=False):
    uid = current_user_id()
    if deck.ownerUserId is not None and deck.ownerUserId != uid:
        abort(404, description="Deck not found")
    if edit and deck.libraryStatus != "saved":
        abort(409, description="Save or restore this deck before editing it")
    return deck
