This is mainly intended as an add-on service for [Kachhapa- the World Turtle|https://github.com/unspezifische/Kachhapa--The-World-Turtle], which is itself a TTRPG campaign manager. The MtG Sandbox web app is intended as a stand-along service, using the same database backend and routing already provided by Kachhapa, to enable user to build their own Magic decks, along with a plethora of resources for examining deck metrics, goldfishing capabilities, simulating games using heuristic AI, and playing against other players in realtime. Since an important part of learning is from mistakes, games are saved and stored in a way that allows players to review a match afterwards and find clues they missed or, with the assistance of the heuristic AI, test alternate methods for dealing with opponents to explore different branches of how a match *could* have gone instead.

## Raspberry Pi Full Stack Setup (Docker Compose)

These steps run the full stack (Postgres + Flask backend + React frontend served by Nginx) on a Raspberry Pi.

### 1) Prerequisites

- Raspberry Pi 4 or 5 (8 GB RAM recommended)
- 64-bit Raspberry Pi OS (Bookworm or newer)
- At least 15 GB free disk space for images, containers, and database growth

Install Docker and Compose plugin:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker compose version
```

### 2) Clone and prepare project files

```bash
git clone https://github.com/unspezifische/MTG-Sandbox.git
cd MTG-Sandbox
```

The backend expects the MTGJSON SQLite source file at `data/AllPrintings.sqlite`.

If you already have it, copy it in:

```bash
mkdir -p data
cp /path/to/AllPrintings.sqlite data/AllPrintings.sqlite
```

### 3) Build and start the full stack

```bash
docker compose up -d --build
docker compose ps
```

Services and ports:

- Frontend (Nginx): `http://<pi-ip>:3000`
- Backend API (direct): `http://<pi-ip>:5050`
- Postgres: `<pi-ip>:5433` (host port)

### 4) First-time card data import (required once)

After containers are healthy, import from SQLite into Postgres:

```bash
docker compose exec backend python scripts/importAllPrintings.py
```

Notes:

- This can take a while on Pi hardware.
- If interrupted, re-run the same command.

### 5) Verify the app is reachable

```bash
curl -I http://localhost:3000
curl -I http://localhost:5050
```

Then open `http://<pi-ip>:3000` from another device on the same network.

### 6) Common operations

Start/stop:

```bash
docker compose up -d
docker compose down
```

View logs:

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

Rebuild after code changes:

```bash
docker compose up -d --build
```