#!/usr/bin/env bash
# Start the userspace tailscaled of this Claude session and join the tailnet under a fresh node name, so that
# `tailscale ssh root@100.121.239.113 ...` works (deploy.py, geozo_report.py). Port 22 is blocked in the sandbox, tailscale is the
# only way in. The daemon keeps its state in memory and dies with the container and, now and then, without it (14.10 night: twice in
# three hours); every restart is a new node, so the name gets a suffix. Old offline nodes: delete them with the tailscale API when
# the work with the server is over.
#
#     bash geozo_site/ts_up.sh [suffix]        # node name cc-mgid-arcadia-<suffix>, default: epoch seconds
#
# The auth key comes from the vault (service tailscale, field TS_AUTHKEY), goes to a 0600 file only for the `tailscale up` and is
# deleted right after; it is never printed.
set -euo pipefail
TS_DIR=${TS_DIR:-/tmp/claude-0/ts}
TS_VER=${TS_VER:-tailscale_1.104.1_amd64}
VAULT=${VAULT:-$(ls /root/.claude/skills/synced/*/secrets/vault.mjs | head -1)}
export CLAUDE_VAULT_FILE=${CLAUDE_VAULT_FILE:-$HOME/.claude/secrets/vault.enc.json}
NAME="cc-mgid-arcadia-${1:-$(date +%s)}"

mkdir -p "$TS_DIR"
cd "$TS_DIR"
if [ ! -x "./$TS_VER/tailscaled" ]; then
  curl -fsSL "https://pkgs.tailscale.com/stable/$TS_VER.tgz" -o "$TS_VER.tgz"
  tar -xzf "$TS_VER.tgz"
fi
if "./$TS_VER/tailscale" --socket ./ts.sock status >/dev/null 2>&1; then
  echo "tailscaled уже работает"
  "./$TS_VER/tailscale" --socket ./ts.sock status | head -2
  exit 0
fi
umask 077
node "$VAULT" get tailscale TS_AUTHKEY | tr -d '\n' > authkey.txt
trap 'rm -f "$TS_DIR/authkey.txt"' EXIT
rm -f ts.sock
(setsid nohup "./$TS_VER/tailscaled" --tun=userspace-networking --state=mem: --socket="$TS_DIR/ts.sock" >> tailscaled.log 2>&1 &)
sleep 5
"./$TS_VER/tailscale" --socket ./ts.sock up --auth-key=file:"$TS_DIR/authkey.txt" --hostname="$NAME" \
  --accept-dns=false --accept-routes=false --timeout=60s
rm -f authkey.txt
"./$TS_VER/tailscale" --socket ./ts.sock status | head -2
