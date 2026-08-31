#!/usr/bin/env bash
set -euo pipefail

# Add or update MTG Sandbox reverse-proxy routes in an existing nginx server block.
#
# This script is additive: it does not replace your nginx config.
# It inserts a marker-delimited block into the first server { ... } block,
# or updates that block if it already exists.
#
# Usage:
#   sudo ./add_mtg_nginx_proxy.sh /etc/nginx/nginx.conf
#   sudo ./add_mtg_nginx_proxy.sh /etc/nginx/sites-available/default

CONF_PATH="${1:-/etc/nginx/nginx.conf}"
BACKEND_UPSTREAM="${BACKEND_UPSTREAM:-http://127.0.0.1:5050}"
BEGIN_MARKER="# BEGIN MTG_SANDBOX_PROXY"
END_MARKER="# END MTG_SANDBOX_PROXY"

if [[ ! -f "$CONF_PATH" ]]; then
  echo "Config not found: $CONF_PATH" >&2
  exit 1
fi

TMP_FILE="$(mktemp)"
BACKUP_PATH="${CONF_PATH}.mtg-sandbox.bak.$(date +%Y%m%d%H%M%S)"

BLOCK_CONTENT=$(cat <<EOF
  $BEGIN_MARKER
  location = /mtg/api {
    return 301 /mtg/api/;
  }

  location /mtg/api/ {
    proxy_pass ${BACKEND_UPSTREAM}/api/;
    proxy_http_version 1.1;

    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }

  location /mtg/socket.io/ {
    proxy_pass ${BACKEND_UPSTREAM}/socket.io/;
    proxy_http_version 1.1;

    proxy_set_header Upgrade \$http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }
  $END_MARKER
EOF
)

cp "$CONF_PATH" "$BACKUP_PATH"
echo "Backup created: $BACKUP_PATH"

if grep -q "$BEGIN_MARKER" "$CONF_PATH"; then
  awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" -v block="$BLOCK_CONTENT" '
    $0 ~ begin {
      print block
      in_block=1
      next
    }
    in_block && $0 ~ end {
      in_block=0
      next
    }
    !in_block { print }
  ' "$CONF_PATH" > "$TMP_FILE"
else
  server_end_line=$(awk '
    function open_count(s,   t) { t = s; return gsub(/\{/, "{", t) }
    function close_count(s,  t) { t = s; return gsub(/\}/, "}", t) }
    {
      line = $0
      if (!in_server && line ~ /^[[:space:]]*server[[:space:]]*\{/) {
        in_server = 1
        depth = open_count(line) - close_count(line)
        if (depth == 0) {
          print NR
          exit
        }
        next
      }

      if (in_server) {
        depth += open_count(line)
        depth -= close_count(line)
        if (depth == 0) {
          print NR
          exit
        }
      }
    }
  ' "$CONF_PATH")

  if [[ -z "$server_end_line" ]]; then
    echo "Could not locate a server block in $CONF_PATH" >&2
    echo "Original file preserved at: $BACKUP_PATH" >&2
    exit 1
  fi

  awk -v insert_line="$server_end_line" -v block="$BLOCK_CONTENT" '
    NR == insert_line { print block }
    { print }
  ' "$CONF_PATH" > "$TMP_FILE"
fi

mv "$TMP_FILE" "$CONF_PATH"

if nginx -t; then
  echo "nginx config test passed."
  echo "Reload with: sudo systemctl reload nginx"
else
  echo "nginx config test failed. Restoring backup..." >&2
  cp "$BACKUP_PATH" "$CONF_PATH"
  exit 1
fi
