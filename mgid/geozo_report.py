"""Read-only report of the MGID -> arcadiablog.com/dom and /dom2 -> Geozo test: spend, visits, block-click signals, Geozo revenue.

    CLAUDE_VAULT_FILE=~/.claude/secrets/vault.enc.json node vault.mjs exec mgid geozo -- python3 geozo_report.py [YYYY-MM-DD]

Two layouts run side by side, each with its own MGID campaign (see geozo_campaign.py): /dom/ (4 slots a page, one ad
each, the pages MGID approved first) and /dom2/ (8-9 slots a page, 3-10 ads each). Every number is printed per variant.
Four sources, each printed on its own so a gap in one shows up instead of being averaged away:
 1. MGID v2 report of each campaign (impressions, clicks, spend, conversions of the goal geozoclick), by hour, and the
    moderation state of its teasers;
 2. the page views of /dom/ and /dom2/ in the site's nginx log (those with a click_id came from MGID, the rest are
    moderators, bots and direct visits);
 3. the relay log /var/log/nginx/arcadiablog.dom.log: one line per signal sent to MGID, with MGID's HTTP status (up=);
    the page that sent it is in ref=, which tells the variants apart;
 4. Geozo publisher statistics of the blocks (clicks, revenue), when the API answers.
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

import mgid_geo_copies as cp  # noqa: E402
from mgid_api import report, v2_campaigns  # noqa: E402

VARIANTS = {   # route -> MGID campaign name
    "dom": "Arcadia KZ content mobile CPA 0.01",
    "dom2": "Arcadia KZ content mobile CPA 0.01 dense",
}
NAME = VARIANTS["dom"]
HOST = "root@100.121.239.113"
TS_BIN = os.environ.get("TS_BIN", "/tmp/claude-0/ts/tailscale_1.104.1_amd64/tailscale")
TS_SOCK = os.environ.get("TS_SOCK", "/tmp/claude-0/ts/ts.sock")
BLOCKS = {   # Geozo block id -> (name, variant, ads in the block)
    1283938: ("dom2-header", "dom", 1), 1283939: ("dom2-feed", "dom", 1),
    1283940: ("dom3-a", "dom2", 3), 1283941: ("dom3-b", "dom2", 4), 1283942: ("dom3-c", "dom2", 10),
}


def money(x):
    return float(x.get("amount") if isinstance(x, dict) else (x or 0))


def ssh(cmd):
    r = subprocess.run([TS_BIN, "--socket", TS_SOCK, "ssh", HOST, cmd], capture_output=True, text=True, timeout=120)
    return r.stdout


def mgid_part(day, route="dom", name=NAME):
    live = v2_campaigns(("name", "status", "bidding"))
    cid = next((i for i, x in live.items() if x.get("name") == name), None)
    if not cid:
        print(f"MGID [{route}]: кампании нет")
        return None
    r = live[cid]
    print(f"MGID [{route}]: кампания {cid}, {(r.get('status') or {}).get('name')}/{(r.get('status') or {}).get('reason')}, "
          f"ставка {(r.get('bidding') or {}).get('strategy')} {(r.get('bidding') or {}).get('price')}")
    tz = Counter((t.get("status") or {}).get("code") for t in cp.teasers(cid).values() if isinstance(t, dict))
    print(f"  тизеры: {dict(tz)}")
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


def site_part(day, route="dom"):
    d = time.strftime("%d/%b/%Y", time.strptime(day, "%Y-%m-%d"))
    out = ssh(f"grep -a '{d}' /var/log/nginx/arcadiablog.access.log | grep -a -E 'GET /{route}/' | grep -a -v -E '\\.(jpg|js|png|css)'")
    views = [l for l in out.splitlines() if l.strip()]
    withid = [l for l in views if "click_id=" in l and "click_id=%7B" not in l and "click_id={" not in l]
    ids = {re.search(r"click_id=([^& ]+)", l).group(1) for l in withid}
    print(f"САЙТ [{route}]: просмотры страниц за {day}: {len(views)}, из них с click_id MGID {len(withid)}, "
          f"уникальных click_id {len(ids)}")
    return len(views), len(withid), len(ids)


def relay_part(day):
    """The relay log has no route of its own: the page that sent the signal is in ref=."""
    out = ssh(f"grep -a '{day}' /var/log/nginx/arcadiablog.dom.log")
    leads = [l for l in out.splitlines() if "/dom/lead" in l]
    res = {}
    for route in VARIANTS:
        mine = [l for l in leads if f'ref="https://arcadiablog.com/{route}/' in l]
        st = Counter(re.search(r"up=(\S+)", l).group(1) for l in mine if re.search(r"up=(\S+)", l))
        res[route] = len(mine)
        print(f"РЕЛЕЙ [{route}]: сигналов за {day}: {len(mine)}, ответ MGID (up=): {dict(st)}")
        for l in mine[-2:]:
            print("   ", l[:200])
    other = len(leads) - sum(res.values())
    if other:
        print(f"РЕЛЕЙ [без страницы-источника]: {other}")
    return res


def geozo_part(day):
    key = os.environ.get("GEOZO_PUBLISHER_API_KEY")
    if not key:
        print("GEOZO: нет ключа в окружении (vault exec geozo)")
        return
    import requests
    print("GEOZO блоки: " + ", ".join(f"{i} {n} ({v}, {k} об.)" for i, (n, v, k) in BLOCKS.items()))
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
        print(f"GEOZO: stats {r.status_code}: {r.text[:1500]}")
        return
    print("GEOZO: статистика не ответила")


if __name__ == "__main__":
    day = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    for route, name in VARIANTS.items():
        mgid_part(day, route, name)
        print()
    for route in VARIANTS:
        site_part(day, route)
    print()
    relay_part(day)
    print()
    geozo_part(day)
