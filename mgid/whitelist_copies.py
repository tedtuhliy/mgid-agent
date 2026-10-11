"""Whitelist copies of the two girls campaigns: only the placements that gave a lead, at the minimum CPC.

    python3 whitelist_copies.py            # plan: reads the sources and the placements, creates nothing
    python3 whitelist_copies.py --apply    # create (paused), whitelist, UTM, teasers; read back; then start

The placements are the ones cpamatica reported as approved leads of each source campaign (aff_sub is
the campaign, aff_sub3 the {widget_id} macro), 30.09 to 11.10. They are written out below and checked
at run time: each must still show MGID traffic in its source campaign, or the group is not created.

One copy per offer, not one copy for everything: the teaser link carries the offer id, and the
conversion cost is one number per campaign (the guard reads it from there). Creatives, title and link
are taken from the source's own teasers; every teaser's CPC is the 1.0 cent minimum.
"""
import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from mgid_api import (CID1, CID2, TARGET, V1, V2, buy_cpa, call, campaign, pause, report,
                      v2_campaigns, whitelist_set, widgets_filter)

HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "whitelist-copies.json"
START = "2026-09-29"            # first day of the girls campaigns' data in the report
DAILY_USD = 20.0                # MGID's minimum daily budget, as in the other copies
CATEGORY = 108                  # Dating
IMG = "https://pixeldrain.com/api/file/"
UTM = {"utm_source": "mgid", "utm_medium": "native", "utm_campaign": "{campaign_id}",
       "utm_custom": "click_id={click_id}&source=mgid_{campaign_id}_{widget_id}"}
WANT_UTM = "click_id=${CLICK_ID}&source=mgid_${CAMPAIGN_ID}_${WIDGET_ID}"

# The minimum CPC is per geo: MGID refused a campaign bid below 1.5 cents on the CIS geos (422
# "bidding.price >= 0.015") and accepted 1.0 cent on LATAM. `bid` is the campaign-level bid in
# dollars, `cpc` the teasers' price in cents; both are the minimum of the group's geos.
GROUPS = [
    {"label": "CIS", "source": 12502232, "offer": 8394, "geo_names": "KZ AZ MD LT",
     "countries": [5, 17, 9, 11], "bid": 0.015, "cpc": 1.5,
     "images": ["odVdUECV", "goFg94KT", "4DeuXaVL"],
     "placements": ["57628091", "57627045", "58022243", "57627015", "57617585", "64349629", "58022244"]},
    {"label": "LATAM", "source": 12502230, "offer": 8326, "geo_names": "CR DO GT PA",
     "countries": [89, 94, 108, 158], "bid": 0.01, "cpc": 1.0,
     "images": ["1NspDXaY", "Z8ewfPfx", "KDfV6CUU"],
     "placements": ["62670116", "72335636", "73376853", "58071814", "72608295", "57830299",
                    "57793776", "57923111"]},
]


def num(x):
    return float(x.get("amount") if isinstance(x, dict) else (x or 0))


def name_of(g):
    return f"Tinely girls {g['label']} mobile WL - {g['geo_names']} ({g['offer']})"


def source_teaser(src):
    """Title and link of the source's own teasers. They must agree, or the copy would be guessing."""
    t = call("GET", V1 + f"goodhits/clients/{CID1}/teasers?campaign={src}&limit=50&start=0")[1]
    xs = [x for x in (t.values() if isinstance(t, dict) else []) if isinstance(x, dict)]
    titles = {x.get("title") for x in xs}
    urls = {x.get("url") for x in xs}
    if not xs or len(titles) != 1 or len(urls) != 1:
        raise SystemExit(f"у исходной {src} тизеры расходятся по заголовку или ссылке: {titles} {urls}")
    return titles.pop(), urls.pop()


def seen_placements(src):
    """Placements that showed impressions in the source campaign over the period, from MGID's report."""
    till = (date.today() + timedelta(days=1)).isoformat()
    rows = report(START, till, ("impressions",), ("campaignId", "widgetId"), [src])
    return {str(r["widgetId"]) for r in rows if num(r.get("impressions")) > 0}


def teasers(cid):
    st, t = call("GET", V1 + f"goodhits/clients/{CID1}/teasers?campaign={cid}&limit=50&start=0")  # start is 0-based
    return {tid: x for tid, x in (t.items() if isinstance(t, dict) else []) if isinstance(x, dict)}


def body_for(g, src_row, name):
    conv = buy_cpa(src_row)[1]
    if conv is None:
        raise SystemExit(f"у исходной {g['source']} нет цены конверсии: сторож не сможет её судить")
    body = {
        "name": name, "showName": "Tinely", "type": src_row.get("type") or "product",
        "isAutoLaunchAdsAfterApproval": True,
        "bidding": {"strategy": "manualBidding", "price": g["bid"]},
        "sourcesOptimization": False,
        "limits": {"limitType": "budget", "dailyLimit": DAILY_USD, "overallLimit": 0.0,
                   "splitDailyLimitEvenly": False},
        "conversionTracking": {"type": "sensors", "decisionStage": None, "interestStage": None,
                               "buyStage": {"targetId": TARGET, "deduplicateConversions": True,
                                            "conversionValue": conv}},
        "geoTargeting": {"countries": g["countries"], "regions": {"mode": "include", "value": []}},
    }
    for k in ("operatingSystemTargeting", "languageTargeting"):
        if src_row.get(k):
            body[k] = src_row[k]
    return body


