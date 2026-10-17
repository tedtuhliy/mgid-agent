#!/bin/bash
# Install the MGID stop-loss of the SECOND account on Inferno (systemd timer, every 2 minutes): pauses every active campaign of the
# account 816921 (v2 939023) whose spend since the reset reaches $3. Its own code directory, env file, state and units: the stop-loss
# of the first (blocked) account, mgid-spend-stop, is not touched and keeps failing quietly until MGID lets that account in again.
#
#   TAILSCALE="/path/tailscale --socket=/path/ts.sock" CLAUDE_VAULT_FILE=~/.claude/secrets/vault.enc.json bash deploy_spend_stop_second_inferno.sh
#
# Order: stage and compile on the box; the token goes into /etc/mgid-second.env through a pipe (never on a command line, never echoed);
# dry run of the staged code (pauses nothing); swap; reset the baseline (only spend from now on counts); units; start.
# Rollback: systemctl disable --now mgid-spend-stop-second.timer
set -euo pipefail
TS="${TAILSCALE:-tailscale}"
HOST=root@100.121.239.113
HERE="$(cd "$(dirname "$0")" && pwd)"
VAULT="${VAULT:-$(ls /root/.claude/skills/synced/*/secrets/vault.mjs | head -1)}"

python3 -m py_compile "$HERE/mgid_api.py" "$HERE/spend_stop.py"
(cd "$HERE" && python3 -m unittest test_spend_stop >/dev/null 2>&1) || { echo "test_spend_stop не проходит — не выкладываю"; exit 1; }

# 1. stage + compile
tar -C "$HERE" -cf - mgid_api.py spend_stop.py | base64 -w0 | $TS ssh "$HOST" \
  'set -e; rm -rf /opt/mgid-spend-stop-second.new && mkdir -p /opt/mgid-spend-stop-second.new /var/lib/mgid-spend-stop-second && chmod 700 /var/lib/mgid-spend-stop-second
   base64 -d | tar -C /opt/mgid-spend-stop-second.new -xf -
   python3 -m py_compile /opt/mgid-spend-stop-second.new/mgid_api.py /opt/mgid-spend-stop-second.new/spend_stop.py && echo staged'

# 2. the env file of the second account: the token travels through the pipe only
{ printf 'MGID_ACCOUNT=second\nMGID_816921_TOKEN='; node "$VAULT" get mgid MGID_816921_TOKEN | tr -d '\n'; printf '\n'; } \
  | $TS ssh "$HOST" 'umask 077; cat > /etc/mgid-second.env && chmod 600 /etc/mgid-second.env && echo "env-файл записан (600)"'

# 3. dry run of the staged code, swap, baseline, units
$TS ssh "$HOST" 'bash -s' <<'REMOTE'
set -e
echo "--- dry run (pauses nothing)"
rc=0
timeout 300 bash -c 'set -a; . /etc/mgid-second.env; set +a; MGID_SPEND_ACTIONS=/tmp/mgid-spend2-dry.log MGID_SPEND_BASELINE=/tmp/mgid-spend2-dry-base.json python3 /opt/mgid-spend-stop-second.new/spend_stop.py' \
  < /dev/null > /tmp/mgid-spend2-dry.out 2>&1 || rc=$?
cut -c1-200 /tmp/mgid-spend2-dry.out | head -30
rm -f /tmp/mgid-spend2-dry.out /tmp/mgid-spend2-dry.log /tmp/mgid-spend2-dry-base.json
test "$rc" = 0 || { echo "dry run упал (код $rc) — ничего не установлено"; rm -rf /opt/mgid-spend-stop-second.new; exit 1; }
echo "--- swap"
rm -rf /opt/mgid-spend-stop-second && mv /opt/mgid-spend-stop-second.new /opt/mgid-spend-stop-second
echo "--- reset: считается только расход с этого момента"
bash -c 'set -a; . /etc/mgid-second.env; set +a; MGID_SPEND_ACTIONS=/var/lib/mgid-spend-stop-second/actions.log MGID_SPEND_BASELINE=/var/lib/mgid-spend-stop-second/baseline.json python3 /opt/mgid-spend-stop-second/spend_stop.py --reset'
cat > /etc/systemd/system/mgid-spend-stop-second.service <<"EOF"
[Unit]
Description=MGID stop-loss, second account: pause every active campaign whose spend since the reset reaches $3

[Service]
Type=oneshot
EnvironmentFile=/etc/mgid-second.env
Environment=MGID_SPEND_LIMIT=3.0
Environment=MGID_SPEND_ACTIONS=/var/lib/mgid-spend-stop-second/actions.log
Environment=MGID_SPEND_BASELINE=/var/lib/mgid-spend-stop-second/baseline.json
WorkingDirectory=/var/lib/mgid-spend-stop-second
ExecStart=/usr/bin/flock -n /var/lib/mgid-spend-stop-second/.lock /usr/bin/python3 /opt/mgid-spend-stop-second/spend_stop.py --apply
TimeoutStartSec=300
EOF
cat > /etc/systemd/system/mgid-spend-stop-second.timer <<"EOF"
[Unit]
Description=Run the MGID stop-loss of the second account every 2 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
AccuracySec=10s
Persistent=true

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now mgid-spend-stop-second.timer >/dev/null 2>&1
systemctl start --no-block mgid-spend-stop-second.service || true
echo "--- timer"
systemctl list-timers mgid-spend-stop-second.timer --no-pager | head -3
REMOTE
