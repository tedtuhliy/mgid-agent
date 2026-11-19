"""The RollerAds sweeps offers as PAUSED test campaigns on NewsBreak, at the minimum bid and the minimum money (owner, 19.11.2026).

    node vault.mjs exec newsbreak rollerads -- python3 nb_sweeps.py                    # plan, read only: the account, the cap, per offer the link, the copy, what exists
    ... python3 nb_sweeps.py --cap                                                      # the account spending cap of data/nb-sweeps.json (the hard money limit)
    ... python3 nb_sweeps.py --upload DIR                                               # DIR/<image>.jpg -> 16:9, uploaded to the NewsBreak Media Library (the URL is kept in the ledger)
    ... python3 nb_sweeps.py --build                                                    # campaign, ad set and ads for every offer that has a link; everything OFF, read back
    ... python3 nb_sweeps.py --status
    ... python3 nb_sweeps.py --all-off                                                  # the safety switch: every campaign, ad set and ad OFF
    ... python3 nb_sweeps.py --refresh-links                                            # rewrite the click-through URL of the existing ads (a new tracker domain)

What is built per offer: ONE campaign (objective WEB_TRAFFIC), ONE ad set (DAILY budget at the platform minimum, CPC at the minimum bid, a flight of `flight_days`, first-party NewsBreak
inventory only, mobile OS for the sweeps), the ads (image + headline pairs). The click-through URL is the tracker link of the RollerAds offer with
`source_id=nb-__FLIGHT_ID__-__CREATIVE_ID__&aff_click_id=__CALLBACK_PARAM__` (NewsBreak macros: ad set id, ad id, the click id `nvss_...`); the tracker keeps `source_id` and
`aff_click_id` (the same as for MGID, README 20.10 and 19.11). A conversion is read on the RollerAds side by `source_id`; no postback to NewsBreak is needed for a traffic campaign.

An offer whose link the cabinet refuses (no access: 403, private: 404) or that is on hold (2139: the advertiser must approve the creatives) is skipped; run --build again when the access comes.
"""
import argparse
import json
import sys
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import nb_api as nb  # noqa: E402

DATA = json.loads((HERE / "data" / "nb-sweeps.json").read_text())
RR = json.loads((HERE.parent / "mgid" / "data" / "rr-sweeps.json").read_text())
OFFERS = {o["id"]: o for o in RR["offers"]}
LEDGER = HERE / "data" / "nb-created.json"
ACC = DATA["account_id"]
IOS = ["ios@12", "ios@13", "ios@14", "ios@15", "ios@16", "ios@17", "ios@18", "ios@26"]
ANDROID = [f"android@{v}" for v in range(5, 17)]


def load_ledger():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {}


def save_ledger(d):
    LEDGER.write_text(json.dumps(d, indent=1, sort_keys=True))


def copy(oid):
    return DATA["offers"].get(str(oid))


def description(oid):
    return (copy(oid) or {}).get("description") or DATA["description"]


def campaign_name(o):
    return f"US | {o['name']} (RollerAds {o['id']}) | NB traffic CPC min"


def ad_set_name(o):
    return f"{'mobile' if copy(o['id'])['mobile'] else 'all devices'} US CPC ${DATA['bid_cents'] / 100:.2f}, ${DATA['daily_budget_cents'] / 100:.0f} a day"


def ad_name(o, n):
    return f"{o['id']} ad {n}"


def click_url(tracker):
    """The click-through URL: the tracker link of the offer on the custom domain (eventsbytlcltd.com, 19.11) plus the macros of NewsBreak
    (the braces of the other networks are not used here: NewsBreak writes __NAME__)."""
    host = RR.get("tracker_domain")
    if host:
        u = urllib.parse.urlsplit(tracker)
        tracker = urllib.parse.urlunsplit((u.scheme, host, u.path, u.query, ""))
    return tracker + ("&" if "?" in tracker else "?") + DATA["click_params"]


def targeting(c):
    t = {"location": {"positive": ["all"]}, "language": {"positive": ["en_us"]}, "ageGroup": {"positive": list(c["age"])}}
    if c["mobile"]:
        t["os"] = {"positive": IOS + ANDROID}
    return t


