"""The RollerAds offers of the owner's sweeps focus (19.11.2026) as paused CPA tune campaigns on the second MGID account.

    python3 rr_sweeps.py                       # plan, read only: per offer the access, the link, the goal, the postback, the campaign, the teaser
    python3 rr_sweeps.py --setup               # the ONE MGID goal rrsweepslead and the ONE RollerAds postback to a.mgid.com for all offers (no link needed)
    python3 rr_sweeps.py --campaigns           # paused product campaigns, targetCpa $1, US, English (mobile OS for the sweeps), read back
    python3 rr_sweeps.py --teasers DIR         # ONE teaser per campaign from DIR/<image>; an offer with `hold` only with --include-hold; --replace ID makes a new one and deletes the old
    python3 rr_sweeps.py --variants DIR        # extra teasers: the same image + headline pairs as the NewsBreak ads (up to 5 in a campaign)
    python3 rr_sweeps.py --status
    python3 rr_sweeps.py --launch 1282 --target 1.0
    run as:  node vault.mjs exec mgid rollerads pixeldrain -- env MGID_ACCOUNT=second python3 rr_sweeps.py ...

Owner, 19.11: «Подготовь ссылки и запустим на тест кампании по cpa tune с ставкой 1 бакс. Креативы сделай через openrouter», and «Менеджер разберётся пушы и нативку на все оферы»
(the traffic types and the access are the manager's). The chain is the one of the 1537 test (README 20.10): teaser -> the tracker link of the offer
(`GET /api/offers/{id}/tracking-link`, cabinet session) with `source_id={widget_id}_{teaser_id}&aff_click_id={click_id}` -> postback of the offer
(`POST /api/offers/postbacks`, `https://a.mgid.com/postback?c={affClickId}&e=rrsweepslead&r={trx}`, ONE for all offers, the account holds at most 10) -> MGID goal `rrsweepslead`. `{trx}` is the payout macro (the other postbacks
of the account use it as `payout=`). No test postback with an invented click id is ever sent to MGID.

Not stored in the repository: tracking links (they carry the account's signature). Facts of 19.11: 1282 has access and its tracker records a click with the labels; 2139 has a link but the tracker
answers 204 and records nothing; 1046, 1719, 2176, 2177, 2212 answer 403 on the link; 2154, 1795, 1725 are not visible (404).
"""
import argparse
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import aray_campaigns as ac  # noqa: E402  (read_back, pixeldrain_upload)
import mgid_geo_copies as cp  # noqa: E402
from mgid_api import CID1, CID2, V1, V2, call, pause, v2_campaigns  # noqa: E402

DATA = json.loads((HERE / "data" / "rr-sweeps.json").read_text())
LEDGER = HERE / "data" / "rr-created.json"
BY_ID = {o["id"]: o for o in DATA["offers"]}
MACROS = "source_id={widget_id}_{teaser_id}&aff_click_id={click_id}"
NB = json.loads((HERE.parent / "newsbreak" / "data" / "nb-sweeps.json").read_text())       # the NewsBreak copy: the same pairs are made as extra teasers here
MAX_TEASERS = 5                      # MGID: at most five teasers on one domain in a product campaign (LS_CAB_GOODS_TEASER_ALLOWED_DOMAIN_LIMIT)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def name(o):
    return f"{DATA['country']} | {o['name']} (RollerAds {o['id']}) | CPA tune ${DATA['cpa']:g}"


def event():
    """ONE goal and ONE postback for all the offers: RollerAds lets an account keep only 10 postbacks (the 11th answers 422 «Maximum number of postbacks reached»)."""
    return DATA["event"]


def postback_url():
    return f"https://a.mgid.com/postback?c={{affClickId}}&e={event()}&r={{trx}}"


def retarget(tracker, host):
    """The tracker link of the offer on the custom domain of the buying team: only the host changes, the path (code and signature) stays."""
    if not host:
        return tracker
    u = urllib.parse.urlsplit(tracker)
    return urllib.parse.urlunsplit((u.scheme, host, u.path, u.query, ""))


def link(tracker):
    """The teaser link: the tracker link of the offer on the custom domain (eventsbytlcltd.com, 19.11) with the labels of MGID (braces stay as they are).
    The tracker keeps `source_id` and `aff_click_id`."""
    tracker = retarget(tracker, DATA.get("tracker_domain"))
    return tracker + ("&" if "?" in tracker else "?") + MACROS


