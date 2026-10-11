"""Offline checks of the spend stop-loss. No network: the report, the campaign list, pause and the
baseline file are replaced or pointed at a temporary directory.

    python3 -m unittest test_spend_stop -v
"""
import contextlib
import io
import json
import os
import tempfile
import unittest

import spend_stop as s


def boom():
    raise RuntimeError("spend not readable")


class Decide(unittest.TestCase):
    def test_limit_is_inclusive_and_only_active_campaigns_are_judged(self):
        res = {c: v for c, _, v in s.decide({1: "a", 2: "b"}, {"1": 3.0, "2": 2.99, "9": 50.0}, limit=3.0)}
        self.assertEqual(res[1], "СТОП")
        self.assertTrue(res[2].startswith("осталось"))
        self.assertNotIn(9, res)

    def test_campaign_missing_from_the_report_is_never_stopped(self):
        self.assertEqual(s.decide({5: "x"}, {}, limit=3.0), [(5, None, "нет в отчёте")])

    def test_count_starts_at_the_baseline(self):
        # lifetime 10.0 with 8.0 spent before the reset: only 2.0 is counted, under the $3 limit
        res = s.decide({1: "a"}, {"1": 10.0}, limit=3.0, baseline={"1": 8.0})
        self.assertEqual(res[0][0], 1)
        self.assertAlmostEqual(res[0][1], 2.0)
        self.assertNotEqual(res[0][2], "СТОП")
        # lifetime 10.0 with 6.0 spent before the reset: 4.0 counted, over the limit
        self.assertEqual(s.decide({1: "a"}, {"1": 10.0}, limit=3.0, baseline={"1": 6.0})[0][2], "СТОП")

    def test_campaign_created_after_the_reset_counts_all_its_spend(self):
        res = s.decide({7: "new"}, {"7": 3.2}, limit=3.0, baseline={"1": 50.0})
        self.assertEqual(res, [(7, 3.2, "СТОП")])


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.real = (s.spend_by_campaign, s.v2_campaigns, s.pause, s.ACTIONS, s.BASELINE, s.sys.argv)
        s.ACTIONS = os.path.join(self.tmp, "actions.log")
        s.BASELINE = os.path.join(self.tmp, "baseline.json")
        self.paused = []
        s.v2_campaigns = lambda fields=None: {
            1: {"name": "over", "status": {"name": "active"}},
            2: {"name": "under", "status": {"name": "active"}},
            3: {"name": "already paused", "status": {"name": "paused"}},
        }
        s.spend_by_campaign = lambda: {"1": 3.5, "2": 1.0, "3": 99.0}

        def pause(cid, on=True):
            self.paused.append(cid)
            return {"name": "paused", "reason": "clientManuallyPaused"}
        s.pause = pause

    def tearDown(self):
        (s.spend_by_campaign, s.v2_campaigns, s.pause, s.ACTIONS, s.BASELINE, s.sys.argv) = self.real

    def run_main(self, *args):
        s.sys.argv = ["spend_stop.py", *args]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = s.main()
        return rc, out.getvalue()

    def test_apply_pauses_only_active_campaigns_at_or_above_the_limit(self):
        rc, out = self.run_main("--apply")
        self.assertEqual(rc, 0)
        self.assertEqual(self.paused, [1])
        self.assertIn("СТОП", out)
        with open(s.ACTIONS) as f:
            self.assertIn("stop camp=1", f.read())

    def test_dry_run_pauses_nothing(self):
        rc, out = self.run_main()
        self.assertEqual(rc, 0)
        self.assertEqual(self.paused, [])
        self.assertIn("СТОП", out)

    def test_unreadable_spend_pauses_nothing(self):
        s.spend_by_campaign = boom
        rc, out = self.run_main("--apply")
        self.assertEqual(rc, 1)
        self.assertEqual(self.paused, [])
        self.assertIn("SPEND_ERR", out)

    def test_reset_remembers_lifetime_spend_and_pauses_nothing(self):
        rc, out = self.run_main("--reset")
        self.assertEqual(rc, 0)
        self.assertEqual(self.paused, [])
        with open(s.BASELINE) as f:
            self.assertEqual(json.load(f), {"1": 3.5, "2": 1.0, "3": 99.0})

    def test_after_reset_only_spend_since_the_reset_is_stopped(self):
        # campaign 1 had 3.5 at the reset; 0.5 more now is nowhere near $3 and must not be paused
        self.run_main("--reset")
        s.spend_by_campaign = lambda: {"1": 4.0, "2": 1.0, "3": 99.0}
        rc, out = self.run_main("--apply")
        self.assertEqual(self.paused, [])
        self.assertNotIn("СТОП", out)

    def test_reset_with_unreadable_spend_writes_nothing(self):
        s.spend_by_campaign = boom
        rc, out = self.run_main("--reset")
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(s.BASELINE))


if __name__ == "__main__":
    unittest.main()
