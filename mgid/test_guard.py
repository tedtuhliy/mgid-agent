"""Offline check of the 2 x CPA rule. No network: the API calls are replaced, the middleware table is
a throw-away sqlite file.

    python3 -m unittest test_guard -v
"""
import io
import os
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout

import mgid_guard as g


def make_db(path, leads=(), nosrc=()):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE mgid_leads (tx TEXT, cid TEXT, payout REAL, cur TEXT, usd REAL, camp TEXT, "
                "widget TEXT, status TEXT, resp TEXT, ts TEXT)")
    con.execute("CREATE TABLE mgid_nosrc (tx TEXT, ts TEXT)")
    for camp, widget, ts in leads:
        con.execute("INSERT INTO mgid_leads (camp, widget, ts) VALUES (?,?,?)", (camp, widget, ts))
    for tx, ts in nosrc:
        con.execute("INSERT INTO mgid_nosrc (tx, ts) VALUES (?,?)", (tx, ts))
    con.commit()
    con.close()


class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        g.STATE = os.path.join(self.tmp, "state.json")
        g.ACTIONS = os.path.join(self.tmp, "actions.log")
        g.DB = os.path.join(self.tmp, "m.db")
        self.blocked = {}          # blacklist of a campaign, or its whitelist when ftype is "only"
        self.ftype = {}
        self.spend = {}
        self.rows = {}
        self.paused = []
        self.unlisted = []
        g.SINCE = "2026-10-01"       # the lead dates below sit inside this window; the window tests set their own
        self.asked_since = []        # `since` the guard passed to widget_spend
        g.v2_campaigns = lambda: self.rows
        g.v1_conversion = lambda cid: (None, None)

        def widget_spend(cid, since=None):
            self.asked_since.append(since)
            return self.spend[cid]
        g.widget_spend = widget_spend
        g.blacklist = lambda cid: (set(self.blocked.get(cid, ())), self.ftype.get(cid, "except"))
        g.widgets_filter = lambda cid: (self.ftype.get(cid, "except"),
                                        {w: [] for w in self.blocked.get(cid, ())})
        g.report = lambda *a, **k: []

        def block(cid, uids):
            self.blocked.setdefault(cid, set()).update(uids)
            return 200, {"id": cid}
        g.block = block

        def whitelist_remove(cid, uids):
            self.unlisted.append((cid, sorted(uids)))
            self.blocked[cid] = self.blocked.get(cid, set()) - set(uids)
            return 204, {}
        g.whitelist_remove = whitelist_remove

        def pause(cid, on=True):
            self.paused.append(cid)
            return {"name": "paused", "reason": "clientManuallyPaused"}
        g.pause = pause

    def camp(self, cid, name, cpa, status="active", target=g.TARGET, strategy="targetCpa", price=None):
        buy = {"targetId": target, "deduplicateConversions": True}
        if cpa is not None:
            buy["conversionValue"] = cpa
        self.rows[cid] = {"name": name, "status": {"name": status},
                          "bidding": {"strategy": strategy, "price": price if price is not None else cpa or 0.045},
                          "conversionTracking": {"type": "sensors", "buyStage": buy} if target else None}

    def run_guard(self, apply=True):
        g.sys.argv = ["mgid_guard.py"] + (["--apply"] if apply else [])
        out = io.StringIO()
        with redirect_stdout(out):
            g.main()
        return out.getvalue()

    def test_threshold_is_two_conversion_costs_of_each_campaign(self):
        make_db(g.DB)
        self.camp(1, "KZ", 0.56)
        self.camp(2, "EE", 1.48)
        # the same $1.20 placement: over 2 x 0.56 = 1.12 in KZ, under 2 x 1.48 = 2.96 in EE
        self.spend = {1: {"100": (80, 1.20), "101": (10, 1.11)}, 2: {"100": (80, 1.20)}}
        self.run_guard()
        self.assertEqual(self.blocked, {1: {"100"}})

    def test_exactly_two_costs_is_blocked(self):
        make_db(g.DB)
        self.camp(1, "LV", 0.32)
        self.spend = {1: {"7": (50, 0.64)}}
        self.run_guard()
        self.assertEqual(self.blocked, {1: {"7"}})

    def test_placement_with_a_lead_is_kept(self):
        make_db(g.DB, leads=[("1", "58022244", "2026-10-11 10:00:00")])
        self.camp(1, "KZ", 0.56)
        self.spend = {1: {"58022244s1151239714": (900, 9.0), "5": (900, 9.0)}}   # sub-source key, same widget
        self.run_guard()
        self.assertEqual(self.blocked, {1: {"5"}})

    def test_lead_of_another_campaign_does_not_protect(self):
        make_db(g.DB, leads=[("2", "5", "2026-10-11 10:00:00")])
        self.camp(1, "KZ", 0.56)
        self.spend = {1: {"5": (90, 3.0)}}
        self.run_guard()
        self.assertEqual(self.blocked, {1: {"5"}})

    def test_paused_and_foreign_campaigns_are_not_judged(self):
        make_db(g.DB)
        self.camp(1, "paused", 0.56, status="paused")
        self.camp(2, "garlic", 0.5, target=999)
        self.camp(3, "manual", 0.44, strategy="manualBidding")
        self.spend = {1: {"5": (90, 9.0)}, 2: {"5": (90, 9.0)}, 3: {"5": (90, 9.0)}}
        self.run_guard()
        self.assertEqual(self.blocked, {3: {"5"}})

    def test_campaign_without_cost_uses_the_flat_threshold_and_says_so(self):
        make_db(g.DB)
        self.camp(1, "nocost", None, strategy="manualBidding")
        self.spend = {1: {"5": (10, 0.31), "6": (10, 0.29)}}
        out = self.run_guard()
        self.assertEqual(self.blocked, {1: {"5"}})
        self.assertIn("MGIDG_NOCPA", out)

    def test_unreadable_target_of_a_cpa_campaign_is_still_watched_with_its_bid(self):
        make_db(g.DB)
        self.camp(1, "lag", None, target=None, strategy="targetCpa", price=0.50)
        self.rows[1]["conversionTracking"] = None       # v2 reads null right after a write
        self.spend = {1: {"5": (40, 1.00), "6": (40, 0.99)}}
        self.run_guard()
        self.assertEqual(self.blocked, {1: {"5"}})

    def test_hold_when_a_lead_came_without_source(self):
        make_db(g.DB, leads=[("1", "9", "2026-10-11 10:00:00")],
                nosrc=[("35_5084_8394_c655cd2e24e4125fa4edd915145e834e", "2026-10-11 12:00:00")])
        self.camp(1, "KZ", 0.56)
        self.spend = {1: {"5": (90, 9.0)}}
        out = self.run_guard()
        self.assertEqual(self.blocked, {})
        self.assertIn("MGIDG_HOLD", out)

    def test_sourceless_lead_of_another_offer_is_not_a_hold(self):
        # the real case: smartlink 16588 pays through the same postback with no source, from other
        # buys, and held the deployed guard from 01.10 to 10.10
        make_db(g.DB, leads=[("1", "9", "2026-10-01 12:58:16")],
                nosrc=[("34_5084_16588_7a4a7fa3d7e85c300e1a6a27bf6fe104", "2026-10-10 07:21:03")])
        self.camp(1, "KZ", 0.56)
        self.spend = {1: {"5": (90, 9.0)}}
        out = self.run_guard()
        self.assertEqual(self.blocked, {1: {"5"}})
        self.assertNotIn("MGIDG_HOLD", out)

    def test_sourceless_lead_with_unreadable_offer_still_holds(self):
        make_db(g.DB, leads=[("1", "9", "2026-10-11 10:00:00")], nosrc=[("weird", "2026-10-11 12:00:00")])
        self.camp(1, "KZ", 0.56)
        self.spend = {1: {"5": (90, 9.0)}}
        self.assertIn("MGIDG_HOLD", self.run_guard())
        self.assertEqual(self.blocked, {})

    def test_hold_when_the_middleware_tables_are_unreadable(self):
        self.camp(1, "KZ", 0.56)
        self.spend = {1: {"5": (90, 9.0)}}
        g.DB = os.path.join(self.tmp, "missing.db")
        self.run_guard()
        self.assertEqual(self.blocked, {})

    def test_dry_run_changes_nothing(self):
        make_db(g.DB)
        self.camp(1, "KZ", 0.56)
        self.spend = {1: {"5": (90, 9.0)}}
        out = self.run_guard(apply=False)
        self.assertEqual(self.blocked, {})
        self.assertIn("<- в блок", out)

    def test_already_blocked_is_not_sent_again(self):
        make_db(g.DB)
        self.camp(1, "KZ", 0.56)
        self.blocked = {1: {"5"}}
        self.spend = {1: {"5": (90, 9.0)}}
        calls = []
        real = g.block
        g.block = lambda cid, uids: calls.append(uids) or real(cid, uids)
        self.run_guard()
        self.assertEqual(calls, [])


    def test_whitelist_placement_that_spent_two_costs_without_lead_is_unlisted(self):
        make_db(g.DB)
        self.camp(1, "CIS wl", 0.44)
        self.ftype[1] = "only"
        self.blocked[1] = {"57628091", "64349629"}
        self.spend = {1: {"57628091": (60, 0.95), "64349629": (5, 0.10)}}    # 2 x 0.44 = 0.88
        self.run_guard()
        self.assertEqual(self.unlisted, [(1, ["57628091"])])
        self.assertEqual(self.blocked[1], {"64349629"})
        self.assertEqual(self.paused, [])

    def test_whitelist_placement_with_a_lead_of_this_campaign_stays(self):
        make_db(g.DB, leads=[("1", "57628091", "2026-10-11 10:00:00")])
        self.camp(1, "CIS wl", 0.44)
        self.ftype[1] = "only"
        self.blocked[1] = {"57628091"}
        self.spend = {1: {"57628091": (60, 0.95)}}
        self.run_guard()
        self.assertEqual(self.unlisted, [])

    def test_a_lead_of_another_campaign_does_not_keep_a_whitelist_placement(self):
        make_db(g.DB, leads=[("2", "57628091", "2026-10-11 10:00:00")])
        self.camp(1, "CIS wl", 0.44)
        self.ftype[1] = "only"
        self.blocked[1] = {"57628091", "64349629"}     # a second one keeps the list from emptying
        self.spend = {1: {"57628091": (60, 0.95), "64349629": (5, 0.10)}}
        self.run_guard()
        self.assertEqual(self.unlisted, [(1, ["57628091"])])
        self.assertEqual(self.paused, [])

    def test_emptied_whitelist_pauses_the_campaign_and_removes_nothing(self):
        make_db(g.DB)
        self.camp(1, "LATAM wl", 0.62)
        self.ftype[1] = "only"
        self.blocked[1] = {"5"}
        self.spend = {1: {"5": (300, 1.30)}}                                  # 2 x 0.62 = 1.24
        self.run_guard()
        self.assertEqual(self.unlisted, [])
        self.assertEqual(self.paused, [1])

    def test_spend_off_the_whitelist_is_warned_and_not_touched(self):
        make_db(g.DB)
        self.camp(1, "CIS wl", 0.44)
        self.ftype[1] = "only"
        self.blocked[1] = {"7", "8"}
        self.spend = {1: {"7": (5, 0.02), "99": (100, 2.0)}}
        out = self.run_guard()
        self.assertIn("MGIDG_WARN", out)
        self.assertEqual(self.unlisted, [])
        self.assertEqual(self.paused, [])

    def test_whitelist_dry_run_changes_nothing(self):
        make_db(g.DB)
        self.camp(1, "CIS wl", 0.44)
        self.ftype[1] = "only"
        self.blocked[1] = {"57628091", "64349629"}
        self.spend = {1: {"57628091": (60, 0.95)}}
        out = self.run_guard(apply=False)
        self.assertEqual(self.unlisted, [])
        self.assertEqual(self.paused, [])
        self.assertIn("<- в блок", out)

    # --- the statistics window (MGID_GUARD_SINCE) ----------------------------------------------

    def test_window_starts_at_midnight_of_the_mgid_day(self):
        g.SINCE = "2026-10-12"
        self.assertEqual(g.since_utc(), "2026-10-11 21:00:00")        # an MGID day is UTC+3

    def test_spend_is_asked_for_from_the_window_start(self):
        g.SINCE = "2026-10-12"
        make_db(g.DB)
        self.camp(1, "KZ", 0.56)
        self.spend = {1: {}}
        self.run_guard()
        self.assertEqual(self.asked_since, ["2026-10-12"])

    def test_mgid_conversions_are_asked_for_from_the_window_start(self):
        g.SINCE = "2026-10-12"
        make_db(g.DB)
        self.camp(1, "KZ", 0.56)
        self.spend = {1: {}}
        asked = []
        g.report = lambda frm, *a, **k: asked.append(frm) or []
        self.run_guard()
        self.assertEqual(asked, ["2026-10-12"])

    def test_lead_before_the_window_does_not_protect_a_placement(self):
        # 12.10 00:00 MSK is 11.10 21:00 UTC: the first lead is a second too old, the second is in
        g.SINCE = "2026-10-12"
        make_db(g.DB, leads=[("1", "5", "2026-10-11 20:59:59"), ("1", "6", "2026-10-11 21:00:00")])
        self.camp(1, "KZ", 0.56)
        self.spend = {1: {"5": (90, 9.0), "6": (90, 9.0)}}
        self.run_guard()
        self.assertEqual(self.blocked, {1: {"5"}})

    def test_hold_still_compares_with_the_newest_placed_lead_of_all_time(self):
        # a placed lead from before the window and a lead without source after it: the UTM may have broken
        g.SINCE = "2026-10-12"
        make_db(g.DB, leads=[("1", "9", "2026-10-01 10:00:00")],
                nosrc=[("35_5084_8394_c655cd2e24e4125fa4edd915145e834e", "2026-10-12 12:00:00")])
        self.camp(1, "KZ", 0.56)
        self.spend = {1: {"5": (90, 9.0)}}
        self.assertIn("MGIDG_HOLD", self.run_guard())
        self.assertEqual(self.blocked, {})

    def test_state_records_the_window(self):
        g.SINCE = "2026-10-12"
        make_db(g.DB)
        self.camp(1, "KZ", 0.56)
        self.spend = {1: {}}
        self.run_guard()
        with open(g.STATE) as f:
            self.assertEqual(g.json.load(f)["since"], "2026-10-12")


if __name__ == "__main__":
    unittest.main()
