#!/usr/bin/env bash
# Local API of the Vision antidetect app on vision-box (Coolify, Hostinger), through the tailnet (ts_tun_up.sh first).
# The X-Token (vault: service `browser-vision`, field VISION_API_TOKEN) goes to curl on stdin, never on the command line.
#
#   bash vision.sh list                              # running profiles: folder_id, profile_id, pid, port
#   bash vision.sh start <folder_id> <profile_id>    # {"success":true,...,"port":N}; N is the CDP port, it changes on every start
#   bash vision.sh stop  <folder_id> <profile_id>    # stop only profiles you started yourself
#
# VISION_HOST: tailnet address of vision-box (default 100.110.129.11; vault service `vision-box` has VISION_BOX_TS_HOSTNAME).
set -euo pipefail
HOST=${VISION_HOST:-100.110.129.11}
VAULT=${VAULT:-$(ls /root/.claude/skills/synced/*/secrets/vault.mjs 2>/dev/null | head -1)}
case "${1:-}" in
  list)  P=/list ;;
  start) P=/start/${2:?folder_id}/${3:?profile_id} ;;
  stop)  P=/stop/${2:?folder_id}/${3:?profile_id} ;;
  *) sed -n 2,8p "$0"; exit 1 ;;
esac
node "$VAULT" exec browser-vision -- bash -c \
  'printf "header = \"X-Token: %s\"\n" "$VISION_API_TOKEN" | curl -sS -m 120 -K - "$0"' "http://$HOST:3030$P"
echo
