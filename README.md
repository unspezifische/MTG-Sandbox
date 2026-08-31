This is mainly intended as an add-on service for [https://github.com/unspezifische/Kachhapa--The-World-Turtle | cKachhapa- the World Turtle], which is itself a TTRPG campaign manager. The MtG Sandbox web app is intended as a stand-along service, using the same database backend and routing already provided by Kachhapa, to enable user to build their own Magic decks, along with a plethora of resources for examining deck metrics, goldfishing capabilities, simulating games using heuristic AI, and playing against other players in realtime. Since an important part of learning is from mistakes, games are saved and stored in a way that allows players to review a match afterwards and find clues they missed or, with the assistance of the heuristic AI, test alternate methods for dealing with opponents to explore different branches of how a match *could* have gone instead.

## Raspberry Pi (no Docker)

### OPTION 1- Add MTG Sandbox routes to an existing nginx config

Use the additive helper script in [backend/scripts/add_mtg_nginx_proxy.sh](backend/scripts/add_mtg_nginx_proxy.sh).

1. Make the script executable:
	`chmod +x backend/scripts/add_mtg_nginx_proxy.sh`
2. Patch your existing nginx config in place:
	`sudo backend/scripts/add_mtg_nginx_proxy.sh /etc/nginx/nginx.conf`
	or
	`sudo backend/scripts/add_mtg_nginx_proxy.sh /etc/nginx/sites-available/default`

The script creates a timestamped backup, inserts or updates a marker-delimited MTG block, runs `nginx -t`, and tells you to reload nginx.

### OPTION 2- Install standalone backend service

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