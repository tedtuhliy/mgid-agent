"""Offer window for the CPA tune campaigns of the 1537 test (21.10): started inside the window of the offer, paused outside it.

    MGID_ACCOUNT=second MGID_WINDOW_CAMPS=12468751,12468752 python3 offer_window.py          # dry run: prints what it would do
    MGID_ACCOUNT=second MGID_WINDOW_CAMPS=12468751,12468752 python3 offer_window.py --apply

LendingTree Mortgage Refinance CPL (1537) is paid on weekdays 08:00-21:00 US Eastern (RollerAds, leads outside the window do not
count). MGID has no day-parting in its API, so it is done from outside, every 5 minutes on Inferno
(`deploy_offer_window_inferno.sh`). Owner, 21.10: "cpa tune окна поставь по расписанию". It replaces the two crons of 31.08 on Inferno
(`lidgen_window.py` every hour and `mgid_daypart.sh` every 30 minutes) that kept restarting the old manual-bid campaigns of the offer
and were switched off on 21.10.

- Only the campaigns in MGID_WINDOW_CAMPS are touched, nothing else in the account.
- Inside the window a paused campaign is started (v1 flag, as `mgid_api.pause`) only if it was paused by us (`clientManuallyPaused`) and the
  stop-loss has not stopped it: its spend since the stop-loss reset (same baseline file, MGID_SPEND_BASELINE) is under MGID_SPEND_LIMIT.
  Otherwise the two would fight every five minutes. To give a campaign a new budget, move its baseline (see README, 21.10).
- Outside the window (nights, weekends) every listed campaign that is not paused is paused.
- A pause that is not ours (`outOfClientFunds`, `managerPaused`, ...) is left alone and reported.
- If the spend cannot be read nothing is STARTED; pausing outside the window still works.
- The window is read in America/New_York, so the EST/EDT change moves nothing.
"""
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spend_stop  # noqa: E402
from mgid_api import pause, v2_campaigns  # noqa: E402

CAMPS = [int(x) for x in os.environ.get("MGID_WINDOW_CAMPS", "").split(",") if x.strip()]
LIMIT = float(os.environ.get("MGID_SPEND_LIMIT", "3.0"))
ACTIONS = os.environ.get("MGID_WINDOW_ACTIONS", "/var/lib/mgid-offer-window-second/actions.log")
OPEN_H, CLOSE_H = 8, 21
OURS = "clientManuallyPaused"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def in_window(at):
    """True on weekdays 08:00-21:00 US Eastern. `at` is an aware datetime."""
    et = at.astimezone(ZoneInfo("America/New_York"))
    return et.weekday() < 5 and OPEN_H <= et.hour < CLOSE_H


def decide(camps, rows, want, spend, baseline, limit=LIMIT):
    """[(campaign id, action, why)] in the given order. action is "start", "pause" or None.

    `rows` is the v2 list ({id: {"name", "status": {"name", "reason"}}}), `spend` the lifetime spend by campaign (None when it could not
    be read), `baseline` the stop-loss baseline."""
    out = []
    for cid in camps:
        row = rows.get(cid)
        if row is None:
            out.append((cid, None, "нет в аккаунте"))
            continue
        status = row.get("status") or {}
        paused = status.get("name") == "paused"
        if not want:
            out.append((cid, None, "окно закрыто, на паузе") if paused else (cid, "pause", "окно закрыто"))
        elif not paused:
            out.append((cid, None, f"в окне, уже {status.get('name')}"))
        elif status.get("reason") != OURS:
            out.append((cid, None, f"в окне, но пауза не наша: {status.get('reason')}"))
        elif spend is None:
            out.append((cid, None, "в окне, расход не прочитан: не запускаю"))
        else:
            counted = max(0.0, spend.get(str(cid), 0.0) - baseline.get(str(cid), 0.0))
            if counted >= limit:
                out.append((cid, None, f"в окне, но стоп-лосс держит: ${counted:.2f} с сброса"))
            else:
                out.append((cid, "start", f"окно открыто, с сброса ${counted:.2f}"))
    return out


def log(line):
    os.makedirs(os.path.dirname(ACTIONS), exist_ok=True)
    with open(ACTIONS, "a") as f:
        f.write(f"{now()} {line}\n")


def main(at=None):
    apply = "--apply" in sys.argv
    if not CAMPS:
        print("MGID_WINDOW_CAMPS is empty: nothing to manage")
        return 1
    at = at or datetime.now(timezone.utc)
    want = in_window(at)
    try:
        rows = v2_campaigns(("name", "status"))
    except Exception as e:
        print(f"LIST_ERR {e}")
        return 1
    try:
        spend, baseline = spend_stop.spend_by_campaign(), spend_stop.load_baseline()
    except Exception as e:
        print(f"SPEND_ERR {e}")
        spend, baseline = None, {}
    et = at.astimezone(ZoneInfo("America/New_York")).strftime("%a %H:%M ET")
    print(f"{now()} UTC ({et}), окно {'ОТКРЫТО' if want else 'закрыто'}, кампаний в списке {len(CAMPS)}")
    rc = 0
    for cid, action, why in decide(CAMPS, rows, want, spend, baseline):
        name = (rows.get(cid) or {}).get("name") or str(cid)
        print(f"  {cid} {name[:44]:<44} {action or '—':<6} {why}")
        if action is None or not apply:
            continue
        st = pause(cid, on=(action == "pause"))
        ok = (st.get("name") == "paused") == (action == "pause")
        log(f"{action} camp={cid} ({name}) {why} -> {st.get('name')}/{st.get('reason')}")
        print(f"    -> {st.get('name')}/{st.get('reason')}" + ("" if ok else "  <- НЕ ПРИМЕНИЛОСЬ"))
        if not ok:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
