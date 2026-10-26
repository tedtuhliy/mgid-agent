"""Offline checks of the Aray campaigns: the link, the campaign body, the value of a lead, the data file. No network.

    MGID_ACCOUNT=second python3 -m unittest test_aray_campaigns -v
"""
import unittest

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


if __name__ == "__main__":
    unittest.main()
