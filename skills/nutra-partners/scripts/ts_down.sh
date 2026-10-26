#!/usr/bin/env bash
# Leave the tailnet the way ts_tun_up.sh joined it: stop the daemon, then delete the offline node through the Tailscale API
# (vault: service `tailscale`, field TS_API_TOKEN). Run it at the end of the job, a forgotten node stays in the owner's tailnet.
# NOTE: never `pkill -f "tailscaled ..."` with a plain pattern, it matches (and kills) your own shell; the bracket below avoids that.
set -uo pipefail
D=${TS_DIR:-/tmp/ts}
HERE=$(cd "$(dirname "$0")" && pwd)
VAULT=${VAULT:-$(ls /root/.claude/skills/synced/*/secrets/vault.mjs 2>/dev/null | head -1)}
pkill -f "[t]ailscaled --state=$D/tun.state" || true
sleep 4
node "$VAULT" exec tailscale -- node "$HERE/ts_cleanup.mjs" || echo "!!! the node stays in the tailnet (offline) until it is deleted by hand: see the message above"
rm -f "$D/tun.state" "$D/tun.sock" "$D/authkey.txt"
