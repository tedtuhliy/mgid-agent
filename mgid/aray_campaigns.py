"""The nine Aray offers of the weekly top (19-25.10.2026) on the second account (26.10): paused CPA tune campaigns, one teaser per campaign
where the lander is not a fabrication.

    MGID_ACCOUNT=second ARAY_CARDS=<aray_cards.json> python3 aray_campaigns.py                    # plan: what exists, what is missing, writes nothing
    ... python3 aray_campaigns.py --creatives <dir> --thumbs <dir>   # 1200x800 images of the teasers from the Aray product shots (Pillow), written to <dir>
    ... python3 aray_campaigns.py --campaigns                        # creates the missing campaigns (paused, auto-launch off), reads each one back
    ... python3 aray_campaigns.py --teasers <dir>                    # uploads the images (vault service pixeldrain) and adds ONE teaser per eligible campaign
    ... python3 aray_campaigns.py --status

Owner, 26.10: «Все 9, нужен запрос» (after the dossier of the Aray top). Per campaign: `product`, `targetCpa` $0.05 (the owner's figure for nutra, 23.10: «Ставки по 5 центов за
cpa tune»), goal `aray_lead` 1278025 (a raw lead; `aray_buy` 1278024 is the confirmation) with the lead value = payout x the approval of the week, country and Spanish, $20 a day, paused,
auto-launch off. The link of the teaser is the Aray tracking link of the offer card (token inside, read from ARAY_CARDS, never stored here) with the chosen lander `al`, `ap=-1`
(«No prelanding», tested 26.10: without it the account's saved pre-lander is used) and the labels `subid={click_id}`, `subacc={widget_id}`, `subacc2={teaser_id}`.

Teasers only where the lander makes no invented people or studies (owner's line of 23.10): the four offers whose only landers are fabrications get the campaign and no teaser (`no_teaser`
in data/aray-offers.json says why). Each teaser goes to moderation the moment it is created; the add limit (`LS_TEASER_ADD_LIMIT_ERROR`) stops the round.
"""
import argparse
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mgid_geo_copies as cp  # noqa: E402
from mgid_api import CID1, CID2, V1, V2, call, pause, v2_campaigns  # noqa: E402

DATA = json.loads((HERE / "data" / "aray-offers.json").read_text())
LEDGER = HERE / "data" / "aray-created.json"
MACROS = "&subid={click_id}&subacc={widget_id}&subacc2={teaser_id}"


def ev(o):
    """Expected pay of one raw lead: payout x the approval of the week, in dollars."""
    return round(o["payout"] * o["approve"] / 100.0, 2)


def name(o):
    return f"{o['geo']} | {o['product']} (Aray {o['aray_id']}) | CPA tune"


def body(o):
    return {"name": name(o), "showName": o["product"], "type": "product", "isAutoLaunchAdsAfterApproval": False,
            "bidding": {"strategy": "targetCpa", "price": DATA["cpa"]}, "sourcesOptimization": False,
            "limits": {"limitType": "budget", "dailyLimit": DATA["daily_usd"], "splitDailyLimitEvenly": False},
            "conversionTracking": {"type": "sensors", "decisionStage": None, "interestStage": None,
                                   "buyStage": {"targetId": DATA["goal"], "deduplicateConversions": True, "conversionValue": ev(o)}},
            "geoTargeting": {"countries": [o["country_id"]], "regions": {"mode": "include", "value": []}},
            "languageTargeting": {"mode": "include", "value": [DATA["language"]]}}


def link(o, tracking_url):
    """The Aray link of the offer card with the lander of `o` and the labels of MGID. Braces of the macros stay as they are."""
    u = urllib.parse.urlsplit(tracking_url)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(u.query, keep_blank_values=True) if k not in ("al", "ap")]
    if o.get("land"):
        q.append(("al", str(o["land"])))
    if o.get("preland") is not None:
        q.append(("ap", str(o["preland"])))
    return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path or "/", urllib.parse.urlencode(q, safe="-_"), "")) + MACROS


def load_ledger():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {}


def save_ledger(d):
    LEDGER.write_text(json.dumps(d, indent=1, sort_keys=True))


