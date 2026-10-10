"""MGID dating: block a placement once it has spent two conversion costs without a lead.

    python3 mgid_guard.py              # dry run: prints the table, blocks nothing
    python3 mgid_guard.py --apply      # what the timer on Inferno runs every 5 minutes
    python3 mgid_guard.py status       # last run, holds, thresholds and every block made

Owner, 10.10: «страховочный скрипт на inferno, который будет стопать площадки после спенда
2 стоимостей конверсий без лидов; стоимость конверсии нужно брать с настроек кампании».
This replaces the flat $0.30 rule of 30.09, which judged a $2 Polish offer and a $0.32 Latvian one
by the same figure.

The rule, per campaign:

    placement spend (lifetime of the campaign) >= MULT x conversion cost, and no lead  ->  block

- The conversion cost is read from the campaign's OWN settings: `conversionTracking.buyStage.
  conversionValue` of the v2 campaign (v1 `conversions` for a campaign on manual bidding that the
  v2 read leaves empty). The guard never looks at cpamatica; the copies made by mgid_geo_copies.py
  carry the cabinet rate of their geo in exactly that field, and the guard follows whatever is
  there, so changing it in the cabinet of MGID (or by `--sync-rates`) changes the threshold.
- A campaign without a conversion cost falls back to the flat `MGID_GUARD_THRESH` and says so
  (MGIDG_NOCPA); it is never skipped silently, because a guard that quietly watches nothing reads
  as "all clean".
- Campaigns are found, not listed: every ACTIVE campaign of the account whose buy stage is the
  dating target 1274200. A copy is covered from the moment it is started, with no edit here.

Spend per placement comes from v1 quality-analysis of each campaign over its whole life
(`dateInterval=all`). A placement counts as having a lead when EITHER source says so:
- our own record. The middleware on Inferno writes every MGID lead into `mgid_leads`, with the
  campaign and widget taken from the UTM (`source=mgid_<campaign>_<widget>`, set by mgid_utm.py);
- or MGID's own buy-stage conversion on that widget (v2 report), fed by the same postback.

It is judged per campaign. A widget blocked in the Kazakh campaign keeps running in the Latvian
one, because rate, geo and audience differ and so can the answer.

Safety:
- widget keys are cut to their leading digits on both sides. A sub-source row ("123s4") and the
  macro value ("123") then cannot miss each other and get a converting placement blocked;
- if a lead arrived WITHOUT a source (`mgid_nosrc`) after the newest MGID lead that carried its
  placement, the UTM may have stopped reaching cpamatica. Leads then cannot be placed, so the
  guard holds (MGIDG_HOLD) instead of blocking every placement for "no lead". The same applies
  when the middleware's tables cannot be read, or when the campaigns cannot be listed;
- the exclusion list only grows (`include, except`), and every write is read back.
"""
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mgid_api import TARGET, blacklist, block, buy_cpa, report, v1_conversion, v2_campaigns, widget_spend  # noqa: E402

MULT = float(os.environ.get("MGID_GUARD_MULT", "2"))        # conversion costs a placement may spend
FLAT = float(os.environ.get("MGID_GUARD_THRESH", "0.30"))   # $ for a campaign with no conversion cost
DB = os.environ.get("MGID_LEADS_DB", "/var/www/postback-middleware/accumulator_exocpa.db")
STATE = os.environ.get("MGID_GUARD_STATE", "/var/lib/mgid-guard/state.json")
ACTIONS = os.environ.get("MGID_GUARD_ACTIONS", "/var/lib/mgid-guard/actions.log")
# cpamatica offers our MGID links point at: Tinely PL 9962, LATAM 8326, CIS/Baltics 8394, UA 8395.
# A lead of any other offer cannot be an MGID lead, whatever its source says (see our_leads).
OFFERS = {int(x) for x in os.environ.get("MGID_OFFERS", "9962,8326,8394,8395").split(",") if x.strip()}
START = "2026-09-30"                   # the campaigns' first day
NOSRC_SINCE = "2026-09-30 12:45:00"    # UTM with the placement live from here (UTC)


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def base(uid):
    m = re.match(r"\d+", str(uid))
    return m.group() if m else str(uid)


def offer_of(tx):
    """cpamatica transaction ids read `<n>_<affiliate>_<offer>_<hash>`; None if it does not."""
    m = re.match(r"\d+_\d+_(\d+)_", str(tx or ""))
    return int(m.group(1)) if m else None