def ad_set_body(campaign_id, o, now=None):
    now = now or int(time.time())
    start = now + 3600
    return {"campaignId": campaign_id, "name": ad_set_name(o), "budgetType": "DAILY", "budget": DATA["daily_budget_cents"], "startTime": start,
            "endTime": start + DATA["flight_days"] * 86400, "bidType": "CPC", "bidRate": DATA["bid_cents"], "deliveryRate": "EVENLY", "platforms": list(DATA["platforms"]),
            "status": "OFF", "targeting": targeting(copy(o["id"]))}


def ads_plan(o):
    """[(image key, headline)] for the ads of an offer: the images and the headlines paired by position, the shorter list repeated."""
    c = copy(o["id"])
    n = max(len(c["images"]), len(c["headlines"]))
    return [(c["images"][i % len(c["images"])], c["headlines"][i % len(c["headlines"])]) for i in range(n)]


def ad_body(ad_set_id, o, n, asset_url, headline, tracker):
    return {"adSetId": ad_set_id, "name": ad_name(o, n), "status": "OFF",
            "creative": {"type": "IMAGE", "headline": headline, "assetUrl": asset_url, "description": description(o["id"]), "callToAction": DATA["cta"],
                         "brandName": copy(o["id"])["brand"], "clickThroughUrl": click_url(tracker)}}


