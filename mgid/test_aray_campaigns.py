"""Offline checks of the Aray campaigns: the link, the campaign body, the value of a lead, the data file. No network.

    MGID_ACCOUNT=second python3 -m unittest test_aray_campaigns -v
"""
import unittest
from unittest import mock

import aray_campaigns as a

CARD = "https://uh76404db1uh.cpa-gate.pro/?target=AbC-dEf_123&al=9128&ap=9130"
BY_ID = {o["aray_id"]: o for o in a.DATA["offers"]}


class Links(unittest.TestCase):
    def test_lander_is_replaced_and_the_prelander_switched_off(self):
        u = a.link(BY_ID[3959], CARD)
        self.assertEqual(u, "https://uh76404db1uh.cpa-gate.pro/?target=AbC-dEf_123&al=9124&ap=-1&subid={click_id}&subacc={widget_id}&subacc2={teaser_id}")

    def test_offer_without_a_saved_prelander_gets_no_ap(self):
        u = a.link(BY_ID[4840], "https://uh76404db1uh.cpa-gate.pro/?target=AbC-dEf_123&al=10092")
        self.assertNotIn("ap=", u)
        self.assertIn("al=10092", u)

    def test_the_macros_of_mgid_keep_their_braces(self):
        for o in a.DATA["offers"]:
            if o.get("land"):
                self.assertTrue(a.link(o, CARD).endswith("&subid={click_id}&subacc={widget_id}&subacc2={teaser_id}"))


class Body(unittest.TestCase):
    def test_value_of_a_lead_is_payout_times_approval(self):
        self.assertEqual(a.ev(BY_ID[4047]), 5.06)      # 11 x 46 %
        self.assertEqual(a.ev(BY_ID[4840]), 3.9)       # 13 x 30 %
        self.assertEqual(a.ev(BY_ID[4081]), 1.93)      # 5.5 x 35 %

    def test_campaign_is_product_cpa_tune_paused_by_us_and_not_auto_launched(self):
        for o in a.DATA["offers"]:
            b = a.body(o)
            self.assertEqual(b["type"], "product")
            self.assertEqual(b["bidding"], {"strategy": "targetCpa", "price": 0.05})
            self.assertFalse(b["isAutoLaunchAdsAfterApproval"])
            self.assertEqual(b["conversionTracking"]["buyStage"]["targetId"], 1278025)
            self.assertEqual(b["conversionTracking"]["buyStage"]["conversionValue"], a.ev(o))
            self.assertEqual(b["geoTargeting"]["countries"], [o["country_id"]])
            self.assertEqual(b["languageTargeting"]["value"], [2])
            self.assertEqual(b["limits"]["dailyLimit"], 20.0)

    def test_names_are_unique_and_say_geo_product_and_offer(self):
        names = [a.name(o) for o in a.DATA["offers"]]
        self.assertEqual(len(set(names)), len(names))
        self.assertEqual(a.name(BY_ID[4047]), "UY | Elastica (Aray 4047) | CPA tune")


class Data(unittest.TestCase):
    def test_nine_offers_five_teasers_and_no_claims_in_the_titles(self):
        self.assertEqual(len(a.DATA["offers"]), 9)
        with_teaser = [o for o in a.DATA["offers"] if "no_teaser" not in o]
        self.assertEqual(len(with_teaser), 5)
        for o in with_teaser:
            self.assertLessEqual(len(o["title"]), 75)
            self.assertTrue(o["title"].startswith(o["product"].split()[0].replace("Elastica", "Elástica")), o["title"])
            for bad in ("dolor", "cura", "elimina", "garantiz", "milagro", "artrosis", "varices", "100%", "alivi"):
                self.assertNotIn(bad, o["title"].lower())

    def test_no_token_is_stored_in_the_data_file(self):
        import json
        raw = json.dumps(a.DATA)
        self.assertNotIn("target=", raw)
        self.assertNotIn("cpa-gate", raw)