def threshold(cpa):
    """($ a placement may spend without a lead, what the figure came from)."""
    if cpa:
        return round(MULT * cpa, 4), f"{MULT:g} x ${cpa:g}"
    return FLAT, f"плоский порог ${FLAT:g}, у кампании нет цены конверсии"


def watched():
    """{campaign id: {name, cpa}} for every active campaign with the dating lead target."""
    out = {}
    for cid, row in v2_campaigns().items():
        if (row.get("status") or {}).get("name") != "active":
            continue
        target, cpa = buy_cpa(row)
        if target is None:                       # v2 can read null for a while after a write
            target, cpa = v1_conversion(cid)
        bid = row.get("bidding") or {}
        auto = bid.get("strategy") in ("targetCpa", "maxConversions")
        # A CPA campaign whose target cannot be read right now is still ours to watch: skipping it
        # would leave exactly the campaigns that spend on their own with no guard at all.
        if target == TARGET or (target is None and auto):
            if not cpa and bid.get("strategy") == "targetCpa":
                cpa = float(bid.get("price") or 0) or None      # the CPA target is a cost setting too
            out[cid] = {"name": row.get("name") or str(cid), "cpa": cpa}
    return out


def our_leads():
    """({(campaign, widget): leads}, hold reason or None) from the middleware's own tables."""
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        rows = con.execute("SELECT camp, widget, COUNT(*), MAX(ts) FROM mgid_leads "
                           "WHERE camp IS NOT NULL AND camp != '' GROUP BY camp, widget").fetchall()
        nosrc = con.execute("SELECT tx, ts FROM mgid_nosrc WHERE ts >= ?", (NOSRC_SINCE,)).fetchall()
        con.close()
    except sqlite3.Error as e:
        return {}, f"таблицы мидлвари не читаются ({e})"
    # Only a lead of OUR offers can be an MGID lead that lost its UTM. The smartlink 16588 and the
    # other cpamatica offers pay through the same postback with no source whenever they come from
    # another buy; counting them kept this guard on HOLD from 01.10 19:30 on, doing nothing.
    last_nosrc = max((t for tx, t in nosrc if offer_of(tx) is None or offer_of(tx) in OFFERS), default=None)
    leads = defaultdict(int)
    for c, w, n, _ in rows:
        if w:
            leads[(str(c), base(w))] += n
    last_placed = max((t for c, w, n, t in rows if w), default=None)
    if last_nosrc and (last_placed is None or last_nosrc > last_placed):
        return leads, (f"лид без source в {last_nosrc} UTC новее последнего MGID-лида с площадкой "
                       f"({last_placed or 'их ещё не было'}): UTM мог перестать доходить")
    return leads, None


def mgid_conversions(camps):
    """{(campaign, widget): buy-stage conversions} as MGID counted them; {} if unavailable."""
    till = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()   # MGID days are UTC+3
    try:
        rows = report(START, till, ("conversionsBuy",), ("campaignId", "widgetId"), list(camps))
    except Exception as e:  # our own table is the primary signal; this one is extra
        print(f"MGIDG_WARN v2 report: {e}")
        return {}
    out = defaultdict(int)
    for r in rows:
        n = r.get("conversionsBuy")
        n = n.get("amount") if isinstance(n, dict) else n
        if float(n or 0) > 0:
            out[(str(r.get("campaignId")), base(r.get("widgetId")))] += int(float(n))
    return out


def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE)


def log_action(line):
    os.makedirs(os.path.dirname(ACTIONS), exist_ok=True)
    with open(ACTIONS, "a") as f:
        f.write(f"{now()} {line}\n")


def status():
    try:
        st = json.load(open(STATE))
    except (OSError, ValueError):
        print("сторож ещё не запускался (нет state.json)")
        return
    print(f"последний прогон {st.get('last_run')} UTC, правило {st.get('mult')} x цена конверсии кампании, "
          f"{'HOLD: ' + st['hold'] if st.get('hold') else 'режет'}")
    if not st.get("camps"):
        print("под наблюдением нет ни одной активной кампании с целью 1274200")
    for cid, c in (st.get("camps") or {}).items():
        print(f"  {cid} {c.get('name')}: порог ${c.get('thresh', 0):.2f} ({c.get('basis')}), "
              f"расход ${c.get('spend', 0):.2f} на {c.get('widgets', 0)} площадках, "
              f"лидов {c.get('leads', 0)}, в блоке {c.get('blocked', 0)}{' | ' + c['error'] if c.get('error') else ''}")
    try:
        tail = open(ACTIONS).read().splitlines()[-15:]
    except OSError:
        tail = []
    print("последние действия:" if tail else "блоков ещё не было")
    for line in tail:
        print("  " + line)


