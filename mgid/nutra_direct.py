"""Direct-offer nutra copies on the second account (20.10): the eight AdCombo campaigns of the blocked main account, paused,
CPA tune $0.05.

    MGID_ACCOUNT=second python3 nutra_direct.py                # plan: what exists, what is missing, writes nothing
    MGID_ACCOUNT=second python3 nutra_direct.py --campaigns    # creates the missing campaigns, paused; reads every one back
    MGID_ACCOUNT=second python3 nutra_direct.py --teasers      # adds the missing teasers, one per campaign per round
    MGID_ACCOUNT=second python3 nutra_direct.py --status       # state of the copies

The sources are campaigns 12469227-12470348 and 12473511 of the main account (v1 816929), AL x3, IT x4, BA x1, teasers that link
straight to AdCombo (`uh1fadd1a6uh.uewhbgfvds.cc` / `axdsz.pro`, `rid=` + `subacc={click_id}&subacc2={widget_id}`). That account
cannot be read any more (API 401 since 14.10), so `data/nutra-direct-copies.json` holds what the session log of 13.10 kept: names,
geo, the conversion value, the link, the image of every teaser and the titles of the first three teasers of each campaign. A teaser
whose title was not in the log (`title_exact: false`) takes one of the campaign's known titles.

- Paused, always: `isAutoLaunchAdsAfterApproval` is off, so an approved teaser does not start a campaign. A teaser goes to moderation the
  moment it is created, paused or not.
- Goal: `lead` (1272844), a postback goal of this account. AdCombo's own S2S postback has to call
  `https://a.mgid.com/postback?c={subacc}&e=lead&r=<payout>`; there is no AdCombo access in the keychain, so that part is the owner's.
- Idempotent: a campaign is found by its name; a created teaser is recorded in data/nutra-direct-created.json (MGID re-hosts the image,
  so the image link cannot be compared). The teaser add limit (`LS_TEASER_ADD_LIMIT_ERROR`) stops the round, run it again later; do not
  hammer it, failed attempts may count too.
- BA: all four teasers were rejected with a malware reason on the lander (the log cuts the text at «Malware has bee»), so only the
  campaign is made.
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mgid_geo_copies as cp  # noqa: E402
from mgid_api import CID1, CID2, V1, V2, call, pause, v2_campaigns  # noqa: E402

DATA = json.loads((HERE / "data" / "nutra-direct-copies.json").read_text())
CREATED = HERE / "data" / "nutra-direct-created.json"
GOAL, CPA, DAILY = 1272844, 0.05, 20.0


def body(c):
    return {"name": c["name"], "showName": c["show"], "type": "product", "isAutoLaunchAdsAfterApproval": False,
            "bidding": {"strategy": "targetCpa", "price": CPA}, "sourcesOptimization": False,
            "limits": {"limitType": "budget", "dailyLimit": DAILY, "splitDailyLimitEvenly": False},
            "conversionTracking": {"type": "sensors", "decisionStage": None, "interestStage": None,
                                   "buyStage": {"targetId": GOAL, "deduplicateConversions": True, "conversionValue": c["value"]}},
            "geoTargeting": {"countries": [c["geo"]], "regions": {"mode": "include", "value": []}},
            "languageTargeting": {"mode": "include", "value": [c["lang"]]}}


def load_created():
    return json.loads(CREATED.read_text()) if CREATED.exists() else {}


def campaign_ids():
    live = v2_campaigns(("name",))
    names = {c["name"]: c for c in DATA["campaigns"]}
    return {names[r["name"]]["src"]: cid for cid, r in live.items() if r.get("name") in names}


def ensure_campaigns(apply):
    have = campaign_ids()
    for c in DATA["campaigns"]:
        if c["src"] in have:
            print(f"{c['name']}: exists {have[c['src']]}")
            continue
        if not apply:
            print(f"{c['name']}: to create")
            continue
        st, d = call("POST", V2 + f"account/{CID2}/campaigns", body(c))
        if st not in (200, 201) or not isinstance(d, dict) or not d.get("id"):
            print(f"{c['name']}: creation failed {st} {json.dumps(d, ensure_ascii=False)[:300]}")
            continue
        cid = int(d["id"])
        s = pause(cid)
        print(f"{c['name']}: created {cid}, {s.get('name')}/{s.get('reason')}")
        time.sleep(2)
    if apply:
        time.sleep(3)
        rows = v2_campaigns(("name", "status", "type", "bidding", "conversionTracking", "geoTargeting", "isAutoLaunchAdsAfterApproval"))
        for c in DATA["campaigns"]:
            cid = campaign_ids().get(c["src"])
            r = rows.get(cid) or {}
            bad = []
            if (r.get("status") or {}).get("name") != "paused":
                bad.append(f"status {r.get('status')}")
            if r.get("type") != "product" or (r.get("bidding") or {}).get("strategy") != "targetCpa":
                bad.append(f"type/bidding {r.get('type')} {r.get('bidding')}")
            if ((r.get("conversionTracking") or {}).get("buyStage") or {}).get("targetId") != GOAL:
                bad.append(f"goal {r.get('conversionTracking')}")
            if (r.get("geoTargeting") or {}).get("countries") != [c["geo"]]:
                bad.append(f"geo {r.get('geoTargeting')}")
            if r.get("isAutoLaunchAdsAfterApproval"):
                bad.append("auto-launch is on")
            print(f"  read back {cid} {c['name']}: {'ok' if not bad else 'PROBLEM ' + '; '.join(bad)}")


def ensure_teasers():
    ids, made = campaign_ids(), load_created()
    queue = {}
    for c in DATA["campaigns"]:
        if c["src"] not in ids or c.get("skip_teasers"):
            continue
        done = set(made.get(str(ids[c["src"]]), []))
        queue[c["src"]] = [t for t in c["teasers"] if str(t["src_tid"]) not in done and t["title"]]
    rnd, limited = 0, False
    while any(queue.values()) and not limited:
        rnd += 1
        for c in DATA["campaigns"]:
            todo = queue.get(c["src"])
            if not todo:
                continue
            t = todo[0]
            cid = ids[c["src"]]
            form = {"campaignId": cid, "url": c["link"], "title": t["title"], "imageLink": t["image"],
                    "priceOfClick": cp.TEASER_CENTS, "whetherShowGoodPrice": 0}
            if t.get("advertText"):
                form["advertText"] = t["advertText"]
            st, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
            new_id = d.get("id") if isinstance(d, dict) else None
            msg = json.dumps(d, ensure_ascii=False)[:200]
            if new_id:
                made.setdefault(str(cid), []).append(str(t["src_tid"]))
                CREATED.write_text(json.dumps(made, indent=1))
                todo.pop(0)
                print(f"  {c['name'][:40]}: teaser {new_id} ({t['title'][:40]})")
                time.sleep(1.2)
            elif "LS_TEASER_ADD_LIMIT_ERROR" in msg:
                print("  teaser add limit: stop, run again later")
                limited = True
                break
            else:
                print(f"  {c['name'][:40]}: src teaser {t['src_tid']} refused: HTTP {st} {msg}")
                todo.pop(0)       # do not retry a refused creative in a loop
    print(f"teasers left: {sum(len(v) for v in queue.values())}")


def status():
    ids, made = campaign_ids(), load_created()
    rows = v2_campaigns(("name", "status", "bidding"))
    for c in DATA["campaigns"]:
        cid = ids.get(c["src"])
        if not cid:
            print(f"{c['name']}: not created")
            continue
        tz = cp.teasers(cid)
        codes = {}
        for x in tz.values():
            k = (x.get("status") or {}).get("code")
            codes[k] = codes.get(k, 0) + 1
        r = rows.get(cid) or {}
        print(f"{cid} {c['name']}: {(r.get('status') or {}).get('name')}, {r.get('bidding')}, teasers {codes} of {len(c['teasers'])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaigns", action="store_true")
    ap.add_argument("--teasers", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status:
        status()
    elif a.teasers:
        ensure_teasers()
    else:
        ensure_campaigns(a.campaigns)
        if not a.campaigns:
            print("(without --campaigns nothing is written)")


if __name__ == "__main__":
    main()
