"""Offline checks of the /dom/ and /dom2/ builds (arcadiablog.com content pages for MGID traffic). No network.

    python3 -m unittest -v test_geozo_site
"""
import re
import tempfile
import unittest
from pathlib import Path

import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "geozo_site"))

import build  # noqa: E402


class Dom(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        sys.argv = ["build.py", "--out", cls.tmp.name]
        build.main()
        cls.out = Path(cls.tmp.name) / "dom"
        cls.pages = {p.name: p.read_text(encoding="utf-8") for p in cls.out.glob("*.html")}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_two_articles_that_link_to_each_other(self):
        self.assertEqual(sorted(self.pages), ["index.html", "rasteniya-osenyu.html"])
        self.assertIn('/dom/rasteniya-osenyu.html', self.pages["index.html"])
        self.assertIn('href="/dom/"', self.pages["rasteniya-osenyu.html"])

    def test_four_labelled_slots_and_none_above_the_title(self):
        for name, h in self.pages.items():
            self.assertEqual(h.count('class="ad-slot"'), 4, name)
            self.assertEqual(h.count('<span class="ad-label">Реклама</span>'), 4, name)
            self.assertLess(h.index("<h1>"), h.index('class="ad-slot"'), name)      # the first slot comes after the title
            self.assertEqual(h.count(build.BLOCK_HEADER), 1, name)
            self.assertEqual(h.count(build.BLOCK_FEED), 3, name)

    def test_no_tiktok_and_no_redirect_tricks(self):
        js = next(self.out.glob("dom.*.js")).read_text(encoding="utf-8")
        for name, h in self.pages.items():
            self.assertNotIn("ttq", h, name)
            self.assertNotIn("tiktok", h.lower(), name)
        for bad in ("window.open", "location.href", "location.replace", "location.assign", "pushState", "popstate",
                    "beforeunload", "document.referrer"):
            self.assertNotIn(bad, js, bad)

    def test_moderate_pages_do_not_carry_the_dense_blocks(self):
        # /dom/ is what MGID approved: the dense blocks and the dense stylesheet must never leak into it
        for name, h in self.pages.items():
            for uuid in (build.BLOCK_DENSE_A, build.BLOCK_DENSE_B, build.BLOCK_DENSE_C):
                self.assertNotIn(uuid, h, name)
            self.assertNotIn("ad-slot compact", h, name)
            self.assertNotIn("gz-media__img-wrapper", h, name)

    def test_script_is_configured_for_the_relay(self):
        js = next(self.out.glob("dom.*.js")).read_text(encoding="utf-8")
        self.assertNotIn("__CFG__", js)
        self.assertIn('"lead": "/dom/lead"', js)
        for name, h in self.pages.items():
            self.assertRegex(h, r'<script src="dom\.[0-9a-f]{8}\.js" defer></script>', name)

    def test_assets_the_pages_use_exist(self):
        for name, h in self.pages.items():
            for ref in re.findall(r'(?:src|href)="(/dom/[^"]+|[A-Za-z0-9._-]+\.(?:js|jpg))"', h):
                path = self.out / ref.replace("/dom/", "") if ref.startswith("/dom/") else self.out / ref
                if path.suffix in (".js", ".jpg"):
                    self.assertTrue(path.exists(), f"{name}: {ref}")

    def test_dates_read_properly(self):
        for name, h in self.pages.items():
            self.assertNotRegex(h, r"г\. г\.", name)


class Dense(unittest.TestCase):
    """The dense variant /dom2/: many labelled slots, up to ten ads in a block, still an article and a uniform page."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        sys.argv = ["build.py", "--out", cls.tmp.name]
        build.main()
        cls.out = Path(cls.tmp.name) / "dom2"
        cls.pages = {p.name: p.read_text(encoding="utf-8") for p in cls.out.glob("*.html")}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_two_articles_that_link_to_each_other_under_dom2(self):
        self.assertEqual(sorted(self.pages), ["index.html", "rasteniya-osenyu.html"])
        self.assertIn('href="/dom2/rasteniya-osenyu.html"', self.pages["index.html"])
        self.assertIn('href="/dom2/"', self.pages["rasteniya-osenyu.html"])
        for name, h in self.pages.items():
            self.assertNotIn('"/dom/', h.replace('"/dom/lead', ""), name)       # nothing points back to the approved variant

    def test_every_slot_is_labelled_and_compact(self):
        for name, h in self.pages.items():
            n = h.count('class="ad-slot compact"')
            self.assertGreaterEqual(n, 8, name)
            self.assertEqual(h.count('class="ad-slot'), n, name)                  # no slot without the compact class
            self.assertEqual(h.count('<span class="ad-label">Реклама</span>'), n, name)

    def test_slots_are_after_the_lead_and_never_split_a_heading_from_its_text(self):
        slot = r'<div class="ad-slot compact"><span class="ad-label">Реклама</span><div data-gz-block="[0-9a-f-]+"></div></div>'
        for name, h in self.pages.items():
            self.assertLess(h.index('<p class="lead">'), h.index('class="ad-slot'), name)   # first slot after the lead
            self.assertLess(h.index("<h1>"), h.index('class="ad-slot'), name)
            self.assertIsNone(re.search(r"</h2>\s*" + slot, h), f"{name}: a slot right after a heading")
            self.assertIsNone(re.search(slot + r"\s*" + slot, h), f"{name}: two slots in a row")

    def test_one_top_block_one_closing_block_and_the_rest_middle(self):
        for name, h in self.pages.items():
            self.assertEqual(h.count(build.BLOCK_DENSE_A), 1, name)
            self.assertEqual(h.count(build.BLOCK_DENSE_C), 1, name)
            self.assertGreaterEqual(h.count(build.BLOCK_DENSE_B), 5, name)
            self.assertGreater(h.index(build.BLOCK_DENSE_C), h.index('class="note"'), name)  # the ten-ad block closes the article
            self.assertLess(h.index(build.BLOCK_DENSE_C), h.index('class="related"'), name)
            self.assertNotIn(build.BLOCK_HEADER, h, name)
            self.assertNotIn(build.BLOCK_FEED, h, name)

    def test_ads_per_page_and_the_ten_ad_ceiling(self):
        self.assertEqual(max(build.DENSE_ADS.values()), 10)                       # the panel's limit for one column
        for name, h in self.pages.items():
            ads = sum(build.DENSE_ADS[u] for u in re.findall(r'data-gz-block="([0-9a-f-]+)"', h))
            self.assertGreaterEqual(ads, 30, name)
            self.assertLessEqual(ads, 60, name)

    def test_dense_stylesheet_is_inlined_only_here(self):
        for name, h in self.pages.items():
            self.assertIn(".ad-slot.compact", h, name)
            self.assertIn('[class*="gz-media__title"]', h, name)

    def test_relay_is_shared_with_the_moderate_variant_and_no_redirect_tricks(self):
        js = next(self.out.glob("dom2.*.js")).read_text(encoding="utf-8")
        self.assertNotIn("__CFG__", js)
        self.assertIn('"lead": "/dom/lead"', js)
        self.assertIn('"route": "dom2"', js)
        for bad in ("window.open", "location.href", "location.replace", "location.assign", "pushState", "popstate",
                    "beforeunload", "document.referrer"):
            self.assertNotIn(bad, js, bad)
        for name, h in self.pages.items():
            self.assertNotIn("ttq", h, name)
            self.assertRegex(h, r'<script src="dom2\.[0-9a-f]{8}\.js" defer></script>', name)

    def test_assets_the_pages_use_exist(self):
        for name, h in self.pages.items():
            for ref in re.findall(r'(?:src|href)="(/dom2/[^"]+|[A-Za-z0-9._-]+\.(?:js|jpg))"', h):
                path = self.out / ref.replace("/dom2/", "") if ref.startswith("/dom2/") else self.out / ref
                if path.suffix in (".js", ".jpg"):
                    self.assertTrue(path.exists(), f"{name}: {ref}")


if __name__ == "__main__":
    unittest.main()
