"""Offline checks of the offer window. No network: the campaign list, the spend, pause and the baseline are replaced.

    python3 -m unittest test_offer_window -v
"""
import contextlib
import io
import os
import tempfile
import unittest
from datetime import datetime, timezone

import offer_window as w


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


class Window(unittest.TestCase):
    def test_open_from_8_to_21_eastern_on_weekdays(self):
        self.assertFalse(w.in_window(utc(2026, 10, 21, 11, 59)))      # Wed 07:59 EDT
        self.assertTrue(w.in_window(utc(2026, 10, 21, 12, 0)))        # Wed 08:00 EDT
        self.assertTrue(w.in_window(utc(2026, 10, 22, 0, 59)))        # Wed 20:59 EDT, already Thursday in UTC
        self.assertFalse(w.in_window(utc(2026, 10, 22, 1, 0)))        # Wed 21:00 EDT
        self.assertTrue(w.in_window(utc(2026, 10, 24, 0, 30)))        # Fri 20:30 EDT, already Saturday in UTC
        self.assertFalse(w.in_window(utc(2026, 10, 24, 16, 0)))       # Saturday
        self.assertFalse(w.in_window(utc(2026, 10, 25, 16, 0)))       # Sunday

    def test_the_change_to_winter_time_moves_the_utc_edges(self):
        self.assertFalse(w.in_window(utc(2026, 11, 2, 12, 59)))       # Mon 07:59 EST
        self.assertTrue(w.in_window(utc(2026, 11, 2, 13, 0)))         # Mon 08:00 EST


ROWS = {
    1: {"name": "paused by us", "status": {"name": "paused", "reason": "clientManuallyPaused"}},
    2: {"name": "running", "status": {"name": "active", "reason": "fulfilled"}},
    3: {"name": "no funds", "status": {"name": "paused", "reason": "outOfClientFunds"}},
    4: {"name": "held by the stop-loss", "status": {"name": "paused", "reason": "clientManuallyPaused"}},
}
SPEND = {"1": 1.0, "2": 9.0, "3": 0.0, "4": 12.0}


def verdicts(want, camps=(1, 2, 3, 4, 9), spend=SPEND, baseline=None, limit=3.0):
    return {c: a for c, a, _ in w.decide(list(camps), ROWS, want, spend, baseline or {}, limit)}


class Decide(unittest.TestCase):
    def test_inside_the_window_only_our_pause_under_the_limit_is_started(self):
        v = verdicts(True)
        self.assertEqual(v[1], "start")
        self.assertIsNone(v[2])            # already running
        self.assertIsNone(v[3])            # not our pause
        self.assertIsNone(v[4])            # spend since the reset is over the limit: the stop-loss holds it
        self.assertIsNone(v[9])            # not in the account

    def test_the_baseline_gives_a_campaign_a_new_budget(self):
        self.assertEqual(verdicts(True, baseline={"4": 10.0})[4], "start")             # 2.0 counted
        self.assertIsNone(verdicts(True, baseline={"4": 8.0})[4])                      # 4.0 counted

    def test_outside_the_window_everything_that_runs_is_paused(self):
        v = verdicts(False)
        self.assertEqual(v[2], "pause")
        self.assertIsNone(v[1])
        self.assertIsNone(v[3])
        self.assertIsNone(v[4])

    def test_unreadable_spend_starts_nothing_but_still_pauses(self):
        self.assertIsNone(verdicts(True, spend=None)[1])
        self.assertEqual(verdicts(False, spend=None)[2], "pause")


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.real = (w.v2_campaigns, w.pause, w.spend_stop.spend_by_campaign, w.spend_stop.load_baseline, w.ACTIONS, w.CAMPS, w.sys.argv)
        w.ACTIONS = os.path.join(self.tmp, "actions.log")
        w.CAMPS = [1, 2]
        w.v2_campaigns = lambda fields=None: ROWS
        w.spend_stop.spend_by_campaign = lambda: SPEND
        w.spend_stop.load_baseline = lambda: {}
        self.calls = []

        def pause(cid, on=True):
            self.calls.append((cid, on))
            return {"name": "paused" if on else "active", "reason": "clientManuallyPaused" if on else "fulfilled"}
        w.pause = pause

    def tearDown(self):
        (w.v2_campaigns, w.pause, w.spend_stop.spend_by_campaign, w.spend_stop.load_baseline, w.ACTIONS, w.CAMPS, w.sys.argv) = self.real

    def run_at(self, at, *flags):
        w.sys.argv = ["offer_window.py", *flags]
        with contextlib.redirect_stdout(io.StringIO()):
            return w.main(at)

    def test_dry_run_changes_nothing(self):
        self.assertEqual(self.run_at(utc(2026, 10, 21, 12, 5)), 0)
        self.assertEqual(self.calls, [])

    def test_apply_in_the_window_starts_the_paused_one(self):
        self.assertEqual(self.run_at(utc(2026, 10, 21, 12, 5), "--apply"), 0)
        self.assertEqual(self.calls, [(1, False)])
        with open(w.ACTIONS) as f:
            self.assertIn("start camp=1", f.read())

    def test_apply_after_the_close_pauses_the_running_one(self):
        self.assertEqual(self.run_at(utc(2026, 10, 22, 1, 5), "--apply"), 0)
        self.assertEqual(self.calls, [(2, True)])

    def test_a_start_that_does_not_stick_is_reported(self):
        w.pause = lambda cid, on=True: {"name": "paused", "reason": "clientManuallyPaused"}
        self.assertEqual(self.run_at(utc(2026, 10, 21, 12, 5), "--apply"), 1)

    def test_an_empty_list_manages_nothing(self):
        w.CAMPS = []
        self.assertEqual(self.run_at(utc(2026, 10, 21, 12, 5), "--apply"), 1)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
