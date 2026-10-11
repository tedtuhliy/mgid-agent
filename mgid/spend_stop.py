"""Stop-loss for MGID: pause every active campaign whose spend reaches LIMIT dollars.

    python3 spend_stop.py            # dry run: prints the spend of each active campaign, pauses nothing
    python3 spend_stop.py --apply    # pauses the campaigns at or above the limit and reads each one back

Owner, 11.11: «настрой на инферно бота который стопнет кампании после спенда в 3 бакса».

- Spend is the lifetime spend of each campaign (v1 campaigns-stat, dateInterval=all), in dollars.
- Only ACTIVE campaigns are judged. Paused campaigns are left alone.
- The bot never starts a campaign. A campaign restarted above the limit is paused again on the next run;
  to lift the rule, change MGID_SPEND_LIMIT in the unit.
- If the spend cannot be read, nothing is paused: the run prints the error and exits 1.
- Runs on Inferno every 2 minutes (mgid-spend-stop.timer). A campaign can go past the limit by what it spends
  between two runs, and MGID's own spend figure can lag behind the clicks.
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mgid_api import CID1, pause, v1, v2_campaigns  # noqa: E402

LIMIT = float(os.environ.get("MGID_SPEND_LIMIT", "3.0"))
ACTIONS = os.environ.get("MGID_SPEND_ACTIONS", "/var/lib/mgid-spend-stop/actions.log")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def spend_by_campaign():
    """{campaign id as str: lifetime spend $} for the whole account. Raises if the report cannot be read."""
    st, d = v1("GET", f"goodhits/clients/{CID1}/campaigns-stat", dateInterval="all")
    rows = d.get("campaigns-stat") if st == 200 and isinstance(d, dict) else None
    if not isinstance(rows, dict):
        raise RuntimeError(f"campaigns-stat: {st} {json.dumps(d, ensure_ascii=False)[:200]}")
    return {str(k): float((v or {}).get("spent") or 0) for k, v in rows.items()}


def decide(active, spend, limit=LIMIT):
    """(campaign id, spend or None, verdict) for every active campaign, in id order.

    `active` maps campaign id to name. A campaign missing from the report is never paused on that basis."""
    out = []
    for cid in sorted(active):
        if str(cid) not in spend:
            out.append((cid, None, "нет в отчёте"))
        elif spend[str(cid)] >= limit:
            out.append((cid, spend[str(cid)], "СТОП"))
        else:
            out.append((cid, spend[str(cid)], f"осталось ${limit - spend[str(cid)]:.2f}"))
    return out


def log(line):
    os.makedirs(os.path.dirname(ACTIONS), exist_ok=True)
    with open(ACTIONS, "a") as f:
        f.write(f"{now()} {line}\n")


def main():
    apply = "--apply" in sys.argv
    try:
        spend = spend_by_campaign()
        rows = v2_campaigns(("name", "status"))
    except Exception as e:           # no spend, no judgement: nothing is paused on a failed read
        print(f"SPEND_ERR {e}")
        return 1
    active = {cid: r.get("name") or str(cid) for cid, r in rows.items()
              if (r.get("status") or {}).get("name") == "active"}
    print(f"{now()} UTC, лимит ${LIMIT:.2f}, активных кампаний {len(active)}")
    rc = 0
    for cid, sp, verdict in decide(active, spend):
        name = active[cid]
        print(f"  {cid} {name[:50]:<50} спенд {'—' if sp is None else '$%.2f' % sp}  {verdict}")
        if verdict != "СТОП" or not apply:
            continue
        st = pause(cid)
        ok = st.get("name") == "paused"
        log(f"stop camp={cid} ({name}) spent=${sp:.2f} limit=${LIMIT:.2f} -> {st.get('name')}/{st.get('reason')}")
        print(f"    пауза: {st.get('name')}/{st.get('reason')}" + ("" if ok else "  <- НЕ ВСТАЛА НА ПАУЗУ"))
        if not ok:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
