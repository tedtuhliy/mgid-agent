"""Offline checks of the Geozo sweeps test: the link, the copy limits, the campaign body, the pictures. No network.

    python3 -m unittest test_gz -v
"""
import io
import json
import unittest

import gz_sweeps as s

TRACKER = "https://tracker.example/or/AbC123/XyZ789"


class Links(unittest.TestCase):
    def test_link_is_the_tracker_on_the_custom_domain_with_the_macros_of_geozo(self):
        self.assertEqual(s.link(TRACKER), "https://eventsbytlcltd.com/or/AbC123/XyZ789?source_id=gz-[CAMPAIGN_ID]-[AD_ID]-[SITE_ID]")

    def test_an_existing_query_gets_an_ampersand(self):
        self.assertEqual(s.link(TRACKER + "?x=1"), "https://eventsbytlcltd.com/or/AbC123/XyZ789?x=1&source_id=gz-[CAMPAIGN_ID]-[AD_ID]-[SITE_ID]")


class Copy(unittest.TestCase):
    def test_titles_are_30_to_65_characters_and_win_only_as_a_chance(self):
        for oid, c in s.DATA["offers"].items():
            for t in c["titles"]:
                self.assertTrue(30 <= len(t) <= 65, (oid, len(t), t))
                low = t.lower()
                self.assertEqual(low.count("win"), low.count("chance to win"), t)
                for bad in ("guarantee", "winner", "you won", "free money"):
                    self.assertNotIn(bad, low, t)

    def test_the_insurance_titles_follow_the_advertiser_rules_no_cash_free_numbers(self):
        for t in s.DATA["offers"]["2139"]["titles"]:
            for bad in ("$", "cash", "free", "urgent", "now"):
                self.assertNotIn(bad, t.lower(), t)

    def test_every_offer_belongs_to_the_list_and_has_pictures_and_three_titles(self):
        for oid, c in s.DATA["offers"].items():
            self.assertIn(int(oid), s.OFFERS)
            self.assertTrue(c["images"])
            self.assertEqual(len(c["titles"]), 3)
            self.assertIn(c["devices"], ("mobile", "all"))

    def test_the_offers_chosen_by_the_owner_and_not_the_ones_without_a_link(self):
        self.assertEqual(sorted(int(k) for k in s.DATA["offers"]), sorted([1282, 1719, 2212, 1046, 1041, 1560, 2238, 2239, 2176, 2177, 2139]))

    def test_pairs_repeat_the_shorter_list(self):
        p = s.pairs(1719)
        self.assertEqual([k for k, _ in p], ["1719", "1719", "1719"])
        self.assertEqual(len(s.pairs(1282)), 3)

    def test_no_link_or_token_is_stored_in_the_data_file(self):
        raw = json.dumps(s.DATA)
        for bad in ("green-planet", "/or/", "tracking_link=", "Private-Token", "tskey"):
            self.assertNotIn(bad, raw)


class Bodies(unittest.TestCase):
    TPL = {"campaign_type_id": 1, "traffic_source_id": 1, "categories": [1, 2, 3], "billing_type": "cpc", "ad_format_type_id": 1}

    def test_campaign_copies_type_source_and_categories_of_the_template(self):
        o, c = s.OFFERS[1282], s.copy(1282)
        b = s.campaign_body(o, c, self.TPL)
        self.assertEqual((b["campaign_type_id"], b["traffic_source_id"], b["categories"], b["countries"]), (1, 1, [1, 2, 3], ["US"]))
        self.assertEqual(b["device_types"], [2, 4])
        self.assertEqual(s.campaign_body(s.OFFERS[2176], s.copy(2176), self.TPL)["device_types"], [1, 2, 4])
        self.assertIn("RollerAds 1282", b["name"])

    def test_group_starts_the_approved_ads_by_itself(self):
        g = s.group_body(s.OFFERS[2212], s.copy(2212), self.TPL)
        self.assertTrue(g["auto_start_ads"])
        self.assertEqual(g["countries"], ["US"])

    def test_money_limits_are_the_platform_minimum_and_the_soft_cap_is_small(self):
        self.assertEqual((s.DATA["daily_limit_usd"], s.DATA["total_limit_usd"]), (20, 20))   # Geozo refuses a campaign limit below $20 (19.11)
        self.assertLessEqual(s.DATA["soft_daily_cap_usd"], 5)
        self.assertGreaterEqual(s.DATA["balance_floor_usd"], 50)
        lad = [float(x) for x in s.DATA["bid_ladder"]]
        self.assertEqual(lad, sorted(lad))
        self.assertLessEqual(lad[-1], 0.1)


class Pictures(unittest.TestCase):
    def test_formats(self):
        from PIL import Image
        im = Image.new("RGB", (1200, 800), (120, 90, 60))
        sq, wd = s.to_formats(im)
        self.assertEqual(Image.open(io.BytesIO(sq)).size, (600, 600))
        self.assertEqual(Image.open(io.BytesIO(wd)).size, (800, 450))

    def test_the_picture_with_the_ai_band_keeps_the_band_in_both_formats(self):
        from PIL import Image
        im = Image.new("RGB", (1200, 675), (200, 200, 200))
        sq, wd = s.to_formats(im, "Some images in this advertisement were generated using AI.")
        self.assertEqual(Image.open(io.BytesIO(sq)).size, (600, 600))
        self.assertEqual(Image.open(io.BytesIO(wd)).size, (800, 450))
        # the band of the square is dark at the bottom, the middle of the picture is not
        q = Image.open(io.BytesIO(sq)).convert("L")
        self.assertLess(q.getpixel((5, 595)), 120)
        self.assertGreater(q.getpixel((300, 300)), 150)


if __name__ == "__main__":
    unittest.main()
