"""The RollerAds sweeps and lead offers on Geozo (US), at the minimum bid and a small daily limit (owner, 19.11.2026: «запустим там тоже все наши связки», «ставки минимально возможные на usa»).

    node vault.mjs exec geozo rollerads -- python3 gz_sweeps.py                    # plan, read only: the balance, per offer the link, the copy, what exists
    ... python3 gz_sweeps.py --images DIR                                          # DIR/<key>.jpg -> DIR/gz/<key>_sq.jpg (600x600) and <key>_wd.jpg (800x450)
    ... python3 gz_sweeps.py --check-links                                         # one request per offer to the link (a click on the tracker): what the tracker answers
    ... python3 gz_sweeps.py --build DIR [--only 1282,1719]                        # campaign + group + teasers, daily limit first, min bid found by the ladder
    ... python3 gz_sweeps.py --status                                              # balance, per offer: limit, ad statuses, shows, clicks, money of today
    ... python3 gz_sweeps.py --guard                                               # the soft cap: stops the ads of a campaign that spent $3 today, restarts them the next UTC day
    ... python3 gz_sweeps.py --all-off                                             # the safety switch: every ad of ours stopped (the guard then never restarts anything)
    ... python3 gz_sweeps.py --bid 0.03 [--only ...]                               # a new bid for the ads of ours

Per offer: ONE campaign (type, source, categories copied from the template campaign that already works for the same kind of link), ONE group (US, devices, auto start of the approved ads),
three teasers (title 30..65 characters, a square and a wide picture). The link is the tracker link of the offer on the custom domain of the buying team with Geozo's macros
`source_id=gz-[CAMPAIGN_ID]-[AD_ID]-[SITE_ID]`; Geozo has no click id macro, the conversion is read on the RollerAds side by source_id. The daily money limit is written to the campaign
BEFORE any teaser exists and read back; an offer whose limit does not read back gets no teaser. Geozo takes no campaign limit below $20 (daily and total): $20 is the hard cap, the
softer $3 a day of the owner is `--guard` (run it every hour).
"""
import argparse
import datetime as dt
import io
import json
import sys
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "newsbreak"))

import gz_api  # noqa: E402

DATA = json.loads((HERE / "data" / "gz-sweeps.json").read_text())
RR = json.loads((HERE.parent / "mgid" / "data" / "rr-sweeps.json").read_text())
OFFERS = {o["id"]: o for o in RR["offers"]}
LEDGER = HERE / "data" / "gz-created.json"
MACROS = "source_id=gz-[CAMPAIGN_ID]-[AD_ID]-[SITE_ID]"
UA_MOBILE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"


def load_ledger():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {}


def save_ledger(d):
    LEDGER.write_text(json.dumps(d, indent=1, sort_keys=True))


def copy(oid):
    return DATA["offers"][str(oid)]


def devices(c):
    return list(DATA["devices_mobile"] if c["devices"] == "mobile" else DATA["devices_all"])


def campaign_name(o):
    return f"US | {o['name']} (RollerAds {o['id']}) | Geozo CPC min"


def link(tracker):
    """The tracker link of the offer on the custom domain (eventsbytlcltd.com, 19.11) plus the macros of Geozo (square brackets, Geozo fills them)."""
    host = RR.get("tracker_domain")
    if host:
        u = urllib.parse.urlsplit(tracker)
        tracker = urllib.parse.urlunsplit((u.scheme, host, u.path, u.query, ""))
    return tracker + ("&" if "?" in tracker else "?") + MACROS


def pairs(oid):
    """[(image key, title)]: the images and the titles paired by position, the shorter list repeated."""
    c = copy(oid)
    n = max(len(c["images"]), len(c["titles"]))
    return [(c["images"][i % len(c["images"])], c["titles"][i % len(c["titles"])]) for i in range(n)]


def campaign_body(o, c, tpl):
    return {"name": campaign_name(o), "billing_type": tpl.get("billing_type") or "cpc", "ad_format_type_id": tpl.get("ad_format_type_id") or 1,
            "campaign_type_id": tpl["campaign_type_id"], "traffic_source_id": tpl["traffic_source_id"], "device_types": devices(c),
            "categories": tpl["categories"], "countries": list(DATA["countries"])}


def group_body(o, c, tpl):
    return {"name": f"US {o['id']} {o['show']}"[:60], "countries": list(DATA["countries"]), "device_types": devices(c), "categories": tpl["categories"], "auto_start_ads": True}


