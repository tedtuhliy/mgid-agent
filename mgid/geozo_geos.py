"""MGID campaigns for the multilingual site arcadiablog.com/blog/<lang>/: one campaign per geo, two teasers each.

Owner, 13.10 night: «запустить кампании на эти гео и языки с 1-2 креативами в самом МГИД. По гео начни с Болгарии, Польши,
Румынии, Чехии, Португалии, Италии, Испании, немецкоговорящих Германии, Швейцарии, Австрии, Венгрии, Словакии, Словении,
Сербии».

    python3 geozo_geos.py                       # plan: prints what would be created, changes nothing
    python3 geozo_geos.py --apply [--only PL,BG]  # create the campaigns PAUSED and add their two teasers (moderation)
    python3 geozo_geos.py --start [--only PL,BG]  # start them (needs a positive balance)
    python3 geozo_geos.py --status              # campaigns, teaser states, today's numbers
    python3 geozo_geos.py --set-cpa BG=0.03,PL=0.05   # change the CPA target of live campaigns (and their names)
    python3 geozo_geos.py --make-goal ebook     # create the MGID goal «E-book download» (event ebook, category Download)
    python3 geozo_geos.py --goal ebook --only PT,ES   # make the buy-stage goal of these campaigns the e-book download
                                                # (back: --goal geozoclick); the learning of the campaign starts over

Everything but the geo is the Kazakhstan test (geozo_campaign.py): campaign type `product`, bidding targetCpa with the
goal «Geozo block click» (target 1280981, event geozoclick, no deduplication: one conversion per counted click on a
block), mobile OS list of the dating copies, daily limit $20 (MGID's minimum); the real cap is mgid-spend-stop on
Inferno, which pauses any campaign at $3 of spend. Language targeting is the geo's language (not Russian).

Teasers: the creative of the article (teasers/<slug>.jpg, 1200x800, served from /blog/c/) and the headline written
by the language's writer (articles/<lang>/teasers.json). Every geo gets the herbs-in-a-jar creative and one more,
rotating over the other food and plant articles from geo to geo, so that the first data also says which article wins.

The target CPA per geo is a starting guess, not a measurement: the cheap geos start at the one cent of the Kazakhstan
test, the geos where MGID's floor price is higher start higher. After the first hours it is set by what delivers.
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "geozo_site"))

import build_multi as bm  # noqa: E402
import mgid_geo_copies as cp  # noqa: E402
import multi_config as mc  # noqa: E402
from mgid_api import CID1, CID2, V1, V2, buy_cpa, call, pause, report, v2_campaigns  # noqa: E402

SITE = "https://arcadiablog.com"
TARGET_ID = 1280981                    # «Geozo block click», eventName geozoclick
LINK = SITE + "/blog/{route}/{slug}.html?click_id={{click_id}}&source=mgid_{{campaign_id}}_{{widget_id}}"
IMAGE = SITE + "/blog/c/{slug}.jpg"
ORDER = ["BG", "PL", "RO", "CZ", "PT", "IT", "ES", "DE", "CH", "AT", "HU", "SK", "SI", "RS",       # the owner's order
         "KZ"]      # 14.10 night: Kazakhstan moves to the Russian version of the blog (/blog/ru/) with the e-book
# 14.10 ~01:25 MSK: after 80 minutes of approved teasers and no impressions in BG RO SK SI HU PL CZ DE AT the target was raised
# (--set-cpa); PT ES IT CH already delivered at the starting values and keep them. 02:33 MSK: a full hour later BG PL RO SK SI HU DE
# AT still had no impression (CZ had started after the first raise), so these eight were doubled (second step; the first is START_CPA
# -> the values of 01:25 MSK). The names of the campaigns carry the value.
CPA = {"BG": 0.06, "RO": 0.06, "RS": 0.01, "SK": 0.06, "SI": 0.06, "HU": 0.08,
       "PL": 0.10, "CZ": 0.05, "PT": 0.02, "ES": 0.02, "IT": 0.02, "DE": 0.20, "AT": 0.20, "CH": 0.05, "KZ": 0.01}
START_CPA = {"BG": 0.01, "RO": 0.01, "RS": 0.01, "SK": 0.01, "SI": 0.01, "HU": 0.015,
             "PL": 0.02, "CZ": 0.02, "PT": 0.02, "ES": 0.02, "IT": 0.02, "DE": 0.04, "AT": 0.04, "CH": 0.05, "KZ": 0.01}
SECOND = ["bread-storage", "fruit-and-vegetables", "houseplants-autumn"]           # the rotating second creative
FIRST = "herbs-in-a-jar"
# Kazakhstan is the cheapest geo (MGID's click costs $0.0001) and has the four teaser headlines of the old tests: all four.
# The older Kazakhstan campaigns (geozo_campaign.py: /dom/, /dom2/) are named «Arcadia KZ content mobile CPA 0.01[ dense]»,
# so this one carries «blog» in its name and cid_of() never mixes them up.
PICKS = {"KZ": [FIRST] + SECOND}
TAG = {"KZ": " blog"}
OUT = HERE / "data" / "geozo-geos.json"


def name_of(geo):
    return f"Arcadia {geo}{TAG.get(geo, '')} content mobile CPA {CPA[geo]:g}"


def saved():
    return json.loads(OUT.read_text()) if OUT.exists() else {}


def cid_of(geo, live):
    """The campaign of a geo: by the id saved at creation (names carry the CPA, which changes), else by name."""
    cid = (saved().get(geo) or {}).get("id")
    if cid in live:
        return cid
    return next((i for i, x in live.items() if x.get("name") == name_of(geo)), None)


def picks(geo):
    """The article slugs advertised in the geo: two (the jar article and one that rotates), four in Kazakhstan."""
    return PICKS.get(geo) or [FIRST, SECOND[ORDER.index(geo) % len(SECOND)]]


def teaser_titles(route):
    _, _, _, tz = bm.load_lang(route)
    return {x["article"]: x["title"] for x in tz}


def body(src, geo, ids):
    route = mc.GEOS[geo][1]
    lang = mc.LANGS[mc.DERIVED[route]["from"] if route in mc.DERIVED else route]["mgid_lang"]
    b = cp.body_for(geo, ids[geo], CPA[geo], src)
    b.update({"name": name_of(geo), "showName": "Arcadia Blog", "type": "product", "isAutoLaunchAdsAfterApproval": True,
              "languageTargeting": {"mode": "include", "value": [lang]}})
    b["conversionTracking"] = {"type": "sensors", "decisionStage": None, "interestStage": None,
                               "buyStage": {"targetId": TARGET_ID, "deduplicateConversions": False,
                                            "conversionValue": CPA[geo]}}
    return b


def teaser_form(cid, geo, slug, title):
    route = mc.GEOS[geo][1]
    return {"campaignId": cid, "url": LINK.format(route=route, slug=slug), "title": title,
            "imageLink": IMAGE.format(slug=slug), "priceOfClick": cp.TEASER_CENTS, "whetherShowGoodPrice": 0}


def plan_rows(geos):
    rows = []
    for g in geos:
        route = mc.GEOS[g][1]
        titles = teaser_titles(route)
        for slug in picks(g):
            rows.append((g, route, slug, titles.get(slug, "?")))
    return rows


def apply(geos, live, src, ids):
    saved = json.loads(OUT.read_text()) if OUT.exists() else {}
    for g in geos:
        name = name_of(g)
        cid = next((i for i, x in live.items() if x.get("name") == name), None)
        if not cid:
            st, d = call("POST", V2 + f"account/{CID2}/campaigns", body(src, g, ids))
            if st not in (200, 201) or not isinstance(d, dict) or not d.get("id"):
                print(f"{g}: создание {st} {json.dumps(d, ensure_ascii=False)[:500]}")
                continue
            cid = int(d["id"])
            print(f"{g}: создана {cid} «{name}»")
            time.sleep(2)
        s = pause(cid)
        print(f"{g}: пауза {s.get('name')}/{s.get('reason')}")
        have = {t.get("imageLink") for t in cp.teasers(cid).values() if isinstance(t, dict)}
        titles = teaser_titles(mc.GEOS[g][1])
        rec = {"id": cid, "name": name, "cpa": CPA[g], "teasers": []}
        for slug in picks(g):
            if IMAGE.format(slug=slug) in have:
                print(f"  тизер {slug}: уже есть")
                continue
            form = teaser_form(cid, g, slug, titles[slug])
            st, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
            tid = d.get("id") if isinstance(d, dict) else None
            print(f"  тизер {slug}: {st} {tid or json.dumps(d, ensure_ascii=False)[:300]}")
            rec["teasers"].append({"slug": slug, "id": tid, "status": st, "title": titles[slug]})
            if isinstance(d, dict) and any("LS_TEASER_ADD_LIMIT_ERROR" in e for e in (d.get("errors") or [])):
                print("  лимит добавления тизеров: остальные позже")
                break
            time.sleep(1)
        saved[g] = rec
        time.sleep(1)
    OUT.parent.mkdir(exist_ok=True)
    json.dump(saved, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"записано: {OUT}")


def start(geos, live):
    st, w = call("GET", V1 + f"clients/{CID1}")
    bal = ((w or {}).get("wallet") or {}).get("balance") if isinstance(w, dict) else None
    print(f"баланс аккаунта: {bal}")
    if bal is None or float(bal) <= 0:
        raise SystemExit("баланс не положительный, не запускаю")
    for g in geos:
        cid = cid_of(g, live)
        if not cid:
            print(f"{g}: кампании нет")
            continue
        s = pause(cid, on=False)
        print(f"{g}: {cid} {s.get('name')}/{s.get('reason')}")
        time.sleep(1)


def set_cpa(changes, live):
    """PATCH the CPA target (bid and the value of the buy-stage goal) of live campaigns and put it in their names.
    MGID is slow to show a PATCH in reads, so the answer of the PATCH itself is what is printed."""
    sv = saved()
    for g, new in changes.items():
        cid = cid_of(g, live)
        if not cid:
            print(f"{g}: кампании нет")
            continue
        old = CPA[g]
        CPA[g] = new
        body = {"name": name_of(g), "isAutoLaunchAdsAfterApproval": True,
                "bidding": {"strategy": "targetCpa", "price": new},
                "conversionTracking": {"type": "sensors", "decisionStage": None, "interestStage": None,
                                       "buyStage": {"targetId": TARGET_ID, "deduplicateConversions": False,
                                                    "conversionValue": new}}}
        st, d = call("PATCH", V2 + f"account/{CID2}/campaigns/{cid}", body)
        print(f"{g} {cid}: {old:g} -> {new:g}  PATCH {st} {'' if st in (200, 204) else json.dumps(d, ensure_ascii=False)[:300]}")
        if st in (200, 204) and g in sv:
            sv[g]["cpa"], sv[g]["name"] = new, name_of(g)
        time.sleep(1)
    OUT.write_text(json.dumps(sv, ensure_ascii=False, indent=1))


GOALS = {   # event name -> (name, description, category). v2 targets of this account accept the categories 1 and 9 only
            # (14.10: 2, 3, 4, 5 answer «Selected category is not available»), so «Download» is category 9 «Other».
    "geozoclick": ("Geozo block click", "one conversion per real click on a Geozo ad block (relay /dom/lead)", 1),
    "ebook": ("E-book download", "arcadiablog.com/blog: the free e-book (PDF) was downloaded with an MGID click id "
                                 "(nginx mirrors /blog/dl/<lang>.pdf to the postback)", 9),
}


def goal_id(event):
    st, d = call("GET", V2 + f"account/{CID2}/targets")
    rows = d.get("data") if isinstance(d, dict) else d
    return next((int(t["id"]) for t in (rows or []) if t.get("eventName") == event), None)


def make_goal(event):
    have = goal_id(event)
    if have:
        print(f"цель {event} уже есть: {have}")
        return have
    name, desc, cat = GOALS[event]
    st, d = call("POST", V2 + f"account/{CID2}/targets", {"type": "postback", "eventName": event, "name": name,
                                                          "description": desc, "categoryId": cat})
    print(f"создание цели {event}: {st} {json.dumps(d, ensure_ascii=False)[:300]}")
    return goal_id(event)


def set_goal(geos, event, live):
    """Make `event` the buy-stage goal of the geo campaigns (the value stays the CPA of the geo; the e-book goal is deduplicated
    per click id because a download can be requested twice, a block click is counted every time)."""
    tid = goal_id(event)
    if not tid:
        raise SystemExit(f"в MGID нет цели {event}: сначала --make-goal {event}")
    for g in geos:
        cid = cid_of(g, live)
        if not cid:
            print(f"{g}: кампании нет")
            continue
        body = {"name": name_of(g), "isAutoLaunchAdsAfterApproval": True,
                "bidding": {"strategy": "targetCpa", "price": CPA[g]},
                "conversionTracking": {"type": "sensors", "decisionStage": None, "interestStage": None,
                                       "buyStage": {"targetId": tid, "deduplicateConversions": event == "ebook",
                                                    "conversionValue": CPA[g]}}}
        st, d = call("PATCH", V2 + f"account/{CID2}/campaigns/{cid}", body)
        print(f"{g} {cid}: цель {event} ({tid})  PATCH {st} {'' if st in (200, 204) else json.dumps(d, ensure_ascii=False)[:300]}")
        time.sleep(1)


def status(geos, live):
    day = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 3 * 3600))        # MGID day = UTC+3
    rep = {}
    try:
        for x in report(day, day, ("impressions", "clicks", "spent", "conversionsBuy"), ("campaignId",)):
            rep[int(x["campaignId"])] = x
    except Exception as e:          # the report must not hide the states
        print("отчёт MGID недоступен:", str(e)[:120])
    for g in geos:
        cid = cid_of(g, live)
        if not cid:
            print(f"{g}: нет кампании")
            continue
        r = live[cid]
        tz = {}
        for t in cp.teasers(cid).values():
            if isinstance(t, dict):
                c = (t.get("status") or {}).get("code")
                tz[c] = tz.get(c, 0) + 1
        x = rep.get(cid) or {}
        money = lambda v: float(v.get("amount") if isinstance(v, dict) else (v or 0))        # noqa: E731
        print(f"{g} {cid}: {(r.get('status') or {}).get('name')}/{(r.get('status') or {}).get('reason')}, "
              f"тизеры {tz}, показы {int(money(x.get('impressions')))}, клики {int(money(x.get('clicks')))}, "
              f"расход ${money(x.get('spent')):.4f}, конверсии {int(money(x.get('conversionsBuy')))}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--set-cpa", default="", help="GEO=price,GEO=price")
    ap.add_argument("--make-goal", default="", choices=["", *GOALS])
    ap.add_argument("--goal", default="", choices=["", *GOALS], help="switch the buy-stage goal of the campaigns of --only")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    geos = [g for g in ORDER if not a.only or g in a.only.split(",")]
    bad = [g for g in (a.only.split(",") if a.only else []) if g not in ORDER]
    if bad:
        raise SystemExit(f"нет таких гео в списке: {bad}")
    live = v2_campaigns(("name", "status", "bidding"))
    if a.make_goal:
        return make_goal(a.make_goal)
    if a.goal:
        if not a.only:
            raise SystemExit("--goal только вместе с --only: цель меняют на нескольких кампаниях, а не на всех сразу")
        return set_goal(geos, a.goal, live)
    if a.set_cpa:
        changes = {kv.split("=")[0]: float(kv.split("=")[1]) for kv in a.set_cpa.split(",")}
        bad = [g for g in changes if g not in ORDER]
        if bad:
            raise SystemExit(f"нет таких гео в списке: {bad}")
        return set_cpa(changes, live)
    if a.status:
        return status(geos, live)
    if a.start:
        return start(geos, live)
    src = v2_campaigns().get(cp.SOURCE)
    if not src:
        raise SystemExit(f"исходной кампании {cp.SOURCE} нет в v2")
    ids = cp.country_ids()
    for g in geos:
        if ids.get(g) != mc.GEOS[g][0]:
            raise SystemExit(f"{g}: id страны в MGID {ids.get(g)}, в конфиге {mc.GEOS[g][0]}")
    print(f"план: {len(geos)} кампаний, targetCpa по гео {[(g, CPA[g]) for g in geos]}, цель {TARGET_ID}, тип product")
    for g, route, slug, title in plan_rows(geos):
        print(f"  {g} (/blog/{route}/) {slug}: {title}")
    if not a.apply:
        print("(без --apply ничего не создаётся)")
        return
    apply(geos, live, src, ids)


if __name__ == "__main__":
    main()
