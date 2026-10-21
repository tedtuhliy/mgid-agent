"""Offline checks of the CPA tune ladder. No network: the campaign list, the click report, the teasers, the PATCH and the state file are replaced.

    python3 -m unittest test_cpa_ladder -v
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import cpa_ladder as c


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


T0 = utc(2026, 10, 21, 13, 7)                    # Wed 09:07 EDT, inside the window
ENTRY = {"t": T0.isoformat(), "clicks": 1925, "price": 0.5}


class Decide(unittest.TestCase):
    def test_first_look_only_takes_a_snapshot(self):
        act, new, _ = c.decide(None, T0, 1925, 0.5, True)
        self.assertEqual((act, new["clicks"], new["price"]), ("seed", 1925, 0.5))

    def test_less_than_an_hour_waits_and_keeps_the_old_entry(self):
        act, new, _ = c.decide(ENTRY, T0 + timedelta(minutes=54), 1930, 0.5, True)
        self.assertEqual(act, "wait")
        self.assertEqual(new, ENTRY)

    def test_an_hour_without_clicks_raises_by_a_step(self):
        act, new, _ = c.decide(ENTRY, T0 + timedelta(minutes=60), 1925, 0.5, True)
        self.assertEqual((act, new["price"], new["clicks"]), ("raise", 1.0, 1925))
        self.assertEqual(new["t"], (T0 + timedelta(minutes=60)).isoformat())

    def test_rate_is_per_hour_so_a_longer_gap_does_not_inflate_it(self):
        # 11 clicks in 70 minutes = 9.4 an hour: still under the goal of 10
        self.assertEqual(c.decide(ENTRY, T0 + timedelta(minutes=70), 1936, 0.5, True)[0], "raise")
        # 12 in 70 minutes = 10.3 an hour
        self.assertEqual(c.decide(ENTRY, T0 + timedelta(minutes=70), 1937, 0.5, True)[0], "hold")

    def test_goal_reached_holds_and_never_lowers(self):
        act, new, _ = c.decide(ENTRY, T0 + timedelta(minutes=60), 1945, 0.5, True)
        self.assertEqual((act, new["price"]), ("hold", 0.5))

    def test_the_ceiling_stops_the_climb(self):
        e = {"t": T0.isoformat(), "clicks": 0, "price": 5.0}
        act, new, _ = c.decide(e, T0 + timedelta(minutes=60), 0, 5.0, True)
        self.assertEqual((act, new["price"]), ("cap", 5.0))

    def test_a_campaign_that_cannot_deliver_never_raises(self):
        self.assertEqual(c.decide(ENTRY, T0 + timedelta(minutes=60), 1925, 0.5, False)[0], "renew")

    def test_a_closed_window_never_raises(self):
        self.assertEqual(c.decide(ENTRY, utc(2026, 10, 22, 1, 7), 1925, 0.5, True)[0], "renew")       # Wed 21:07 EDT
        self.assertEqual(c.decide(ENTRY, utc(2026, 10, 24, 16, 7), 1925, 0.5, True)[0], "renew")      # Saturday

    def test_a_look_from_the_day_before_is_renewed_not_judged(self):
        old = {"t": utc(2026, 10, 20, 19, 7).isoformat(), "clicks": 1000, "price": 0.5}
        self.assertEqual(c.decide(old, utc(2026, 10, 21, 13, 7), 1000, 0.5, True)[0], "renew")


ROWS = {1: {"name": "e", "status": {"name": "active"}, "bidding": {"strategy": "targetCpa", "price": 0.5}},
        2: {"name": "f", "status": {"name": "paused"}, "bidding": {"strategy": "targetCpa", "price": 0.5}}}


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.real = (c.v2_campaigns, c.clicks_by_campaign, c.active_teasers, c.call, c.STATE, c.ACTIONS, c.CAMPS, c.sys.argv)
        c.STATE, c.ACTIONS, c.CAMPS = os.path.join(self.tmp, "state.json"), os.path.join(self.tmp, "actions.log"), [1, 2]
        self.rows = {k: dict(v, bidding=dict(v["bidding"])) for k, v in ROWS.items()}
        c.v2_campaigns = lambda fields=None: self.rows
        c.clicks_by_campaign = lambda: {"1": 1925, "2": 1825}
        c.active_teasers = lambda cid: 8
        self.patches = []
        self.stick = True

        def call(method, url, body=None, form=False, timeout=90):
            self.patches.append((url.rsplit("/", 1)[-1], body))
            if self.stick:
                self.rows[int(url.rsplit("/", 1)[-1])]["bidding"]["price"] = body["bidding"]["price"]
            return 204, None
        c.call = call
        with open(c.STATE, "w") as f:
            json.dump({"1": ENTRY, "2": dict(ENTRY, t=(T0 + timedelta(minutes=50)).isoformat())}, f)

    def tearDown(self):
        (c.v2_campaigns, c.clicks_by_campaign, c.active_teasers, c.call, c.STATE, c.ACTIONS, c.CAMPS, c.sys.argv) = self.real

    def run_at(self, at, *flags):
        c.sys.argv = ["cpa_ladder.py", *flags]
        with contextlib.redirect_stdout(io.StringIO()):
            return c.main(at)

    def state(self):
        with open(c.STATE) as f:
            return json.load(f)

    def test_dry_run_changes_nothing(self):
        self.assertEqual(self.run_at(T0 + timedelta(minutes=61)), 0)
        self.assertEqual(self.patches, [])
        self.assertEqual(self.state()["1"], ENTRY)

    def test_apply_raises_the_one_with_no_clicks_and_leaves_the_paused_one(self):
        self.assertEqual(self.run_at(T0 + timedelta(minutes=61), "--apply"), 0)
        self.assertEqual(self.patches, [("1", {"bidding": {"strategy": "targetCpa", "price": 1.0}})])
        self.assertEqual(self.state()["1"]["price"], 1.0)
        self.assertEqual(self.state()["2"]["clicks"], 1825)          # not active: renewed, not judged
        with open(c.ACTIONS) as f:
            self.assertIn("raise camp=1 0.50 -> 1.00", f.read())

    def test_a_raise_that_does_not_stick_leaves_the_state_alone(self):
        self.stick = False
        self.assertEqual(self.run_at(T0 + timedelta(minutes=61), "--apply"), 1)
        self.assertEqual(self.state()["1"], ENTRY)

    def test_an_empty_list_manages_nothing(self):
        c.CAMPS = []
        self.assertEqual(self.run_at(T0 + timedelta(minutes=61), "--apply"), 1)


if __name__ == "__main__":
    unittest.main()
