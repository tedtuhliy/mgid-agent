"""Ukraine: one CPA copy of the Tinely CIS mobile campaign on the UA offer, bid 1 cent.

Owner, 12.10: «На Украину есть объявления? Убери блеклист и запусти Украину на cpa tune 1 цент?»

- Offer 8395, Tinely - Mobile/Desktop [UA] SOI 18+ (Exclusive): the cabinet card is ACTIVE, payout $1.00, UA only.
- Bid and conversion cost are $0.01, the owner's figure. At a $1.00 payout that is 1% of the payout; the 10% rule
  in cpa_share.py would bid $0.10. The owner's figure is used here.
- No placement blacklist: the copy takes only the mobile settings of the source campaign, so the 243 placements
  blocked on it stay behind. The account's sources blocklist was switched off on 12.10; the list it held is in
  data/sources-blocklist-before-12.10.json.
- Created paused and read back; --resume starts it. Auto-launch after approval is on, so the ads start by
  themselves once MGID approves the teasers.

    python3 ua_copy.py              # plan only, creates nothing
    python3 ua_copy.py --apply      # create paused, UTM, 3 teasers, read everything back
    python3 ua_copy.py --resume     # start it (needs a positive balance)
"""
import argparse
import json
import sys
import time
from pathlib import Path

import mgid_geo_copies as cp
from mgid_api import CID1, CID2, V1, V2, call, campaign, pause, v2_campaigns

OFFER = 8395
GEO = "UA"
CPA = 0.01
OUT = Path(__file__).resolve().parent / "data" / "ua-copy.json"


def body(src, country_id):
    b = cp.body_for(GEO, country_id, CPA, src)
    b["isAutoLaunchAdsAfterApproval"] = True
    return b


def plan(src):
    print(f"{cp.name_of(GEO)}: гео {cp.country_ids()[GEO]} (Ukraine), оффер {OFFER}, targetCpa ${CPA} / "
          f"цена конверсии ${CPA}, бюджет ${cp.DAILY_USD:.0f}/сутки, {len(cp.IMAGES)} тизера, пауза при создании")
    print(f"  ОС и язык с источника {cp.SOURCE} {src['name']}; блеклист площадок не переносится")


def create(live, src):
    name = cp.name_of(GEO)
    cid = next((i for i, x in live.items() if x.get("name") == name), None)
    if cid:
        print(f"{name}: уже есть {cid}, достраиваю")
    else:
        st, d = call("POST", V2 + f"account/{CID2}/campaigns", body(src, cp.country_ids()[GEO]))
        if st not in (200, 201) or not isinstance(d, dict) or not d.get("id"):
            raise SystemExit(f"создание: {st} {json.dumps(d, ensure_ascii=False)[:500]}")
        cid = int(d["id"])
        print(f"{name}: создана {cid}")
        time.sleep(2)
    # paused first: nothing may run before the checks below are green
    st = pause(cid)
    print(f"  пауза: {st.get('name')}/{st.get('reason')}")
    st, _ = call("PUT", V1 + f"goodhits/campaigns/{cid}/utmtracking/", cp.UTM, form=True)
    print(f"  UTM: {st}")
    url = cp.LINK.format(offer=OFFER)
    for img in cp.IMAGES[len(cp.teasers(cid)):]:
        form = {"campaignId": cid, "url": url, "title": cp.TITLE, "imageLink": cp.IMG + img,
                "priceOfClick": cp.TEASER_CENTS, "categoryId": 108, "whetherShowGoodPrice": 0}
        st, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
        shown = d.get("id") if isinstance(d, dict) and d.get("id") else json.dumps(d, ensure_ascii=False)[:300]
        print(f"  тизер {img}: {st} {shown}")
        time.sleep(1)
    time.sleep(2)
    bad, tz = cp.read_back(cid, GEO, CPA)
    wf = campaign(cid, ("id", "widgetsFilterUid")).get("widgetsFilterUid") or {}
    if (wf.get("widgets") or []) or wf.get("filterType") not in (None, "off"):
        bad.append(f"в кампании есть блеклист площадок: {str(wf)[:80]}")
    print(f"  проверка: {'всё совпало' if not bad else 'ЕСТЬ РАСХОЖДЕНИЯ'}; тизеры "
          f"{[(t, (x.get('status') or {}).get('code')) for t, x in tz.items()]}")
    for b in bad:
        print("    !", b)
    return {"id": cid, "name": name, "geo": GEO, "offer": OFFER, "cpa": CPA,
            "source": cp.SOURCE, "teasers": sorted(tz), "problems": bad}


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
    plan(src)
    if not a.apply:
        print("(без --apply ничего не создаётся)")
        return
    r = create(live, src)
    OUT.parent.mkdir(exist_ok=True)
    json.dump(r, open(OUT, "w"), ensure_ascii=False, indent=1)
    if r["problems"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
