"""Offline checks of the policy of geozo_step.py (the ladder of target CPAs): `python3 -m unittest -v test_geozo_step`. No network."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geozo_step as gs  # noqa: E402

OK = dict(gap_h=2.0, per_hour=5, spend=0.002, clicks=3, conv=0, active=True, balance=12.0)


def decide(cur=0.12, **kw):
    return gs.decide(cur, **{**OK, **kw})


class Policy(unittest.TestCase):
    def test_weak_delivery_an_hour_after_the_last_step_doubles_the_target(self):
        self.assertEqual(decide(0.12)[0], 0.24)

    def test_never_more_than_the_ceiling(self):
        self.assertEqual(decide(0.4)[0], gs.CEILING)
        self.assertIsNone(decide(gs.CEILING)[0])

    def test_one_step_at_a_time_waits_for_the_gap(self):
        self.assertIsNone(decide(gap_h=0.5)[0])
        self.assertIsNone(decide(gap_h=None)[0])             # first sight: the clock only starts

    def test_a_geo_that_delivers_is_left_alone(self):
        self.assertIsNone(decide(per_hour=gs.WEAK_PER_H)[0])
        self.assertIsNone(decide(per_hour=1000)[0])

    def test_teasers_on_moderation_nothing_to_raise(self):
        self.assertIsNone(decide(active=False)[0])

    def test_guards(self):
        self.assertIsNone(decide(balance=gs.MIN_BALANCE - 0.01)[0])                 # the wallet is the real limit
        self.assertIsNone(decide(spend=1.5, conv=gs.MIN_CONV - 1)[0])               # money without a chain
        self.assertEqual(decide(spend=1.5, conv=gs.MIN_CONV, clicks=3000)[0], 0.24)  # the chain works: the cost is fine
        self.assertIsNone(decide(spend=0.05, clicks=4)[0])                          # a click at over a cent
        self.assertEqual(decide(spend=0.0, clicks=0)[0], 0.24)                       # no clicks at all: nothing to divide by

    def test_kazakhstan_is_left_to_the_owner(self):
        self.assertIn("KZ", gs.SKIP)

    def test_hours_back_counts_completed_moscow_hours_over_midnight(self):
        now = datetime(2026, 10, 13, 21, 30, tzinfo=timezone.utc)                  # 00:30 on 14.10 in Moscow
        self.assertEqual(gs.hours_back(now, 2), [("2026-10-13", "23"), ("2026-10-13", "22")])
        now = datetime(2026, 10, 14, 8, 55, tzinfo=timezone.utc)                   # 11:55
        self.assertEqual(gs.hours_back(now, 2), [("2026-10-14", "10"), ("2026-10-14", "9")])


if __name__ == "__main__":
    unittest.main()
