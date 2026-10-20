"""Offer 1537 (LendingTree Mortgage Refinance CPL, RollerAds CPA network): keeps the teasers of the two CPA tune campaigns on the
click-id link (20.10).

    MGID_ACCOUNT=second python3 rr1537_teasers.py          # plan: prints what each campaign has, writes nothing
    MGID_ACCOUNT=second python3 rr1537_teasers.py --apply

The link hands MGID's click id to the RollerAds tracker as `aff_click_id`; on a lead RollerAds' offer postback 1373 sends it back to
a.mgid.com (README, 20.10). MGID cannot change the link of a teaser: a POST to an existing teaser id answers 200 and creates a
duplicate. So a teaser on a link without `aff_click_id` is replaced: the new one is created first, then the old one is deleted.
A deleted teaser cannot be restored; the creatives (title and the MGID-hosted image) are kept in data/rr1537-creatives.json.

- Idempotent. A teaser is right when its link carries `aff_click_id`; a rerun does only what is missing.
- The teaser add limit (`LS_TEASER_ADD_LIMIT_ERROR`) stops the creating. It looks per campaign (about 10 creations a day, deletions do not
  give them back), see README 20.10; the old-link teasers are deleted anyway, a teaser whose clicks cannot be matched is worth nothing.
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mgid_geo_copies as cp  # noqa: E402
from mgid_api import CID1, V1, call  # noqa: E402

DATA = json.loads((HERE / "data" / "rr1537-creatives.json").read_text())
LINK = DATA["link"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    limited = False
    for cid, creatives in DATA["campaigns"].items():
        cid = int(cid)
        live = {int(tid): t for tid, t in cp.teasers(cid).items()}
        right = {(t.get("title"), t.get("imageLink")) for t in live.values() if "aff_click_id" in str(t.get("url"))}
        stale = [tid for tid, t in live.items() if "aff_click_id" not in str(t.get("url"))]
        missing = [c for c in creatives if (c["title"], c["imageLink"]) not in right]
        print(f"{cid}: {len(right)} on the click-id link, {len(stale)} on an old link, {len(missing)} missing")
        if not a.apply:
            continue
        for c in missing:
            if limited:
                break
            form = {"campaignId": cid, "url": LINK, "title": c["title"], "imageLink": c["imageLink"],
                    "priceOfClick": cp.TEASER_CENTS, "whetherShowGoodPrice": 0}
            st, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
            new_id = d.get("id") if isinstance(d, dict) else None
            print(f"  {c['title'][:50]}: HTTP {st} {new_id or json.dumps(d, ensure_ascii=False)[:160]}")
            if not new_id and "LS_TEASER_ADD_LIMIT_ERROR" in json.dumps(d):
                print("  teaser add limit: the rest later, run it again")
                limited = True
            time.sleep(1)
        for tid in stale:
            st, _ = call("DELETE", V1 + f"goodhits/clients/{CID1}/teasers/{tid}")
            print(f"  old-link teaser {tid} deleted: HTTP {st}")
            time.sleep(0.7)
    if not a.apply:
        print("(without --apply nothing is written)")


if __name__ == "__main__":
    main()
