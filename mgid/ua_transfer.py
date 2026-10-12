"""Ukraine: the creatives of the old test campaign on account 816921 go into the UA campaign on 816929.

Owner, 12.10: «По старой UA-кампании 12478529 на 816921 перенеси полностью картинки и текста в новый аккаунт
и запусти на cpa tune на 1 цент».

- Read only from 816921: campaign 12478529 has 10 teasers, all approved. Their status is campaignBlocked, which
  is the pause of the campaign, not moderation. Nothing on 816921 is changed.
- Written to 816929: campaign 12511370 (Tinely girls UA mobile CPA, offer 8395, targetCpa and conversion cost
  $0.01, active since 12.10).
- Title and image are copied as they are. The link is the standard one for MGID leads (aff_sub5=mgid, as in the
  CIS copies). The old link had aff_sub5=native; the guard and the postback routing count MGID leads by
  aff_sub5=mgid, so the old link would not be counted as ours.
- The new teasers are new objects, so MGID moderates them again. The campaign is active, so they start by
  themselves once approved.
- The three CIS teasers already in the campaign stay in place.

    python3 ua_transfer.py          # plan: lists what would be created
    python3 ua_transfer.py --apply  # create the teasers that are not there yet, then read back
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mgid_geo_copies as cp  # noqa: E402
from mgid_api import CID1, V1, buy_cpa, call, v2_campaigns  # noqa: E402

OLD_ACCOUNT = 816921
OLD_CAMPAIGN = 12478529
UA_CAMPAIGN = 12511370
OFFER = 8395
OUT = HERE / "data" / "ua-old-teasers.json"
UA_HDR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/126.0 Safari/537.36")


def old_teasers():
    """Read-only call to the old account with its own token. Nothing is written there."""
    q = urllib.parse.urlencode({"campaign": OLD_CAMPAIGN, "limit": 50, "start": 0})
    req = urllib.request.Request(f"https://api.mgid.com/v1/goodhits/clients/{OLD_ACCOUNT}/teasers?{q}",
                                 headers={"Authorization": "Bearer " + os.environ["MGID_816921_TOKEN"],
                                          "Accept": "application/json", "User-Agent": UA_HDR})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read() or b"null")
    items = [x for x in (d.values() if isinstance(d, dict) else []) if isinstance(x, dict)]
    return sorted(items, key=lambda x: int(x["id"]))


def form_for(old, link):
    return {"campaignId": UA_CAMPAIGN, "url": link, "title": old["title"], "imageLink": old["imageLink"],
            "priceOfClick": cp.TEASER_CENTS, "categoryId": 108, "whetherShowGoodPrice": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    old = old_teasers()
    have = {t.get("imageLink") for t in cp.teasers(UA_CAMPAIGN).values() if isinstance(t, dict)}
    link = cp.LINK.format(offer=OFFER)
    print(f"old campaign {OLD_CAMPAIGN} on {OLD_ACCOUNT}: {len(old)} teasers; "
          f"campaign {UA_CAMPAIGN} on {CID1} already has {len(have)} images")
    for o in old:
        mark = "already there" if o.get("imageLink") in have else "to create"
        print(f"  {o['id']} | {o.get('title')} | {mark}")
    print(f"link: {link}")
    if not a.apply:
        print("(plan only: nothing created)")
        return
    rows = []
    for o in old:
        if o.get("imageLink") in have:
            continue
        st, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form_for(o, link), form=True)
        new_id = d.get("id") if isinstance(d, dict) else None
        print(f"  {o['id']} -> {st} {new_id or json.dumps(d, ensure_ascii=False)[:300]}")
        rows.append({"old_id": o["id"], "title": o.get("title"), "imageLink": o.get("imageLink"),
                     "new_id": new_id, "status": st})
        if isinstance(d, dict) and any("LS_TEASER_ADD_LIMIT_ERROR" in e for e in (d.get("errors") or [])):
            print("  лимит добавления тизеров: остальные не пробую, запустите скрипт позже (он дозальёт)")
            break
        time.sleep(1)
    OUT.parent.mkdir(exist_ok=True)
    prev = json.load(open(OUT)) if OUT.exists() else []
    merged = {r["old_id"]: r for r in prev}
    merged.update({r["old_id"]: r for r in rows})     # one line per old teaser, the latest attempt wins
    json.dump(sorted(merged.values(), key=lambda r: r["old_id"]), open(OUT, "w"), ensure_ascii=False, indent=1)
    time.sleep(2)
    now = cp.teasers(UA_CAMPAIGN)
    codes = Counter(str((t.get("status") or {}).get("code")) for t in now.values() if isinstance(t, dict))
    camp = v2_campaigns(("name", "status", "bidding", "conversionTracking"))[UA_CAMPAIGN]
    b = camp.get("bidding") or {}
    print(f"\nteasers in {UA_CAMPAIGN}: {len(now)} {dict(codes)}")
    print(f"campaign: {(camp.get('status') or {}).get('name')}/{(camp.get('status') or {}).get('reason')} | "
          f"bid {b.get('strategy')} {b.get('price')} | conversion {buy_cpa(camp)[1]}")
    print(f"record saved to {OUT}")


if __name__ == "__main__":
    main()
