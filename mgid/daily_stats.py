"""Statistics of every campaign of the second account for a Moscow day: spend, revenue, profit, as a spreadsheet.

    MGID_ACCOUNT=second python3 daily_stats.py --out stats.xlsx                       # today (Moscow), and the totals since SINCE
    MGID_ACCOUNT=second python3 daily_stats.py --day 2026-10-27 --since 2026-10-25 --out stats.xlsx
    ... --out stats.csv                                                               # the "today" sheet as CSV

Owner, 27.10: «прислать сегодняшнюю статистику всех кампаний расход доход».

- "Day" is the Moscow day (the owner reads in MSK). The v2 report returns whole days of the account's zone (Europe/Tirane: UTC+2 until 25.10, UTC+1 after), so the
  day is cut from the hourly buckets: a bucket counts when its start, converted to UTC, lies in [00:00 MSK of the day, 00:00 MSK of the next day).
- Revenue is the metric `revenue` of the v2 report: what the postbacks of the partners reported to MGID with each conversion (the `r=` value), not the partner's own
  books (holds, rejections and approvals that happen later are not in it). Profit is revenue minus spend. The campaigns that other chats created are listed too, flagged;
  their real revenue is in their partner's cabinet.
- Metrics probed 27.10: `revenue`, `profit`, `conversions`, `conversionsDecision`, `conversionsInterest`, `ctr`, `cpc`, `cpm` are valid; `roi`, `cpa` are not.
"""
import argparse
import csv
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgid_api import _num, report, v2_campaigns  # noqa: E402

MSK = ZoneInfo("Europe/Moscow")
TIRANE = ZoneInfo("Europe/Tirane")
METRICS = ("impressions", "clicks", "spent", "revenue", "conversions")

# Created by this session (skills/mgid, §4): the 1537 tests, the eight nutra copies, the nine Aray campaigns. Everything else on the account is somebody else's.
OURS = {12468751, 12468752, 12520626, 12520627, *range(12520656, 12520664), *range(12525146, 12525155)}

HEAD = ("Кампания", "Чья", "Статус", "Ставка $", "Показы", "Клики", "Расход $", "Доход $", "Прибыль $", "Конверсии")


def msk_window(day):
    """[start, end) of the Moscow day `day` ('YYYY-MM-DD') in UTC."""
    d = date.fromisoformat(day)
    start = datetime(d.year, d.month, d.day, tzinfo=MSK).astimezone(timezone.utc)
    return start, start + timedelta(days=1)


def bucket_start(day, hour):
    """UTC start of a report bucket: `day` is a date of the account's zone (Tirane), `hour` its hour of the day."""
    d = date.fromisoformat(str(day)[:10])
    return datetime(d.year, d.month, d.day, int(_num(hour)), tzinfo=TIRANE).astimezone(timezone.utc)


def collect(rows, keep):
    """{campaign id: [impressions, clicks, spent, revenue, conversions]} of the rows that `keep(row)` accepts."""
    out = {}
    for r in rows:
        if not keep(r):
            continue
        v = out.setdefault(int(r["campaignId"]), [0, 0, 0.0, 0.0, 0])
        v[0] += int(_num(r.get("impressions")))
        v[1] += int(_num(r.get("clicks")))
        v[2] += _num(r.get("spent"))
        v[3] += _num(r.get("revenue"))
        v[4] += int(_num(r.get("conversions")))
    return out


def day_rows(day):
    """Hourly rows of the Moscow day `day`, cut to the day."""
    lo, hi = msk_window(day)
    rows = report(day, day, METRICS, ("campaignId", "day", "hour"))
    return [r for r in rows if lo <= bucket_start(r["day"], r["hour"]) < hi]


def since_rows(since, day):
    """Daily rows from the account's date `since` through the Moscow day `day`."""
    return [r for r in report(since, day, METRICS, ("campaignId", "day")) if str(r["day"])[:10] >= since]


def table(stats, meta):
    """Rows for a sheet, the biggest spend first, and the totals {ours, others, all}."""
    lines, tot = [], {"наши": [0, 0, 0.0, 0.0, 0], "не наши": [0, 0, 0.0, 0.0, 0]}
    for cid, v in sorted(stats.items(), key=lambda kv: -kv[1][2]):
        m = meta.get(cid) or {}
        who = "наша" if cid in OURS else "не наша"
        bid = (m.get("bidding") or {}).get("price")
        lines.append((f"{m.get('name') or cid} [{cid}]", who, (m.get("status") or {}).get("name") or "?", bid, v[0], v[1], round(v[2], 2), round(v[3], 2),
                      round(v[3] - v[2], 2), v[4]))
        t = tot["наши" if cid in OURS else "не наши"]
        for i in range(5):
            t[i] += v[i]
    tot["всего"] = [a + b for a, b in zip(tot["наши"], tot["не наши"])]
    return lines, tot


