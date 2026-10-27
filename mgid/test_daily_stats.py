"""Offline checks of daily_stats: the Moscow day cut from the hourly buckets of the account's zone, and the sums. No network.

    MGID_ACCOUNT=second python3 -m unittest test_daily_stats -v
"""
import unittest
from datetime import datetime, timezone
from unittest import mock

import daily_stats as d


def row(cid, day, hour, spent, revenue=0, clicks=0, imp=0, conv=0):
    return {"campaignId": cid, "day": day, "hour": hour, "spent": {"amount": str(spent), "currency": "USD"}, "revenue": {"amount": str(revenue), "currency": "USD"},
            "clicks": clicks, "impressions": imp, "conversions": conv}


class Window(unittest.TestCase):
    def test_a_moscow_day_starts_at_21_utc_the_evening_before(self):
        lo, hi = d.msk_window("2026-10-27")
        self.assertEqual(lo, datetime(2026, 10, 26, 21, tzinfo=timezone.utc))
        self.assertEqual(hi, datetime(2026, 10, 27, 21, tzinfo=timezone.utc))

    def test_tirane_buckets_after_the_clock_change_are_utc_plus_one(self):
        self.assertEqual(d.bucket_start("2026-10-26", 22), datetime(2026, 10, 26, 21, tzinfo=timezone.utc))   # the first bucket of the Moscow 27.10
        self.assertEqual(d.bucket_start("2026-10-26", 21), datetime(2026, 10, 26, 20, tzinfo=timezone.utc))   # still 26.10 in Moscow

    def test_tirane_buckets_before_the_clock_change_are_utc_plus_two(self):
        self.assertEqual(d.bucket_start("2026-10-24", 22), datetime(2026, 10, 24, 20, tzinfo=timezone.utc))

    def test_day_rows_keep_exactly_the_moscow_day(self):
        rows = [row(1, "2026-10-26", 21, 1.0), row(1, "2026-10-26", 22, 2.0), row(1, "2026-10-27", 0, 4.0), row(1, "2026-10-27", 21, 8.0), row(1, "2026-10-27", 22, 16.0)]
        with mock.patch.object(d, "report", lambda *a, **k: rows):
            kept = d.day_rows("2026-10-27")
        self.assertEqual([x["spent"]["amount"] for x in kept], ["2.0", "4.0", "8.0"])     # 22:00 Tirane on the 27th is 00:00 Moscow on the 28th


class Sums(unittest.TestCase):
    def test_collect_sums_per_campaign_and_reads_money_objects(self):
        rows = [row(1, "2026-10-27", 1, 0.5, 0.1, 3, 100, 1), row(1, "2026-10-27", 2, 1.5, 0.0, 4, 200, 0), row(2, "2026-10-27", 1, 2.0, 0.0, 1, 50, 0)]
        s = d.collect(rows, lambda r: True)
        self.assertEqual(s[1], [300, 7, 2.0, 0.1, 1])
        self.assertEqual(s[2], [50, 1, 2.0, 0.0, 0])

    def test_table_sorts_by_spend_flags_ours_and_totals(self):
        stats = {12525146: [0, 0, 0.0, 0.0, 0], 12523608: [9590, 111, 2.27, 0.3, 3], 12523610: [10664, 103, 2.61, 0.0, 0]}
        meta = {12523608: {"name": "AZ | BeeFlex Forte (aff 824)", "status": {"name": "active"}, "bidding": {"price": 1.2}}}
        lines, tot = d.table(stats, meta)
        self.assertEqual([x[0].split("[")[1] for x in lines], ["12523610]", "12523608]", "12525146]"])
        self.assertEqual([x[1] for x in lines], ["не наша", "не наша", "наша"])
        self.assertEqual(lines[1][8], round(0.3 - 2.27, 2))
        self.assertEqual(tot["всего"][2], 4.88)
        self.assertEqual(tot["наши"][2], 0.0)


if __name__ == "__main__":
    unittest.main()
