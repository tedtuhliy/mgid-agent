"""Per-geo CPA copies of the Tinely CIS-mobile campaign: Kazakhstan and the Baltics.

Owner, 10.10: «сделай копии ... начать тесты можно с казахов и балтийских стран с тех оферов где
уже были лиды у нас ... стоимость конверсии нужно брать с настроек кампании, а сами ставки с кабинета
cpamatica по каждому гео отдельно».

    python3 mgid_geo_copies.py                      # plan only, creates nothing
    python3 mgid_geo_copies.py --apply [--only KZ]  # create (paused), UTM, teasers, read everything back
    python3 mgid_geo_copies.py --sync-rates         # copies' CPA <- data/rates-8394.json (after a cabinet change)
    python3 mgid_geo_copies.py --resume             # start the copies (needs a positive balance)

Where it comes from. Offer Tinely (8394) is the only cpamatica offer that has paid us in these
geos: 7 leads from Kazakhstan at $0.56 and 1 from Lithuania at $0.44, all of them from the two CIS
mobile tests of 30.09–01.10 (campaigns 12501891 and 12502232). Latvia and Estonia sit on the same
offer and have a cabinet rate, but no lead yet. One campaign per geo, because the rate differs by
geo (KZ 0.56, LT 0.44, LV 0.32, EE 1.48) and the guard judges each campaign by its own CPA.

What a copy is. The live settings of the source campaign (`SOURCE`: type, mobile OS list, Russian
browser language) with four changes:
- geo: the one country;
- bidding: `targetCpa`, price = the cabinet rate of that geo x `CPA_SHARE`;
- conversion cost: the same figure in the buy stage of target 1274200, which is the number the
  placement guard reads (inferno/mgid_guard.py, spend >= 2 x this and no lead -> block);
- daily budget: the $20 minimum, not the $2000 the 30.09 relaunch left on the girls campaigns.
Everything else as before: UTM that returns click id, campaign and placement with the lead, three
women-only teasers (same photos, same title, same cpamatica link), category 108 Dating.

Safety. MGID creates a campaign ACTIVE, so each copy is paused right after creation (and kept off
auto-launch), which means nothing runs on a top-up by itself. `--resume` is the single switch that
starts them.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from cpam_rates import load as load_rates
from mgid_api import CID1, CID2, TARGET, V1, V2, buy_cpa, call, campaign, pause, v2_campaigns

HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "geo-copies.json"

SOURCE = 12502232          # Tinely girls CIS mobile: the relaunched campaign that has live settings
OFFER = 8394               # Tinely [LT, LV, EE, KZ, MD, GE, AZ]; leads: KZ x7, LT x1
GEOS = ["KZ", "LT", "LV", "EE"]
# Share of the cabinet rate used as the CPA target and as the conversion cost. 1.0 is the owner's
# instruction (the bid IS the cabinet rate). At 1.0 the best case is break-even, so lower it here,
# in this one place, to leave a margin: 0.7 means a target of 70% of the payout.
CPA_SHARE = 1.0
DAILY_USD = 20.0           # MGID's minimum daily budget
TEASER_CENTS = 1.5         # as on the live copies; the CPC itself is chosen by targetCpa
IMG = "https://pixeldrain.com/api/file/"
IMAGES = ["odVdUECV", "goFg94KT", "4DeuXaVL"]          # 1200x800, women alone (30.09 relaunch)
TITLE = "Одинокие девушки в г. {City} — кто онлайн"
LINK = ("https://go.cm-trk6.com/aff_c?offer_id={offer}&aff_id=5084&aff_sub5=mgid"
        "&aff_sub={{campaign_id}}&aff_sub3={{widget_id}}")
UTM = {"utm_source": "mgid", "utm_medium": "native", "utm_campaign": "{campaign_id}",
       "utm_custom": "click_id={click_id}&source=mgid_{campaign_id}_{widget_id}"}
WANT_UTM = "click_id=${CLICK_ID}&source=mgid_${CAMPAIGN_ID}_${WIDGET_ID}"


def name_of(geo):
    return f"Tinely girls {geo} mobile CPA"


def country_ids():
    st, d = call("GET", V2 + "dictionaries/countries")
    if st != 200:
        raise SystemExit(f"справочник стран: {st} {str(d)[:200]}")
    return {c["iso"]: int(c["id"]) for c in d["data"]}


def cpa_of(geo, rates):
    if geo not in rates["payouts"]:
        raise SystemExit(f"в кабинете нет ставки для {geo}: {rates['payouts']}")
    return round(rates["payouts"][geo] * CPA_SHARE, 3)


def body_for(geo, cid_geo, cpa, src):
    body = {
        "name": name_of(geo), "showName": "Tinely", "type": src.get("type") or "product",
        "isAutoLaunchAdsAfterApproval": False,
        "bidding": {"strategy": "targetCpa", "price": cpa},
        "sourcesOptimization": False,
        "limits": {"limitType": "budget", "dailyLimit": DAILY_USD, "splitDailyLimitEvenly": False},
        "conversionTracking": {"type": "sensors", "decisionStage": None, "interestStage": None,
                               "buyStage": {"targetId": TARGET, "deduplicateConversions": True,
                                            "conversionValue": cpa}},
        "geoTargeting": {"countries": [cid_geo], "regions": {"mode": "include", "value": []}},
    }
    for k in ("operatingSystemTargeting", "languageTargeting", "browserTargeting"):
        if src.get(k):
            body[k] = src[k]
    return body


def teasers(cid):
    st, t = call("GET", V1 + f"goodhits/clients/{CID1}/teasers?campaign={cid}&limit=50&start=0")  # start is 0-based
    return {tid: x for tid, x in (t.items() if isinstance(t, dict) else []) if isinstance(x, dict)}


def read_back(cid, geo, cpa):
    """Everything the copy should be, read through the API that did not write it. Returns problems."""
    bad = []
    row = v2_campaigns().get(cid) or {}
    b = row.get("bidding") or {}
    if b.get("strategy") != "targetCpa" or abs(float(b.get("price") or 0) - cpa) > 1e-9:
        bad.append(f"ставка {b}, а нужна targetCpa {cpa}")
    if (row.get("status") or {}).get("name") != "paused":
        bad.append(f"статус {row.get('status')}, а нужна пауза")
    if (row.get("geoTargeting") or {}).get("countries") != [country_ids()[geo]]:
        bad.append(f"гео {(row.get('geoTargeting') or {}).get('countries')}")
    target, price = buy_cpa(row)      # v1 `conversions` does not answer for targetCpa campaigns
    if target != TARGET or price is None or abs(price - cpa) > 1e-9:
        bad.append(f"цена конверсии v2: цель {target} / {price}, а нужна {TARGET} / {cpa}")
    c = campaign(cid)
    lim = (c.get("limitsFilter") or {})
    if float(lim.get("dailyLimit") or 0) != DAILY_USD * 100:      # v1 shows the daily budget x100
        bad.append(f"дневной лимит v1 {lim}, ждали {DAILY_USD * 100:.0f} (= ${DAILY_USD:.0f})")
    if (c.get("trackingOptions") or {}).get("utm_custom") != WANT_UTM:
        bad.append(f"UTM {(c.get('trackingOptions') or {}).get('utm_custom')!r}")
    tz = teasers(cid)
    if len(tz) != len(IMAGES):
        bad.append(f"тизеров {len(tz)} из {len(IMAGES)}")
    return bad, tz


def create(geo, ids, rates, src, live):
    cpa = cpa_of(geo, rates)
    name = name_of(geo)
    cid = next((i for i, x in live.items() if x.get("name") == name), None)
    if not cid:
        st, d = call("POST", V2 + f"account/{CID2}/campaigns", body_for(geo, ids[geo], cpa, src))
        if st not in (200, 201) or not isinstance(d, dict) or not d.get("id"):
            print(f"{name}: создание {st} {json.dumps(d, ensure_ascii=False)[:500]}")
            return None
        cid = int(d["id"])
        print(f"{name}: создана {cid}")
        time.sleep(2)
    else:
        print(f"{name}: уже есть {cid}, достраиваю")
    # paused first: nothing may run before the checks below are green. MGID creates the campaign
    # active (with no funds it just sits there), so this is not optional.
    st = pause(cid)
    print(f"  пауза: {st.get('name')}/{st.get('reason')}")
    # the three utm_* fields go together, form body only
    st, _ = call("PUT", V1 + f"goodhits/campaigns/{cid}/utmtracking/", UTM, form=True)
    print(f"  UTM: {st}")
    # MGID re-hosts images on imghosts.com, so a teaser cannot be matched to its source link;
    # a rerun tops the campaign up to three teasers instead of matching images.
    have = len(teasers(cid))
    for img in IMAGES[have:]:
        form = {"campaignId": cid, "url": LINK.format(offer=OFFER), "title": TITLE, "imageLink": IMG + img,
                "priceOfClick": TEASER_CENTS, "categoryId": 108, "whetherShowGoodPrice": 0}
        st, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
        print(f"  тизер {img}: {st} {d.get('id') if isinstance(d, dict) and d.get('id') else json.dumps(d, ensure_ascii=False)[:300]}")
        time.sleep(1)
    time.sleep(2)
    bad, tz = read_back(cid, geo, cpa)
    print(f"  проверка: {'всё совпало' if not bad else 'ЕСТЬ РАСХОЖДЕНИЯ'}; тизеры "
          f"{[(t, (x.get('status') or {}).get('code')) for t, x in tz.items()]}")
    for b in bad:
        print("    !", b)
    return {"id": cid, "name": name, "geo": geo, "offer": OFFER, "cpa": cpa, "payout": rates["payouts"][geo],
            "source": SOURCE, "teasers": sorted(tz), "problems": bad}


def known():
    return json.load(open(OUT)) if OUT.exists() else {}


def sync_rates(rates):
    """Copies' CPA <- the saved cabinet rates. A cabinet rate can drop (the cpamatica skill logs
    «снизили выплату»); the copy would keep bidding the old figure until this runs."""
    live = v2_campaigns()
    for geo in GEOS:
        row = next((x for i, x in live.items() if x.get("name") == name_of(geo)), None)
        if not row:
            print(f"{geo}: копии нет")
            continue
        cpa = cpa_of(geo, rates)
        cur = ((row.get("conversionTracking") or {}).get("buyStage") or {}).get("conversionValue")
        now = (row.get("bidding") or {}).get("price")
        if cur == cpa and now == cpa:
            print(f"{geo}: CPA {cpa} совпадает с кабинетом")
            continue
        body = {"name": row["name"], "isAutoLaunchAdsAfterApproval": False,
                "bidding": {"strategy": "targetCpa", "price": cpa},
                "conversionTracking": {"type": "sensors", "decisionStage": None, "interestStage": None,
                                       "buyStage": {"targetId": TARGET, "deduplicateConversions": True,
                                                    "conversionValue": cpa}}}
        st, d = call("PATCH", V2 + f"account/{CID2}/campaigns/{row['id']}", body)
        print(f"{geo}: было ставка {now} / цена конверсии {cur}, стало {cpa}: PATCH {st} {'' if st in (200, 204) else d}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", help="одно гео, например KZ")
    ap.add_argument("--sync-rates", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--force", action="store_true", help="--resume при нулевом балансе")
    a = ap.parse_args()
    rates = load_rates(OFFER)
    if rates.get("status") != 1:
        raise SystemExit(f"оффер {OFFER} в кабинете не ACTIVE (status {rates.get('status')}): лить нельзя")
    geos = [a.only.upper()] if a.only else GEOS

    if a.sync_rates:
        return sync_rates(rates)
    if a.resume:
        st, w = call("GET", V1 + f"clients/{CID1}")
        bal = ((w or {}).get("wallet") or {}).get("balance") if isinstance(w, dict) else None
        print(f"баланс аккаунта: {bal}")
        if (bal is None or float(bal) <= 0) and not a.force:
            raise SystemExit("баланс не положительный — не запускаю (--force, если это сделано сознательно)")
        for g, x in known().items():
            if g in geos:
                st = pause(x["id"], on=False)
                print(f"{g} {x['id']}: {st.get('name')}/{st.get('reason')}")
        return

    live = v2_campaigns()
    src = live.get(SOURCE)
    if not src:
        raise SystemExit(f"исходной кампании {SOURCE} нет в v2")
    ids = country_ids()
    print(f"оффер {rates['name']} ({OFFER}), ставки кабинета на {rates['fetched']}: "
          f"{ {g: rates['payouts'].get(g) for g in GEOS} }")
    print(f"источник {SOURCE} {src['name']}: ОС {len((src.get('operatingSystemTargeting') or {}).get('value') or [])} шт, "
          f"язык {src.get('languageTargeting')}\n")
    done = known()
    for g in geos:
        cpa = cpa_of(g, rates)
        exists = next((i for i, x in live.items() if x.get("name") == name_of(g)), None)
        if not a.apply:
            print(f"{g}: {name_of(g)} — {'уже есть ' + str(exists) if exists else 'создать'}; гео {ids[g]}, "
                  f"targetCpa ${cpa} (ставка кабинета {rates['payouts'][g]} x {CPA_SHARE}), "
                  f"цена конверсии ${cpa}, бюджет ${DAILY_USD:.0f}/сутки, {len(IMAGES)} тизера, пауза")
            continue
        r = create(g, ids, rates, src, live)
        if r:
            done[g] = r
        OUT.parent.mkdir(exist_ok=True)
        json.dump(done, open(OUT, "w"), ensure_ascii=False, indent=1)
    if not a.apply:
        print("\n(без --apply ничего не создаётся)")
    elif any(x.get("problems") for x in done.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
