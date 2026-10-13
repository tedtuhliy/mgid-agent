"""MGID campaign for the Kazakhstan content site arcadiablog.com/dom (Geozo ad blocks), CPA tune at one cent.

Owner, 13.10 evening: «Давай попробуем запустить на cpa tune с ценой в 1 цент контент арбитраж ... цель за лид сделать
клик на самих блоках geozo», then «Запусти на этом сайте версию под Казахстан для теста, статьи обычные под аудитории
40+ ... запусти трафик на мгид со ставкой в 1 цент cpa tune. Нужно будет слать конверсию на каждый учтённый платный
клик на geozo».

    python3 geozo_campaign.py            # plan: prints what would be created, changes nothing
    python3 geozo_campaign.py --apply    # create PAUSED, add the teasers, read everything back
    python3 geozo_campaign.py --start    # start it (needs a positive balance); approved teasers then serve

- Conversion goal: MGID postback target 1280981 «Geozo block click» (eventName geozoclick), created 13.10 with
  POST v2 account/939031/targets. NOT the dating target 1274200, so mgid-guard does not read it. Deduplication is OFF:
  the owner wants one conversion per counted click on a block, not one per visitor.
- The signal comes from the page (dom.js) -> nginx relay /dom/lead -> https://a.mgid.com/postback?c=<click id>&e=geozoclick&r=0.01
  (geozo_site/deploy.py). The teaser link carries the click id: ?click_id={click_id}&source=mgid_{campaign_id}_{widget_id}.
- Bid and conversion value both $0.01 (targetCpa), KZ, Russian, mobile OS list of the dating copies, campaign type
  `content` (the landing is an article). Daily limit is MGID's minimum for this account ($20); mgid-spend-stop on Inferno
  pauses any active campaign at $3 spend, which is the real cap of this test.
- Six teasers, three per article, photos that show what the title says (geozo_site/teasers/).
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

NAME = "Arcadia KZ content mobile CPA 0.01"
GEO = "KZ"
CPA = 0.01
TARGET_ID = 1280981                    # «Geozo block click», eventName geozoclick
SITE = "https://arcadiablog.com"
LINK = SITE + "{path}?click_id={{click_id}}&source=mgid_{{campaign_id}}_{{widget_id}}"
TEASERS = [   # (image, title, page)
    ("t1", "Банка с водой вместо пакета: простой способ сохранить зелень", "/dom/"),
    ("t2", "Как разложить холодильник, чтобы реже выбрасывать еду", "/dom/"),
    ("t3", "Хлеб черствеет в холодильнике? Есть способ лучше", "/dom/"),
    ("t4", "Комнатные растения осенью: 7 советов, чтобы они дожили до весны", "/dom/rasteniya-osenyu.html"),
    ("t5", "Зелень на подоконнике осенью: как сохранить её до весны", "/dom/rasteniya-osenyu.html"),
    ("t6", "Пересаживать комнатные растения осенью или лучше весной?", "/dom/rasteniya-osenyu.html"),
]
OUT = HERE / "data" / "geozo-campaign.json"


def body(src):
    b = cp.body_for(GEO, cp.country_ids()[GEO], CPA, src)
    b.update({"name": NAME, "showName": "Arcadia Blog", "type": "content", "isAutoLaunchAdsAfterApproval": True})
    b["conversionTracking"] = {"type": "sensors", "decisionStage": None, "interestStage": None,
                               "buyStage": {"targetId": TARGET_ID, "deduplicateConversions": False,
                                            "conversionValue": CPA}}
    return b


def teaser_form(cid, image, title, path):
    return {"campaignId": cid, "url": LINK.format(path=path), "title": title,
            "imageLink": f"{SITE}/dom/img/{image}.jpg", "priceOfClick": cp.TEASER_CENTS, "whetherShowGoodPrice": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--start", action="store_true")
    a = ap.parse_args()
    live = v2_campaigns()
    exists = next((i for i, x in live.items() if x.get("name") == NAME), None)

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
    print(f"план: {NAME} | {GEO}, targetCpa ${CPA}, конверсия ${CPA}, цель {TARGET_ID} без дедупа, тип content, "
          f"${cp.DAILY_USD:.0f}/сутки, язык {src.get('languageTargeting')}, {len(TEASERS)} тизеров; "
          f"{'уже есть ' + str(exists) if exists else 'будет создана на паузе'}")
    for image, title, path in TEASERS:
        print(f"  {image}: {title}\n      {LINK.format(path=path)}")
    if not a.apply:
        print("(без --apply ничего не создаётся)")
        return

    if exists:
        cid = exists
    else:
        st, d = call("POST", V2 + f"account/{CID2}/campaigns", body(src))
        if st not in (200, 201) or not isinstance(d, dict) or not d.get("id"):
            raise SystemExit(f"создание: {st} {json.dumps(d, ensure_ascii=False)[:600]}")
        cid = int(d["id"])
        print(f"создана {cid}")
        time.sleep(2)
    s = pause(cid)
    print(f"пауза: {s.get('name')}/{s.get('reason')}")

    have = {t.get("imageLink") for t in cp.teasers(cid).values() if isinstance(t, dict)}
    rows = []
    for image, title, path in TEASERS:
        form = teaser_form(cid, image, title, path)
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
    OUT.parent.mkdir(exist_ok=True)
    json.dump({"id": cid, "name": NAME, "geo": GEO, "cpa": CPA, "target": TARGET_ID, "teasers": rows},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"записано: {OUT}")


if __name__ == "__main__":
    main()