def campaign_ids():
    rows = v2_campaigns(("name",))
    by_name = {r.get("name"): cid for cid, r in rows.items()}
    return {o["aray_id"]: by_name.get(name(o)) for o in DATA["offers"]}


def creative(src, out):
    """1200x800 JPEG: the product shot without its plain margins, centred on its own background colour, no text, no people."""
    from PIL import Image
    im = Image.open(src).convert("RGBA")
    flat = Image.new("RGBA", im.size, (255, 255, 255, 255))
    flat.alpha_composite(im)
    im = flat.convert("RGB")
    bgc = im.getpixel((2, 2))
    diff = Image.new("L", im.size, 0)
    px, dp = im.load(), diff.load()
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            p = px[x, y]
            if max(abs(p[0] - bgc[0]), abs(p[1] - bgc[1]), abs(p[2] - bgc[2])) > 14:
                dp[x, y] = 255
    box = diff.getbbox() or (0, 0) + im.size
    pad = 12
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(im.size[0], box[2] + pad), min(im.size[1], box[3] + pad))
    prod = im.crop(box)
    k = min(1000 / prod.size[0], 720 / prod.size[1], 2.0)
    prod = prod.resize((max(1, int(prod.size[0] * k)), max(1, int(prod.size[1] * k))), Image.LANCZOS)
    canvas = Image.new("RGB", (1200, 800), bgc)
    # feathered edges: soft shadows of a product shot would otherwise show as a rectangle on the flat background
    from PIL import ImageDraw, ImageFilter
    mask = Image.new("L", prod.size, 0)
    ImageDraw.Draw(mask).rectangle((36, 36, prod.size[0] - 37, prod.size[1] - 37), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(18))
    canvas.paste(prod, ((1200 - prod.size[0]) // 2, (800 - prod.size[1]) // 2), mask)
    canvas.save(out, "JPEG", quality=90)
    return out


def pixeldrain_upload(path):
    """PUT to pixeldrain with the key of the vault service `pixeldrain` (Basic auth, empty user). Returns the file id."""
    key = os.environ["PIXELDRAIN_API_KEY"]
    req = urllib.request.Request("https://pixeldrain.com/api/file/" + urllib.parse.quote(Path(path).name), data=Path(path).read_bytes(), method="PUT",
                                 headers={"Authorization": "Basic " + base64.b64encode((":" + key).encode()).decode(), "Content-Type": "image/jpeg"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())["id"]


def plan():
    ids = campaign_ids()
    led = load_ledger()
    print(f"goal {DATA['goal_name']} {DATA['goal']}, target CPA ${DATA['cpa']}, ${DATA['daily_usd']} a day, language {DATA['language']}")
    for o in DATA["offers"]:
        cid = ids.get(o["aray_id"])
        t = (led.get(str(o["aray_id"])) or {}).get("teaser")
        print(f"  {o['aray_id']:>5} {name(o):<44} EV ${ev(o):<5} campaign {cid or 'to create'} | teaser {t or ('NONE: ' + o['no_teaser'][:60] if 'no_teaser' in o else 'to add')}")


def make_campaigns():
    ids = campaign_ids()
    led = load_ledger()
    for o in DATA["offers"]:
        if ids.get(o["aray_id"]):
            print(f"{name(o)}: exists {ids[o['aray_id']]}")
            continue
        st, d = call("POST", V2 + f"account/{CID2}/campaigns", body(o))
        if st not in (200, 201) or not isinstance(d, dict) or not d.get("id"):
            print(f"{name(o)}: creation failed {st} {json.dumps(d, ensure_ascii=False)[:300]}")
            continue
        cid = int(d["id"])
        s = pause(cid)
        led.setdefault(str(o["aray_id"]), {})["campaign"] = cid
        save_ledger(led)
        print(f"{name(o)}: created {cid}, {s.get('name')}/{s.get('reason')}")
    rows = v2_campaigns(("name", "status", "type", "bidding", "conversionTracking", "geoTargeting", "languageTargeting", "isAutoLaunchAdsAfterApproval", "limits"))
    for o in DATA["offers"]:
        cid = campaign_ids().get(o["aray_id"])
        r = rows.get(cid) or {}
        want = body(o)
        bad = []
        if (r.get("status") or {}).get("name") != "paused":
            bad.append(f"status {r.get('status')}")
        if r.get("type") != "product" or (r.get("bidding") or {}).get("strategy") != "targetCpa" or float((r.get("bidding") or {}).get("price") or 0) != DATA["cpa"]:
            bad.append(f"type/bidding {r.get('type')} {r.get('bidding')}")
        buy = ((r.get("conversionTracking") or {}).get("buyStage")) or {}
        if buy.get("targetId") != DATA["goal"] or float(buy.get("conversionValue") or 0) != ev(o):
            bad.append(f"goal {buy}")
        if (r.get("geoTargeting") or {}).get("countries") != want["geoTargeting"]["countries"]:
            bad.append(f"geo {r.get('geoTargeting')}")
        if ((r.get("languageTargeting") or {}).get("value")) != [DATA["language"]]:
            bad.append(f"language {r.get('languageTargeting')}")
        if r.get("isAutoLaunchAdsAfterApproval"):
            bad.append("auto-launch is on")
        print(f"  read back {cid} {name(o)}: {'ok' if not bad else 'PROBLEM ' + '; '.join(bad)}")


def make_teasers(imgdir):
    cards = json.loads(Path(os.environ["ARAY_CARDS"]).read_text())
    ids = campaign_ids()
    led = load_ledger()
    for o in DATA["offers"]:
        if "no_teaser" in o:
            print(f"{name(o)}: no teaser ({o['no_teaser'][:90]})")
            continue
        cid = ids.get(o["aray_id"])
        entry = led.setdefault(str(o["aray_id"]), {})
        if not cid:
            print(f"{name(o)}: no campaign yet")
            continue
        if entry.get("teaser"):
            print(f"{name(o)}: teaser {entry['teaser']} exists")
            continue
        if not entry.get("image"):
            entry["image"] = pixeldrain_upload(Path(imgdir) / f"{o['aray_id']}.jpg")
            save_ledger(led)
        url = link(o, cards[str(o["aray_id"])]["o"]["tracking_url"])
        form = {"campaignId": cid, "url": url, "title": o["title"], "imageLink": "https://pixeldrain.com/api/file/" + entry["image"],
                "priceOfClick": cp.TEASER_CENTS, "whetherShowGoodPrice": 0}
        st, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
        tid = d.get("id") if isinstance(d, dict) else None
        msg = json.dumps(d, ensure_ascii=False)[:240]
        if tid:
            entry["teaser"] = int(tid)
            save_ledger(led)
            print(f"{name(o)}: teaser {tid} ({o['title'][:50]})")
        elif "LS_TEASER_ADD_LIMIT_ERROR" in msg:
            print("teaser add limit: stop, run again later")
            return
        else:
            print(f"{name(o)}: refused: HTTP {st} {msg}")


def status():
    ids = campaign_ids()
    for o in DATA["offers"]:
        cid = ids.get(o["aray_id"])
        if not cid:
            print(f"{name(o)}: no campaign")
            continue
        t = cp.teasers(cid)
        print(f"{cid} {name(o)} | teasers " + (", ".join(f"{k}:{(v.get('status') or {}).get('code')}" for k, v in t.items()) or "none"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--creatives", metavar="DIR")
    ap.add_argument("--thumbs", metavar="DIR")
    ap.add_argument("--campaigns", action="store_true")
    ap.add_argument("--teasers", metavar="DIR")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.creatives:
        os.makedirs(a.creatives, exist_ok=True)
        for o in DATA["offers"]:
            if "no_teaser" in o:
                continue
            print("image:", creative(Path(a.thumbs) / o["thumb"], Path(a.creatives) / f"{o['aray_id']}.jpg"))
    elif a.campaigns:
        make_campaigns()
    elif a.teasers:
        make_teasers(a.teasers)
    elif a.status:
        status()
    else:
        plan()


if __name__ == "__main__":
    main()
