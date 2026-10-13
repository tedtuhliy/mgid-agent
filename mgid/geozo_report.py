"""Read-only report of the MGID -> arcadiablog.com/dom -> Geozo test: spend, visits, block-click signals, Geozo revenue.

    node ~/.claude/skills/secrets/vault.mjs exec mgid geozo -- python3 geozo_report.py [YYYY-MM-DD]

Four sources, each printed on its own so a gap in one shows up instead of being averaged away:
 1. MGID v2 report of the campaign (impressions, clicks, spend, conversions of the goal geozoclick), by hour;
 2. the page views of /dom/ in the site's nginx log (those with a click_id came from MGID, the rest are moderators,
    bots and direct visits);
 3. the relay log /var/log/nginx/arcadiablog.dom.log: one line per signal sent to MGID, with MGID's HTTP status (up=);
 4. Geozo publisher statistics of the blocks dom-header / dom-feed (clicks, revenue), when the API answers.
RPV = Geozo revenue / MGID clicks; a click costs more than it earns when RPV < MGID cost per click.
"""
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from mgid_api import report, v2_campaigns  # noqa: E402

NAME = "Arcadia KZ content mobile CPA 0.01"
HOST = "root@100.121.239.113"
TS_BIN = os.environ.get("TS_BIN", "/tmp/claude-0/ts/tailscale_1.104.1_amd64/tailscale")
TS_SOCK = os.environ.get("TS_SOCK", "/tmp/claude-0/ts/ts.sock")
BLOCKS = {1283936: "dom-header", 1283937: "dom-feed"}


def money(x):
    return float(x.get("amount") if isinstance(x, dict) else (x or 0))


def ssh(cmd):
    r = subprocess.run([TS_BIN, "--socket", TS_SOCK, "ssh", HOST, cmd], capture_output=True, text=True, timeout=120)
    return r.stdout


def mgid_part(day):
    live = v2_campaigns(("name", "status", "bidding"))
    cid = next((i for i, x in live.items() if x.get("name") == NAME), None)
    if not cid:
        print("MGID: кампании нет")
        return None
    r = live[cid]
    print(f"MGID: кампания {cid}, {(r.get('status') or {}).get('name')}/{(r.get('status') or {}).get('reason')}, "
          f"ставка {(r.get('bidding') or {}).get('strategy')} {(r.get('bidding') or {}).get('price')}")
    rows = report(day, day, ("impressions", "clicks", "spent", "conversionsBuy"), ("campaignId", "hour"), camps=[cid])
    hours = defaultdict(lambda: [0, 0, 0.0, 0])
    for x in rows:
        h = str(x["hour"]).split()[-1][:2]
        v = hours[h]
        v[0] += int(money(x["impressions"])); v[1] += int(money(x["clicks"])); v[2] += money(x["spent"])
        v[3] += int(money(x.get("conversionsBuy")))
    tot = [sum(v[i] for v in hours.values()) for i in range(4)]
    print(f"  за {day}: показы {tot[0]}, клики {tot[1]}, расход ${tot[2]:.4f}, CPC ${tot[2] / tot[1] if tot[1] else 0:.5f}, "
          f"конверсии цели {tot[3]}")
    for h in sorted(hours):
        v = hours[h]
        print(f"    {h}:00  показы {v[0]:>5}  клики {v[1]:>4}  расход ${v[2]:.4f}  конверсии {v[3]}")
    return tot


def site_part(day):
    d = time.strftime("%d/%b/%Y", time.strptime(day, "%Y-%m-%d"))
    out = ssh(f"grep -a '{d}' /var/log/nginx/arcadiablog.access.log | grep -a -E 'GET /dom/' | grep -a -v -E '\\.(jpg|js|png|css)'")
    views = [l for l in out.splitlines() if l.strip()]
    withid = [l for l in views if "click_id=" in l and "click_id=%7B" not in l and "click_id={" not in l]
    print(f"САЙТ: просмотры страниц /dom/ за {day}: {len(views)}, из них с click_id MGID {len(withid)}")
    print(f"  с click_id без макросов, уникальных id: {len({re.search(r'click_id=([^& ]+)', l).group(1) for l in withid})}")
    out = ssh(f"grep -a '{time.strftime('%Y-%m-%d', time.strptime(day, '%Y-%m-%d'))}' /var/log/nginx/arcadiablog.dom.log")
    leads = [l for l in out.splitlines() if "/dom/lead" in l]
    st = Counter(re.search(r"up=(\S+)", l).group(1) for l in leads if re.search(r"up=(\S+)", l))
    print(f"РЕЛЕЙ: сигналов за {day}: {len(leads)}, ответ MGID (up=): {dict(st)}")
    for l in leads[-3:]:
        print("   ", l[:200])
    return len(views), len(withid), len(leads)


def geozo_part(day):
    key = os.environ.get("GEOZO_PUBLISHER_API_KEY")
    if not key:
        print("GEOZO: нет ключа в окружении (vault exec geozo)")
        return
    import requests
    params = {"filters[date_from]": day, "filters[date_to]": day, "groups[]": "block_id",
              "order_by[0][column]": "block_id", "order_by[0][direction]": "asc",
              "filters[block_id_in][]": list(BLOCKS)}
    for i in range(5):
        try:
            r = requests.get("https://api.geozo.com/v1/webmaster/stats", headers={"Private-Token": key, "Accept": "application/json"},
                             params=params, timeout=40)
        except requests.RequestException:
            time.sleep(3)
            continue
        if r.status_code == 429:
            time.sleep(10 * (i + 1))
            continue
        print(f"GEOZO: stats {r.status_code}: {r.text[:900]}")
        return
    print("GEOZO: статистика не ответила")


if __name__ == "__main__":
    day = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    mgid_part(day)
    print()
    site_part(day)
    print()
    geozo_part(day)
