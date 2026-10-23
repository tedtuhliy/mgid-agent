#!/usr/bin/env bash
# Join the owner's tailnet from the sandbox with a REAL TUN device. The userspace tailscaled cannot carry curl/ssh/CDP to tailnet
# addresses, only a daemon with a TUN device can. The auth key (vault: service `tailscale`, field TS_AUTHKEY) goes through a 0600 file
# that is removed on exit; it never reaches the command line or stdout.
#
#   bash ts_tun_up.sh [suffix]      # node name cc-mgid-arcadia-<suffix>, default "vb"
#   bash ts_down.sh                 # when done: stop the daemon and delete the node
#
# TS_DIR (default /tmp/ts) holds the static tailscale build, the state and the socket. The build is fetched from pkgs.tailscale.com.
# The vault must be the FRESH copy (see the `secrets` skill): the old local file of the container lacks some services.
set -euo pipefail
D=${TS_DIR:-/tmp/ts}; mkdir -p "$D"
VAULT=${VAULT:-$(ls /root/.claude/skills/synced/*/secrets/vault.mjs 2>/dev/null | head -1)}
BIN=$(ls -d "$D"/tailscale_*_amd64 2>/dev/null | tail -1 || true)
if [ -z "$BIN" ]; then
  curl -sS -m 30 'https://pkgs.tailscale.com/stable/?mode=json' -o "$D/idx.json"
  T=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['Tarballs']['amd64'])" "$D/idx.json")
  curl -sS -m 180 -o "$D/$T" "https://pkgs.tailscale.com/stable/$T"
  tar xzf "$D/$T" -C "$D"
  BIN=$D/${T%.tgz}
fi
SOCK=$D/tun.sock
if "$BIN/tailscale" --socket="$SOCK" status >/dev/null 2>&1; then
  echo "tun tailscaled already up"; "$BIN/tailscale" --socket="$SOCK" status | head -3; exit 0
fi
rm -f "$SOCK"
(setsid nohup "$BIN/tailscaled" --state="$D/tun.state" --socket="$SOCK" --port=41641 >> "$D/tun.log" 2>&1 < /dev/null &)
sleep 5
umask 077
node "$VAULT" exec tailscale -- bash -c 'printf %s "$TS_AUTHKEY" > "$0"' "$D/authkey.txt"
trap 'rm -f "$D/authkey.txt"' EXIT
timeout 90 "$BIN/tailscale" --socket="$SOCK" up --auth-key=file:"$D/authkey.txt" --hostname="cc-mgid-arcadia-${1:-vb}" \
  --accept-dns=false --accept-routes=false --netfilter-mode=off --timeout=60s
"$BIN/tailscale" --socket="$SOCK" status | head -12
