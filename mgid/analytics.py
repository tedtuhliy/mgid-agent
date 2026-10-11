"""MGID Tinely: analytics by geo and by placement. Spend from MGID, leads and money from cpamatica.

    node ~/.claude/skills/secrets/vault.mjs exec mgid -- python3 analytics.py \\
        --conv <Tedbolt>/mirelia_api/.mirelia/cpam-conv.json [--from 2026-09-29] [--out DIR]

The conversions file comes from `cpamatica.mjs conv <from> <to>` (see the cpamatica skill). MGID's
own `conversionsBuy` is NOT used for money: it counts our postback, not what cpamatica pays. Both are
printed side by side for geos so that a postback gap shows.

How the two sides are joined:
- geo: MGID `country` (a name, mapped to ISO through the dictionary) <-> cpamatica `country`. Both
  are IP based and can disagree on a few clicks; the leads of one campaign never move between geos.
- placement: MGID `widgetId` <-> cpamatica `aff_sub3`, which carries MGID's `{widget_id}` macro, in
  campaign `aff_sub`. The macro may come with a sub-source (`58071814s701611`), so both sides are cut
  to their leading digits, as the guard does.
- A lead whose `aff_sub` is the literal `{campaign_id}` is a click on a link with an unsubstituted
  macro (a hand test), belongs to no campaign and is left out of every table but the total.

The guard replay uses each campaign's own conversion cost (2 x, as mgid_guard.py) and says how much
spend sat above that line: an upper bound of what a guard acting exactly at the line would have saved.
"""
import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from mgid_api import V2, blacklist, buy_cpa, call, report, v2_campaigns

MULT = 2.0
FLAT = 0.30          # campaign without a conversion cost, as in the guard
METRICS = ("spent", "clicks", "impressions", "conversionsBuy")


def num(x):
    return float(x.get("amount") if isinstance(x, dict) else (x or 0))


def base(uid):
    m = re.match(r"\d+", str(uid or ""))
    return m.group() if m else None


def iso_by_name():
    st, d = call("GET", V2 + "dictionaries/countries")
    if st != 200:
        raise SystemExit(f"справочник стран: {st}")
    return {c["name"]: c["iso"] for c in d["data"]}


def pct(a, b):
    return 100.0 * a / b if b else 0.0


def load_leads(path, camps):
    """Approved cpamatica leads that came from MGID: [{camp, geo, widget, usd, time, offer, os}]."""
    rows = json.load(open(path), strict=False).get("report") or []
    out, seen, orphan = [], set(), []
    for r in rows:
        if str(r.get("aff_sub5")) != "mgid" and str(r.get("aff_sub")) not in camps:
            continue
        tx = r.get("transaction_id")
        if tx in seen:
            continue
        seen.add(tx)
        lead = {"camp": str(r.get("aff_sub")), "geo": r.get("country"), "widget": base(r.get("aff_sub3")),
                "usd": float(r.get("payoutInUSD") or 0), "time": r.get("time"),
                "offer": (r.get("offer") or {}).get("name", "")[:40], "os": r.get("device_os"),
                "status": r.get("status")}
        (out if lead["camp"] in camps else orphan).append(lead)
    return out, orphan


def collect(frm):
    camps = {cid: r for cid, r in v2_campaigns().items() if "Tinely" in (r.get("name") or "")}
    till = (date.today() + timedelta(days=1)).isoformat()
    geo = report(frm, till, METRICS, ("campaignId", "country"), list(camps))
    wid = report(frm, till, METRICS, ("campaignId", "widgetId"), list(camps))
    bl = {cid: {base(w) for w in blacklist(cid)[0]} for cid in camps}
    return camps, geo, wid, bl


def geo_table(geo, leads, names):
    t = defaultdict(lambda: {"spent": 0.0, "clicks": 0, "impr": 0, "mgid_conv": 0, "leads": 0, "usd": 0.0,
                             "camps": defaultdict(float)})
    for r in geo:
        iso = names.get(r["country"], r["country"])
        x = t[iso]
        x["spent"] += num(r["spent"])
        x["clicks"] += int(num(r["clicks"]))
        x["impr"] += int(num(r["impressions"]))
        x["mgid_conv"] += int(num(r["conversionsBuy"]))
        x["camps"][str(r["campaignId"])] += num(r["spent"])
    for l in leads:
        x = t[l["geo"]]
        x["leads"] += 1
        x["usd"] += l["usd"]
    return t