def total_line(label, t):
    return (label, "", "", None, t[0], t[1], round(t[2], 2), round(t[3], 2), round(t[3] - t[2], 2), t[4])


def write_xlsx(path, sheets, notes):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    wb.remove(wb.active)
    for title, (lines, tot) in sheets:
        ws = wb.create_sheet(title[:31])
        ws.append(HEAD)
        for c in ws[1]:
            c.font = Font(bold=True)
            c.fill = PatternFill("solid", fgColor="DDDDDD")
            c.alignment = Alignment(wrap_text=True, vertical="center")
        for ln in lines:
            ws.append(ln)
        for label in ("наши", "не наши", "всего"):
            ws.append(total_line("ИТОГО " + label, tot[label]))
            for c in ws[ws.max_row]:
                c.font = Font(bold=True)
        for col, w in zip("ABCDEFGHIJ", (58, 9, 10, 9, 9, 8, 10, 10, 11, 10)):
            ws.column_dimensions[col].width = w
        for row in ws.iter_rows(min_row=2, min_col=7, max_col=9):
            for c in row:
                c.number_format = "0.00"
        ws.freeze_panes = "B2"
    ws = wb.create_sheet("Пояснения")
    for n in notes:
        ws.append([n])
    ws.column_dimensions["A"].width = 140
    for row in ws.iter_rows():
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(path)


def main():
    ap = argparse.ArgumentParser()
    today = datetime.now(MSK).date().isoformat()
    ap.add_argument("--day", default=today, help="Moscow day, default today")
    ap.add_argument("--since", default=None, help="account date for the second sheet, default: the day before --day minus 2")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    since = a.since or (date.fromisoformat(a.day) - timedelta(days=2)).isoformat()
    meta = v2_campaigns(("name", "status", "bidding"))
    day_stats = collect(day_rows(a.day), lambda r: True)
    since_stats = collect(since_rows(since, a.day), lambda r: True)
    sheets = [(f"День {a.day} (МСК)", table(day_stats, meta)), (f"С {since}", table(since_stats, meta))]
    now = datetime.now(MSK).strftime("%d.%m.%Y %H:%M МСК")
    notes = [
        f"Выгрузка {now}. Лист «День»: московские сутки {a.day} (00:00 МСК до момента выгрузки), собраны из часовых данных MGID (его бакеты в зоне аккаунта, Europe/Tirane).",
        f"Лист «С {since}»: суммы по датам аккаунта (Тирана) от {since} до сегодня.",
        "Доход: метрика revenue отчёта MGID, то есть сумма, которую партнёрка передала постбеком вместе с конверсией. Это не бухгалтерия партнёрки: подтверждения, холд и отклонения, которые случаются позже, сюда не попадают.",
        "Прибыль = доход минус расход. Конверсии: все конверсии по целям кампании.",
        "«Чья»: «наша» это кампании, созданные в этом чате (тесты 1537, восемь нутра-копий, девять офферов Aray); «не наша» создал другой чат или владелец вручную. Их настоящую выручку показывает их партнёрка, у нас доступа к ней нет.",
        "Ставка: целевая цена конверсии (CPA tune) на момент выгрузки. Статус на момент выгрузки.",
    ]
    if a.out.endswith(".csv"):
        with open(a.out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(HEAD)
            lines, tot = sheets[0][1]
            w.writerows(lines)
            for label in ("наши", "не наши", "всего"):
                w.writerow(total_line("ИТОГО " + label, tot[label]))
    else:
        write_xlsx(a.out, sheets, notes)
    for title, (lines, tot) in sheets:
        t = tot["всего"]
        print(f"{title}: кампаний {len(lines)}, показы {t[0]}, клики {t[1]}, расход {t[2]:.2f}, доход {t[3]:.2f}, прибыль {t[3] - t[2]:.2f}, конверсий {t[4]}")
        for label in ("наши", "не наши"):
            u = tot[label]
            print(f"   {label}: расход {u[2]:.2f}, доход {u[3]:.2f}, конверсий {u[4]}")


if __name__ == "__main__":
    main()
