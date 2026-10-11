"""Switch dating campaigns to CPA bidding at one cent: targetCpa $0.01, conversion cost 0.01, teasers 1.0 cent.

    python3 cpa_cent.py 12502227 12502228        # plan: prints the current settings, changes nothing
    python3 cpa_cent.py --apply 12502227         # PATCH the campaign and its teasers, then read everything back

Owner, 11.11: «переведи все дейтинг кампании на cpatune с настройкой в 1 цент».

- The campaign's CPA target is 0.01 dollars. Its conversion cost in the settings is 0.01 too, the same rule
  as the LATAM CPA test: the guard stops a placement after 2 cents without a lead of that campaign.
- Teasers are not touched: MGID refuses a teaser CPC change under CPA bidding ("CPC changes are not allowed
  with CPA bidding strategy campaign"), so the click price there is set by the algorithm.
- MGID has been slow to show a PATCH in reads (a 204 that reads back unchanged for a while), so the read-back
  polls for up to two minutes before it reports a mismatch.
"""
import json
import sys
import time

from mgid_api import CID1, CID2, TARGET, V1, V2, buy_cpa, call, campaign, v1, v2_campaigns

CPA = 0.01
CONV = 0.01
CPC_CENTS = 1.0


def teasers(cid):
    st, t = call("GET", V1 + f"goodhits/clients/{CID1}/teasers?campaign={cid}&limit=50&start=0")  # start is 0-based
    return {tid: x for tid, x in (t.items() if isinstance(t, dict) else []) if isinstance(x, dict)}


def patch_campaign(cid, name):
    body = {
        "name": name, "isAutoLaunchAdsAfterApproval": True,
        "bidding": {"strategy": "targetCpa", "price": CPA},
        "conversionTracking": {"type": "sensors", "decisionStage": None, "interestStage": None,
                               "buyStage": {"targetId": TARGET, "deduplicateConversions": True,
                                            "conversionValue": CONV}},
    }
    return call("PATCH", V2 + f"account/{CID2}/campaigns/{cid}", body)


def settled(cid):
    """(bidding strategy, price), conversion cost as MGID reads them now."""
    row = v2_campaigns(("name", "bidding", "conversionTracking"))[cid]
    b = row.get("bidding") or {}
    _, conv = buy_cpa(row)
    return (b.get("strategy"), float(b.get("price") or 0)), conv


def ok(state):
    (strategy, price), conv = state
    return strategy == "targetCpa" and abs(price - CPA) < 1e-9 and conv is not None and abs(conv - CONV) < 1e-9


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    cids = [int(a) for a in args if a.isdigit()]
    rows = v2_campaigns(("name",))
    for cid in cids:
        if cid not in rows:
            print(f"{cid}: нет в списке")
            continue
        name = rows[cid]["name"]
        now_state = settled(cid)
        print(f"{cid} {name}: сейчас {now_state[0]}, конверсия {now_state[1]}")
        if not apply or ok(now_state):
            continue
        st_c, body = patch_campaign(cid, name)
        print(f"   PATCH кампании {st_c}")
        for _ in range(12):
            if ok(settled(cid)):
                break
            time.sleep(10)
        final = settled(cid)
        print(f"   после записи: {final[0]}, конверсия {final[1]} -> "
              f"{'OK' if ok(final) else 'НЕ СОВПАЛО: ' + json.dumps(body, ensure_ascii=False)[:200]}")


if __name__ == "__main__":
    main()
