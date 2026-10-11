#!/bin/bash
# Install / update the MGID spend stop-loss on Inferno (systemd timer, every 2 minutes).
# Its own directory, units and state: the placement guard (mgid-guard) is not touched.
# The token comes from /etc/mgid-guard.env, which the guard already uses.
#
#   TAILSCALE="/path/tailscale --socket=/path/ts.sock" bash deploy_spend_stop_inferno.sh
#
# Order: stage and compile on the box; dry run of the staged code (pauses nothing); swap; units; start.
# Rollback: systemctl disable --now mgid-spend-stop.timer
# Secrets travel on stdin only, never on a command line, never echoed.
set -euo pipefail
TS="${TAILSCALE:-tailscale}"
HOST=root@100.121.239.113
HERE="$(cd "$(dirname "$0")" && pwd)"

python3 -m py_compile "$HERE/mgid_api.py" "$HERE/spend_stop.py"
(cd "$HERE" && python3 -m unittest test_spend_stop >/dev/null 2>&1) || { echo "test_spend_stop не проходит — не выкладываю"; exit 1; }

# 1. stage + compile
tar -C "$HERE" -cf - mgid_api.py spend_stop.py | base64 -w0 | $TS ssh "$HOST" \
  'set -e; rm -rf /opt/mgid-spend-stop.new && mkdir -p /opt/mgid-spend-stop.new /var/lib/mgid-spend-stop && chmod 700 /var/lib/mgid-spend-stop
   base64 -d | tar -C /opt/mgid-spend-stop.new -xf -
   python3 -m py_compile /opt/mgid-spend-stop.new/mgid_api.py /opt/mgid-spend-stop.new/spend_stop.py && echo staged'

# 2. dry run of the staged code (no --apply: pauses nothing), then swap and units
$TS ssh "$HOST" 'bash -s' <<'REMOTE'
set -e
echo "--- dry run (pauses nothing)"
rc=0
timeout 300 bash -c 'set -a; . /etc/mgid-guard.env; set +a; MGID_SPEND_ACTIONS=/tmp/mgid-spend-dry.log python3 /opt/mgid-spend-stop.new/spend_stop.py' \
  < /dev/null > /tmp/mgid-spend-dry.out 2>&1 || rc=$?
cut -c1-200 /tmp/mgid-spend-dry.out | head -30
rm -f /tmp/mgid-spend-dry.out /tmp/mgid-spend-dry.log
test "$rc" = 0 || { echo "dry run упал (код $rc) — ничего не установлено"; rm -rf /opt/mgid-spend-stop.new; exit 1; }
echo "--- swap"
rm -rf /opt/mgid-spend-stop && mv /opt/mgid-spend-stop.new /opt/mgid-spend-stop
cat > /etc/systemd/system/mgid-spend-stop.service <<"EOF"
[Unit]
Description=MGID stop-loss: pause every active campaign whose lifetime spend reaches $3

[Service]
Type=oneshot
EnvironmentFile=/etc/mgid-guard.env
Environment=MGID_SPEND_LIMIT=3.0
Environment=MGID_SPEND_ACTIONS=/var/lib/mgid-spend-stop/actions.log
WorkingDirectory=/var/lib/mgid-spend-stop
ExecStart=/usr/bin/flock -n /var/lib/mgid-spend-stop/.lock /usr/bin/python3 /opt/mgid-spend-stop/spend_stop.py --apply
TimeoutStartSec=300
EOF
cat > /etc/systemd/system/mgid-spend-stop.timer <<"EOF"
[Unit]
Description=Run the MGID stop-loss every 2 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
AccuracySec=10s
Persistent=true

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now mgid-spend-stop.timer >/dev/null 2>&1
systemctl start --no-block mgid-spend-stop.service || true
echo "--- timer"
systemctl list-timers mgid-spend-stop.timer --no-pager | head -3
REMOTE