def body(o, goal_id, os_ids):
    b = {"name": name(o), "showName": o["show"], "type": "product", "isAutoLaunchAdsAfterApproval": False,
         "bidding": {"strategy": "targetCpa", "price": DATA["cpa"]}, "sourcesOptimization": False,
         "limits": {"limitType": "budget", "dailyLimit": DATA["daily_usd"], "splitDailyLimitEvenly": False},
         "conversionTracking": {"type": "sensors", "decisionStage": None, "interestStage": None,
                                "buyStage": {"targetId": goal_id, "deduplicateConversions": True, "conversionValue": o["value"]}},
         "geoTargeting": {"countries": [DATA["country_id"]], "regions": {"mode": "include", "value": []}},
         "languageTargeting": {"mode": "include", "value": [DATA["language"]]}}
    if o.get("mobile") and os_ids:
        b["operatingSystemTargeting"] = {"mode": "include", "value": os_ids}
    return b


def mobile_os_ids(rows):
    """Ids of the MGID operating systems of the phones and tablets we want (iOS and Android, every version)."""
    return [int(x["id"]) for x in rows if x.get("name") in DATA["mobile_os"] and x.get("deviceType") in ("mobile", "tablet")]


def nb_pairs(oid):
    """[(image key, headline)] of an offer as the NewsBreak ads have them: the images and the headlines paired by position, the shorter list repeated."""
    c = NB["offers"].get(str(oid))
    if not c:
        return []
    n = max(len(c["images"]), len(c["headlines"]))
    return [(c["images"][i % len(c["images"])], c["headlines"][i % len(c["headlines"])]) for i in range(n)]


def load_ledger():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {}


def save_ledger(d):
    LEDGER.write_text(json.dumps(d, indent=1, sort_keys=True))


