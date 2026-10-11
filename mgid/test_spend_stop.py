"""Offline checks of the spend stop-loss. No network: the report, the campaign list and pause are replaced.

    python3 -m unittest test_spend_stop -v
"""
import contextlib
import io
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


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.real = (s.spend_by_campaign, s.v2_campaigns, s.pause, s.ACTIONS, s.sys.argv)
        s.ACTIONS = os.path.join(self.tmp, "actions.log")
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
        s.spend_by_campaign, s.v2_campaigns, s.pause, s.ACTIONS, s.sys.argv = self.real

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


if __name__ == "__main__":
    unittest.main()
