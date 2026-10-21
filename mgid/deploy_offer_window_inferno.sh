#!/bin/bash
# Install the offer window of the 1537 CPA tune campaigns on Inferno (systemd timer, every 5 minutes): the listed campaigns of the
# account 816921 (v2 939023) are started inside the window of the offer (weekdays 08:00-21:00 US Eastern) and paused outside it.
# Owner, 21.10: "cpa tune окна поставь по расписанию". It replaces the old crons of 31.08 (lidgen_window.py, mgid_daypart.sh), which were
# commented out in the crontab of root on 21.10 and restarted the old manual-bid campaigns every hour.
#
#   TAILSCALE="/path/tailscale --socket=/path/ts.sock" CLAUDE_VAULT_FILE=~/.claude/secrets/vault.enc.json bash deploy_offer_window_inferno.sh
#
# Own code directory, state and units. The env file /etc/mgid-second.env (account switch and token) and the stop-loss baseline of the second
# account already exist and are only read. The campaign list is in the unit: change it there, `systemctl daemon-reload`.
# MGID_SPEND_LIMIT (5.0 since the evening of 21.10) has to equal the limit of mgid-spend-stop-second: a higher number here would start what the
# stop-loss has just paused, a lower one would refuse to start a campaign that is still under the stop-loss limit.
# Order: tests, stage and compile on the box, dry run of the staged code (changes nothing), swap, units, start.
# Rollback: systemctl disable --now mgid-offer-window-second.timer
set -euo pipefail
TS="${TAILSCALE:-tailscale}"
HOST=root@100.121.239.113
HERE="$(cd "$(dirname "$0")" && pwd)"
CAMPS="${MGID_WINDOW_CAMPS:-12468751,12468752,12520626,12520627}"

python3 -m py_compile "$HERE/mgid_api.py" "$HERE/spend_stop.py" "$HERE/offer_window.py"
(cd "$HERE" && python3 -m unittest test_offer_window test_spend_stop >/dev/null 2>&1) || { echo "тесты не проходят — не выкладываю"; exit 1; }

# 1. stage + compile
tar -C "$HERE" -cf - mgid_api.py spend_stop.py offer_window.py | base64 -w0 | $TS ssh "$HOST" \
  'set -e; rm -rf /opt/mgid-offer-window-second.new && mkdir -p /opt/mgid-offer-window-second.new /var/lib/mgid-offer-window-second && chmod 700 /var/lib/mgid-offer-window-second
   base64 -d | tar -C /opt/mgid-offer-window-second.new -xf -
   python3 -m py_compile /opt/mgid-offer-window-second.new/mgid_api.py /opt/mgid-offer-window-second.new/spend_stop.py /opt/mgid-offer-window-second.new/offer_window.py && echo staged
   python3 -c "from zoneinfo import ZoneInfo; ZoneInfo(\"America/New_York\")" && echo "tzdata ok"'

# 2. dry run of the staged code (no --apply: changes nothing), swap, units
$TS ssh "$HOST" "CAMPS=$CAMPS bash -s" <<'REMOTE'
set -e
echo "--- dry run (changes nothing)"
rc=0
timeout 300 bash -c 'set -a; . /etc/mgid-second.env; set +a; MGID_WINDOW_CAMPS=$CAMPS MGID_SPEND_BASELINE=/var/lib/mgid-spend-stop-second/baseline.json MGID_WINDOW_ACTIONS=/tmp/mgid-ow-dry.log python3 /opt/mgid-offer-window-second.new/offer_window.py' \
  < /dev/null > /tmp/mgid-ow-dry.out 2>&1 || rc=$?
cut -c1-200 /tmp/mgid-ow-dry.out | head -12
rm -f /tmp/mgid-ow-dry.out /tmp/mgid-ow-dry.log
test "$rc" = 0 || { echo "dry run упал (код $rc) — ничего не установлено"; rm -rf /opt/mgid-offer-window-second.new; exit 1; }
echo "--- swap"
rm -rf /opt/mgid-offer-window-second && mv /opt/mgid-offer-window-second.new /opt/mgid-offer-window-second
cat > /etc/systemd/system/mgid-offer-window-second.service <<EOF2
[Unit]
Description=MGID offer window, second account: start the 1537 CPA tune campaigns inside the window of the offer, pause them outside

[Service]
Type=oneshot
EnvironmentFile=/etc/mgid-second.env
Environment=MGID_WINDOW_CAMPS=$CAMPS
Environment=MGID_SPEND_LIMIT=5.0
Environment=MGID_SPEND_BASELINE=/var/lib/mgid-spend-stop-second/baseline.json
Environment=MGID_WINDOW_ACTIONS=/var/lib/mgid-offer-window-second/actions.log
WorkingDirectory=/var/lib/mgid-offer-window-second
ExecStart=/usr/bin/flock -n /var/lib/mgid-offer-window-second/.lock /usr/bin/python3 /opt/mgid-offer-window-second/offer_window.py --apply
TimeoutStartSec=300
EOF2
cat > /etc/systemd/system/mgid-offer-window-second.timer <<"EOF2"
[Unit]
Description=Run the MGID offer window of the second account every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=10s
Persistent=true

[Install]
WantedBy=timers.target
EOF2
systemctl daemon-reload
systemctl enable --now mgid-offer-window-second.timer >/dev/null 2>&1
systemctl start --no-block mgid-offer-window-second.service || true
echo "--- timer"
systemctl list-timers mgid-offer-window-second.timer --no-pager | head -3
REMOTE
