"""Read-only report of the MGID -> arcadiablog.com -> Geozo tests: one row per campaign.

    CLAUDE_VAULT_FILE=~/.claude/secrets/vault.enc.json node vault.mjs exec mgid geozo -- python3 geozo_report.py [YYYY-MM-DD ...]

The day is the MGID day, Moscow time (UTC+3), and it defaults to today in Moscow: right after 21:00 UTC that is already
tomorrow's date, and the nginx logs (UTC) are cut by the same Moscow window, not by their own date. (13.10 night: the first
run after 21:00 UTC asked MGID for the day that had just ended and showed zero impressions for campaigns that had started
after midnight Moscow time.)

Campaigns: the two Kazakhstan layouts (/dom/ moderate, /dom2/ dense, geozo_campaign.py; both paused once the blog campaign
runs), the fourteen geos of the multilingual site (/blog/<lang>/, geozo_geos.py) and, since 14.10 night, Kazakhstan on the
Russian version of the blog (/blog/ru/, label «KZ blog»; geozo_geos.py KZ). Four sources, each on its own so that a gap in one shows up:
 1. MGID v2 report by campaign (impressions, clicks, spend, conversions of the goal geozoclick) and the moderation state
    of the teasers;
 2. page views in the site's nginx log, counted by the campaign id inside `source=mgid_<campaign>_<widget>` (so Germany,
    Austria and Switzerland, which share /blog/de/, stay apart); a view with a 32-character click id is a real MGID click,
    the rest are moderators, bots and our own checks;
 3. the relay log /var/log/nginx/arcadiablog.dom.log: one line per signal sent to MGID after a real click on an ad block,
    with MGID's HTTP status (up=); the page that sent it is in ref=, which carries the same source=. The free e-book
    (/blog/dl/<lang>.pdf?click_id=..&source=..) writes two lines per download: the request itself (up=-) and the mirrored
    postback (up=<MGID's status>); the first is counted as «скач», the second as «ebook200». Since 14.10 night the download is one more
    conversion of the same goal as a block click (event geozoclick), so MGID's «конв» of a campaign is about «up=200» + «ebook200»;
 4. Geozo publisher statistics of the blocks (clicks, revenue), when the API answers (it has answered 429 so far).
RPV = Geozo revenue / MGID clicks; a click costs more than it earns when RPV < MGID cost per click.
"""
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "geozo_site"))

import geozo_geos as gg  # noqa: E402
import mgid_geo_copies as cp  # noqa: E402
from mgid_api import report, v2_campaigns  # noqa: E402

MSK = timezone(timedelta(hours=3))
HOST = "root@100.121.239.113"
TS_BIN = os.environ.get("TS_BIN", "/tmp/claude-0/ts/tailscale_1.104.1_amd64/tailscale")
TS_SOCK = os.environ.get("TS_SOCK", "/tmp/claude-0/ts/ts.sock")
NAME = "Arcadia KZ content mobile CPA 0.01"            # kept: older notes import it
CAMPAIGNS = [("KZ /dom/", "Arcadia KZ content mobile CPA 0.01"),
             ("KZ /dom2/", "Arcadia KZ content mobile CPA 0.01 dense")] + [(g, gg.name_of(g)) for g in gg.ORDER]
SHOW = {"KZ": "KZ blog"}     # how a label is printed (the geo code KZ is the campaign on /blog/ru/, the other two are /dom/ and /dom2/)
BLOCKS = {   # Geozo block id -> (name, where, ads in the block)
    1283938: ("dom2-header", "KZ /dom/", 1), 1283939: ("dom2-feed", "KZ /dom/", 1),
    1283940: ("dom3-a", "dense and /blog/", 3), 1283941: ("dom3-b", "dense and /blog/", 4),
    1283942: ("dom3-c", "dense and /blog/", 10),
}


def money(x):
    return float(x.get("amount") if isinstance(x, dict) else (x or 0))


def ssh(cmd):
    r = subprocess.run([TS_BIN, "--socket", TS_SOCK, "ssh", HOST, cmd], capture_output=True, text=True, timeout=180)
    return r.stdout


def mgid_rows(day):
    live = v2_campaigns(("name", "status", "bidding"))
    ids = {label: (gg.cid_of(label, live) if label in gg.ORDER else
                   next((i for i, x in live.items() if x.get("name") == name), None)) for label, name in CAMPAIGNS}
    rep = {}
    try:
        for x in report(day, day, ("impressions", "clicks", "spent", "conversionsBuy"), ("campaignId",)):
            rep[int(x["campaignId"])] = x
    except Exception as e:
        print("отчёт MGID недоступен:", str(e)[:150])
    rows = {}
    for label, _ in CAMPAIGNS:
        cid = ids[label]
        if not cid:
            rows[label] = None
            continue
        r = live[cid]
        tz = Counter((t.get("status") or {}).get("code") for t in cp.teasers(cid).values() if isinstance(t, dict))
        x = rep.get(cid) or {}
        rows[label] = {"cid": cid, "status": f"{(r.get('status') or {}).get('name')}/{(r.get('status') or {}).get('reason')}",
                       "bid": (r.get("bidding") or {}).get("price"), "teasers": dict(tz),
                       "imp": int(money(x.get("impressions"))), "clk": int(money(x.get("clicks"))),
                       "spent": money(x.get("spent")), "conv": int(money(x.get("conversionsBuy")))}
    return rows


