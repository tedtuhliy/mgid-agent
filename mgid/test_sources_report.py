"""Offline checks of the Sources report. No network: the answers of `quality-analysis-sources` are written out here.

    python3 -m unittest test_sources_report -v
"""
import unittest

import sources_report as s


def answer(cid, rows):
    return {str(cid): {"2026-10-21_2026-10-22": rows}}


def row(name, imp, clk, spent, conv=0):
    return {"sourceName": name, "impressions": imp, "clicks": clk, "spent": spent, "conversionsBuy": conv}


class Sources(unittest.TestCase):
    def test_two_campaigns_are_summed_by_source_id(self):
        a = answer(1, {"7639": row("buzzday.info", 3000, 20, 2.0), "9": row("a.com", 10, 0, 0.0)})
        b = answer(2, {"7639": row("buzzday.info", 1700, 8, 1.3)})
        rows = s.aggregate([a, b])
        self.assertEqual(rows["7639"], {"name": "buzzday.info", "imp": 4700, "clk": 28, "spent": 3.3, "conv": 0})
        self.assertIn("9", rows)

    def test_a_source_without_any_delivery_is_left_out(self):
        rows = s.aggregate([answer(1, {"5": row("quiet.com", 0, 0, 0.0)})])
        self.assertEqual(rows, {})

    def test_an_empty_or_missing_answer_is_harmless(self):
        self.assertEqual(s.aggregate([{}, None, {"1": {}}, {"1": {"x": None}}]), {})

    def test_ctr_and_the_flag(self):
        news = {"name": "n", "imp": 4704, "clk": 28, "spent": 3.3, "conv": 0}                 # 0.6 %
        bait = {"name": "b", "imp": 395, "clk": 23, "spent": 2.0, "conv": 0}                  # 5.8 %
        one = {"name": "o", "imp": 1, "clk": 1, "spent": 0.2, "conv": 0}                      # 100 % but a single click
        ghost = {"name": "g", "imp": 0, "clk": 4, "spent": 0.4, "conv": 0}                    # clicks without impressions
        self.assertAlmostEqual(s.ctr(bait), 5.82, places=2)
        self.assertFalse(s.flagged(news))
        self.assertTrue(s.flagged(bait))
        self.assertFalse(s.flagged(one))
        self.assertTrue(s.flagged(ghost))


if __name__ == "__main__":
    unittest.main()
