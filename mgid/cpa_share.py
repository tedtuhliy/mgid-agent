"""CPA bid of dating campaigns = 10% of the cpamatica payout for their geo.

    python3 cpa_share.py 12502227 12502228           # plan: prints the bid and the current settings, changes nothing
    python3 cpa_share.py --apply 12502227 12502228   # PATCH each campaign, then read it back

Owner, 12.10: «Точней поставь 10% от выплат на гео ставку cpatune».

- One campaign has one bid: MGID cannot price geos apart inside a campaign. A campaign on several geos gets
  10% of the LOWEST payout among them, so no geo is bid above 10% of its own payout. Exact per-geo bids would
  need one campaign per geo, which is a new campaign rather than a setting.
- The bid (targetCpa price) and the conversion cost in the campaign settings are the same number. The guard
  stops a placement after 2x that cost without a lead, so its threshold follows the bid.
- Teasers are not touched: MGID refuses a teaser CPC change under CPA bidding.
- Payouts come from data/rates-<offer>.json, saved from the cabinet card by cpam_rates.py. A geo without a
  payout is refused, never guessed.
- MGID has been slow to show a PATCH in reads, so the read-back polls for up to two minutes.
"""
import argparse
import json
import re
import sys
import time

from cpam_rates import load
from mgid_api import CID1, CID2, TARGET, V2, buy_cpa, call, v1, v2_campaigns

SHARE = 0.10
# MGID country ids from dictionaries/countries, checked 12.10
COUNTRY_ID = {"KZ": 5, "LV": 8, "MD": 9, "EE": 10, "LT": 11, "GE": 15, "AZ": 17, "PL": 19,
              "CL": 86, "CR": 89, "DO": 94, "EC": 96, "GT": 108, "HN": 111, "PA": 158}
ID_COUNTRY = {v: k for k, v in COUNTRY_ID.items()}
FIELDS = ("name", "status", "bidding", "conversionTracking", "geoTargeting")


def geos_of(row):
    """ISO codes of a campaign's geo targeting. An id missing from COUNTRY_ID is refused, not skipped."""
    geo = row.get("geoTargeting") or {}
    ids = [v for val in geo.values() if isinstance(val, list) for v in val if isinstance(v, int)]
    unknown = sorted(i for i in ids if i not in ID_COUNTRY)
    if unknown or not ids:
        raise ValueError(f"гео {unknown or 'не заданы'}")
    return sorted(ID_COUNTRY[i] for i in ids)


def offer_of(cid):
    """The one offer behind a campaign, read from its teasers' links. Several offers are refused."""
    _, tz = v1("GET", f"goodhits/clients/{CID1}/teasers?campaign={cid}&limit=50&start=0")  # start is 0-based
    offers = {int(o) for t in (tz.values() if isinstance(tz, dict) else []) if isinstance(t, dict)
              for o in re.findall(r"offer_id=(\d+)", json.dumps(t))}
    if len(offers) != 1:
        raise ValueError(f"офферов у кампании {sorted(offers)}")
    return offers.pop()


def by_country(payouts):
    """{ISO: $}. A payout group can carry a suffix ('GT - Mobile/Desktop'); only the code before it is kept."""
    return {k.split(" - ")[0].strip(): v for k, v in payouts.items()}


def bid(geos, payouts):
    """(CPA in $, the geo it was taken from) for a campaign on `geos`, given {ISO: $} of its offer."""
    missing = sorted(g for g in geos if g not in payouts)
    if missing:
        raise ValueError(f"в карточке оффера нет выплаты по гео {missing}")
    low = min(geos, key=lambda g: payouts[g])
    return round(SHARE * payouts[low], 4), low


def state_of(row):
    """((bidding strategy, price), conversion cost) as MGID reads them in one campaign row."""
    b = row.get("bidding") or {}
    _, conv = buy_cpa(row)
    return (b.get("strategy"), float(b.get("price") or 0)), conv


def settled(cid):
    return state_of(v2_campaigns(FIELDS)[cid])


def ok(state, cpa):
    (strategy, price), conv = state
    return (strategy == "targetCpa" and abs(price - cpa) < 1e-9
            and conv is not None and abs(conv - cpa) < 1e-9)


def patch_campaign(cid, name, cpa):
    body = {
        "name": name, "isAutoLaunchAdsAfterApproval": True,
        "bidding": {"strategy": "targetCpa", "price": cpa},
        "conversionTracking": {"type": "sensors", "decisionStage": None, "interestStage": None,
                               "buyStage": {"targetId": TARGET, "deduplicateConversions": True,
                                            "conversionValue": cpa}},
    }
    return call("PATCH", V2 + f"account/{CID2}/campaigns/{cid}", body)


def main():
    ap = argparse.ArgumentParser(description="CPA bid = 10% of the cabinet payout per geo")
    ap.add_argument("cids", nargs="+", type=int)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    rows = v2_campaigns(FIELDS)
    failed = 0
    for cid in a.cids:
        row = rows.get(cid)
        if row is None:
            print(f"{cid}: нет в списке кампаний")
            failed += 1
            continue
        try:
            geos = geos_of(row)
            offer = offer_of(cid)
            pay = by_country(load(offer)["payouts"])
            cpa, low = bid(geos, pay)
        except (ValueError, OSError) as e:
            print(f"{cid} {row['name']}: пропуск, {e}")
            failed += 1
            continue
        state = state_of(row)
        (strategy, price), conv = state
        print(f"{cid} {row['name']} [{(row.get('status') or {}).get('name')}]\n"
              f"   гео {', '.join(geos)}, оффер {offer}, ниже всего {low} ${pay[low]:g}\n"
              f"   сейчас {strategy} {price:g}, конверсия {conv} -> ставка {cpa:g}")
        if not a.apply:
            continue
        if ok(state, cpa):
            print("   уже стоит")
            continue
        st, body = patch_campaign(cid, row["name"], cpa)
        if st not in (200, 204):
            print(f"   отказ {st}: {json.dumps(body, ensure_ascii=False)[:300]}")
            failed += 1
            continue
        for _ in range(12):
            if ok(settled(cid), cpa):
                break
            time.sleep(10)
        final = settled(cid)
        if not ok(final, cpa):
            failed += 1
        (fs, fp), fc = final
        print(f"   PATCH {st}, после записи: {fs} {fp:g}, конверсия {fc} -> "
              f"{'OK' if ok(final, cpa) else 'НЕ СОВПАЛО'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