class RollerAds:
    """The cabinet session of RollerAds (`/api/offers/*` is closed to the API key)."""
    BASE = "https://my.rollerads.com"

    def __init__(self):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        st, _ = self.req("POST", "/api/auth/login", {"user_login": os.environ["ROLLERADS_LOGIN"], "user_password": os.environ["ROLLERADS_PASSWORD"]})
        if st != 200:
            raise SystemExit(f"RollerAds login: HTTP {st}")

    def req(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        h = {"accept": "application/json", "User-Agent": UA, "Origin": self.BASE, "Referer": self.BASE + "/"}
        if data:
            h["content-type"] = "application/json"
        r = urllib.request.Request(self.BASE + path, data=data, method=method, headers=h)
        try:
            with self.op.open(r, timeout=60) as resp:
                raw = resp.read().decode()
                return resp.status, (json.loads(raw) if raw[:1] in ("{", "[") else raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            return e.code, (json.loads(raw) if raw[:1] in ("{", "[") else raw)

    def card(self, oid):
        st, d = self.req("GET", f"/api/offers/{oid}")
        return (d.get("response") if isinstance(d, dict) else None) if st == 200 else None

    def tracker(self, oid):
        st, d = self.req("GET", f"/api/offers/{oid}/tracking-link")
        return ((d.get("response") or {}).get("tracking_link") if isinstance(d, dict) else None) if st == 200 else None

    def postbacks(self):
        st, d = self.req("GET", "/api/offers/postbacks")
        r = d.get("response") if isinstance(d, dict) else None
        return (r if isinstance(r, list) else (r or {}).get("rows") or []) if st == 200 else []


def goals():
    st, d = call("GET", V2 + f"account/{CID2}/targets")
    rows = d.get("data") if isinstance(d, dict) else d
    return {t.get("eventName"): int(t["id"]) for t in (rows or [])}


def campaign_ids():
    by_name = {r.get("name"): cid for cid, r in v2_campaigns(("name",)).items()}
    return {o["id"]: by_name.get(name(o)) for o in DATA["offers"]}


def facts(ra):
    """Per offer: visible, the access of the account, the tracker link (None when the cabinet refuses it)."""
    out = {}
    for o in DATA["offers"]:
        c = ra.card(o["id"])
        out[o["id"]] = {"visible": c is not None, "access": (c or {}).get("offer_account_privacy_status"), "tracker": ra.tracker(o["id"]) if c else None}
        time.sleep(0.4)
    return out


def plan():
    ra = RollerAds()
    f = facts(ra)
    g = goals().get(event())
    mine = next((p for p in ra.postbacks() if p.get("postback_title") == DATA["postback_title"]), None)
    allow = set(((mine or {}).get("postback_targeting_offer") or {}).get("allow") or [])
    ids = campaign_ids()
    led = load_ledger()
    print(f"target CPA ${DATA['cpa']:g}, ${DATA['daily_usd']:g} a day, {DATA['country']}, language {DATA['language']} | goal {event()} {g or '-'} | postback {DATA['postback_title']} "
          f"{(mine or {}).get('postback_id', '-')} for {len(allow)} offers")
    for o in DATA["offers"]:
        x = f[o["id"]]
        t = (led.get(str(o["id"])) or {}).get("teaser")
        state = "no card (private)" if not x["visible"] else f"access {x['access']}, link {'yes' if x['tracker'] else 'NO'}"
        print(f"  {o['id']:>5} {o['name'][:44]:<44} {o['kind']:<13} {state:<28} postback {'yes' if o['id'] in allow else '-':<3} "
              f"campaign {ids.get(o['id']) or '-':<9} teaser {t or ('hold' if o.get('hold') else ('no title' if not o.get('title') else '-'))}")


def shared_goal():
    g = goals().get(event())
    if g:
        return g
    st, d = call("POST", V2 + f"account/{CID2}/targets", {"type": "postback", "eventName": event(), "name": "RollerAds sweeps lead (shared postback)",
                                                         "description": "One postback of the RollerAds account (" + DATA["postback_title"] + ") for the offers " + " ".join(str(o["id"]) for o in DATA["offers"]) + ": e=" + event(), "categoryId": 9})
    print(f"goal {event()} -> HTTP {st} {json.dumps(d, ensure_ascii=False)[:160]}")
    for _ in range(6):
        g = goals().get(event())
        if g:
            return g
        time.sleep(4)
    return None


def setup():
    """The shared MGID goal and the shared RollerAds postback (created once, the offers it targets are widened with PATCH; no link is needed)."""
    ra = RollerAds()
    g = shared_goal()
    if not g:
        raise SystemExit("the goal is not readable yet, run --setup again")
    led = load_ledger()
    led["shared"] = {"goal": g}
    ids = [o["id"] for o in DATA["offers"]]
    mine = next((p for p in ra.postbacks() if p.get("postback_title") == DATA["postback_title"]), None)
    body_ = {"postback_title": DATA["postback_title"], "postback_url": postback_url(), "postback_targeting_offer": {"allow": ids}}
    if mine is None:
        st, d = ra.req("POST", "/api/offers/postbacks", body_)
        print(f"postback {DATA['postback_title']} -> HTTP {st} {json.dumps(d, ensure_ascii=False)[:160]}")
    else:
        allow = set(((mine.get("postback_targeting_offer") or {}).get("allow")) or [])
        if allow != set(ids) or mine.get("postback_url") != postback_url():
            st, d = ra.req("PATCH", f"/api/offers/postbacks/{mine['postback_id']}", body_)
            print(f"postback {mine['postback_id']} widened -> HTTP {st}")
        else:
            print(f"postback {mine['postback_id']} {DATA['postback_title']}: ok, {len(ids)} offers")
    save_ledger(led)
    print(f"goal {event()} {g}")


def make_campaigns():
    ids = campaign_ids()
    led = load_ledger()
    g = goals().get(event())
    if not g:
        raise SystemExit("no shared goal yet, run --setup first")
    st, d = call("GET", "https://api.mgid.com/v2/ads/dictionaries/operating-systems")
    os_ids = mobile_os_ids((d or {}).get("data", []) if isinstance(d, dict) else [])
    for o in DATA["offers"]:
        if ids.get(o["id"]):
            print(f"{name(o)}: exists {ids[o['id']]}")
            led.setdefault(str(o["id"]), {})["campaign"] = ids[o["id"]]
            continue
        st, d = call("POST", V2 + f"account/{CID2}/campaigns", body(o, g, os_ids))
        if st not in (200, 201) or not isinstance(d, dict) or not d.get("id"):
            print(f"{name(o)}: creation failed {st} {json.dumps(d, ensure_ascii=False)[:300]}")
            continue
        cid = int(d["id"])
        s = pause(cid)
        led.setdefault(str(o["id"]), {})["campaign"] = cid
        save_ledger(led)
        print(f"{name(o)}: created {cid}, {s.get('name')}/{s.get('reason')}")
    rows = v2_campaigns(("name", "status", "type", "bidding", "conversionTracking", "geoTargeting", "languageTargeting", "operatingSystemTargeting", "isAutoLaunchAdsAfterApproval"))
    for o in DATA["offers"]:
        cid = campaign_ids().get(o["id"])
        if not cid:
            continue
        r = rows.get(cid) or {}
        bad = []
        if (r.get("status") or {}).get("name") != "paused":
            bad.append(f"status {r.get('status')}")
        if r.get("type") != "product" or (r.get("bidding") or {}).get("strategy") != "targetCpa" or float((r.get("bidding") or {}).get("price") or 0) != DATA["cpa"]:
            bad.append(f"bidding {r.get('bidding')}")
        if (((r.get("conversionTracking") or {}).get("buyStage")) or {}).get("targetId") != g:
            bad.append("goal")
        if (r.get("geoTargeting") or {}).get("countries") != [DATA["country_id"]]:
            bad.append(f"geo {r.get('geoTargeting')}")
        if r.get("isAutoLaunchAdsAfterApproval"):
            bad.append("auto-launch is on")
        print(f"  read back {cid} {name(o)}: {'ok' if not bad else 'PROBLEM ' + '; '.join(bad)}")


def make_teasers(imgdir, include_hold=False, replace=()):
    ra = RollerAds()
    ids = campaign_ids()
    led = load_ledger()
    for o in DATA["offers"]:
        cid = ids.get(o["id"])
        entry = led.setdefault(str(o["id"]), {})
        if not cid or not o.get("title"):
            print(f"{o['id']} {o['name']}: " + ("no campaign" if not cid else "no title yet"))
            continue
        if o.get("hold") and not include_hold:
            print(f"{o['id']} {o['name']}: on hold ({o['hold']})")
            continue
        old_teaser = None
        if entry.get("teaser"):
            if o["id"] not in replace:
                print(f"{o['id']} {o['name']}: teaser {entry['teaser']} exists")
                continue
            old_teaser = entry["teaser"]      # a teaser cannot be edited: the new one is made first, the old one is deleted after it
        tracker = ra.tracker(o["id"])
        if not tracker:
            print(f"{o['id']} {o['name']}: no link")
            continue
        img = Path(imgdir) / o["image"]
        if not img.exists():
            print(f"{o['id']} {o['name']}: no image {img}")
            continue
        iname = f"rr{o['id']}_{img.name}"
        if not entry.get("image"):
            tmp = Path(imgdir) / iname
            tmp.write_bytes(img.read_bytes())
            entry["image"] = ac.pixeldrain_upload(tmp)
            save_ledger(led)
        form = {"campaignId": cid, "url": link(tracker), "title": o["title"], "imageLink": "https://pixeldrain.com/api/file/" + entry["image"],
                "priceOfClick": cp.TEASER_CENTS, "whetherShowGoodPrice": 0}
        st, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
        tid = d.get("id") if isinstance(d, dict) else None
        msg = json.dumps(d, ensure_ascii=False)[:240]
        if tid:
            entry["teaser"] = int(tid)
            save_ledger(led)
            print(f"{name(o)}: teaser {tid} ({o['title'][:50]})")
            if old_teaser:
                st2, _ = call("DELETE", V1 + f"goodhits/clients/{CID1}/teasers/{old_teaser}")
                print(f"   the old teaser {old_teaser} deleted: HTTP {st2}")
        elif "LS_TEASER_ADD_LIMIT_ERROR" in msg:
            print("teaser add limit: stop, run again later")
            return
        else:
            print(f"{name(o)}: refused: HTTP {st} {msg}")


def make_variants(imgdir, include_hold=False):
    """The same image + headline pairs as the NewsBreak ads, as extra teasers of the campaigns (owner, 19.11: «на мгид все тоже самое подготовь»). A pair whose title is already a
    teaser of the campaign is skipped (MGID writes titles in Title Case: compared in lower case); at most MAX_TEASERS in a campaign; the images are `<imgdir>/<key>.jpg`."""
    ra = RollerAds()
    ids = campaign_ids()
    led = load_ledger()
    for o in DATA["offers"]:
        cid = ids.get(o["id"])
        pairs = nb_pairs(o["id"])
        if not cid or not pairs or (o.get("hold") and not include_hold):
            continue
        tracker = ra.tracker(o["id"]) if ra.card(o["id"]) else None
        if not tracker:
            print(f"{o['id']} {o['name']}: no link, skipped")
            continue
        entry = led.setdefault(str(o["id"]), {})
        images = entry.setdefault("images", {})
        extra = entry.setdefault("extra", {})
        have = {(v.get("title") or "").lower() for v in cp.teasers(cid).values()}
        for key, title in pairs:
            if len(have) >= MAX_TEASERS:
                break
            if title.lower() in have:
                continue
            if len(title) > 75:
                print(f"{o['id']}: title longer than 75, skipped: {title[:40]}")
                continue
            if key not in images:
                src = Path(imgdir) / f"{key}.jpg"
                if not src.exists():
                    print(f"{o['id']}: no image {src}")
                    continue
                tmp = Path(imgdir) / f"rr{o['id']}_{key}.jpg"
                tmp.write_bytes(src.read_bytes())
                images[key] = ac.pixeldrain_upload(tmp)
                save_ledger(led)
            form = {"campaignId": cid, "url": link(tracker), "title": title, "imageLink": "https://pixeldrain.com/api/file/" + images[key],
                    "priceOfClick": cp.TEASER_CENTS, "whetherShowGoodPrice": 0}
            st, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
            tid = d.get("id") if isinstance(d, dict) else None
            msg = json.dumps(d, ensure_ascii=False)[:240]
            if tid:
                extra[title] = int(tid)
                have.add(title.lower())
                save_ledger(led)
                print(f"{name(o)}: teaser {tid} ({key}: {title[:46]})")
            elif "LS_TEASER_ADD_LIMIT_ERROR" in msg:
                print("teaser add limit: stop, run again later")
                return
            else:
                print(f"{name(o)}: refused: HTTP {st} {msg}")


def status():
    ids = campaign_ids()
    rows = v2_campaigns(("name", "status", "bidding"))
    for o in DATA["offers"]:
        cid = ids.get(o["id"])
        if not cid:
            print(f"{o['id']} {o['name']}: no campaign")
            continue
        t = cp.teasers(cid)
        r = rows.get(cid) or {}
        print(f"{cid} {name(o)} | {(r.get('status') or {}).get('name')}/{(r.get('status') or {}).get('reason')} | target {(r.get('bidding') or {}).get('price')} | teasers "
              + (", ".join(f"{k}:{(v.get('status') or {}).get('code')}" for k, v in t.items()) or "none"))


def launch(oid, target):
    """Start ONE campaign: the target is written while it is paused and read back (the v2 read lags a write), the start is the last step."""
    o = BY_ID.get(oid)
    if o is None:
        raise SystemExit(f"{oid}: not in the list")
    cid = campaign_ids().get(oid)
    if not cid:
        raise SystemExit(f"{name(o)}: no campaign")
    row = v2_campaigns(("status",)).get(cid) or {}
    if (row.get("status") or {}).get("name") != "paused":
        raise SystemExit(f"{cid} {name(o)}: not paused ({row.get('status')}), not touching it")
    st, d = call("PATCH", V2 + f"account/{CID2}/campaigns/{cid}", {"bidding": {"strategy": "targetCpa", "price": target}})
    got, ok = ac.read_back(cid, "bidding", lambda b: float((b or {}).get("price") or 0) == target)
    if st not in (200, 204) or not ok:
        raise SystemExit(f"{cid}: target did not stick (HTTP {st}), now {got}; NOT started")
    s = pause(cid, on=False)
    led = load_ledger()
    led.setdefault(str(oid), {})["launched"] = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "target": target}
    save_ledger(led)
    print(f"{cid} {name(o)}: started, target ${target}, status {s.get('name')}/{s.get('reason')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", action="store_true")
    ap.add_argument("--campaigns", action="store_true")
    ap.add_argument("--teasers", metavar="DIR")
    ap.add_argument("--variants", metavar="DIR", help="extra teasers: the image + headline pairs of the NewsBreak ads (images DIR/<key>.jpg)")
    ap.add_argument("--include-hold", action="store_true", help="also the offers on hold (creatives not yet approved by the advertiser)")
    ap.add_argument("--replace", type=int, action="append", default=[], metavar="OFFER_ID", help="make a new teaser for this offer and delete the old one (the link changed)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--launch", type=int, metavar="OFFER_ID")
    ap.add_argument("--target", type=float)
    a = ap.parse_args()
    if a.setup:
        setup()
    elif a.campaigns:
        make_campaigns()
    elif a.teasers:
        make_teasers(a.teasers, a.include_hold, set(a.replace))
    elif a.variants:
        make_variants(a.variants, a.include_hold)
    elif a.status:
        status()
    elif a.launch:
        if a.target is None:
            raise SystemExit("--launch needs --target")
        launch(a.launch, a.target)
    else:
        plan()


if __name__ == "__main__":
    main()
