#!/bin/sh
set -eu

# Existing databases must be upgraded by Alembic, never by db.create_all().
# Docker's loopback address is not the external Kachhapa identity service.
python - <<'PY'
import os
from urllib.parse import urlsplit
import requests
url = os.environ.get('KACHHAPA_AUTH_URL', '').rstrip('/')
parsed = urlsplit(url)
if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.hostname in ('localhost', '127.0.0.1', '::1', '0.0.0.0'):
    raise SystemExit('Set KACHHAPA_AUTH_URL to a reachable external Kachhapa service, e.g. http://host.docker.internal')
try:
    response = requests.get(url + '/api/session', timeout=(3, 5), allow_redirects=False)
    if response.status_code not in (200, 401) or not isinstance(response.json(), dict):
        raise ValueError('Unexpected identity endpoint response')
except (requests.RequestException, ValueError):
    raise SystemExit('Kachhapa identity endpoint is unreachable or invalid; verify KACHHAPA_AUTH_URL')
PY
python -m flask --app run:app db upgrade
exec "$@"
