"""Stop-loss for MGID: pause every active campaign whose spend since the last reset reaches LIMIT dollars.

    python3 spend_stop.py            # dry run: prints the spend of each active campaign, pauses nothing
    python3 spend_stop.py --apply    # pauses the campaigns at or above the limit and reads each one back
    python3 spend_stop.py --reset    # starts the count from now: remembers every campaign's lifetime spend

Owner, 11.11: «настрой на инферно бота который стопнет кампании после спенда в 3 бакса».
Owner, 11.11: «сбрось 3 бакса начиная с сейчас считай».

- Spend is the lifetime spend from v1 campaigns-stat (dateInterval=all), in dollars. The bot counts from
  the baseline: the spend each campaign had when the count was last reset. A campaign that is not in the
  baseline (created after the reset) counts all its spend.
- Only ACTIVE campaigns are judged. Paused campaigns are left alone.
- The bot never starts a campaign. A campaign restarted above the limit is paused again on the next run;
  to lift the rule, run --reset again or change MGID_SPEND_LIMIT in the unit.
- If the spend cannot be read, nothing is paused and nothing is reset: the run prints the error and exits 1.
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
BASELINE = os.environ.get("MGID_SPEND_BASELINE", "/var/lib/mgid-spend-stop/baseline.json")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def spend_by_campaign():
    """{campaign id as str: lifetime spend $} for the whole account. Raises if the report cannot be read."""
    st, d = v1("GET", f"goodhits/clients/{CID1}/campaigns-stat", dateInterval="all")
    rows = d.get("campaigns-stat") if st == 200 and isinstance(d, dict) else None
    if not isinstance(rows, dict):
        raise RuntimeError(f"campaigns-stat: {st} {json.dumps(d, ensure_ascii=False)[:200]}")
    return {str(k): float((v or {}).get("spent") or 0) for k, v in rows.items()}


def load_baseline():
    """{campaign id as str: lifetime spend at the last reset}. Empty if the bot was never reset."""
    try:
        with open(BASELINE) as f:
            return {str(k): float(v) for k, v in json.load(f).items()}
    except (OSError, ValueError):
        return {}


def save_baseline(spend):
    os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
    tmp = BASELINE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(spend, f, ensure_ascii=False, indent=1)
    os.replace(tmp, BASELINE)


def decide(active, spend, limit=LIMIT, baseline=None):
    """(campaign id, spend counted since the reset or None, verdict) for every active campaign, in id order.

    `active` maps campaign id to name. A campaign missing from the report is never paused on that basis."""
    base = baseline or {}
    out = []
    for cid in sorted(active):
        if str(cid) not in spend:
            out.append((cid, None, "нет в отчёте"))
            continue
        counted = max(0.0, spend[str(cid)] - base.get(str(cid), 0.0))
        if counted >= limit:
            out.append((cid, counted, "СТОП"))
        else:
            out.append((cid, counted, f"осталось ${limit - counted:.2f}"))
    return out


def log(line):
    os.makedirs(os.path.dirname(ACTIONS), exist_ok=True)
    with open(ACTIONS, "a") as f:
        f.write(f"{now()} {line}\n")


def main():
    apply = "--apply" in sys.argv
    reset = "--reset" in sys.argv
    try:
        spend = spend_by_campaign()
        rows = v2_campaigns(("name", "status"))
    except Exception as e:           # no spend, no judgement: nothing is paused or reset on a failed read
        print(f"SPEND_ERR {e}")
        return 1
    if reset:
        save_baseline(spend)
        log(f"reset: baseline set for {len(spend)} campaigns, limit ${LIMIT:.2f} counts from now")
        print(f"{now()} UTC, база сброшена для {len(spend)} кампаний: лимит ${LIMIT:.2f} считается с этого момента")
        return 0
    baseline = load_baseline()
    active = {cid: r.get("name") or str(cid) for cid, r in rows.items()
              if (r.get("status") or {}).get("name") == "active"}
    print(f"{now()} UTC, лимит ${LIMIT:.2f} с момента сброса, активных кампаний {len(active)}")
    rc = 0
    for cid, counted, verdict in decide(active, spend, baseline=baseline):
        name = active[cid]
        life = spend.get(str(cid))
        shown = "—" if counted is None else f"${counted:.2f} (всего ${life:.2f})"
        print(f"  {cid} {name[:50]:<50} с сброса {shown}  {verdict}")
        if verdict != "СТОП" or not apply:
            continue
        st = pause(cid)
        ok = st.get("name") == "paused"
        log(f"stop camp={cid} ({name}) counted=${counted:.2f} lifetime=${life:.2f} limit=${LIMIT:.2f} "
            f"-> {st.get('name')}/{st.get('reason')}")
        print(f"    пауза: {st.get('name')}/{st.get('reason')}" + ("" if ok else "  <- НЕ ВСТАЛА НА ПАУЗУ"))
        if not ok:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
