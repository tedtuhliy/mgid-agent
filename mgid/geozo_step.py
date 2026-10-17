"""One gradual step of the target-CPA ladder of the geo campaigns (geozo_geos.py).

    python3 geozo_step.py            # dry run: what would change and why, nothing is written
    python3 geozo_step.py --apply    # PATCH the targets (geozo_geos.set_cpa) and remember when

Owner, 14.10 11:54 MSK: «Поднимай ставки так же постепенно, как делал». What was done by hand, written down so that it can be
repeated every hour or so without anyone adding it up again: a geo whose campaign delivers (almost) nothing an hour after the
last change of its target gets the target doubled, one step at a time, never all the way up at once.

A geo (of geozo_geos.ORDER, except KZ) is raised when ALL of this holds:
  - at least one of its teasers is active (RS and part of SI wait for MGID's moderation, nothing to raise);
  - the target was last changed MIN_GAP_H hours ago or earlier (data/geozo-ladder.json keeps the time; a geo seen for the first
    time with active teasers only gets its clock started);
  - delivery is weak: the mean of impressions of the last two COMPLETED Moscow hours is under WEAK_PER_H;
  - the target is under CEILING; the new target is min(FACTOR * target, CEILING).
and NONE of these guards trips (the geo is left alone and the reason is printed):
  - the wallet is under MIN_BALANCE dollars (nothing is raised anywhere: the wallet is the real limit of the test);
  - the geo spent more than MAX_SPEND_NO_CONV dollars today with under 5 conversions (money without a chain);
  - the geo's realized cost per click today is over MAX_CPC (the target is a ceiling, not a price: MGID charged $0.0001-0.002
    a click in every geo so far; a click at a cent means the auction has started to take the ceiling).
KZ (the blog campaign at 1 cent) delivers about a thousand impressions an hour at the floor price and is raised only by the
owner's word. MGID fills the hourly rows late, so «zero» in the first hours of a campaign is provisional: that is why the rule
looks at completed hours only and waits an hour between steps.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "geozo_site"))

FACTOR = 2.0
CEILING = 0.50            # no target above this, whatever the rule says
MIN_GAP_H = 0.9           # hours since the last change of the target of the geo
WEAK_PER_H = 50           # impressions an hour (mean of the last two completed hours) under which a geo does not deliver
MAX_CPC = 0.01            # realized cost per click of the day over which a geo is not raised
MAX_SPEND_NO_CONV = 1.0   # dollars spent today with fewer than MIN_CONV conversions: not raised
MIN_CONV = 5
MIN_BALANCE = 4.0
SKIP = {"KZ"}
MSK = timezone(timedelta(hours=3))
from mgid_api import ACCOUNT  # noqa: E402  (no side effects: it only reads MGID_ACCOUNT)

# {geo: {"cpa": target, "at": ISO time of the last change or first sight}}, one file per account
STATE = HERE / "data" / ("geozo-ladder.json" if ACCOUNT == "main" else f"geozo-ladder.{ACCOUNT}.json")


def decide(cur, gap_h, per_hour, spend, clicks, conv, active, balance):
    """(new target or None, reason). Pure: the whole policy is here."""
    if balance is not None and balance < MIN_BALANCE:
        return None, f"баланс ${balance:.2f} < ${MIN_BALANCE:.0f}: ничего не поднимаю"
    if not active:
        return None, "тизеры на модерации"
    if gap_h is None:
        return None, "первый раз вижу активные тизеры: запускаю часы, поднимать буду через час"
    if gap_h < MIN_GAP_H:
        return None, f"ставку меняли {gap_h:.1f} ч назад, жду час"
    if per_hour >= WEAK_PER_H:
        return None, f"показы идут ({per_hour:.0f} в час), не трогаю"
    if spend > MAX_SPEND_NO_CONV and conv < MIN_CONV:
        return None, f"потрачено ${spend:.2f} при {conv} конверсиях: стоп, смотрит владелец"
    if clicks and spend / clicks > MAX_CPC:
        return None, f"клик стоит ${spend / clicks:.4f} > ${MAX_CPC}: стоп, смотрит владелец"
    if cur >= CEILING:
        return None, f"потолок ${CEILING} достигнут"
    new = min(round(cur * FACTOR, 4), CEILING)
    return new, f"показов {per_hour:.0f} в час за два полных часа: ×{FACTOR:g}"


def hours_back(now, n):
    """The n last COMPLETED Moscow hours as (date, 'hour') with the hour the way MGID's report prints it."""
    h = now.astimezone(MSK).replace(minute=0, second=0, microsecond=0)
    return [((h - timedelta(hours=i)).date().isoformat(), str((h - timedelta(hours=i)).hour)) for i in range(1, n + 1)]


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def sync_cpa_literal(cpa):
    """Write the targets in force into the CPA table of geozo_geos.py (the file is what the next session reads first)."""
    import re
    f = HERE / "geozo_geos.py"
    body = ", ".join(f'"{g}": {cpa[g]:g}' for g in cpa)
    lines, row = [], "CPA = {"
    for item in body.split(", "):
        if len(row) + len(item) + 2 > 126:
            lines.append(row.rstrip())
            row = "       "
        row += item + ", "
    lines.append(row.rstrip().rstrip(",") + "}")
    s = f.read_text(encoding="utf-8")
    s2 = re.sub(r"^CPA = \{[^}]*\}", "\n".join(lines), s, count=1, flags=re.M)
    if s2 != s:
        f.write_text(s2, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    import geozo_geos as gg
    import geozo_report as gr
    import mgid_geo_copies as cp
    from mgid_api import CID1, V1, call, v2_campaigns

    now = datetime.now(timezone.utc)
    today = now.astimezone(MSK).date().isoformat()
    st, w = call("GET", V1 + f"clients/{CID1}")
    balance = float(((w or {}).get("wallet") or {}).get("balance")) if isinstance(w, dict) and (w.get("wallet") or {}).get("balance") is not None else None
    live = v2_campaigns(("name", "status", "bidding"))
    state = load_state()
    saved = gg.saved()
    cache = {}

    def hourly(cid, day):
        if (cid, day) not in cache:
            cache[(cid, day)] = gr.hourly(day, cid)
        return cache[(cid, day)]

    print(f"{now.astimezone(MSK):%d.%m %H:%M} МСК, баланс MGID ${balance if balance is None else round(balance, 2)}, "
          f"режим {'ПРИМЕНЯЮ' if a.apply else 'сухой прогон'}")
    changes, new_state = {}, dict(state)
    for g in gg.ORDER:
        if g in SKIP:
            continue
        cid = gg.cid_of(g, live)
        if not cid:
            print(f"{g}: кампании нет")
            continue
        cur = float((state.get(g) or {}).get("cpa") or (saved.get(g) or {}).get("cpa") or gg.CPA[g])
        codes = [(t.get("status") or {}).get("code") for t in cp.teasers(cid).values()]
        active = "active" in codes
        at = (state.get(g) or {}).get("at")
        gap_h = (now - datetime.fromisoformat(at.replace("Z", "+00:00"))).total_seconds() / 3600 if at else None
        last = hours_back(now, 2)
        per_hour = sum(int(hourly(cid, d).get(h, [0])[0]) for d, h in last) / len(last)
        day = hourly(cid, today)
        imp, clk, spend, conv = (sum(v[i] for v in day.values()) for i in range(4))
        new, why = decide(cur, gap_h, per_hour, spend, clk, conv, active, balance)
        print(f"{g}: цель {cur:g}, показов/ч {per_hour:.0f}, за день {imp} пок / {clk} кл / ${spend:.4f} / {conv} конв -> "
              f"{'ПОДНЯТЬ до ' + format(new, 'g') if new else 'без изменений'}: {why}")
        if new:
            changes[g] = new
        elif gap_h is None and active:
            new_state[g] = {"cpa": cur, "at": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
    print("изменения:", changes or "нет")
    if a.apply:
        if changes:
            gg.set_cpa(changes, live)
            stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            for g, v in changes.items():
                new_state[g] = {"cpa": v, "at": stamp}
        STATE.write_text(json.dumps(new_state, ensure_ascii=False, indent=1))
        if changes and ACCOUNT == "main":          # the CPA table of geozo_geos.py is the main account's; the second one keeps its values in its data file
            sync_cpa_literal(gg.CPA)
        print(f"состояние записано: {STATE}")


if __name__ == "__main__":
    main()
