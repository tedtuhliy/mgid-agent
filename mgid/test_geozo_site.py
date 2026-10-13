"""Offline checks of the /dom/ build (arcadiablog.com content pages for MGID traffic). No network.

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


if __name__ == "__main__":
    unittest.main()