class Launch(unittest.TestCase):
    """`launch` against an in-memory campaign: the order of the writes, the refusals, and that the start is the last step."""

    CID = 12525146

    def setUp(self):
        self.state = {"status": {"name": "paused"}, "geoTargeting": {"countries": [191], "regions": {"mode": "include", "value": []}},
                      "bidding": {"strategy": "targetCpa", "price": 0.05}}
        self.log = []
        self.ledger = {}
        self.stick = True
        self.lag = 0                                    # reads that still show the old values after a write
        self.queued, self.reads_left = [], 0

        def call(method, url, body=None, **kw):
            self.log.append((method, body))
            if self.stick:
                self.queued.append(body)
                self.reads_left = self.lag
            return 204, None

        def v2(fields=()):
            if self.reads_left > 0:
                self.reads_left -= 1
            else:
                while self.queued:
                    self.state.update(self.queued.pop(0))
            return {self.CID: self.state}

        def pause(cid, on=True):
            self.log.append(("pause" if on else "start", cid))
            self.state["status"] = {"name": "paused" if on else "active", "reason": "clientManuallyPaused" if on else "unfulfilled"}
            return self.state["status"]

        self.patches = [
            mock.patch.object(a, "call", call), mock.patch.object(a, "pause", pause),
            mock.patch.object(a, "v2_campaigns", v2), mock.patch.object(a, "READ_BACK_WAIT", 0.0),
            mock.patch.object(a, "campaign_ids", lambda: {o["aray_id"]: self.CID for o in a.DATA["offers"]}),
            mock.patch.object(a, "load_ledger", lambda: self.ledger), mock.patch.object(a, "save_ledger", lambda d: None),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_regions_and_target_are_written_first_and_the_start_is_last(self):
        a.launch(4047, 4.0)
        self.assertEqual([x[0] for x in self.log], ["PATCH", "PATCH", "start"])
        self.assertEqual(self.log[0][1], {"geoTargeting": {"countries": [191], "regions": {"mode": "include", "value": [3796, 3803, 3804]}}})
        self.assertEqual(self.log[1][1], {"bidding": {"strategy": "targetCpa", "price": 4.0}})
        self.assertEqual(self.state["status"]["name"], "active")
        self.assertEqual(self.ledger["4047"]["launched"]["target"], 4.0)

    def test_no_regions_no_start(self):
        with self.assertRaises(SystemExit):
            a.launch(4840, 3.0)                         # Vitaflex PE: the delivery sheet has not been read yet
        self.assertEqual(self.log, [])

    def test_regions_can_be_given_on_the_command_line(self):
        a.launch(4840, 3.0, ["3000", "3001"])
        self.assertEqual(self.log[0][1]["geoTargeting"]["regions"]["value"], [3000, 3001])

    def test_target_above_the_value_of_a_lead_is_refused(self):
        with self.assertRaises(SystemExit):
            a.launch(4047, 5.07)                        # a lead is worth 5.06
        self.assertEqual(self.log, [])

    def test_a_campaign_that_is_not_paused_is_not_touched(self):
        self.state["status"] = {"name": "active"}
        with self.assertRaises(SystemExit):
            a.launch(4047, 4.0)
        self.assertEqual(self.log, [])

    def test_a_read_that_lags_the_write_is_waited_for(self):
        self.lag = 3                                    # 27.10: the regions read back empty right after the 204
        a.launch(4047, 4.0)
        self.assertEqual(self.log[-1], ("start", self.CID))
        self.assertEqual(self.state["geoTargeting"]["regions"]["value"], [3796, 3803, 3804])

    def test_nothing_starts_when_the_write_does_not_stick(self):
        self.stick = False
        with self.assertRaises(SystemExit):
            a.launch(4047, 4.0)
        self.assertNotIn(("start", self.CID), self.log)
        self.assertEqual(self.state["status"]["name"], "paused")


if __name__ == "__main__":
    unittest.main()
