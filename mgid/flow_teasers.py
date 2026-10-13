"""New teasers for the mainstream tests, pointing at our own cpamatica flow instead of the direct offer links (13.10).

    python3 flow_teasers.py          # plan: prints what each campaign has, creates nothing
    python3 flow_teasers.py --apply  # 3 new teasers per campaign, then the rejected ones they replace are deleted

All 14 teasers of the first batch of 12.10 were rejected as "Explicit content" (Date4you US: `campaignBlocked`).
MGID's screenshots show explicit pages that are not ours: a click that cpamatica cannot hand to the offer (outside its
geo or device, a datacenter address, a capped or paused offer) is sent on to the account's trafficback, offer 8978
Flirtooy WW (`last=3`), and Flirtooy's pages (flirtoooy.com/direct_short, /tt2_8, /sexting) are explicit. Owner, 13.10:
«Да они скорей всего зашли на трафикбек ссылки, нужно сделать свой flow», then «Те что откровенны сами по себе мы не
делай».

The flow is `0-Olte`: one entry per offer and geo, for mobile and for desktop/tablet, and as its last offer the
Mainstream Dating Smartlink WW (6011) instead of the adult smartlink. Flirtooy (8978) is not in it, and its three
campaigns (AU, CA, NZ) are left as they were. The link keeps our subs: `aff_sub` = campaign, `aff_sub3` = placement,
and MGID's own UTM still brings `click_id` and `source` (checked: the flow hands them on to the offer link).

- Idempotent. A teaser counts as new when its link carries the flow hash, so a rerun after the add limit only
  tops the campaign up to three. MGID re-hosts the images, so images cannot be compared.
- The old rejected teasers of a campaign are deleted only once it has its three new ones.
- Everything stays paused: nothing runs until the owner says so.
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mainstream_tests as mt  # noqa: E402
import mgid_geo_copies as cp  # noqa: E402
from mgid_api import CID1, V1, call  # noqa: E402

FLOW = "0-Olte"
LINK = f"https://go.cm-trk6.com/aff_f?h={FLOW}&aff_sub5=mgid&aff_sub={{campaign_id}}&aff_sub3={{widget_id}}"
EXPLICIT = {8978}                 # Flirtooy WW: its own landing pages are explicit
OUT = HERE / "data" / "flow-teasers.json"
DEAD = ("rejected", "campaignBlocked")


def code(t):
    s = t.get("status")
    return s.get("code") if isinstance(s, dict) else s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    rows = {r["name"]: r for r in json.load(open(mt.OUT)) if r.get("cid")}
    todo = []
    for t in mt.TESTS:
        r = rows.get(mt.name_of(t))
        if t["offer"] in EXPLICIT:
            print(f"пропуск: {mt.name_of(t)}: оффер {t['offer']} откровенный сам по себе")
        elif not r:
            print(f"нет кампании {mt.name_of(t)}")
        else:
            todo.append((t, r["cid"]))

    results = []
    for t, cid in todo:
        now = cp.teasers(cid)
        mine = {tid: x for tid, x in now.items() if f"h={FLOW}" in str(x.get("url"))}
        old = {tid: x for tid, x in now.items() if tid not in mine}
        print(f"{mt.name_of(t)} ({cid}): тизеров {len(now)}, с флоу {len(mine)}, старых {len(old)} "
              f"{sorted({code(x) for x in old.values()})}")
        if not a.apply:
            continue
        added = []
        for img in cp.IMAGES[len(mine):]:
            form = {"campaignId": cid, "url": LINK, "title": t["title"], "imageLink": cp.IMG + img,
                    "priceOfClick": cp.TEASER_CENTS, "categoryId": 108, "whetherShowGoodPrice": 0}
            st, d = call("POST", V1 + f"goodhits/clients/{CID1}/teasers", form, form=True)
            new_id = d.get("id") if isinstance(d, dict) else None
            added.append({"image": img, "status": st, "id": new_id,
                          "error": None if new_id else json.dumps(d, ensure_ascii=False)[:200]})
            print(f"    тизер {img}: {st} {new_id or json.dumps(d, ensure_ascii=False)[:160]}")
            if isinstance(d, dict) and any("LS_TEASER_ADD_LIMIT_ERROR" in e for e in (d.get("errors") or [])):
                print("    лимит добавления тизеров: остальное позже, запустите --apply ещё раз")
                results.append({"name": mt.name_of(t), "cid": cid, "added": added, "deleted": [], "limit": True})
                OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
                return
            time.sleep(1)
        time.sleep(2)
        after = cp.teasers(cid)
        mine_after = {tid: x for tid, x in after.items() if f"h={FLOW}" in str(x.get("url"))}
        deleted = []
        if len(mine_after) >= 3:
            for tid, x in old.items():
                if code(x) in DEAD and int(x.get("campaignId") or 0) == cid:
                    st, d = call("DELETE", V1 + f"goodhits/clients/{CID1}/teasers/{tid}")
                    deleted.append({"id": tid, "status": st})
                    time.sleep(0.5)
        print(f"  новых тизеров {len(mine_after)} {sorted({code(x) for x in mine_after.values()})}, "
              f"старых удалено {len(deleted)}")
        results.append({"name": mt.name_of(t), "cid": cid, "added": added, "deleted": deleted,
                        "new_codes": sorted({str(code(x)) for x in mine_after.values()}),
                        "new_total": len(mine_after)})
    if a.apply:
        OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
        print(f"записано: {OUT}")
    else:
        print("(без --apply ничего не создаётся)")


if __name__ == "__main__":
    main()
