"""Offline checks of the CPA bid rule. No network: payouts and geo targeting are passed in.

    python3 -m unittest test_cpa_share -v
"""
import unittest

from cpa_share import bid, by_country, geos_of


class Bid(unittest.TestCase):
    def test_single_geo_is_thirty_percent_of_its_payout(self):
        self.assertEqual(bid(["PL"], {"PL": 2.0}), (0.6, "PL"))
        self.assertEqual(bid(["UA"], {"UA": 1.0}), (0.3, "UA"))

    def test_several_geos_take_the_lowest_payout(self):
        pay = {"CL": 1.0, "CR": 0.8, "DO": 0.62, "EC": 0.62, "GT": 0.7, "HN": 0.8, "PA": 0.48}
        self.assertEqual(bid(["CR", "DO", "GT", "PA"], pay), (0.144, "PA"))

    def test_cents_are_exact(self):
        self.assertEqual(bid(["EE"], {"EE": 1.48}), (0.444, "EE"))
        self.assertEqual(bid(["LV"], {"LV": 0.32}), (0.096, "LV"))
        self.assertEqual(bid(["KZ"], {"KZ": 0.56}), (0.168, "KZ"))

    def test_share_can_be_changed_per_region(self):
        self.assertEqual(bid(["PL"], {"PL": 2.0}, 0.5), (1.0, "PL"))                          # 13.10: half of the payout
        pay = {"CR": 0.8, "DO": 0.62, "GT": 0.7, "PA": 0.48}
        self.assertEqual(bid(["CR", "DO", "GT", "PA"], pay, 0.4), (0.192, "PA"))             # 30% + 10 points
        self.assertEqual(bid(["AZ", "KZ"], {"AZ": 0.2, "KZ": 0.56}, 0.6), (0.12, "AZ"))      # CIS doubled

    def test_geo_without_a_payout_is_refused(self):
        with self.assertRaises(ValueError):
            bid(["KZ", "PL"], {"KZ": 0.56})


class Geos(unittest.TestCase):
    def test_ids_become_sorted_iso_codes(self):
        self.assertEqual(geos_of({"geoTargeting": {"countries": [19, 89]}}), ["CR", "PL"])

    def test_unknown_country_id_is_refused(self):
        with self.assertRaises(ValueError):
            geos_of({"geoTargeting": {"countries": [999]}})

    def test_campaign_without_geo_is_refused(self):
        with self.assertRaises(ValueError):
            geos_of({})


class Payouts(unittest.TestCase):
    def test_payout_group_suffix_is_dropped(self):
        self.assertEqual(by_country({"GT - Mobile/Desktop": 0.7, "PA": 0.48}), {"GT": 0.7, "PA": 0.48})


if __name__ == "__main__":
    unittest.main()
