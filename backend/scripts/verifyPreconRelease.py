"""Operator-run release evidence: backup, live auth/proxy probes and PostgreSQL plans.

Run from backend with its existing virtualenv. Credentials come only from the
service environment; reports never contain cookies, access tokens or database URLs.
This cannot certify the manual signed-in browser smoke test.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select, func, text
from sqlalchemy.engine import make_url
import requests
from app import create_app
from app.extensions import db
from app.models.mtgCore import Card
from app.models.mtgDecks import Deck
from app.models.mtgGames import GamePlayer
from app.models.mtgPrecons import PreconTemplate, PreconTemplateVersion
from app.services.statistics import participation_query


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-dir", type=Path, help="Back up first, before running migrations; no live API probe")
    parser.add_argument("--base-url", help="Deployed frontend origin with /mtg prefix when applicable")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--origins-out", type=Path, help="Capture personal origins before full catalog sync")
    parser.add_argument("--origins-before", type=Path, help="Compare personal origins after full catalog sync")
    args = parser.parse_args()
    if not os.getenv("DATABASE_URL"):
        parser.error("Set DATABASE_URL to the populated target database")
    if args.backup_dir:
        if not shutil.which("pg_dump") or not shutil.which("pg_restore"):
            parser.error("Install PostgreSQL client utilities before taking the backup")
        args.backup_dir.mkdir(parents=True, exist_ok=True)
        args.backup_dir.chmod(0o700)
        target = args.backup_dir / ("mtg-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".dump")
        url = make_url(os.environ["DATABASE_URL"]).set(drivername="postgresql")
        env = dict(os.environ, PGDATABASE=url.render_as_string(hide_password=False))
        # Credentials stay in the child environment, not command arguments or logs.
        subprocess.run(["pg_dump", "--format=custom", "--file", str(target)], env=env, check=True)
        target.chmod(0o600)
        subprocess.run(["pg_restore", "--list", str(target)], stdout=subprocess.DEVNULL, check=True)
        print("Backup created and its archive directory verified:", target)
        return
    app = create_app()
    evidence = {"releaseReady": False, "signedInBrowserSmokeTest": "pending", "checks": {}}
    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            parser.error("Live release validation requires PostgreSQL")
        db.session.execute(text("SET LOCAL statement_timeout = '30s'"))
        revisions = list(db.session.scalars(text("SELECT version_num FROM alembic_version")))
        evidence["checks"]["migrationsApplied"] = revisions == ["a93c4e125b87"]
        origins = [dict(id=d.id, sourcePreconId=d.sourcePreconId, sourcePreconVersionId=d.sourcePreconVersionId)
                   for d in db.session.scalars(select(Deck).where(Deck.sourcePreconId.is_not(None)).order_by(Deck.id))]
        if args.origins_out:
            args.origins_out.write_text(json.dumps(origins, indent=2) + "\n")
            args.origins_out.chmod(0o600)
            print("Captured personal origins:", len(origins))
            return
        if args.origins_before:
            original = {d["id"]: d for d in json.loads(args.origins_before.read_text())}
            current = {d["id"]: d for d in origins}
            if any(current.get(key) != value for key, value in original.items()):
                raise RuntimeError("Personal origins changed during catalog synchronization")
            evidence["checks"]["personalOriginsUnchanged"] = True
        evidence["counts"] = {name: db.session.scalar(select(func.count()).select_from(cls))
                              for name, cls in (("cards", Card), ("precons", PreconTemplate), ("participants", GamePlayer))}
        incomplete = db.session.execute(select(PreconTemplate.id, PreconTemplate.name, PreconTemplateVersion.issues)
            .join(PreconTemplateVersion, PreconTemplate.current_version_id == PreconTemplateVersion.id)
            .where(PreconTemplateVersion.status != "complete")).mappings().all()
        evidence["incompleteCatalog"] = [dict(row) for row in incomplete]
        if not args.base_url or not args.report:
            parser.error("Live probe requires --base-url and --report")
        token = os.environ.get("MTG_SESSION_COOKIE")
        if not token:
            parser.error("Set MTG_SESSION_COOKIE locally from a signed-in test session; never paste credentials into a report")
        base = args.base_url.rstrip("/")
        auth = app.config["KACHHAPA_AUTH_URL"].rstrip("/")
        session = requests.Session()
        # Pass the cookie only to the two explicitly configured trusted destinations.
        cookies = {"kachhapa_session": token}
        verified = session.get(auth + "/api/session", cookies=cookies, timeout=(3, 10), allow_redirects=False)
        if verified.status_code != 200:
            raise RuntimeError("Live Kachhapa session verification failed")
        uid = verified.json().get("id")
        if not isinstance(uid, int) or isinstance(uid, bool):
            raise RuntimeError("Identity endpoint did not return a valid account")
        evidence["checks"]["liveIdentity"] = True
        for name, suffix in (("catalogProxy", "/api/precons?limit=1"), ("statisticsProxy", "/api/profile/stats")):
            start = time.perf_counter()
            result = session.get(base + suffix, cookies=cookies, timeout=(3, 30), allow_redirects=False)
            if result.status_code != 200:
                raise RuntimeError(name + " failed")
            result.json()
            evidence["checks"][name] = True
            evidence[name + "Ms"] = round(1000 * (time.perf_counter() - start), 2)
        socket = session.get(base + "/socket.io/", params={"EIO": 4, "transport": "polling"}, timeout=(3, 10))
        evidence["checks"]["socketProxy"] = socket.status_code == 200 and socket.text.startswith("0{")
        stats = participation_query(uid, library=True).subquery()
        queries = {"catalog": select(PreconTemplate.id).where(PreconTemplate.name.ilike("%dragon%")).limit(25),
                   "statistics": select(func.count()).select_from(stats).where(stats.c.category == "competitive")}
        evidence["queryPlans"] = {}
        for name, query in queries.items():
            compiled = str(query.compile(dialect=db.engine.dialect, compile_kwargs={"literal_binds": True}))
            plan = db.session.execute(text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + compiled)).scalar_one()[0]
            evidence["queryPlans"][name] = {key: plan.get(key) for key in ("Planning Time", "Execution Time")}
        evidence["checks"]["catalogPopulated"] = evidence["counts"]["precons"] > 0
        evidence["incompleteCatalogReview"] = "pending" if incomplete else "not needed"
        evidence["timestamp"] = datetime.now(timezone.utc).isoformat()
        args.report.write_text(json.dumps(evidence, indent=2) + "\n")
        args.report.chmod(0o600)
        print("Live API/SQL evidence saved. Browser smoke and release review still required.")
        if not all(evidence["checks"].values()):
            raise SystemExit("Release gate remains blocked; review the report")


if __name__ == "__main__":
    main()
