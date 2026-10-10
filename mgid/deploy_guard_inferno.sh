#!/bin/bash
# Install / update the MGID placement guard on Inferno (systemd timer, every 5 minutes).
# Touches nothing else on the box: the middleware, TDS and the other guards stay as they are.
# The guard only READS the middleware's database (sqlite mode=ro).
#
#   bash deploy_guard_inferno.sh            # code + units (keeps the existing /etc/mgid-guard.env)
#   node <vault.mjs> exec mgid -- bash deploy_guard_inferno.sh --env
#                                           # also (re)write /etc/mgid-guard.env from MGID_816929_TOKEN
#
# Needs the tailnet up. A plain `ssh` to port 22 hangs from a Claude sandbox, so everything goes
# through `tailscale ssh`; TAILSCALE can carry the binary and its socket when it is not on PATH:
#   TAILSCALE="/path/tailscale --socket=/path/ts.sock" bash deploy_guard_inferno.sh
#
# Order, so that a bad build never replaces a working guard:
#   1. stage the new code beside the live one and compile it on the box;
#   2. DRY RUN the staged code against the live API and the live middleware tables; a failure aborts;
#   3. back up the live code (/opt/mgid-guard/backup-<utc>/), swap, rewrite the unit;
#   4. start the service once and show its journal.
# Rollback: cp /opt/mgid-guard/backup-<utc>/*.py /opt/mgid-guard/ && systemctl start mgid-guard.service
# (the unit keeps working with the old code: it only reads env that the old code ignores).
#
# Secrets travel on stdin only, never on a command line, never echoed.
set -euo pipefail
TS="${TAILSCALE:-tailscale}"
HOST=root@100.121.239.113
HERE="$(cd "$(dirname "$0")" && pwd)"

python3 -m py_compile "$HERE/mgid_api.py" "$HERE/mgid_guard.py"
(cd "$HERE" && python3 -m unittest test_guard >/dev/null 2>&1) || { echo "test_guard не проходит — не выкладываю"; exit 1; }

# 1. stage + compile
tar -C "$HERE" -cf - mgid_api.py mgid_guard.py | base64 -w0 | $TS ssh "$HOST" \
  'set -e; mkdir -p /opt/mgid-guard /var/lib/mgid-guard && chmod 700 /var/lib/mgid-guard
   rm -rf /opt/mgid-guard.new && mkdir /opt/mgid-guard.new
   base64 -d | tar -C /opt/mgid-guard.new -xf -
   python3 -m py_compile /opt/mgid-guard.new/mgid_api.py /opt/mgid-guard.new/mgid_guard.py && echo staged'

# 2. credentials (optional): KEY="value", quotes and backslashes escaped for systemd
if [ "${1:-}" = "--env" ]; then
  python3 - <<'EOF' | base64 -w0 | $TS ssh "$HOST" \
    'umask 077 && base64 -d > /etc/mgid-guard.env && chmod 600 /etc/mgid-guard.env && echo env ok'
import os
def q(v):
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
print("MGID_816929_TOKEN=" + q(os.environ["MGID_816929_TOKEN"]))
EOF
fi

# 3. dry run of the staged code, then swap
$TS ssh "$HOST" 'bash -s' <<'REMOTE'
set -e
set -a; . /etc/mgid-guard.env; set +a
echo "--- dry run (nothing is written, state goes to /tmp)"
rc=0
MGID_GUARD_STATE=/tmp/mgid-guard-dry.json MGID_GUARD_ACTIONS=/tmp/mgid-guard-dry.log \
  python3 /opt/mgid-guard.new/mgid_guard.py > /tmp/mgid-guard-dry.out 2>&1 || rc=$?
cut -c1-220 /tmp/mgid-guard-dry.out | head -40
rm -f /tmp/mgid-guard-dry.out
test "$rc" = 0 || { echo "dry run упал (код $rc) — старый сторож остаётся"; rm -rf /opt/mgid-guard.new; exit 1; }
echo "--- swap"
B=/opt/mgid-guard/backup-$(date -u +%Y%m%d-%H%M%S)
mkdir -p "$B" && cp -p /opt/mgid-guard/*.py "$B"/ 2>/dev/null || true
mv /opt/mgid-guard.new/mgid_api.py /opt/mgid-guard.new/mgid_guard.py /opt/mgid-guard/
rm -rf /opt/mgid-guard.new /tmp/mgid-guard-dry.json /tmp/mgid-guard-dry.log
echo "backup: $B"
cat > /etc/systemd/system/mgid-guard.service <<"EOF"
[Unit]
Description=MGID dating guard: block placements that spent 2 conversion costs of their campaign without a lead
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/mgid-guard.env
Environment=MGID_GUARD_MULT=2
Environment=MGID_GUARD_THRESH=0.30
Environment=MGID_OFFERS=9962,8326,8394,8395
Environment=MGID_GUARD_STATE=/var/lib/mgid-guard/state.json
Environment=MGID_GUARD_ACTIONS=/var/lib/mgid-guard/actions.log
Environment=MGID_LEADS_DB=/var/www/postback-middleware/accumulator_exocpa.db
WorkingDirectory=/var/lib/mgid-guard
ExecStart=/usr/bin/flock -w 60 /var/lib/mgid-guard/.lock /usr/bin/python3 /opt/mgid-guard/mgid_guard.py --apply
TimeoutStartSec=240
EOF
cat > /etc/systemd/system/mgid-guard.timer <<"EOF"
[Unit]
Description=Run the MGID placement guard every 5 minutes

[Timer]
OnBootSec=3min
OnUnitActiveSec=5min
AccuracySec=30s
Persistent=true

[Install]
WantedBy=timers.target
EOF
cat > /usr/local/bin/mgid-guard-status <<"EOF"
#!/bin/sh
# last run, holds, thresholds and every block of the MGID placement guard; never prints the token
MGID_GUARD_STATE=/var/lib/mgid-guard/state.json MGID_GUARD_ACTIONS=/var/lib/mgid-guard/actions.log \
  exec /usr/bin/python3 /opt/mgid-guard/mgid_guard.py status
EOF
chmod 755 /usr/local/bin/mgid-guard-status
systemctl daemon-reload
systemctl enable --now mgid-guard.timer >/dev/null 2>&1
systemctl start mgid-guard.service || true
journalctl -u mgid-guard.service -n 14 --no-pager -o cat
systemctl list-timers mgid-guard.timer --no-pager | head -3
REMOTE
