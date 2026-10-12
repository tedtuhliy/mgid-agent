"""Test campaigns for the approved mainstream dating offers that are not run on MGID yet (12.10).

Owner, 12.10: «Подготовь все гео на тест»: Tinely ES (9960), ZA (8331), HT (8330), CO (8329) and the offers
labelled Mainstream: Date4you US (5368), iDates UK (5655) and DE (5656), Singles-Meets US (9047), Singles-meets US
(9014) and DK (9018), SingleMeets NO (10233). The Multi-Geo (9045) and Flirtooy WW (8978) offers are split by
geo: only the English-speaking geos for now (IE for 9045, AU/CA/NZ for 8978).

    python3 mainstream_tests.py          # plan: prints every campaign, creates nothing
    python3 mainstream_tests.py --apply  # create paused, UTM, 3 teasers each, read everything back

- Bid and conversion cost = 30% of the payout for the geo (the rule in cpa_share.py). Offers that pay in EUR are
  converted at EUR_USD, an estimate: the dated rates found on 12.10 were 1.14-1.16 for late July to early August.
- Creatives: the women-alone photos of the Tinely tests, titles in the language of the geo (the UA lesson: a title in
  another language is rejected as "Language mismatch"). MGID's own language follows the geo unless set.
- Everything is created paused: nothing runs until the owner says so. A campaign already created under the same name
  is reused, and teasers already in place are skipped, so a rerun after the teaser add limit finishes the job.
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mgid_geo_copies as cp  # noqa: E402
from mgid_api import CID1, CID2, V1, V2, buy_cpa, call, pause, v2_campaigns  # noqa: E402

SHARE = 0.30
EUR_USD = 1.15
OUT = HERE / "data" / "mainstream-tests.json"
EN = "Single women in {City} — see who's online now"
ES = "Chicas solteras en {City}: mira quién está en línea"
TESTS = [
    dict(offer=9960, brand="Tinely", geo="ES", usd=1.35, title=ES),
    dict(offer=8331, brand="Tinely", geo="ZA", usd=0.78, title=EN),
    dict(offer=8330, brand="Tinely", geo="HT", usd=0.23, title="Femmes célibataires à {City} — voyez qui est en ligne"),
    dict(offer=8329, brand="Tinely", geo="CO", usd=0.19, title=ES),
    dict(offer=5368, brand="Date4you", geo="US", eur=1.60, title=EN),
    dict(offer=5655, brand="iDates", geo="GB", eur=1.84, title="Single women in {City} — see who's online tonight"),
    dict(offer=5656, brand="iDates", geo="DE", eur=1.60, title="Single-Frauen in {City} — wer ist gerade online?"),
    dict(offer=9047, brand="Singles-Meets", geo="US", eur=1.56, title="Meet singles in {City} — see who's online now"),
    dict(offer=9014, brand="Singles-meets", geo="US", eur=1.56, title="Singles in {City} near you — see who's online"),
    dict(offer=9018, brand="Singles-meets", geo="DK", eur=3.40, title="Single kvinder i {City} — se hvem der er online nu"),
    dict(offer=10233, brand="SingleMeets", geo="NO", eur=3.50, title="Single kvinner i {City} — se hvem som er pålogget nå"),
    dict(offer=9045, brand="Singles-Meets", geo="IE", eur=2.35, title=EN),
    dict(offer=8978, brand="Flirtooy", geo="AU", usd=5.0, title=EN),
    dict(offer=8978, brand="Flirtooy", geo="CA", usd=4.0, title=EN),
    dict(offer=8978, brand="Flirtooy", geo="NZ", usd=4.0, title=EN),
]


def payout_usd(t):
    return t["usd"] if "usd" in t else t["eur"] * EUR_USD


def bid(t):
    return round(SHARE * payout_usd(t), 4)


def name_of(t):
    return f"{t['brand']} {t['geo']} mobile CPA ({t['offer']})"


def body(t, country_id, cpa, src):
    b = cp.body_for(t["geo"], country_id, cpa, src)
    b["name"] = name_of(t)
    b["showName"] = t["brand"]
    b["isAutoLaunchAdsAfterApproval"] = True
    b.pop("languageTargeting", None)     # the source is Russian-only; the geo sets the language
    return b


def add_teasers(cid, t):
    """Adds the missing creatives. Returns (added rows, hit the add limit)."""
    have = {x.get("imageLink") for x in cp.teasers(cid).values() if isinstance(x, dict)}
    link = cp.LINK.format(offer=t["offer"])
    rows = []
    for img in cp.IMAGES:
        if cp.IMG + img in have:
            continue
        form = {"campaignId": cid, "url": link, "title": t["title"], "imageLink": cp.IMG + img,
                "priceOfClick": cp.TEASER_CENTS, "categoryId": 108, "whetherShowGoodPrice": 0}
        st, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
        new_id = d.get("id") if isinstance(d, dict) else None
        rows.append({"image": img, "status": st, "id": new_id,
                     "error": None if new_id else json.dumps(d, ensure_ascii=False)[:200]})
        print(f"    тизер {img}: {st} {new_id or json.dumps(d, ensure_ascii=False)[:160]}")
        if isinstance(d, dict) and any("LS_TEASER_ADD_LIMIT_ERROR" in e for e in (d.get("errors") or [])):
            print("    лимит добавления тизеров: остальные позже, запустите --apply ещё раз")
            return rows, True
        time.sleep(1)
    return rows, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    live = v2_campaigns()
    src = live.get(cp.SOURCE)
    if not src:
        raise SystemExit(f"исходной кампании {cp.SOURCE} нет в v2")
    ids = cp.country_ids()
    for t in TESTS:
        t["country_id"] = ids[t["geo"]]
        print(f"план: {name_of(t)} | гео {t['geo']} ({t['country_id']}) | выплата ${payout_usd(t):.4f} | "
              f"ставка ${bid(t):.4f} | «{t['title']}»")
    if not a.apply:
        print("(без --apply ничего не создаётся)")
        return

    results = []
    limit_hit = False
    for t in TESTS:
        name = name_of(t)
        cid = next((i for i, x in live.items() if x.get("name") == name), None)
        if cid:
            print(f"{name}: уже есть {cid}, достраиваю")
        else:
            st, d = call("POST", V2 + f"account/{CID2}/campaigns", body(t, t["country_id"], bid(t), src))
            if st not in (200, 201) or not isinstance(d, dict) or not d.get("id"):
                print(f"{name}: создание {st} {json.dumps(d, ensure_ascii=False)[:300]}")
                results.append({"name": name, "error": f"создание {st}"})
                continue
            cid = int(d["id"])
            print(f"{name}: создана {cid}")
            time.sleep(2)
        st = pause(cid)
        print(f"  пауза: {st.get('name')}/{st.get('reason')}")
        st, _ = call("PUT", V1 + f"goodhits/campaigns/{cid}/utmtracking/", cp.UTM, form=True)
        print(f"  UTM: {st}")
        rows, hit = ([], True) if limit_hit else add_teasers(cid, t)
        limit_hit = limit_hit or hit
        time.sleep(2)
        row = v2_campaigns().get(cid) or {}
        b = row.get("bidding") or {}
        now = cp.teasers(cid)
        codes = sorted({str((x.get("status") or {}).get("code")) for x in now.values() if isinstance(x, dict)})
        problems = []
        if b.get("strategy") != "targetCpa" or abs(float(b.get("price") or 0) - bid(t)) > 1e-9:
            problems.append(f"ставка {b}")
        if abs((buy_cpa(row)[1] or 0) - bid(t)) > 1e-9:
            problems.append(f"конверсия {buy_cpa(row)[1]}")
        if (row.get("geoTargeting") or {}).get("countries") != [t["country_id"]]:
            problems.append(f"гео {(row.get('geoTargeting') or {}).get('countries')}")
        print(f"  проверка: ставка {b.get('price')}, тизеров {len(now)} {codes}; {'; '.join(problems) or 'всё совпало'}")
        results.append({"name": name, "cid": cid, "offer": t["offer"], "geo": t["geo"], "bid": bid(t),
                        "teasers_in_campaign": len(now), "teasers_added": rows, "problems": problems})

    OUT.parent.mkdir(exist_ok=True)
    json.dump(results, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"записано: {OUT}")


if __name__ == "__main__":
    main()
