"""MGID campaign for the Kazakhstan content site arcadiablog.com/dom (Geozo ad blocks), CPA tune at one cent.

Owner, 13.10 evening: «Давай попробуем запустить на cpa tune с ценой в 1 цент контент арбитраж ... цель за лид сделать
клик на самих блоках geozo», then «Запусти на этом сайте версию под Казахстан для теста, статьи обычные под аудитории
40+ ... запусти трафик на мгид со ставкой в 1 цент cpa tune. Нужно будет слать конверсию на каждый учтённый платный
клик на geozo».

    python3 geozo_campaign.py            # plan: prints what would be created, changes nothing
    python3 geozo_campaign.py --apply    # create the campaign PAUSED (no teasers yet), read the settings back
    python3 geozo_campaign.py --teasers  # add the teasers (they go to moderation at once), read back
    python3 geozo_campaign.py --start    # start it (needs a positive balance); approved teasers then serve
    ... --variant dom2                   # the same for the dense pages (/dom2/), a campaign of its own

Two campaigns, one per layout, because a landing page that MGID has approved is not edited afterwards (an ad-heavier
page than the approved one would be moderation evasion) and a denser page has to pass moderation as it is:
  dom  «Arcadia KZ content mobile CPA 0.01»        -> /dom/   4 slots a page, one ad each (approved 13.10 ~20:00 UTC)
  dom2 «Arcadia KZ content mobile CPA 0.01 dense»  -> /dom2/  8-9 slots a page, 3-10 ads each, compact cards

- Conversion goal: MGID postback target 1280981 «Geozo block click» (eventName geozoclick), created 13.10 with
  POST v2 account/939031/targets. NOT the dating target 1274200, so mgid-guard does not read it. Deduplication is OFF:
  the owner wants one conversion per counted click on a block, not one per visitor.
- The signal comes from the page (dom.js) -> nginx relay /dom/lead -> https://a.mgid.com/postback?c=<click id>&e=geozoclick&r=0.01
  (geozo_site/deploy.py). The teaser link carries the click id: ?click_id={click_id}&source=mgid_{campaign_id}_{widget_id}.
- Bid and conversion value both $0.01 (targetCpa), KZ, Russian, mobile OS list of the dating copies, campaign type
  `product`: MGID refuses targetCpa on `content` campaigns (BIDDING_STRATEGY_CAMPAIGN_TYPES_ERROR, checked 13.10). Daily limit is MGID's minimum for this account ($20); mgid-spend-stop on Inferno
  pauses any active campaign at $3 spend, which is the real cap of this test.
- Six teasers planned, three per article, photos that show what the title says (geozo_site/teasers/). MGID took five
  (LS_CAB_GOODS_TEASER_ALLOWED_DOMAIN_LIMIT on the sixth: five per landing domain in one campaign).
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mgid_geo_copies as cp  # noqa: E402
from mgid_api import CID1, CID2, V1, V2, buy_cpa, call, campaign, pause, v2_campaigns  # noqa: E402

VARIANTS = {   # name of the MGID campaign, URL prefix of the landing pages, file with the ids
    "dom": {"name": "Arcadia KZ content mobile CPA 0.01", "prefix": "/dom", "out": "geozo-campaign.json"},
    "dom2": {"name": "Arcadia KZ content mobile CPA 0.01 dense", "prefix": "/dom2", "out": "geozo-campaign-dom2.json"},
}
NAME = VARIANTS["dom"]["name"]                      # kept for geozo_report.py and older notes
GEO = "KZ"
CPA = 0.01
TARGET_ID = 1280981                    # «Geozo block click», eventName geozoclick
SITE = "https://arcadiablog.com"
LINK = SITE + "{path}?click_id={{click_id}}&source=mgid_{{campaign_id}}_{{widget_id}}"
TEASERS = [   # (image, title, page under the variant's prefix)
    ("t1", "Банка с водой вместо пакета: простой способ сохранить зелень", "/"),
    ("t2", "Как разложить холодильник, чтобы реже выбрасывать еду", "/"),
    ("t3", "Хлеб черствеет в холодильнике? Есть способ лучше", "/"),
    ("t4", "Комнатные растения осенью: 7 советов, чтобы они дожили до весны", "/rasteniya-osenyu.html"),
    ("t5", "Зелень на подоконнике осенью: как сохранить её до весны", "/rasteniya-osenyu.html"),
    ("t6", "Пересаживать комнатные растения осенью или лучше весной?", "/rasteniya-osenyu.html"),
]


def body(src, v):
    b = cp.body_for(GEO, cp.country_ids()[GEO], CPA, src)
    b.update({"name": v["name"], "showName": "Arcadia Blog", "type": "product", "isAutoLaunchAdsAfterApproval": True})
    b["conversionTracking"] = {"type": "sensors", "decisionStage": None, "interestStage": None,
                               "buyStage": {"targetId": TARGET_ID, "deduplicateConversions": False,
                                            "conversionValue": CPA}}
    return b


def teaser_form(cid, image, title, path, prefix):
    return {"campaignId": cid, "url": LINK.format(path=prefix + path), "title": title,
            "imageLink": f"{SITE}{prefix}/img/{image}.jpg", "priceOfClick": cp.TEASER_CENTS, "whetherShowGoodPrice": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--teasers", action="store_true")
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--variant", choices=sorted(VARIANTS), default="dom")
    a = ap.parse_args()
    v = VARIANTS[a.variant]
    name, prefix = v["name"], v["prefix"]
    out_file = HERE / "data" / v["out"]
    live = v2_campaigns()
    exists = next((i for i, x in live.items() if x.get("name") == name), None)

    if a.start:
        if not exists:
            raise SystemExit("кампании нет, сначала --apply")
        st, w = call("GET", V1 + f"clients/{CID1}")
        bal = ((w or {}).get("wallet") or {}).get("balance") if isinstance(w, dict) else None
        print(f"баланс аккаунта: {bal}")
        if bal is None or float(bal) <= 0:
            raise SystemExit("баланс не положительный, не запускаю")
        s = pause(exists, on=False)
        print(f"{exists}: {s.get('name')}/{s.get('reason')}")
        return

    src = live.get(cp.SOURCE)
    if not src:
        raise SystemExit(f"исходной кампании {cp.SOURCE} нет в v2")
    print(f"план: {name} | {GEO}, targetCpa ${CPA}, конверсия ${CPA}, цель {TARGET_ID} без дедупа, тип product, "
          f"${cp.DAILY_USD:.0f}/сутки, язык {src.get('languageTargeting')}, {len(TEASERS)} тизеров; "
          f"{'уже есть ' + str(exists) if exists else 'будет создана на паузе'}")
    for image, title, path in TEASERS:
        print(f"  {image}: {title}\n      {LINK.format(path=prefix + path)}")
    if not (a.apply or a.teasers):
        print("(без --apply / --teasers ничего не создаётся)")
        return

    if exists:
        cid = exists
    else:
        st, d = call("POST", V2 + f"account/{CID2}/campaigns", body(src, v))
        if st not in (200, 201) or not isinstance(d, dict) or not d.get("id"):
            raise SystemExit(f"создание: {st} {json.dumps(d, ensure_ascii=False)[:600]}")
        cid = int(d["id"])
        print(f"создана {cid}")
        time.sleep(2)
    s = pause(cid)
    print(f"пауза: {s.get('name')}/{s.get('reason')}")

    have = {t.get("imageLink") for t in cp.teasers(cid).values() if isinstance(t, dict)}
    rows = []
    for image, title, path in (TEASERS if a.teasers else []):
        if f"{SITE}{prefix}/img/{image}.jpg" in have:
            print(f"  тизер {image}: уже есть")
            continue
        form = teaser_form(cid, image, title, path, prefix)
        st, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
        new_id = d.get("id") if isinstance(d, dict) else None
        print(f"  тизер {image}: {st} {new_id or json.dumps(d, ensure_ascii=False)[:300]}")
        rows.append({"image": image, "title": title, "path": path, "id": new_id, "status": st})
        if isinstance(d, dict) and any("LS_TEASER_ADD_LIMIT_ERROR" in e for e in (d.get("errors") or [])):
            print("  лимит добавления тизеров: остальные позже")
            break
        time.sleep(1)

    time.sleep(3)
    row = v2_campaigns().get(cid) or {}
    b = row.get("bidding") or {}
    target, value = buy_cpa(row)
    c = campaign(cid)
    print(f"проверка: ставка {b.get('strategy')} {b.get('price')}, цель {target}, значение {value}, "
          f"дедуп {((row.get('conversionTracking') or {}).get('buyStage') or {}).get('deduplicateConversions')}, "
          f"тип {row.get('type')}, статус {(row.get('status') or {}).get('name')}, "
          f"гео {(row.get('geoTargeting') or {}).get('countries')}, язык {row.get('languageTargeting')}, "
          f"лимит v1 {(c.get('limitsFilter') or {})}")
    now = cp.teasers(cid)
    print(f"тизеров {len(now)}: {sorted({(t.get('status') or {}).get('code') for t in now.values() if isinstance(t, dict)})}")
    out_file.parent.mkdir(exist_ok=True)
    json.dump({"id": cid, "name": name, "geo": GEO, "cpa": CPA, "target": TARGET_ID, "teasers": rows},
              open(out_file, "w"), ensure_ascii=False, indent=1)
    print(f"записано: {out_file}")


if __name__ == "__main__":
    main()
