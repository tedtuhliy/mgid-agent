"""CPA tune ladder for the 1537 test (21.10): every hour a campaign that gets too few clicks gets a target CPA higher by $0.50.

    MGID_ACCOUNT=second MGID_LADDER_CAMPS=12468751,12468752 python3 cpa_ladder.py          # dry run: prints what it would do
    MGID_ACCOUNT=second MGID_LADDER_CAMPS=12468751,12468752 python3 cpa_ladder.py --apply

Owner, 21.10: «Поставь просто 50 центов ставку cpa tune и если трафика за час не будет хотя бы пару кликов то поднимай по 50 центов так
каждый час пока не пойдёт хотя бы 10 20 кликов в час». At 5 cents the campaigns got a handful of impressions an hour, at 50 cents it was the same
for the first hour; a CPA tune campaign with no conversions yet has no other lever than the target.

- State per campaign (MGID_LADDER_STATE): the time, the lifetime clicks and the target CPA at the last change or look. An hour (55 minutes) or more later
  the clicks since then are counted: fewer than GOAL (10) an hour -> the target goes up by STEP (0.50), at most to MAX (5.00); GOAL or more -> held.
  The target is never lowered here. "A pair of clicks" and "10-20 an hour" of the order are one rule: keep climbing until 10 an hour.
- Only a campaign that can deliver is judged: active, at least one teaser active (approved), and the offer window (`offer_window.in_window`, weekdays
  08:00-21:00 US Eastern) open now and at the time of the last look, on the same Eastern date. Otherwise the state is only renewed: nights, weekends,
  a campaign held by the stop-loss or waiting for moderation never raise anything.
- Clicks are the lifetime clicks of v1 `campaigns-stat`; MGID's figures lag, the lag is the same every hour, so the difference is fair.
- A raise is a v2 PATCH of `bidding` and is read back; if it does not stick the state is not moved. The stop-loss ($5 per campaign since its reset;
  $3 until the evening of 21.10) stays above all of this.
"""
import json
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mgid_api import CID1, CID2, V2, call, v1, v2_campaigns  # noqa: E402
from offer_window import in_window  # noqa: E402

CAMPS = [int(x) for x in os.environ.get("MGID_LADDER_CAMPS", "").split(",") if x.strip()]
STATE = os.environ.get("MGID_LADDER_STATE", "/var/lib/mgid-cpa-ladder-second/state.json")
ACTIONS = os.environ.get("MGID_LADDER_ACTIONS", "/var/lib/mgid-cpa-ladder-second/actions.log")
GOAL = float(os.environ.get("MGID_LADDER_GOAL", "10"))        # clicks an hour that end the climb
STEP = float(os.environ.get("MGID_LADDER_STEP", "0.50"))
MAX = float(os.environ.get("MGID_LADDER_MAX", "5.00"))
MIN_MINUTES = 55
ET = ZoneInfo("America/New_York")


def stamp(at):
    return at.strftime("%Y-%m-%d %H:%M:%S")


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, STATE)


def log(at, line):
    os.makedirs(os.path.dirname(ACTIONS), exist_ok=True)
    with open(ACTIONS, "a") as f:
        f.write(f"{stamp(at)} {line}\n")


def clicks_by_campaign():
    """{campaign id as str: lifetime clicks}. Raises if the report cannot be read."""
    st, d = v1("GET", f"goodhits/clients/{CID1}/campaigns-stat", dateInterval="all")
    rows = d.get("campaigns-stat") if st == 200 and isinstance(d, dict) else None
    if not isinstance(rows, dict):
        raise RuntimeError(f"campaigns-stat: {st} {json.dumps(d, ensure_ascii=False)[:200]}")
    return {str(k): int((v or {}).get("clicks") or 0) for k, v in rows.items()}