# ---- pictures
def to_formats(im, disclaimer=None):
    """(square 600x600 JPEG, wide 800x450 JPEG). A picture with the band «generated using AI» at the bottom keeps the band: the wide one is the whole picture, the square is the picture
    above the band with a new band drawn over its bottom (a centre crop would cut the words)."""
    from PIL import Image, ImageDraw, ImageFont
    im = im.convert("RGB")
    w, h = im.size
    th = round(w * 9 / 16)
    if h >= th:
        top = (h - th) // 2
        wide = im.crop((0, top, w, top + th))
    else:
        tw = round(h * 16 / 9)
        left = (w - tw) // 2
        wide = im.crop((left, 0, left + tw, h))
    wide = wide.resize((800, 450), Image.LANCZOS)
    if disclaimer:
        side = h - round(h * 0.07)
        left = (w - side) // 2
        sq = im.crop((left, 0, left + side, side)).resize((600, 600), Image.LANCZOS).convert("RGBA")
        over = Image.new("RGBA", sq.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        d.rectangle((0, 564, 600, 600), fill=(0, 0, 0, 170))
        font = ImageFont.truetype("DejaVuSans.ttf", 15)
        tw_ = d.textlength(disclaimer, font=font)
        d.text(((600 - tw_) / 2, 573), disclaimer, font=font, fill=(255, 255, 255, 255))
        sq = Image.alpha_composite(sq, over).convert("RGB")
    else:
        side = min(w, h)
        left, top = (w - side) // 2, (h - side) // 2
        sq = im.crop((left, top, left + side, top + side)).resize((600, 600), Image.LANCZOS)
    out = []
    for x in (sq, wide):
        b = io.BytesIO()
        x.save(b, "JPEG", quality=90)
        out.append(b.getvalue())
    return out[0], out[1]


def make_images(srcdir):
    from PIL import Image
    out = Path(srcdir) / "gz"
    out.mkdir(exist_ok=True)
    for oid, c in DATA["offers"].items():
        for key in c["images"]:
            src = Path(srcdir) / f"{key}.jpg"
            if not src.exists():
                print(f"{oid}: no file {src}")
                continue
            sq, wd = to_formats(Image.open(src), c.get("disclaimer"))
            (out / f"{key}_sq.jpg").write_bytes(sq)
            (out / f"{key}_wd.jpg").write_bytes(wd)
            print(f"{oid}: {key} -> square {len(sq) // 1024} KB, wide {len(wd) // 1024} KB")


# ---- reading
def facts(ra):
    out = {}
    for oid in DATA["offers"]:
        c = ra.card(int(oid))
        out[int(oid)] = ra.tracker(int(oid)) if c else None
        time.sleep(0.4)
    return out


def plan():
    from ra_client import RollerAds
    g = gz_api.Geozo()
    print(f"balance ${g.balance():.2f} (shared with the other campaigns of the account) | hard caps ${DATA['daily_limit_usd']} a day and ${DATA['total_limit_usd']} in total a campaign, soft cap ${DATA['soft_daily_cap_usd']} a day | min bid ladder {DATA['bid_ladder'][0]}..{DATA['bid_ladder'][-1]}")
    ra = RollerAds()
    f = facts(ra)
    led = load_ledger()
    for oid, c in DATA["offers"].items():
        e = (led.get("offers") or {}).get(oid) or {}
        print(f"  {oid:>5} {OFFERS[int(oid)]['name'][:46]:<46} link {'yes' if f[int(oid)] else 'NO ':<3} devices {devices(c)} titles {len(c['titles'])} "
              f"campaign {e.get('campaign', '-')} ads {len(e.get('ads', {}))}")


def check_links():
    import requests
    from ra_client import RollerAds
    ra = RollerAds()
    for oid in DATA["offers"]:
        t = ra.tracker(int(oid)) if ra.card(int(oid)) else None
        if not t:
            print(f"{oid}: no link")
            continue
        url = link(t).replace("[CAMPAIGN_ID]", "0").replace("[AD_ID]", "0").replace("[SITE_ID]", "0")
        try:
            r = requests.get(url, headers={"User-Agent": UA_MOBILE}, allow_redirects=False, timeout=25)
            loc = urllib.parse.urlsplit(r.headers.get("Location", "")).netloc
            print(f"{oid}: HTTP {r.status_code} -> {loc or '(no redirect)'}")
        except Exception as e:                                       # noqa: BLE001
            print(f"{oid}: {str(e)[:80]}")
        time.sleep(1.2)


def ledger_ads(led, only=None):
    return [int(a) for oid, e in (led.get("offers") or {}).items() if not only or int(oid) in only for a in (e.get("ads") or {}).values()]


def status():
    g = gz_api.Geozo()
    led = load_ledger()
    day = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    print(f"balance ${g.balance():.2f} | UTC day {day}")
    rows = {str(r.get("ad_id")): r for r in g.stats(day, day, "ad_id")}
    tot = 0.0
    for oid, e in (led.get("offers") or {}).items():
        camp = g.campaign(e["campaign"]) if e.get("campaign") else {}
        ads = {}
        shows = clicks = 0
        money = 0.0
        for title, aid in (e.get("ads") or {}).items():
            a = g.ad(aid)
            ads[aid] = a.get("status_id")
            r = rows.get(str(aid)) or {}
            shows += int(r.get("shows_count") or 0)
            clicks += int(r.get("clicks_count") or 0)
            money += float(r.get("money") or 0)
        tot += money
        print(f"{oid:>5} campaign {e.get('campaign')} {camp.get('status', '?')} limit {camp.get('daily_money_limit')} | bid {e.get('bid')} | ads {ads} | today shows {shows} clicks {clicks} spent ${money:.3f}")
    print(f"spent today by our campaigns: ${tot:.2f}")


def stop_ads(g, ids):
    for i in range(0, len(ids), 30):
        st, d = g.stop(ids[i:i + 30])
        print(f"stop {len(ids[i:i + 30])} ads -> HTTP {st} {json.dumps(d)[:120]}")


def all_off():
    g = gz_api.Geozo()
    led = load_ledger()
    led["manual_off"] = True                       # the guard must not undo a stop of the owner
    save_ledger(led)
    stop_ads(g, ledger_ads(led))


def guard():
    """The soft cap: an offer whose ads spent `soft_daily_cap_usd` today (UTC day of Geozo) is stopped, started again on the next UTC day; the whole test is stopped while the balance of the
    account is below `balance_floor_usd` (it is shared with the campaigns that earn). Nothing is restarted after `--all-off`."""
    g = gz_api.Geozo()
    led = load_ledger()
    day = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    bal = g.balance()
    rows = {str(r.get("ad_id")): r for r in g.stats(day, day, "ad_id")}
    low = bal < DATA["balance_floor_usd"]
    print(f"guard {day}: balance ${bal:.2f} (floor ${DATA['balance_floor_usd']}){' LOW: stopping everything' if low else ''}")
    for oid, e in (led.get("offers") or {}).items():
        ids = [int(a) for a in (e.get("ads") or {}).values()]
        if not ids:
            continue
        spent = sum(float((rows.get(str(a)) or {}).get("money") or 0) for a in ids)
        over = spent >= DATA["soft_daily_cap_usd"]
        print(f"  {oid:>5} spent today ${spent:.3f}{' >= soft cap: stop' if over else ''}")
        if low or over:
            stop_ads(g, ids)
            e["guard_day"] = day
        elif e.get("guard_day") and e["guard_day"] != day and not led.get("manual_off"):
            st, d = g.start(ids)
            print(f"  {oid}: a new UTC day, started again -> HTTP {st} {json.dumps(d)[:100]}")
            e.pop("guard_day", None)
    save_ledger(led)


def set_bid(bid, only=None):
    g = gz_api.Geozo()
    led = load_ledger()
    ids = ledger_ads(led, only)
    for i in range(0, len(ids), 30):
        st, d = g.set_bid(ids[i:i + 30], bid)
        print(f"bid {bid} for {len(ids[i:i + 30])} ads -> HTTP {st} {json.dumps(d)[:120]}")
    for oid, e in (led.get("offers") or {}).items():
        if not only or int(oid) in only:
            e["bid"] = bid
    save_ledger(led)


# ---- build
def _id(d):
    return ((d.get("id") or (d.get("data") or {}).get("id")) if isinstance(d, dict) else None)


def place(g, gid, title, url, sq, wd, start):
    """Create the teaser at the lowest accepted bid, walking the ladder up from `start`; (ad id, bid, error)."""
    ladder = DATA["bid_ladder"]
    i = ladder.index(start) if start in ladder else 0
    while i < len(ladder):
        aid, err = g.create_teaser(gid, title, url, ladder[i], sq, wd)
        if aid:
            return aid, ladder[i], None
        if err == "MINBID":
            i += 1
            continue
        return None, None, err
    return None, None, "the ladder is exhausted"


def limit_ok(g, cid, tpl):
    """Both hard caps read back (the write lands with a delay: read again a few times)."""
    for _ in range(4):
        c = g.campaign(cid) or {}
        if (c.get("daily_money_limit") is not None and abs(float(c["daily_money_limit"]) - DATA["daily_limit_usd"]) < 0.001
                and c.get("total_money_limit") is not None and abs(float(c["total_money_limit"]) - DATA["total_limit_usd"]) < 0.001):
            return True
        time.sleep(4)
    return False


def build(imgdir, only=None):
    from ra_client import RollerAds
    ra = RollerAds()
    g = gz_api.Geozo()
    led = load_ledger()
    tpl = g.campaign(DATA["template_campaign"])
    if not tpl.get("categories"):
        raise SystemExit("the template campaign cannot be read")
    imgs = Path(imgdir) / "gz"
    print(f"balance ${g.balance():.2f}")
    for oid_s, c in DATA["offers"].items():
        oid = int(oid_s)
        if only and oid not in only:
            continue
        o = OFFERS[oid]
        tracker = ra.tracker(oid) if ra.card(oid) else None
        if not tracker:
            print(f"{oid} {o['name']}: no link, skipped")
            continue
        entry = led.setdefault("offers", {}).setdefault(oid_s, {})
        if not entry.get("campaign"):
            st, d = g.create_campaign(campaign_body(o, c, tpl))
            cid = _id(d)
            if not cid:
                print(f"{oid}: campaign refused: HTTP {st} {json.dumps(d)[:300]}")
                continue
            entry["campaign"] = cid
            save_ledger(led)
            print(f"{oid}: campaign {cid} created")
        cid = entry["campaign"]
        if not entry.get("limit_ok"):
            st, d = g.update_campaign(cid, {"traffic_source_id": tpl["traffic_source_id"], "daily_money_limit": DATA["daily_limit_usd"], "total_money_limit": DATA["total_limit_usd"]})
            if not limit_ok(g, cid, tpl):
                print(f"{oid}: the limits do not read back (HTTP {st} {json.dumps(d)[:200]}): NO teasers for this offer")
                continue
            entry["limit_ok"] = True
            save_ledger(led)
        if not entry.get("group"):
            st, d = g.create_group(cid, group_body(o, c, tpl))
            gid = _id(d)
            if not gid:
                print(f"{oid}: group refused: HTTP {st} {json.dumps(d)[:300]}")
                continue
            entry["group"] = gid
            save_ledger(led)
            print(f"{oid}: group {gid} created, devices {devices(c)}")
        ads = entry.setdefault("ads", {})
        url = link(tracker)
        for key, title in pairs(oid):
            if title in ads:
                continue
            sqf, wdf = imgs / f"{key}_sq.jpg", imgs / f"{key}_wd.jpg"
            if not sqf.exists() or not wdf.exists():
                print(f"{oid}: no pictures for {key}, run --images first")
                continue
            aid, bid, err = place(g, entry["group"], title, url, sqf.read_bytes(), wdf.read_bytes(), led.get("min_bid") or DATA["bid_ladder"][0])
            if aid:
                ads[title] = aid
                entry["bid"] = bid
                if not led.get("min_bid") or float(bid) < float(led["min_bid"]) or float(bid) > float(led["min_bid"]):
                    led["min_bid"] = bid
                save_ledger(led)
                print(f"{oid}: teaser {aid} at ${bid} ({title[:44]})")
            elif err == "LIMIT":
                print("the daily limit of 100 teasers is spent: stop, run again after 00:00 UTC")
                return
            else:
                print(f"{oid}: refused: {err}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", metavar="DIR")
    ap.add_argument("--check-links", action="store_true")
    ap.add_argument("--build", metavar="DIR")
    ap.add_argument("--only", help="comma separated offer ids")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--all-off", action="store_true")
    ap.add_argument("--guard", action="store_true")
    ap.add_argument("--bid")
    a = ap.parse_args()
    only = {int(x) for x in a.only.split(",")} if a.only else None
    if a.images:
        make_images(a.images)
    elif a.check_links:
        check_links()
    elif a.build:
        build(a.build, only)
    elif a.status:
        status()
    elif a.all_off:
        all_off()
    elif a.guard:
        guard()
    elif a.bid:
        set_bid(a.bid, only)
    else:
        plan()


if __name__ == "__main__":
    main()
