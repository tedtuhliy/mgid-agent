"""Ukraine, second campaign: recreated with the Ukrainian creatives that already served in Ukraine.

Owner, 12.10: «ошибка осталась нужно кампанию пересоздать заново с новыми укр креативами».

- The first UA campaign (12511370) copied the browser language of its CIS source: Russian only (value [39]).
  The old Ukrainian campaign that delivered 557 clicks in Ukraine (12478529 on account 816921) had no language
  targeting, so the new campaign has none either.
- Creatives: the ten Ukrainian teasers of 12478529, with the same titles and images (data/ua-old-teasers.json),
  and our standard link (aff_sub5=mgid). New teasers still go through MGID's moderation.
- Bid and conversion cost $0.01 (targetCpa), $20 a day, offer 8395, geo Ukraine, mobile OS list of the source.
- The first campaign 12511370 is paused, not deleted.

    python3 ua_v2.py              # plan: prints the settings, creates nothing
    python3 ua_v2.py --apply      # create paused, UTM, teasers, read back, pause 12511370
    python3 ua_v2.py --resume     # start the new campaign (needs a positive balance)
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mgid_geo_copies as cp  # noqa: E402
from mgid_api import CID1, CID2, V1, V2, buy_cpa, call, campaign, pause, v2_campaigns  # noqa: E402

NAME = "Tinely girls UA mobile CPA v2"
FIRST = 12511370
OFFER = 8395
GEO = "UA"
CPA = 0.01
RECORD = HERE / "data" / "ua-old-teasers.json"
OUT = HERE / "data" / "ua-v2.json"


def body(src):
    b = cp.body_for(GEO, cp.country_ids()[GEO], CPA, src)
    b["name"] = NAME
    b["isAutoLaunchAdsAfterApproval"] = True
    b.pop("languageTargeting", None)          # no language targeting, as in the campaign that delivered
    return b


def old_teasers():
    return [r for r in json.load(open(RECORD)) if r.get("imageLink")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()

    if a.resume:
        cid = json.load(open(OUT))["id"]
        st, w = call("GET", V1 + f"clients/{CID1}")
        bal = ((w or {}).get("wallet") or {}).get("balance") if isinstance(w, dict) else None
        print(f"баланс аккаунта: {bal}")
        if bal is None or float(bal) <= 0:
            raise SystemExit("баланс не положительный, не запускаю")
        st = pause(cid, on=False)
        print(f"{cid}: {st.get('name')}/{st.get('reason')}")
        return

    live = v2_campaigns()
    src = live.get(cp.SOURCE)
    if not src:
        raise SystemExit(f"исходной кампании {cp.SOURCE} нет в v2")
    teasers_plan = old_teasers()
    print(f"план: {NAME} | гео {GEO} ({cp.country_ids()[GEO]}), оффер {OFFER}, targetCpa ${CPA} / "
          f"конверсия ${CPA}, ${cp.DAILY_USD:.0f}/сутки, без языкового таргетинга, "
          f"{len(teasers_plan)} украинских тизеров из 12478529, пауза {FIRST} после создания")
    if not a.apply:
        print("(без --apply ничего не создаётся)")
        return

    exists = next((i for i, x in live.items() if x.get("name") == NAME), None)
    if exists:
        cid = exists
        print(f"{NAME}: уже есть {cid}, достраиваю")
    else:
        st, d = call("POST", V2 + f"account/{CID2}/campaigns", body(src))
        if st not in (200, 201) or not isinstance(d, dict) or not d.get("id"):
            raise SystemExit(f"создание: {st} {json.dumps(d, ensure_ascii=False)[:500]}")
        cid = int(d["id"])
        print(f"{NAME}: создана {cid}")
        time.sleep(2)
    st = pause(cid)                           # nothing runs before the checks below
    print(f"  пауза: {st.get('name')}/{st.get('reason')}")
    st, _ = call("PUT", V1 + f"goodhits/campaigns/{cid}/utmtracking/", cp.UTM, form=True)
    print(f"  UTM: {st}")

    have = {t.get("imageLink") for t in cp.teasers(cid).values() if isinstance(t, dict)}
    link = cp.LINK.format(offer=OFFER)
    rows = []
    for r in teasers_plan:
        if r["imageLink"] in have:
            continue
        form = {"campaignId": cid, "url": link, "title": r["title"], "imageLink": r["imageLink"],
                "priceOfClick": cp.TEASER_CENTS, "categoryId": 108, "whetherShowGoodPrice": 0}
        st, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
        new_id = d.get("id") if isinstance(d, dict) else None
        print(f"  тизер {r['old_id']} -> {st} {new_id or json.dumps(d, ensure_ascii=False)[:200]}")
        rows.append({"old_id": r["old_id"], "title": r["title"], "imageLink": r["imageLink"],
                     "new_id": new_id, "status": st})
        if isinstance(d, dict) and any("LS_TEASER_ADD_LIMIT_ERROR" in e for e in (d.get("errors") or [])):
            print("  лимит добавления тизеров: остальные не пробую, запустите --apply позже")
            break
        time.sleep(1)

    time.sleep(2)
    row = v2_campaigns().get(cid) or {}
    b = row.get("bidding") or {}
    c = campaign(cid, ("id", "name", "limitsFilter", "trackingOptions"))
    now = cp.teasers(cid)
    problems = []
    if b.get("strategy") != "targetCpa" or abs(float(b.get("price") or 0) - CPA) > 1e-9:
        problems.append(f"ставка {b}")
    if abs((buy_cpa(row)[1] or 0) - CPA) > 1e-9:
        problems.append(f"конверсия {buy_cpa(row)[1]}")
    if (row.get("geoTargeting") or {}).get("countries") != [cp.country_ids()[GEO]]:
        problems.append(f"гео {(row.get('geoTargeting') or {}).get('countries')}")
    if row.get("languageTargeting"):
        problems.append(f"язык {row.get('languageTargeting')}")
    if float(((c.get("limitsFilter") or {}).get("dailyLimit")) or 0) != cp.DAILY_USD * 100:
        problems.append(f"дневной лимит {(c.get('limitsFilter') or {})}")
    if (c.get("trackingOptions") or {}).get("utm_custom") != cp.WANT_UTM:
        problems.append("UTM")
    print(f"  проверка: ставка {b.get('strategy')} {b.get('price')}, конверсия {buy_cpa(row)[1]}, "
          f"язык {row.get('languageTargeting')}, тизеров {len(now)} "
          f"{sorted({(t.get('status') or {}).get('code') for t in now.values() if isinstance(t, dict)})}")
    for p in problems:
        print("    !", p)

    first = pause(FIRST)                      # the first campaign: paused, not deleted
    print(f"  {FIRST} (первая кампания): {first.get('name')}/{first.get('reason')}")
    OUT.parent.mkdir(exist_ok=True)
    json.dump({"id": cid, "name": NAME, "geo": GEO, "offer": OFFER, "cpa": CPA, "paused_first": FIRST,
               "teasers": rows, "teasers_in_campaign": len(now), "problems": problems},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