def active_teasers(cid):
    st, t = v1("GET", f"goodhits/clients/{CID1}/teasers", campaign=cid, limit=50, start=0)       # start is 0-based
    rows = t.values() if st == 200 and isinstance(t, dict) else []
    return sum(1 for x in rows if isinstance(x, dict) and (x.get("status") or {}).get("code") == "active")


def decide(entry, at, clicks, price, can_deliver):
    """(action, new state entry, why). action: "seed", "renew", "wait", "hold", "raise", "cap".

    `entry` is the stored {"t", "clicks", "price"} or None, `can_deliver` says active + an approved teaser."""
    snap = {"t": at.isoformat(), "clicks": clicks, "price": price}
    if entry is None:
        return "seed", snap, "первый взгляд"
    then = datetime.fromisoformat(entry["t"])
    same_day = then.astimezone(ET).date() == at.astimezone(ET).date() and in_window(then) and in_window(at)
    if not can_deliver or not in_window(at):
        return "renew", snap, "не доставляет или окно закрыто"
    if not same_day:
        return "renew", snap, "окно было закрыто с прошлого взгляда"
    minutes = (at - then).total_seconds() / 60
    if minutes < MIN_MINUTES:
        return "wait", entry, f"прошло {minutes:.0f} мин"
    rate = max(0, clicks - entry["clicks"]) * 60 / minutes
    if rate >= GOAL:
        return "hold", snap, f"{rate:.1f} кл/час, цель {GOAL:g} достигнута"
    new = round(price + STEP, 2)
    if new > MAX + 1e-9:
        return "cap", snap, f"{rate:.1f} кл/час, потолок ${MAX:.2f}"
    return "raise", {"t": at.isoformat(), "clicks": clicks, "price": new}, f"{rate:.1f} кл/час < {GOAL:g}"


def main(at=None):
    apply = "--apply" in sys.argv
    if not CAMPS:
        print("MGID_LADDER_CAMPS is empty: nothing to manage")
        return 1
    at = at or datetime.now(timezone.utc)
    try:
        rows = v2_campaigns(("name", "status", "bidding"))
        clicks = clicks_by_campaign()
    except Exception as e:
        print(f"READ_ERR {e}")
        return 1
    state = load_state()
    print(f"{stamp(at)} UTC, лестница CPA tune: цель {GOAL:g} кл/час, шаг ${STEP:.2f}, потолок ${MAX:.2f}, кампаний {len(CAMPS)}")
    rc = 0
    for cid in CAMPS:
        row = rows.get(cid)
        if row is None or str(cid) not in clicks:
            print(f"  {cid} нет в аккаунте или в отчёте")
            continue
        price = float((row.get("bidding") or {}).get("price") or 0)
        active = (row.get("status") or {}).get("name") == "active"
        can = active and in_window(at) and active_teasers(cid) > 0
        action, new, why = decide(state.get(str(cid)), at, clicks[str(cid)], price, can)
        print(f"  {cid} {str(row.get('name'))[:40]:<40} цель ${price:.2f}  {action:<5} {why}")
        if not apply:
            continue
        if action == "raise":
            st, d = call("PATCH", V2 + f"account/{CID2}/campaigns/{cid}", {"bidding": {"strategy": "targetCpa", "price": new["price"]}})
            got = float(((v2_campaigns(("bidding",)).get(cid) or {}).get("bidding") or {}).get("price") or 0) if st in (200, 204) else None
            ok = got is not None and abs(got - new["price"]) < 1e-9
            log(at, f"raise camp={cid} {price:.2f} -> {new['price']:.2f} ({why}) http={st} readback={got}")
            print(f"    -> цель ${got if got is not None else '?'}" + ("" if ok else "  <- НЕ ПРИМЕНИЛОСЬ"))
            if not ok:
                rc = 1
                continue
        elif action in ("seed", "hold", "cap", "renew"):
            if action != "renew":
                log(at, f"{action} camp={cid} price={price:.2f} ({why})")
        state[str(cid)] = new
    if apply:
        save_state(state)
    return rc


if __name__ == "__main__":
    sys.exit(main())