def check(cid, g, src_row):
    """Everything the copy should be, read back through the API that did not write it. Returns problems."""
    bad = []
    row = v2_campaigns()[cid]
    b = row.get("bidding") or {}
    if b.get("strategy") != "manualBidding" or abs(float(b.get("price") or 0) - g["bid"]) > 1e-9:
        bad.append(f"ставка кампании {b}")
    if sorted((row.get("geoTargeting") or {}).get("countries") or []) != sorted(g["countries"]):
        bad.append(f"гео {(row.get('geoTargeting') or {}).get('countries')}")
    target, conv = buy_cpa(row)
    if target != TARGET or conv != buy_cpa(src_row)[1]:
        bad.append(f"цель конверсии {target} / {conv}")
    typ, uids = widgets_filter(cid)
    if typ != "only" or set(uids) != set(g["placements"]):
        bad.append(f"вайтлист {typ}: {sorted(uids)}")
    c = campaign(cid)
    if (c.get("trackingOptions") or {}).get("utm_custom") != WANT_UTM:
        bad.append(f"UTM {(c.get('trackingOptions') or {}).get('utm_custom')!r}")
    if float((c.get("limitsFilter") or {}).get("dailyLimit") or 0) != DAILY_USD * 100:   # v1 shows it x100
        bad.append(f"дневной лимит {c.get('limitsFilter')}")
    tz = teasers(cid)
    if len(tz) != len(g["images"]):
        bad.append(f"тизеров {len(tz)} из {len(g['images'])}")
    for tid, x in tz.items():
        locs = [float(p.get("priceOfClick") or 0) for p in x.get("priceOfClickByLocations") or []]
        if not locs or any(abs(p - g["cpc"]) > 1e-9 for p in locs):
            bad.append(f"тизер {tid}: ставка по гео {locs or 'не видна'}, нужна {g['cpc']}")
    return bad, tz


def group_run(g, live, apply):
    src = live[g["source"]]
    name = name_of(g)
    title, url = source_teaser(g["source"])
    seen = seen_placements(g["source"])
    gone = [w for w in g["placements"] if w not in seen]
    print(f"\n{name}")
    print(f"   из исходной {g['source']} {src['name']}: площадок в списке {len(g['placements'])}, "
          f"видны MGID: {len(g['placements']) - len(gone)}" + (f", НЕ видны: {gone}" if gone else ""))
    print(f"   гео {g['geo_names']}, ставка {g['cpc']}¢ (кампания ${g['bid']}), бюджет ${DAILY_USD:.0f}/сутки, "
          f"цель {TARGET} за ${buy_cpa(src)[1]}, тизеров {len(g['images'])}, оффер {g['offer']}, заголовок «{title}»")
    if gone:
        return {"name": name, "error": f"площадки не видны MGID: {gone}"}
    cid = next((i for i, r in live.items() if r.get("name") == name), None)
    if not apply:
        print(f"   {'уже есть ' + str(cid) if cid else 'создать'}")
        return None
    if cid is None:
        st, d = call("POST", V2 + f"account/{CID2}/campaigns", body_for(g, src, name))
        if st not in (200, 201) or not isinstance(d, dict) or not d.get("id"):
            print(f"   создание {st} {json.dumps(d, ensure_ascii=False)[:400]}")
            return {"name": name, "error": f"создание {st}"}
        cid = int(d["id"])
        print(f"   создана {cid}")
        time.sleep(2)
    st = pause(cid)                       # MGID creates campaigns active: pause before anything else
    print(f"   пауза до настройки: {st.get('name')}/{st.get('reason')}")
    if st.get("name") != "paused":
        return {"id": cid, "name": name, "error": "не встала на паузу"}
    wst, _ = whitelist_set(cid, g["placements"])
    print(f"   вайтлист: PUT {wst}")
    ust, _ = call("PUT", V1 + f"goodhits/campaigns/{cid}/utmtracking/", UTM, form=True)
    print(f"   UTM: {ust}")
    have = len(teasers(cid))
    for img in g["images"][have:]:
        form = {"campaignId": cid, "url": url, "title": title, "imageLink": IMG + img,
                "priceOfClick": g["cpc"], "categoryId": CATEGORY, "whetherShowGoodPrice": 0}
        tst, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
        out = d.get("id") if isinstance(d, dict) and d.get("id") else json.dumps(d, ensure_ascii=False)[:200]
        print(f"   тизер {img}: {tst} {out}")
        time.sleep(1)
    time.sleep(2)
    bad, tz = check(cid, g, src)
    print(f"   проверка: {'всё совпало' if not bad else 'РАСХОЖДЕНИЯ'}; тизеры "
          f"{[(t, (x.get('status') or {}).get('code')) for t, x in tz.items()]}")
    for b in bad:
        print("     !", b)
    if bad:
        return {"id": cid, "name": name, "problems": bad}          # stays paused
    st = pause(cid, on=False)
    print(f"   старт: {st.get('name')}/{st.get('reason')}")
    return {"id": cid, "name": name, "geo": g["geo_names"], "offer": g["offer"],
            "placements": g["placements"], "teasers": sorted(tz), "status": st.get("name"), "problems": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", choices=[g["label"] for g in GROUPS], help="one group, e.g. CIS")
    a = ap.parse_args()
    live = v2_campaigns()
    results = {}
    for g in GROUPS:
        if a.only and g["label"] != a.only:
            continue
        if g["source"] not in live:
            raise SystemExit(f"исходной кампании {g['source']} нет в v2")
        r = group_run(g, live, a.apply)
        if r:
            results[g["label"]] = r
            live = v2_campaigns()
    if not a.apply:
        print("\n(без --apply ничего не создаётся)")
        return
    OUT.parent.mkdir(exist_ok=True)
    saved = json.load(open(OUT)) if OUT.exists() else {}      # a run for one group keeps the other
    saved.update(results)
    json.dump(saved, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\nзаписано {OUT}")
    if any(r.get("problems") or r.get("error") for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
