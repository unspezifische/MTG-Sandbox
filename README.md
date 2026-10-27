This is mainly intended as an add-on service for [https://github.com/unspezifische/Kachhapa--The-World-Turtle | cKachhapa- the World Turtle], which is itself a TTRPG campaign manager. The MtG Sandbox web app is intended as a stand-along service, using the same database backend and routing already provided by Kachhapa, to enable user to build their own Magic decks, along with a plethora of resources for examining deck metrics, goldfishing capabilities, simulating games using heuristic AI, and playing against other players in realtime. Since an important part of learning is from mistakes, games are saved and stored in a way that allows players to review a match afterwards and find clues they missed or, with the assistance of the heuristic AI, test alternate methods for dealing with opponents to explore different branches of how a match *could* have gone instead.

# Populate the MTG card database

The catalog importer reads `data/AllPrintings.sqlite` and populates the
`mtgCore` PostgreSQL schema with both cards and tokens. Make sure that source
file exists and is not empty before starting the import. Normal imports upsert
by MTGJSON UUID, preserving the database IDs already referenced by saved decks
and games.

For the Docker stack, start the database and backend, then run the importer in
the backend container:

```sh
docker compose up -d --build db backend
docker compose exec -T backend python scripts/importAllPrintings.py
```

For the bare-metal Raspberry Pi installation, initialize and migrate the
database first, then run:

```sh
cd /home/ijohnson/MtG-webapp/backend
PG_RAW_URL='postgresql://admin:admin@127.0.0.1:5432/mtg_sandbox' \
MTGJSON_SQLITE_PATH='/home/ijohnson/MtG-webapp/data/AllPrintings.sqlite' \
/home/ijohnson/MtG-webapp/venv/bin/python scripts/importAllPrintings.py
```

The importer prints the final set, card, token, face, printing, and product
counts when it completes. Do not use `--wipe-core` on a populated deployment;
that destructive rebuild mode can cascade into saved deck and game data. After
refreshing the core catalog, rerun the precon sync so previously unresolved
token UUIDs can attach to their imported records:

```sh
cd /home/ijohnson/MtG-webapp
source venv/bin/activate
cd backend
python -m flask --app run:app sync-precons
```

Every sync writes `backend/precon-sync-results.json`, including aggregate
counts and each incomplete or failed deck's stable `fileName`, name, code, and
issues/error. After repairing the card catalog or a transient download problem,
retry only those entries with:

```sh
python -m flask --app run:app sync-precons \
  --retry-report precon-sync-results.json \
  --report precon-sync-retry-results.json
```

# Raspberry Pi (no Docker)

The backend uses Gunicorn with one gevent-websocket worker. Keep the worker
count at one unless the deployment adds sticky Socket.IO routing and a shared
message queue; Engine.IO polling sessions otherwise can land on a process that
does not own them.

## OPTION 1- Add MTG Sandbox routes to an existing nginx config
Use the additive helper script in [backend/scripts/add_mtg_nginx_proxy.sh](backend/scripts/add_mtg_nginx_proxy.sh).

1. Make the script executable:
	`chmod +x backend/scripts/add_mtg_nginx_proxy.sh`
2. Patch your existing nginx config in place:
	`sudo backend/scripts/add_mtg_nginx_proxy.sh /etc/nginx/nginx.conf`
	or
	`sudo backend/scripts/add_mtg_nginx_proxy.sh /etc/nginx/sites-available/default`

The script creates a timestamped backup, inserts or updates a marker-delimited MTG block, runs `nginx -t`, and tells you to reload nginx.

## OPTION 2- Install standalone backend service
Use [backend/mtg-backend-standalone.service](backend/mtg-backend-standalone.service) as a template.

1. Copy env template and set DB credentials:
	`sudo cp backend/mtg-backend.env.example /etc/default/mtg-sandbox-backend`
2. Copy service unit and adjust paths/user (`/home/pi`, `User=pi`) if needed:
	`sudo cp backend/mtg-backend-standalone.service /etc/systemd/system/mtg-backend.service`
3. Enable and start:
	`sudo systemctl daemon-reload`
	`sudo systemctl enable --now mtg-backend.service`

The backend listens on `127.0.0.1:5050` and is intended to be exposed only through nginx reverse proxy routes.'

# Docker Container
This stack can also be run in a Docker environment. The included `docker-compose.yaml` can be used by running 'docker compose --build -d' in the terminal window. As always, make sure the Docker engine is already running.
