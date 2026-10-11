"""LATAM campaign on CPA bidding: every geo that gave a lead, in one campaign.

    python3 latam_cpa.py            # plan: reads the source and its teasers, creates nothing
    python3 latam_cpa.py --apply    # create (paused), UTM and teasers, read everything back, then start

Owner, 11.10: «запусти латам те гео что дали лиды за cpa, все в одной кампании, ставка 0.01, cpa bidding».

- Geos: CR, DO, GT, PA, the LATAM geos with approved leads (cpamatica, 30.09 to 11.10). CL, EC, HN had none.
- Bidding: targetCpa, the CPA target is 0.01 dollars, as the owner set it.
- Conversion cost, the number the guard reads: the same 0.01. The guard then stops a placement once it has
  spent 2 cents without a lead of this campaign. The owner's rule takes the cost from the campaign settings.
- Placements: no whitelist. Every LATAM placement is open to this campaign.
- Teasers: the source LATAM creatives (same images, title and link), CPC 1.0 cent, the minimum MGID accepted
  on LATAM. The campaign is created paused; it is started only after every check below passes.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from mgid_api import (CID1, CID2, TARGET, V1, V2, buy_cpa, call, campaign, pause, v2_campaigns,
                      widgets_filter)
from whitelist_copies import CATEGORY, DAILY_USD, IMG, UTM, WANT_UTM, source_teaser, teasers

HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "latam-cpa.json"
SOURCE = 12502230                       # Tinely girls LATAM mobile: OS, language, teasers
COUNTRIES = [89, 94, 108, 158]          # CR DO GT PA
IMAGES = ["1NspDXaY", "Z8ewfPfx", "KDfV6CUU"]
NAME = "Tinely girls LATAM CPA - CR DO GT PA (8326)"
CPA = 0.01                              # target CPA, dollars, as the owner set it
CONV = CPA                              # conversion cost in the campaign settings, the guard's number
CPC_CENTS = 1.0                         # teasers' price, the LATAM minimum


def body(src):
    return {
        "name": NAME, "showName": "Tinely", "type": src.get("type") or "product",
        "isAutoLaunchAdsAfterApproval": True,
        "bidding": {"strategy": "targetCpa", "price": CPA},
        "sourcesOptimization": False,
        "limits": {"limitType": "budget", "dailyLimit": DAILY_USD, "overallLimit": 0.0,
                   "splitDailyLimitEvenly": False},
        "conversionTracking": {"type": "sensors", "decisionStage": None, "interestStage": None,
                               "buyStage": {"targetId": TARGET, "deduplicateConversions": True,
                                            "conversionValue": CONV}},
        "geoTargeting": {"countries": COUNTRIES, "regions": {"mode": "include", "value": []}},
        "operatingSystemTargeting": src["operatingSystemTargeting"],
        "languageTargeting": src["languageTargeting"],
    }


def check(cid):
    """Everything the campaign should be, read back through the API. Returns problems and teasers."""
    bad = []
    row = v2_campaigns()[cid]
    b = row.get("bidding") or {}
    if b.get("strategy") != "targetCpa" or abs(float(b.get("price") or 0) - CPA) > 1e-9:
        bad.append(f"ставка {b}")
    if sorted((row.get("geoTargeting") or {}).get("countries") or []) != sorted(COUNTRIES):
        bad.append(f"гео {(row.get('geoTargeting') or {}).get('countries')}")
    target, conv = buy_cpa(row)
    if target != TARGET or conv != CONV:
        bad.append(f"цель конверсии {target} / {conv}")
    typ, uids = widgets_filter(cid)
    if typ != "off" or uids:
        bad.append(f"фильтр площадок {typ}: {sorted(uids)}")
    c = campaign(cid)
    if (c.get("trackingOptions") or {}).get("utm_custom") != WANT_UTM:
        bad.append(f"UTM {(c.get('trackingOptions') or {}).get('utm_custom')!r}")
    if float((c.get("limitsFilter") or {}).get("dailyLimit") or 0) != DAILY_USD * 100:   # v1 shows it x100
        bad.append(f"дневной лимит {c.get('limitsFilter')}")
    tz = teasers(cid)
    if len(tz) != len(IMAGES):
        bad.append(f"тизеров {len(tz)} из {len(IMAGES)}")
    for tid, x in tz.items():
        locs = [float(p.get("priceOfClick") or 0) for p in x.get("priceOfClickByLocations") or []]
        if not locs or any(abs(p - CPC_CENTS) > 1e-9 for p in locs):
            bad.append(f"тизер {tid}: ставка {locs or 'не видна'}, нужна {CPC_CENTS}")
    return bad, tz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    live = v2_campaigns()
    if SOURCE not in live:
        raise SystemExit(f"исходной кампании {SOURCE} нет в v2")
    src = live[SOURCE]
    title, url = source_teaser(SOURCE)
    wallet = call("GET", V1 + f"clients/{CID1}")[1].get("wallet")
    print(f"{NAME}")
    print(f"   гео CR DO GT PA, targetCpa ${CPA}, стоимость конверсии в настройках ${CONV} "
          f"(сторож: 2 x = ${2 * CONV:.2f} без лида), бюджет ${DAILY_USD:.0f}/сутки, тизеров {len(IMAGES)} "
          f"по {CPC_CENTS}¢, заголовок «{title}», без вайтлиста")
    print(f"   кошелёк MGID до запуска: {wallet}")
    cid = next((i for i, r in live.items() if r.get("name") == NAME), None)
    if not a.apply:
        print(f"   {'уже есть ' + str(cid) if cid else 'создать'}")
        print("\n(без --apply ничего не создаётся)")
        return
    if cid is None:
        st, d = call("POST", V2 + f"account/{CID2}/campaigns", body(src))
        if st not in (200, 201) or not isinstance(d, dict) or not d.get("id"):
            print(f"   создание {st} {json.dumps(d, ensure_ascii=False)[:400]}")
            sys.exit(1)
        cid = int(d["id"])
        print(f"   создана {cid}")
        time.sleep(2)
    st = pause(cid)                                   # MGID creates campaigns active: pause first
    print(f"   пауза до настройки: {st.get('name')}/{st.get('reason')}")
    if st.get("name") != "paused":
        sys.exit(1)
    ust, _ = call("PUT", V1 + f"goodhits/campaigns/{cid}/utmtracking/", UTM, form=True)
    print(f"   UTM: {ust}")
    have = len(teasers(cid))
    for img in IMAGES[have:]:
        form = {"campaignId": cid, "url": url, "title": title, "imageLink": IMG + img,
                "priceOfClick": CPC_CENTS, "categoryId": CATEGORY, "whetherShowGoodPrice": 0}
        tst, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
        out = d.get("id") if isinstance(d, dict) and d.get("id") else json.dumps(d, ensure_ascii=False)[:200]
        print(f"   тизер {img}: {tst} {out}")
        time.sleep(1)
    time.sleep(2)
    bad, tz = check(cid)
    print(f"   проверка: {'всё совпало' if not bad else 'РАСХОЖДЕНИЯ'}; тизеры "
          f"{[(t, (x.get('status') or {}).get('code')) for t, x in tz.items()]}")
    for b in bad:
        print("     !", b)
    if bad:
        sys.exit(1)                                   # stays paused
    st = pause(cid, on=False)
    print(f"   старт: {st.get('name')}/{st.get('reason')}")
    OUT.parent.mkdir(exist_ok=True)
    json.dump({"id": cid, "name": NAME, "geo": "CR DO GT PA", "cpa": CPA, "conv": CONV,
               "teasers": sorted(tz), "status": st.get("name")},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"записано {OUT}")


if __name__ == "__main__":
    main()