def hourly(day, cid):
    """Hour by hour numbers of one campaign: {hour: [impressions, clicks, spend, conversions]}."""
    out = {}
    for x in report(day, day, ("impressions", "clicks", "spent", "conversionsBuy"), ("campaignId", "hour"), camps=[cid]):
        h = str(x["hour"]).split()[-1][:2]
        v = out.setdefault(h, [0, 0, 0.0, 0])
        v[0] += int(money(x["impressions"])); v[1] += int(money(x["clicks"])); v[2] += money(x["spent"])
        v[3] += int(money(x.get("conversionsBuy")))
    return out


def msk_window(day):
    d0 = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=MSK)
    return d0, d0 + timedelta(days=1)


def site_rows(day):
    """views[cid]: page views whose URL carries that campaign's source and a 32-character click id; ids[cid]: how many
    different click ids; sig[cid]: Counter of MGID's answer (up=) to the relay signals sent from pages of that campaign.
    Only lines inside the Moscow day are counted (the logs are UTC)."""
    d0, d1 = msk_window(day)
    utc_days = sorted({d0.astimezone(timezone.utc).date(), (d1 - timedelta(seconds=1)).astimezone(timezone.utc).date()})
    acc, rel = "", ""
    for u in utc_days:
        acc += ssh(f"grep -a '{u.strftime('%d/%b/%Y')}' /var/log/nginx/arcadiablog.access.log | grep -a -E 'GET /(dom2?|blog)/' | "
                   "grep -a -v -E '\\.(jpg|js|png|css)'")
        rel += ssh(f"grep -a '{u.isoformat()}' /var/log/nginx/arcadiablog.dom.log")
    views, ids = Counter(), {}
    for l in acc.splitlines():
        t = re.search(r"\[(\d\d/\w{3}/\d{4}:\d\d:\d\d:\d\d [+-]\d{4})\]", l)
        if not t or not d0 <= datetime.strptime(t.group(1), "%d/%b/%Y:%H:%M:%S %z") < d1:
            continue
        m = re.search(r"source=mgid_(\d+)_", l)
        c = re.search(r"click_id=([0-9a-f]{32})\b", l)
        if m and c:
            views[int(m.group(1))] += 1
            ids.setdefault(int(m.group(1)), set()).add(c.group(1))
    sig, dl, dl_up = {}, Counter(), Counter()
    for l in rel.splitlines():
        t = re.search(r"\[(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d)\]", l)
        if not t or not d0 <= datetime.fromisoformat(t.group(1)) < d1:
            continue
        m = re.search(r"source=mgid_(\d+)_", l)
        u = re.search(r"up=(\S+)", l)
        cid = int(m.group(1)) if m else 0
        if "/dom/lead" in l:
            sig.setdefault(cid, Counter())[u.group(1) if u else "-"] += 1
        elif "/blog/dl/" in l and re.search(r"click_id=[0-9a-f]{32}\b", l):
            if u and u.group(1) != "-":
                dl_up[cid] += (u.group(1) == "200")
            else:
                dl[cid] += 1
    return views, {k: len(v) for k, v in ids.items()}, sig, dl, dl_up


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
    for i in range(3):
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
    print("GEOZO: статистика не ответила (429)")


def main():
    days = sys.argv[1:] or [datetime.now(MSK).date().isoformat()]
    for day in days:
        one_day(day)
    print()
    geozo_part(days[-1])


def one_day(day):
    rows = mgid_rows(day)
    views, uniq, sig, dl, dl_up = site_rows(day)
    print(f"отчёт за {day} (сутки MGID = МСК)")
    print(f"{'кампания':10} {'статус':22} {'ставка':>6} {'тизеры':26} {'показы':>6} {'клики':>5} {'расход$':>8} {'конв':>4} "
          f"{'заходы':>6} {'клик-id':>7} {'сигналы':>7} {'up=200':>6} {'скач':>4} {'ebook200':>8}")
    tot = [0, 0, 0.0, 0, 0, 0, 0, 0, 0, 0]
    for label, _ in CAMPAIGNS:
        r = rows[label]
        if not r:
            print(f"{SHOW.get(label, label):10} нет кампании")
            continue
        cid = r["cid"]
        s = sig.get(cid, Counter())
        v = [r["imp"], r["clk"], r["spent"], r["conv"], views.get(cid, 0), uniq.get(cid, 0), sum(s.values()), s.get("200", 0),
             dl.get(cid, 0), dl_up.get(cid, 0)]
        tot = [a + b for a, b in zip(tot, v)]
        print(f"{SHOW.get(label, label):10} {r['status'][:22]:22} {r['bid']!s:>6} {str(r['teasers'])[:26]:26} {v[0]:>6} {v[1]:>5} {v[2]:>8.4f} "
              f"{v[3]:>4} {v[4]:>6} {v[5]:>7} {v[6]:>7} {v[7]:>6} {v[8]:>4} {v[9]:>8}")
    print(f"{'ИТОГО':10} {'':22} {'':>6} {'':26} {tot[0]:>6} {tot[1]:>5} {tot[2]:>8.4f} {tot[3]:>4} {tot[4]:>6} {tot[5]:>7} {tot[6]:>7} "
          f"{tot[7]:>6} {tot[8]:>4} {tot[9]:>8}")
    print("(заходы = страницы с source=mgid_<кампания>_ и 32-значным click_id; среди них и проверки модераторов MGID;")
    print(" конв MGID = сигналы up=200 с блоков + скачивания книги ebook200, одна цель geozoclick)")
    if sig.get(0):
        print(f"сигналов без кампании в ref: {sum(sig[0].values())} (наши проверки)")


if __name__ == "__main__":
    main()