def placement_table(wid, leads, camps, bl):
    p = {}
    for r in wid:
        w, c = base(r["widgetId"]), str(r["campaignId"])
        if not w:
            continue
        x = p.setdefault((c, w), {"spent": 0.0, "clicks": 0, "impr": 0, "leads": 0, "usd": 0.0})
        x["spent"] += num(r["spent"])
        x["clicks"] += int(num(r["clicks"]))
        x["impr"] += int(num(r["impressions"]))
    unmatched = []
    for l in leads:
        k = (l["camp"], l["widget"])
        if k in p:
            p[k]["leads"] += 1
            p[k]["usd"] += l["usd"]
        else:
            unmatched.append(l)
    return p, unmatched


def threshold(row):
    cpa = buy_cpa(row)[1] if row else None
    return (MULT * cpa, cpa) if cpa else (FLAT, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conv", required=True, help="cpam-conv.json from cpamatica.mjs conv")
    ap.add_argument("--from", dest="frm", default="2026-09-29")
    ap.add_argument("--out", help="directory for geo.csv, placements.csv and report.md")
    a = ap.parse_args()

    camps, geo, wid, bl = collect(a.frm)
    cids = {str(c) for c in camps}
    leads, orphan = load_leads(a.conv, cids)
    names = iso_by_name()
    nm = {str(c): r["name"].replace("Tinely ", "") for c, r in camps.items()}

    G = geo_table(geo, leads, names)
    P, unmatched = placement_table(wid, leads, camps, bl)
    tot_s = sum(x["spent"] for x in G.values())
    tot_c = sum(x["clicks"] for x in G.values())
    tot_l = len(leads)
    tot_r = sum(l["usd"] for l in leads)
    out = []
    w = out.append

    w(f"# MGID Tinely: гео и площадки ({a.frm} — {date.today().isoformat()})")
    w(f"\nРасход MGID **${tot_s:.2f}**, кликов {tot_c}, лидов cpamatica {tot_l} на **${tot_r:.2f}** "
      f"(+{len(orphan)} тестовых без кампании на ${sum(l['usd'] for l in orphan):.2f}), итог **{tot_r - tot_s:+.2f}$**.")

    # ---------------------------------------------------------------- geo
    w("\n## По гео\n")
    w("| Гео | Расход | Клики | CPC | Лиды | CR | Ср. выплата | Доход | Итог | Безубыт. CR | MGID видит лидов |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    geo_rows = []
    for iso, x in sorted(G.items(), key=lambda kv: -kv[1]["spent"]):
        if x["spent"] < 0.005 and not x["leads"]:
            continue
        cpc = x["spent"] / x["clicks"] if x["clicks"] else 0.0
        avg = x["usd"] / x["leads"] if x["leads"] else 0.0
        be = pct(cpc, avg) if avg else None
        geo_rows.append([iso, round(x["spent"], 2), x["clicks"], round(cpc * 100, 2), x["leads"], round(pct(x["leads"], x["clicks"]), 2),
                         round(avg, 2), round(x["usd"], 2), round(x["usd"] - x["spent"], 2), round(be, 2) if be else "", x["mgid_conv"]])
        w(f"| {iso} | ${x['spent']:.2f} | {x['clicks']} | {cpc * 100:.2f}¢ | {x['leads']} | {pct(x['leads'], x['clicks']):.2f}% | "
          f"{'$%.2f' % avg if avg else '—'} | ${x['usd']:.2f} | {x['usd'] - x['spent']:+.2f}$ | "
          f"{'%.1f%%' % be if be else '—'} | {x['mgid_conv']} |")
    w("\nCPC — средняя цена клика; безубыточный CR = CPC / средняя выплата лида (где лидов нет, считать нечем).")

    # geo inside each campaign that spent over $3
    for cid in sorted(cids, key=lambda c: -sum(num(r["spent"]) for r in geo if str(r["campaignId"]) == c)):
        rows = [r for r in geo if str(r["campaignId"]) == cid and num(r["spent"]) > 0]
        if sum(num(r["spent"]) for r in rows) < 3:
            continue
        w(f"\n**{nm[cid]} ({cid})** по странам:\n")
        w("| Гео | Расход | Клики | Лиды | Доход |")
        w("|---|---|---|---|---|")
        for r in sorted(rows, key=lambda r: -num(r["spent"])):
            iso = names.get(r["country"], r["country"])
            ls = [l for l in leads if l["camp"] == cid and l["geo"] == iso]
            w(f"| {iso} | ${num(r['spent']):.2f} | {int(num(r['clicks']))} | {len(ls)} | ${sum(l['usd'] for l in ls):.2f} |")

    # ---------------------------------------------------------------- placements
    w("\n## Площадки\n")
    w("| Кампания | Площадок с кликами | С лидами | Расход | из него на площадках без лидов | топ-10 площадок | топ-50 |")
    w("|---|---|---|---|---|---|---|")
    conc = {}
    for cid in sorted(cids, key=lambda c: -sum(x["spent"] for (cc, _), x in P.items() if cc == c)):
        ws = sorted(((k[1], x) for k, x in P.items() if k[0] == cid and x["spent"] > 0), key=lambda kv: -kv[1]["spent"])
        s = sum(x["spent"] for _, x in ws)
        if s < 1:
            continue
        s0 = sum(x["spent"] for _, x in ws if not x["leads"])
        top = lambda n: sum(x["spent"] for _, x in ws[:n])  # noqa: E731
        conc[cid] = (len(ws), s)
        w(f"| {nm[cid]} ({cid}) | {len(ws)} | {sum(1 for _, x in ws if x['leads'])} | ${s:.2f} | ${s0:.2f} ({pct(s0, s):.0f}%) | "
          f"{pct(top(10), s):.0f}% | {pct(top(50), s):.0f}% |")

    w("\n### Площадки с лидами\n")
    w("| Кампания | Площадка | Расход | Клики | Лиды | Доход | Итог | В блоке |")
    w("|---|---|---|---|---|---|---|---|")
    win = sorted(((k, x) for k, x in P.items() if x["leads"]), key=lambda kv: -(kv[1]["usd"] - kv[1]["spent"]))
    for (c, wd), x in win:
        w(f"| {nm[c]} ({c}) | {wd} | ${x['spent']:.2f} | {x['clicks']} | {x['leads']} | ${x['usd']:.2f} | "
          f"{x['usd'] - x['spent']:+.2f}$ | {'да' if wd in bl.get(int(c), set()) else 'нет'} |")
    if unmatched:
        w(f"\nЛиды, чью площадку не нашли в отчёте MGID: {len(unmatched)} на ${sum(l['usd'] for l in unmatched):.2f}.")

    w("\n### Правило «2 цены конверсии без лида» задним числом\n")
    w("| Кампания | Цена конверсии | Порог | Площадок выше порога без лида | Расход выше порога | Уже в блоке | Не в блоке |")
    w("|---|---|---|---|---|---|---|")
    replay = {}
    for cid in sorted(cids):
        thr, cpa = threshold(camps[int(cid)])
        off = [(k[1], x) for k, x in P.items() if k[0] == cid and x["spent"] >= thr and not x["leads"]]
        if not off and sum(x["spent"] for k, x in P.items() if k[0] == cid) < 1:
            continue
        done = [wd for wd, _ in off if wd in bl.get(int(cid), set())]
        left = [(wd, x) for wd, x in off if wd not in bl.get(int(cid), set())]
        exc = sum(x["spent"] - thr for _, x in off)
        replay[cid] = (thr, len(off), exc, len(done), left)
        w(f"| {nm[cid]} ({cid}) | {'$%.2f' % cpa if cpa else '—'} | ${thr:.2f} | {len(off)} | ${exc:.2f} | {len(done)} | {len(left)} |")
    w("\nРасход выше порога — сколько на этих площадках потрачено сверх линии: верхняя граница того, что сэкономил бы сторож, сработав ровно на пороге.")

    # ---------------------------------------------------------------- files
    text = "\n".join(out)
    print(text)
    if a.out:
        d = Path(a.out)
        d.mkdir(parents=True, exist_ok=True)
        (d / "report.md").write_text(text + "\n")
        with open(d / "geo.csv", "w", newline="") as f:
            cw = csv.writer(f)
            cw.writerow(["geo", "spent", "clicks", "cpc_cents", "leads", "cr_pct", "avg_payout", "revenue", "pnl", "breakeven_cr_pct", "mgid_conv"])
            cw.writerows(geo_rows)
        with open(d / "placements.csv", "w", newline="") as f:
            cw = csv.writer(f)
            cw.writerow(["campaign", "campaign_name", "widget", "spent", "clicks", "impressions", "leads", "revenue", "pnl", "blocked"])
            for (c, wd), x in sorted(P.items(), key=lambda kv: -kv[1]["spent"]):
                if x["spent"] > 0 or x["leads"]:
                    cw.writerow([c, nm[c], wd, round(x["spent"], 4), x["clicks"], x["impr"], x["leads"], round(x["usd"], 2),
                                 round(x["usd"] - x["spent"], 4), int(wd in bl.get(int(c), set()))])
        print(f"\n(записано в {d}: report.md, geo.csv, placements.csv)", file=sys.stderr)


if __name__ == "__main__":
    main()