def main():
    if "status" in sys.argv[1:]:
        return status()
    apply = "--apply" in sys.argv
    try:
        camps = watched()
    except Exception as e:
        # no list of campaigns = nothing can be judged; say so loudly and let systemd show a failure
        print(f"MGIDG_ERR список кампаний не получен: {e}")
        sys.exit(1)
    leads, hold = our_leads()
    conv = mgid_conversions(camps)
    try:
        bad = set(json.load(open(STATE)).get("unknown_uids") or [])
    except (OSError, ValueError):
        bad = set()
    st = {"last_run": now(), "mult": MULT, "hold": hold, "camps": {}}
    if hold:
        print(f"MGIDG_HOLD {hold} — площадки не режу")
    if not camps:
        print("MGIDG под наблюдением нет ни одной активной кампании с целью 1274200")
    for cid, info in camps.items():
        name = info["name"]
        thresh, basis = threshold(info["cpa"])
        c = st["camps"][str(cid)] = {"name": name, "cpa": info["cpa"], "thresh": thresh, "basis": basis}
        if not info["cpa"]:
            print(f"MGIDG_NOCPA {cid} {name}: цены конверсии в настройках нет — {basis}")
        try:
            spend = widget_spend(cid)
            have, ftype = blacklist(cid)
        except Exception as e:
            c["error"] = str(e)[:200]
            print(f"MGIDG_ERR {cid} {name}: {e}")
            continue
        agg = defaultdict(lambda: [0, 0.0])
        for uid, (clicks, spent) in spend.items():
            a = agg[base(uid)]
            a[0] += clicks
            a[1] += spent
        have_b = {base(w) for w in have}
        n_leads = lambda w: leads.get((str(cid), w), 0) + conv.get((str(cid), w), 0)  # noqa: E731
        kill = sorted(w for w, (clicks, spent) in agg.items()
                      if spent >= thresh and not n_leads(w) and w not in have_b and w not in bad)
        c.update(widgets=len(agg), spend=round(sum(a[1] for a in agg.values()), 2),
                 leads=sum(n for (k, _), n in leads.items() if k == str(cid)), blocked=len(have_b))
        print(f"MGIDG {cid} {name}: расход ${c['spend']:.2f} на {len(agg)} площадках, лидов {c['leads']}, "
              f"в блоке {len(have_b)} ({ftype}); к блоку (≥ ${thresh:.2f} = {basis}, без лида): {len(kill)}")
        if not apply:
            for w, (clicks, spent) in sorted(agg.items(), key=lambda kv: -kv[1][1])[:15]:
                mark = "  <- в блок" if w in kill else ("  (уже в блоке)" if w in have_b else "")
                print(f"    {w:<12} {clicks:>5} кл ${spent:>6.2f}  лидов {n_leads(w)}{mark}")
            continue
        if not kill or hold:
            continue
        # A uid MGID does not know comes back in `data` with WIDGETS_WITH_THESE_UIDS_DO_NOT_EXIST
        # (HTTP 200); the valid ones in the same call are still added (checked 30.09).
        st_code, resp = block(cid, kill)
        after, _ = blacklist(cid)
        after_b = {base(w) for w in after}
        unknown = {str(x) for x in (resp.get("data") or [])} if isinstance(resp, dict) and resp.get("errors") else set()
        bad.update(unknown)
        missed = [w for w in kill if w not in after_b and w not in unknown]
        c["blocked"] = len(after_b)
        done = [w for w in kill if w in after_b]
        for w in done:
            log_action(f"block camp={cid} ({name}) widget={w} spent=${agg[w][1]:.2f} clicks={agg[w][0]} leads=0 "
                       f"thresh=${thresh:.2f} ({basis})")
        print(f"MGIDG_BLOCK {cid} {name}: {len(done)} площадок в блок ({', '.join(done)}); PATCH {st_code}")
        if unknown:
            print(f"MGIDG_WARN {cid}: MGID не знает площадок {sorted(unknown)} — больше их не шлю")
        if missed:
            print(f"MGIDG_ERR {cid}: не записались {missed}: {json.dumps(resp, ensure_ascii=False)[:200]}")
            c["error"] = f"не записались {len(missed)}"
    if apply:
        st["unknown_uids"] = sorted(bad)
        save_state(st)


if __name__ == "__main__":
    main()
