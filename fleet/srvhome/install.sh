#!/usr/bin/env bash
# srvhome installer - run ON the target server (no sudo needed).
#
#   ./install.sh
#
# - back-fills the deploy DB from `git log` for every app in apps.json
#   (so history is not empty on day one),
# - installs the post-merge hook into each app repo,
# - installs a user crontab keepalive (@reboot + per-minute run.sh).
#
# The Nginx route and (optionally) the systemd unit still need Brad's
# sudo - see nginx-snippet.conf and srvhome.service.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "== srvhome install ( $DIR ) =="
command -v python3 >/dev/null || { echo "python3 not found"; exit 1; }

BACKFILL_N="${BACKFILL_N:-30}"

# emit "name<TAB>expanded-path" per app, using python (no jq dependency)
python3 - "$DIR/apps.json" <<'PY' | while IFS=$'\t' read -r name path; do
import json, os, sys
for a in json.load(open(sys.argv[1])):
    p = os.path.expanduser(a["path"])
    print(f"{a['name']}\t{p}")
PY
  if [ ! -d "$path/.git" ]; then
    echo "  ! $name: $path is not a git repo - skipping"
    continue
  fi
  echo "  - $name: backfilling last $BACKFILL_N commits"
  python3 record_deploy.py --backfill "$name" "$path" "$BACKFILL_N"

  hook="$path/.git/hooks/post-merge"
  install -m 0755 hooks/post-merge "$hook"
  sed -i "s#^SRVHOME_DIR=.*#SRVHOME_DIR=\"\${SRVHOME_DIR:-$DIR}\"#" "$hook"
  echo "    installed hook -> $hook"
done

# --- srvhome tracks its OWN version too, when it runs from a git checkout ---
# (the BdRPiSrvAMI deploy is a read-only BdRDev checkout run from fleet/srvhome/).
if SELF_ROOT="$(git -C "$DIR" rev-parse --show-toplevel 2>/dev/null)"; then
  echo "  - srvhome: backfilling own history from $SELF_ROOT (as 'srvhome')"
  python3 record_deploy.py --backfill --path fleet/srvhome \
    srvhome "$SELF_ROOT" "$BACKFILL_N" || true
  hook="$SELF_ROOT/.git/hooks/post-merge"
  install -m 0755 hooks/post-merge "$hook"
  sed -i "s#^SRVHOME_DIR=.*#SRVHOME_DIR=\"\${SRVHOME_DIR:-$DIR}\"#" "$hook"
  sed -i "s#^SRVHOME_APP_NAME=.*#SRVHOME_APP_NAME=\"srvhome\"#" "$hook"
  sed -i "s#^SRVHOME_APP_PATH=.*#SRVHOME_APP_PATH=\"fleet/srvhome\"#" "$hook"
  echo "    installed self-hook -> $hook"
else
  echo "  - srvhome: not a git checkout ($DIR) - self version-check disabled"
fi

# --- keepalive via user crontab (works without linger / without sudo) ---
RUN="$DIR/run.sh"
TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -v "srvhome/run.sh" > "$TMP" || true
{
  echo "@reboot $RUN            # srvhome/run.sh"
  echo "* * * * * $RUN          # srvhome/run.sh"
} >> "$TMP"
crontab "$TMP"
rm -f "$TMP"
echo "  - user crontab keepalive installed"

"$RUN" || true
sleep 1
echo "== health: $(curl -s http://127.0.0.1:8610/healthz || echo UNREACHABLE) =="
