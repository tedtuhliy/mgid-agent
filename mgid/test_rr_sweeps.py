"""Offline checks of the RollerAds sweeps campaigns: the link, the postback, the campaign body, the data file. No network.

    MGID_ACCOUNT=second python3 -m unittest test_rr_sweeps -v
"""
import json
import unittest

import rr_sweeps as r

TRACKER = "https://tracker.example/or/AbC123/XyZ789"


class Links(unittest.TestCase):
    def test_labels_of_mgid_keep_their_braces(self):
        self.assertEqual(r.link(TRACKER), "https://eventsbytlcltd.com/or/AbC123/XyZ789?source_id={widget_id}_{teaser_id}&aff_click_id={click_id}")

    def test_an_existing_query_gets_an_ampersand(self):
        self.assertEqual(r.link(TRACKER + "?x=1"), "https://eventsbytlcltd.com/or/AbC123/XyZ789?x=1&source_id={widget_id}_{teaser_id}&aff_click_id={click_id}")

    def test_only_the_host_is_replaced_code_and_signature_stay(self):
        self.assertEqual(r.retarget(TRACKER, "custom.example"), "https://custom.example/or/AbC123/XyZ789")
        self.assertEqual(r.retarget(TRACKER, None), TRACKER)

    def test_one_postback_for_all_offers_carries_the_click_id_the_event_and_the_payout_macro(self):
        # RollerAds keeps at most 10 postbacks per account (the 11th: 422 «Maximum number of postbacks reached»), so one goal and one postback serve all ten offers
        self.assertEqual(r.postback_url(), "https://a.mgid.com/postback?c={affClickId}&e=rrsweepslead&r={trx}")
        self.assertEqual(r.event(), "rrsweepslead")


class Body(unittest.TestCase):
    OS = [19, 20, 3]

    def test_cpa_tune_product_with_the_goal_the_target_and_the_country(self):
        b = r.body(r.BY_ID[1282], 1234567, self.OS)
        self.assertEqual(b["type"], "product")
        self.assertEqual(b["bidding"], {"strategy": "targetCpa", "price": 1.0})
        self.assertEqual(b["conversionTracking"]["buyStage"]["targetId"], 1234567)
        self.assertEqual(b["geoTargeting"]["countries"], [4])
        self.assertEqual(b["languageTargeting"]["value"], [1])
        self.assertEqual(b["limits"]["dailyLimit"], 20.0)
        self.assertFalse(b["isAutoLaunchAdsAfterApproval"])
        self.assertEqual(b["showName"], "Level Reward")          # the brand under the teaser carries no prize amount

    def test_mobile_os_only_for_the_mobile_offers(self):
        self.assertEqual(r.body(r.BY_ID[1282], 1, self.OS)["operatingSystemTargeting"], {"mode": "include", "value": self.OS})
        self.assertNotIn("operatingSystemTargeting", r.body(r.BY_ID[2139], 1, self.OS))

    def test_mobile_os_ids_take_ios_and_android_phones_and_tablets_only(self):
        rows = [{"id": 8, "name": "Windows OS", "deviceType": "desktop"}, {"id": 12, "name": "Android", "deviceType": "mobile"}, {"id": 19, "name": "iOS", "deviceType": "mobile"},
                {"id": 40, "name": "iOS", "deviceType": "tablet"}, {"id": 99, "name": "Other Mobile OS", "deviceType": "mobile"}, {"id": 77, "name": "Android", "deviceType": "desktop"}]
        self.assertEqual(r.mobile_os_ids(rows), [12, 19, 40])

    def test_names_are_unique_and_say_geo_offer_and_the_target(self):
        names = [r.name(o) for o in r.DATA["offers"]]
        self.assertEqual(len(set(names)), len(names))
        self.assertEqual(r.name(r.BY_ID[1282]), "US | Level Reward $1000 (RollerAds 1282) | CPA tune $1")


class Variants(unittest.TestCase):
    def test_pairs_follow_the_newsbreak_ads(self):
        p = r.nb_pairs(1282)
        self.assertEqual(len(p), 4)
        self.assertEqual(p[0][0], "1282_a")
        self.assertEqual(r.nb_pairs(1046), [("1046", r.NB["offers"]["1046"]["headlines"][0]), ("1046", r.NB["offers"]["1046"]["headlines"][1])])
        self.assertEqual(r.nb_pairs(1), [])

    def test_every_headline_fits_the_mgid_title_and_the_domain_limit(self):
        for oid in r.NB["offers"]:
            pairs = r.nb_pairs(int(oid))
            self.assertLessEqual(len(pairs), r.MAX_TEASERS, oid)
            for _, title in pairs:
                self.assertLessEqual(len(title), 75, title)


class Data(unittest.TestCase):
    def test_twelve_offers_with_unique_ids_and_the_owners_numbers(self):
        ids = [o["id"] for o in r.DATA["offers"]]
        self.assertEqual(len(ids), 12)
        self.assertEqual(sorted(ids), sorted([2139, 2176, 2177, 1046, 2154, 1795, 1725, 1282, 1719, 2212, 2238, 2239]))

    def test_every_offer_with_a_title_has_an_image_and_the_titles_make_no_cash_claims(self):
        for o in r.DATA["offers"]:
            if o.get("title"):
                self.assertTrue(o.get("image"), o["id"])
                self.assertLessEqual(len(o["title"]), 75, o["id"])
                for bad in ("$1000", "$500", "free", "guarantee", "win ", "cash", "winner"):
                    self.assertNotIn(bad, o["title"].lower(), o["id"])

    def test_only_the_insurance_offer_waits_for_the_advertiser(self):
        self.assertEqual([o["id"] for o in r.DATA["offers"] if o.get("hold")], [2139])

    def test_no_link_or_token_is_stored_in_the_data_file(self):
        raw = json.dumps(r.DATA)
        for bad in ("green-planet", "/or/", "tracking_link=", "tskey", "signature"):
            self.assertNotIn(bad, raw)


if __name__ == "__main__":
    unittest.main()
