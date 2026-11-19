"""Offline checks of the NewsBreak test: the click URL, the ad set at the platform minimums, the copy limits, the 16:9 crop. No network.

    python3 -m unittest test_nb -v
"""
import json
import tempfile
import unittest
from pathlib import Path

import nb_sweeps as s

TRACKER = "https://tracker.example/or/AbC123/XyZ789"


class Urls(unittest.TestCase):
    def test_click_url_carries_the_callback_flight_and_creative_macros(self):
        u = s.click_url(TRACKER)
        self.assertEqual(u, TRACKER + "?source_id=nb-__FLIGHT_ID__-__CREATIVE_ID__&aff_click_id=__CALLBACK_PARAM__")

    def test_an_existing_query_gets_an_ampersand(self):
        self.assertIn("?x=1&source_id=", s.click_url(TRACKER + "?x=1"))


class AdSet(unittest.TestCase):
    O = s.OFFERS[1282]

    def test_minimum_money_everything_off_first_party_inventory_only(self):
        b = s.ad_set_body("999", self.O, now=1_800_000_000)
        self.assertEqual((b["budgetType"], b["budget"], b["bidType"], b["bidRate"], b["status"]), ("DAILY", 1000, "CPC", 10, "OFF"))
        self.assertEqual(b["platforms"], ["NEWSBREAK"])
        self.assertEqual(b["endTime"] - b["startTime"], 14 * 86400)
        self.assertGreater(b["startTime"], 1_800_000_000)

    def test_sweeps_are_mobile_only_and_the_insurance_offer_is_not(self):
        self.assertIn("os", s.targeting(s.copy(1282)))
        self.assertIn("ios@17", s.targeting(s.copy(1282))["os"]["positive"])
        self.assertIn("android@13", s.targeting(s.copy(1282))["os"]["positive"])
        self.assertNotIn("os", s.targeting(s.copy(2139)))

    def test_the_limits_in_the_data_file_are_the_platform_minimums_not_below(self):
        self.assertGreaterEqual(s.DATA["bid_cents"], 10)               # 9 cents: «illegal bid rate too small» (19.11)
        self.assertGreaterEqual(s.DATA["daily_budget_cents"], 1000)    # budget must be at least 1000 cents
        self.assertGreaterEqual(s.DATA["spending_cap_cents"], s.DATA["daily_budget_cents"])


class Copy(unittest.TestCase):
    def test_headlines_fit_90_characters_and_make_no_cash_claims(self):
        for oid, c in s.DATA["offers"].items():
            for h in c["headlines"]:
                self.assertLessEqual(len(h), 90, h)
                for bad in ("$1000", "$500", "free", "guarantee", "win ", "cash", "winner"):
                    self.assertNotIn(bad, h.lower(), h)

    def test_every_copy_belongs_to_an_offer_of_the_list_and_has_images(self):
        for oid, c in s.DATA["offers"].items():
            self.assertIn(int(oid), s.OFFERS)
            self.assertTrue(c["images"] and c["headlines"] and c["brand"])

    def test_ads_pair_images_with_headlines_and_repeat_the_shorter_list(self):
        p = s.ads_plan(s.OFFERS[1282])
        self.assertEqual(len(p), 3)
        self.assertEqual(p[0], ("1282_a", s.DATA["offers"]["1282"]["headlines"][0]))
        p = s.ads_plan(s.OFFERS[1046])
        self.assertEqual([k for k, _ in p], ["1046", "1046"])

    def test_names_are_unique(self):
        names = [s.campaign_name(o) for o in s.RR["offers"]]
        self.assertEqual(len(set(names)), len(names))

    def test_only_the_insurance_offer_waits_for_the_advertiser(self):
        self.assertEqual([k for k, c in s.DATA["offers"].items() if c.get("hold")], ["2139"])

    def test_no_link_or_token_is_stored_in_the_data_file(self):
        raw = json.dumps(s.DATA)
        for bad in ("green-planet", "/or/", "Access-Token", "tskey"):
            self.assertNotIn(bad, raw)


class Upload(unittest.TestCase):
    def test_a_duplicate_upload_returns_the_url_of_the_existing_media(self):
        import nb_api
        from unittest import mock
        dup = (409, {"code": -1, "data": {"assetUrl": "https://cdn/x.jpg", "mediaId": "1"}, "errMsg": "Fail to create media: media with the same content already exists."})
        with mock.patch.object(nb_api, "call", lambda *a, **k: dup):
            self.assertEqual(nb_api.upload_asset("1", "/tmp/x.jpg"), "https://cdn/x.jpg")
        with mock.patch.object(nb_api, "call", lambda *a, **k: (200, {"code": 0, "data": {"assetUrl": "https://cdn/y.jpg"}})):
            self.assertEqual(nb_api.upload_asset("1", "/tmp/x.jpg"), "https://cdn/y.jpg")
        with mock.patch.object(nb_api, "call", lambda *a, **k: (500, {"code": -1})):
            with self.assertRaises(RuntimeError):
                nb_api.upload_asset("1", "/tmp/x.jpg")


class Images(unittest.TestCase):
    def test_crop_is_16_by_9_1200_wide(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "a.jpg"
            Image.new("RGB", (1200, 800), (200, 100, 50)).save(src)
            out = s.crop169(src, Path(d) / "b.jpg")
            self.assertEqual(Image.open(out).size, (1200, 675))


if __name__ == "__main__":
    unittest.main()