def crop169(src, dst):
    """1200x675 JPEG, the centre of the picture (the generated pictures are 3:2)."""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    w, h = im.size
    th = round(w * 9 / 16)
    top = max(0, (h - th) // 2)
    im.crop((0, top, w, top + th)).resize((1200, 675), Image.LANCZOS).save(dst, "JPEG", quality=90)
    return dst


def upload(imgdir):
    led = load_ledger()
    assets = led.setdefault("assets", {})
    out = Path(imgdir) / "nb16x9"
    out.mkdir(exist_ok=True)
    for key in sorted({k for c in DATA["offers"].values() for k in c["images"]}):
        if key in assets:
            print(f"{key}: uploaded already")
            continue
        src = Path(imgdir) / f"{key}.jpg"
        if not src.exists():
            print(f"{key}: no file {src}")
            continue
        assets[key] = nb.upload_asset(ACC, crop169(src, out / f"{key}.jpg"), media_name=f"rr sweeps {key}")
        save_ledger(led)
        print(f"{key}: {assets[key][-50:]}")


def find(rows, name):
    return next((r for r in rows if r.get("name") == name), None)


def build(include_hold=False):
    from ra_client import RollerAds
    ra = RollerAds()
    led = load_ledger()
    assets = led.get("assets", {})
    for o in RR["offers"]:
        oid = o["id"]
        c = copy(oid)
        if not c:
            print(f"{oid} {o['name']}: no NewsBreak copy yet")
            continue
        if c.get("hold") and not include_hold:
            print(f"{oid} {o['name']}: on hold ({c['hold']})")
            continue
        tracker = ra.tracker(oid) if ra.card(oid) else None
        if not tracker:
            print(f"{oid} {o['name']}: no link yet (access), skipped")
            continue
        miss = [k for k in c["images"] if k not in assets]
        if miss:
            print(f"{oid} {o['name']}: images not uploaded: {miss}, run --upload first")
            continue
        entry = led.setdefault("offers", {}).setdefault(str(oid), {})
        camp = find(nb.campaigns(ACC), campaign_name(o))
        if not camp:
            camp = nb.create_campaign(ACC, campaign_name(o), DATA["objective"], status="OFF")
            print(f"{oid}: campaign {camp['id']} created")
        entry["campaign"] = camp["id"]
        aset = find(nb.ad_sets(ACC, [camp["id"]]), ad_set_name(o))
        if not aset:
            aset = nb.create_ad_set(ad_set_body(camp["id"], o))
            print(f"{oid}: ad set {aset['id']} created, budget {aset['budget']}c {aset['budgetType']}, bid {aset['bidRate']}c")
        entry["ad_set"] = aset["id"]
        have = {a["name"] for a in nb.ads(ACC, [aset["id"]])}
        entry.setdefault("ads", {})
        for n, (key, headline) in enumerate(ads_plan(o), 1):
            if ad_name(o, n) in have:
                continue
            ad = nb.create_ad(ad_body(aset["id"], o, n, assets[key], headline, tracker))
            entry["ads"][ad_name(o, n)] = ad["id"]
            print(f"{oid}: ad {ad['id']} {ad_name(o, n)} ({key}), audit {ad.get('auditStatus')}, online {ad.get('onlineStatus')}")
        save_ledger(led)


def refresh_links():
    """Rewrite the click-through URL of the ads that exist (the custom domain, 19.11): the creative is rebuilt from the data file, an update of a PENDING ad restarts nothing useful."""
    from ra_client import RollerAds
    ra = RollerAds()
    led = load_ledger()
    assets = led.get("assets", {})
    for oid, e in (led.get("offers") or {}).items():
        o = OFFERS[int(oid)]
        tracker = ra.tracker(int(oid)) if ra.card(int(oid)) else None
        if not tracker:
            print(f"{oid}: no link, skipped")
            continue
        for n, (key, headline) in enumerate(ads_plan(o), 1):
            ad_id = (e.get("ads") or {}).get(ad_name(o, n))
            if not ad_id or key not in assets:
                continue
            body = {"creative": ad_body(e["ad_set"], o, n, assets[key], headline, tracker)["creative"]}
            st, d = nb.call("PUT", f"/ad/update/{ad_id}", body)
            print(f"{oid}: ad {ad_id} update -> HTTP {st} code {d.get('code') if isinstance(d, dict) else d}")


def status():
    camps = nb.campaigns(ACC)
    for cp in camps:
        print(f"campaign {cp['id']} {cp['name']} | {cp.get('status')}/{cp.get('onlineStatus')}")
        for s in nb.ad_sets(ACC, [cp["id"]]):
            print(f"  ad set {s['id']} {s['name']} | {s.get('status')}/{s.get('onlineStatus')} | {s['budgetType']} {s['budget']}c | {s['bidType']} {s.get('bidRate')}c")
            for a in nb.ads(ACC, [s["id"]]):
                print(f"    ad {a['id']} {a['name']} | {a.get('status')}/{a.get('onlineStatus')} | audit {a.get('auditStatus')} {a.get('statusTxt') or ''}")
    print("spending cap:", nb.budget_info(ACC))
    if not camps:
        print("no campaigns")


def all_off():
    for cp in nb.campaigns(ACC):
        for s in nb.ad_sets(ACC, [cp["id"]]):
            for a in nb.ads(ACC, [s["id"]]):
                if a.get("status") != "OFF":
                    nb.set_status("ad", a["id"], "OFF")
            if s.get("status") != "OFF":
                nb.set_status("ad-set", s["id"], "OFF")
        if cp.get("status") != "OFF":
            nb.set_status("campaign", cp["id"], "OFF")
    print("everything OFF")


def plan():
    from ra_client import RollerAds
    print("account", ACC, "| cap:", nb.budget_info(ACC))
    print(f"limits: CPC ${DATA['bid_cents'] / 100:.2f}, ${DATA['daily_budget_cents'] / 100:.0f} a day, {DATA['flight_days']} days, cap ${DATA['spending_cap_cents'] / 100:.0f}")
    ra = RollerAds()
    led = load_ledger()
    for o in RR["offers"]:
        oid = o["id"]
        c = copy(oid)
        tracker = ra.tracker(oid) if ra.card(oid) else None
        e = (led.get("offers") or {}).get(str(oid)) or {}
        print(f"  {oid:>5} {o['name'][:44]:<44} link {'yes' if tracker else 'NO ':<3} copy {'yes' if c else '-':<3} {('HOLD' if c and c.get('hold') else ''):<5} "
              f"campaign {e.get('campaign', '-')} ads {len(e.get('ads', {}))}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", action="store_true")
    ap.add_argument("--upload", metavar="DIR")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--include-hold", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--all-off", action="store_true")
    ap.add_argument("--refresh-links", action="store_true")
    a = ap.parse_args()
    if a.cap:
        print(nb.set_spending_cap(ACC, DATA["spending_cap_cents"]))
        print(nb.budget_info(ACC))
    elif a.upload:
        upload(a.upload)
    elif a.build:
        build(a.include_hold)
    elif a.status:
        status()
    elif a.all_off:
        all_off()
    elif a.refresh_links:
        refresh_links()
    else:
        plan()


if __name__ == "__main__":
    main()
