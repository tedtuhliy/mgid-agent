"""The Sources tab of MGID in the terminal: the domains a campaign gets its traffic from (22.10). Read-only.

    MGID_ACCOUNT=second python3 sources_report.py 12468751,12468752 2026-10-21 2026-10-22          # top 25 domains
    MGID_ACCOUNT=second python3 sources_report.py 12468751,12468752 2026-10-21 2026-10-22 --top 50

Owner, 22.10: «посмотреть с каких площадок идёт? Именно название доменов через вкладку sources».

- Source of the numbers: v1 `goodhits/campaigns/{id}/quality-analysis-sources/` with `dateInterval=interval`; `sourceName` is the DOMAIN of the
  publisher, only sources with delivery are listed. The v2 report has the same names as its `source` dimension, and with the dimensions
  `widgetId` x `source` it tells which widget id (the `{widget_id}` of the teaser link, `source_id` in the RollerAds tracker) is which domain.
- The days are MGID days in the time zone of the account: `Europe/Tirane` for the second account (UTC+2 until 25.10, UTC+1 after), see `mgid_api.report`.
- A source is flagged when it has at least 2 clicks and a CTR of 5 % or more: on a handful of impressions that is the mark of placements where the
  ad is clicked by accident or by a script (on 22.10 vitabloomy.shop, 5.8 %, whose widgets also sent every click to the tracker twice, and nullsite.info,
  clicks with almost no impressions); real news sites sit at 0.3-1.5 %.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mgid_api import v1  # noqa: E402

FLAG_CTR, FLAG_CLICKS = 5.0, 2


def aggregate(payloads):
    """{source id: row} summed over the answers of `quality-analysis-sources` (one per campaign).

    An answer is {campaign id: {"<from>_<to>": {source id: {"sourceName", "impressions", "clicks", "spent", ...}}}}."""
    out = {}
    for payload in payloads:
        for periods in (payload or {}).values():
            for rows in (periods or {}).values():
                for sid, r in (rows or {}).items():
                    a = out.setdefault(str(sid), {"name": r.get("sourceName") or str(sid), "imp": 0, "clk": 0, "spent": 0.0, "conv": 0})
                    a["imp"] += int(r.get("impressions") or 0)
                    a["clk"] += int(r.get("clicks") or 0)
                    a["spent"] += float(r.get("spent") or 0)
                    a["conv"] += int(r.get("conversionsBuy") or 0)
    return {k: v for k, v in out.items() if v["imp"] or v["clk"] or v["spent"]}


def ctr(row):
    return 100.0 * row["clk"] / row["imp"] if row["imp"] else (100.0 if row["clk"] else 0.0)


def flagged(row):
    return row["clk"] >= FLAG_CLICKS and ctr(row) >= FLAG_CTR


def main(argv):
    top = int(argv[argv.index("--top") + 1]) if "--top" in argv else 25
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--top")]
    if len(args) != 3:
        print(__doc__)
        return 1
    camps = [int(x) for x in args[0].split(",") if x.strip()]
    payloads = []
    for cid in camps:
        st, d = v1("GET", f"goodhits/campaigns/{cid}/quality-analysis-sources/", dateInterval="interval", startDate=args[1], endDate=args[2])
        if st != 200 or not isinstance(d, dict) or d.get("errors"):
            print(f"{cid}: quality-analysis-sources {st} {str(d)[:200]}")
            return 1
        payloads.append(d)
    rows = aggregate(payloads)
    tot_imp = sum(r["imp"] for r in rows.values())
    tot_clk = sum(r["clk"] for r in rows.values())
    tot_spent = sum(r["spent"] for r in rows.values())
    print(f"campaigns {camps}, {args[1]} .. {args[2]} (MGID days of the account): {len(rows)} domains, {tot_imp} impressions, {tot_clk} clicks, ${tot_spent:.2f}")
    print(f"{'domain':<34}{'impr':>7}{'clicks':>7}{'spent':>8}{'cpc':>8}{'ctr %':>7}  conv")
    for r in sorted(rows.values(), key=lambda x: (-x["clk"], -x["spent"], -x["imp"]))[:top]:
        cpc = r["spent"] / r["clk"] if r["clk"] else 0.0
        print(f"{r['name'][:33]:<34}{r['imp']:>7}{r['clk']:>7}{r['spent']:>8.2f}{cpc:>8.3f}{ctr(r):>7.1f}  {r['conv']}{'  <- CTR' if flagged(r) else ''}")
    bad = [r for r in rows.values() if flagged(r)]
    if bad:
        print(f"flagged (>= {FLAG_CLICKS} clicks and CTR >= {FLAG_CTR:g} %): {len(bad)} domains, {sum(r['clk'] for r in bad)} of {tot_clk} clicks, "
              f"${sum(r['spent'] for r in bad):.2f} of ${tot_spent:.2f}: " + ", ".join(sorted(r["name"] for r in bad)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
