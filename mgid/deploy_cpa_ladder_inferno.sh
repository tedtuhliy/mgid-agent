#!/bin/bash
# Install the CPA tune ladder of the 1537 test on Inferno (systemd timer, every hour at :07): a campaign of the list that gets fewer than 10
# clicks an hour gets a target CPA higher by $0.50, up to $5.00 (cpa_ladder.py). Owner, 21.10: «поднимай по 50 центов так каждый час пока не
# пойдёт хотя бы 10 20 кликов в час».
#
#   TAILSCALE="/path/tailscale --socket=/path/ts.sock" CLAUDE_VAULT_FILE=~/.claude/secrets/vault.enc.json bash deploy_cpa_ladder_inferno.sh
#
# Own code directory, state and units; /etc/mgid-second.env and the stop-loss baseline are only read. The state file is seeded once with the
# looks the ladder has to start from (E v2 raised to 0.50 at 13:07 UTC, F v2 at 13:59:35). The campaign list is in the unit.
# Rollback: systemctl disable --now mgid-cpa-ladder-second.timer
set -euo pipefail
TS="${TAILSCALE:-tailscale}"
HOST=root@100.121.239.113
HERE="$(cd "$(dirname "$0")" && pwd)"
CAMPS="${MGID_LADDER_CAMPS:-12468751,12468752,12520626,12520627}"

python3 -m py_compile "$HERE/mgid_api.py" "$HERE/spend_stop.py" "$HERE/offer_window.py" "$HERE/cpa_ladder.py"
(cd "$HERE" && python3 -m unittest test_cpa_ladder test_offer_window test_spend_stop >/dev/null 2>&1) || { echo "тесты не проходят — не выкладываю"; exit 1; }

# 1. stage + compile (offer_window and spend_stop are imported by the ladder)
tar -C "$HERE" -cf - mgid_api.py spend_stop.py offer_window.py cpa_ladder.py | base64 -w0 | $TS ssh "$HOST" \
  'set -e; rm -rf /opt/mgid-cpa-ladder-second.new && mkdir -p /opt/mgid-cpa-ladder-second.new /var/lib/mgid-cpa-ladder-second && chmod 700 /var/lib/mgid-cpa-ladder-second
   base64 -d | tar -C /opt/mgid-cpa-ladder-second.new -xf -
   python3 -m py_compile /opt/mgid-cpa-ladder-second.new/cpa_ladder.py && echo staged'

# 2. dry run, swap, seed, units
$TS ssh "$HOST" "CAMPS=$CAMPS bash -s" <<'REMOTE'
set -e
ENVS='MGID_LADDER_CAMPS=$CAMPS MGID_SPEND_BASELINE=/var/lib/mgid-spend-stop-second/baseline.json MGID_LADDER_STATE=/tmp/mgid-ladder-dry-state.json MGID_LADDER_ACTIONS=/tmp/mgid-ladder-dry.log'
echo "--- dry run (changes nothing)"
rc=0
timeout 300 bash -c "set -a; . /etc/mgid-second.env; set +a; $ENVS python3 /opt/mgid-cpa-ladder-second.new/cpa_ladder.py" < /dev/null > /tmp/mgid-ladder-dry.out 2>&1 || rc=$?
cut -c1-200 /tmp/mgid-ladder-dry.out | head -10
rm -f /tmp/mgid-ladder-dry.out /tmp/mgid-ladder-dry.log /tmp/mgid-ladder-dry-state.json
test "$rc" = 0 || { echo "dry run упал (код $rc) — ничего не установлено"; rm -rf /opt/mgid-cpa-ladder-second.new; exit 1; }
echo "--- swap + seed"
rm -rf /opt/mgid-cpa-ladder-second && mv /opt/mgid-cpa-ladder-second.new /opt/mgid-cpa-ladder-second
if [ ! -s /var/lib/mgid-cpa-ladder-second/state.json ]; then
  cat > /var/lib/mgid-cpa-ladder-second/state.json <<"EOF2"
{"12468751": {"t": "2026-10-21T13:07:28+00:00", "clicks": 1925, "price": 0.5},
 "12468752": {"t": "2026-10-21T13:59:35+00:00", "clicks": 1825, "price": 0.5}}
EOF2
  echo "state seeded"
fi
cat > /etc/systemd/system/mgid-cpa-ladder-second.service <<EOF2
[Unit]
Description=MGID CPA tune ladder, second account: raise the target CPA of a campaign with too few clicks an hour by 0.50

[Service]
Type=oneshot
EnvironmentFile=/etc/mgid-second.env
Environment=MGID_LADDER_CAMPS=$CAMPS
Environment=MGID_SPEND_BASELINE=/var/lib/mgid-spend-stop-second/baseline.json
Environment=MGID_LADDER_STATE=/var/lib/mgid-cpa-ladder-second/state.json
Environment=MGID_LADDER_ACTIONS=/var/lib/mgid-cpa-ladder-second/actions.log
WorkingDirectory=/var/lib/mgid-cpa-ladder-second
ExecStart=/usr/bin/flock -n /var/lib/mgid-cpa-ladder-second/.lock /usr/bin/python3 /opt/mgid-cpa-ladder-second/cpa_ladder.py --apply
TimeoutStartSec=300
EOF2
cat > /etc/systemd/system/mgid-cpa-ladder-second.timer <<"EOF2"
[Unit]
Description=Run the MGID CPA tune ladder of the second account every hour at :07

[Timer]
OnCalendar=*:07:00
AccuracySec=10s
Persistent=true

[Install]
WantedBy=timers.target
EOF2
systemctl daemon-reload
systemctl enable --now mgid-cpa-ladder-second.timer >/dev/null 2>&1
systemctl start --no-block mgid-cpa-ladder-second.service || true
sleep 6
echo "--- first run"
journalctl -u mgid-cpa-ladder-second.service --no-pager -o cat -n 12 | cut -c1-200
echo "--- timer"
systemctl list-timers mgid-cpa-ladder-second.timer --no-pager | head -3
REMOTE
