"""Offline checks of the multilingual build (geozo_site/build_multi.py) on synthetic ten-article language folders.

    python3 -m unittest -v test_multi_site

The folders are generated here, so the test does not depend on the real texts (those are checked by
geozo_site/check_articles.py). No network.
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "geozo_site"))

import build as kz  # noqa: E402
import build_multi as bm  # noqa: E402
import check_articles as ck  # noqa: E402
import multi_config as mc  # noqa: E402

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def fake_article(slug, lang):
    body = [{"t": "p", "lead": True, "x": f"Lead {slug} {lang} straße."}, {"t": "p", "x": f"Intro {slug}."}]
    for i in range(1, 7):
        body += [{"t": "h2", "x": f"Section {i} {slug}"}, {"t": "p", "x": f"Paragraph {i}a of {slug}."},
                 {"t": "p", "x": f"Paragraph {i}b of {slug}."}]
    body += [{"t": "h2", "x": "Summary"}, {"t": "ul", "x": ["a", "b", "c", "d"]}, {"t": "p", "x": "Closing."}]
    return {"rubric": "Home", "title": f"Title of {slug} straße ({lang})", "teaser": f"Teaser of {slug}",
            "description": f"Description of {slug}", "heroAlt": f"Alt {slug}", "body": body}


def fake_lang(root, lang):
    d = Path(root) / lang
    d.mkdir(parents=True)
    for slug in mc.SLUGS:
        (d / f"{slug}.json").write_text(json.dumps(fake_article(slug, lang)), encoding="utf-8")
    ui = {"brand_tag": "tips", "read_also": "Read also", "read_min": "{n} min read", "home_title": "Home title ß",
          "home_intro": "Intro", "all_articles": "All articles", "nav_home": "Home", "nav_about": "About",
          "nav_contact": "Contact", "nav_privacy": "Privacy", "disclosure": "Ads are marked.", "cookie": "Cookies.",
          "cookie_more": "More", "cookie_ok": "OK", "disclaimer": "Informational.", "months": MONTHS,
          "date_fmt": "{d} {month} {y}"}
    (d / "ui.json").write_text(json.dumps(ui), encoding="utf-8")
    pages = {k: {"title": f"{k} title", "paras": [f"{k} paragraph {i}" for i in range(3)]} for k in mc.PAGE_KEYS}
    (d / "pages.json").write_text(json.dumps(pages), encoding="utf-8")
    (d / "teasers.json").write_text(json.dumps([{"article": s, "title": f"Teaser {s}"} for s in mc.TEASER_SLUGS]),
                                    encoding="utf-8")


class Multi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = tempfile.TemporaryDirectory()
        cls.out = tempfile.TemporaryDirectory()
        cls.real_art = ck.ART
        ck.ART = Path(cls.src.name)
        for lang in ("pl", "de", "bg"):
            fake_lang(cls.src.name, lang)
        cls.routes = ["pl", "de", "ch", "bg"]
        bm.build(cls.out.name, cls.routes)
        cls.root = Path(cls.out.name) / "blog"

    @classmethod
    def tearDownClass(cls):
        ck.ART = cls.real_art
        cls.src.cleanup()
        cls.out.cleanup()

    def page(self, route, name):
        return (self.root / route / name).read_text(encoding="utf-8")

    def test_every_route_has_home_ten_articles_and_service_pages(self):
        for r in self.routes:
            names = sorted(p.name for p in (self.root / r).glob("*.html"))
            want = sorted(["index.html", "about.html", "contact.html", "privacy.html"] + [f"{s}.html" for s in mc.SLUGS])
            self.assertEqual(names, want, r)

    def test_article_pages_carry_dense_slots_with_the_local_label(self):
        labels = {"pl": "Reklama", "de": "Anzeige", "ch": "Anzeige", "bg": "Реклама"}
        for r in self.routes:
            for s in mc.SLUGS:
                h = self.page(r, f"{s}.html")
                n = h.count('class="ad-slot compact"')
                self.assertGreaterEqual(n, 8, f"{r}/{s}")
                self.assertEqual(h.count('class="ad-slot'), n, f"{r}/{s}")
                self.assertEqual(h.count(f'<span class="ad-label">{labels[r]}</span>'), n, f"{r}/{s}")
                self.assertEqual(h.count(kz.BLOCK_DENSE_A), 1, f"{r}/{s}")
                self.assertEqual(h.count(kz.BLOCK_DENSE_C), 1, f"{r}/{s}")
                self.assertGreaterEqual(h.count(kz.BLOCK_DENSE_B), 5, f"{r}/{s}")
                self.assertLess(h.index('<p class="lead">'), h.index('class="ad-slot'), f"{r}/{s}")
                self.assertGreater(h.index(kz.BLOCK_DENSE_C), h.index('class="note"'), f"{r}/{s}")
                slot = r'<div class="ad-slot compact"><span class="ad-label">[^<]+</span><div data-gz-block="[0-9a-f-]+"></div></div>'
                self.assertIsNone(re.search(r"</h2>\s*" + slot, h), f"{r}/{s}: slot right after a heading")
                self.assertIsNone(re.search(slot + r"\s*" + slot, h), f"{r}/{s}: two slots in a row")
                self.assertIn("async", h.split("786uvq768ypk0f4dm.go")[0].split("<script")[-1], f"{r}/{s}: loader")

    def test_home_and_service_pages_have_no_ads_and_no_loader(self):
        for r in self.routes:
            for name in ["index.html", "about.html", "contact.html", "privacy.html"]:
                h = self.page(r, name)
                self.assertNotIn('class="ad-slot', h, f"{r}/{name}")
                self.assertNotIn("ecstaticexistence", h, f"{r}/{name}")
                self.assertNotIn("data-gz-block", h, f"{r}/{name}")

    def test_home_lists_all_ten_articles(self):
        for r in self.routes:
            h = self.page(r, "index.html")
            for s in mc.SLUGS:
                self.assertIn(f'href="/blog/{r}/{s}.html"', h, r)

    def test_html_lang(self):
        want = {"pl": "pl", "de": "de", "ch": "de-CH", "bg": "bg"}
        for r in self.routes:
            self.assertIn(f'<html lang="{want[r]}">', self.page(r, "index.html"), r)

    def test_switzerland_is_german_with_ss(self):
        for s in mc.SLUGS:
            de, ch = self.page("de", f"{s}.html"), self.page("ch", f"{s}.html")
            self.assertIn("straße", de)
            self.assertNotIn("ß", ch, s)
            self.assertIn("strasse", ch, s)
        self.assertNotIn("ß", self.page("ch", "index.html"))

    def test_every_internal_reference_exists(self):
        for r in self.routes:
            for p in (self.root / r).glob("*.html"):
                h = p.read_text(encoding="utf-8")
                for ref in set(re.findall(r'(?:src|href)="(/blog/[^"?#]+)', h)):
                    self.assertTrue((Path(self.out.name) / ref.lstrip("/")).exists(), f"{r}/{p.name}: {ref}")

    def test_images_and_script_are_shared_and_hashed(self):
        self.assertEqual(len(list((self.root / "h").glob("*.jpg"))), 10)
        self.assertEqual(len(list((self.root / "t").glob("*.jpg"))), 10)
        self.assertEqual(len(list((self.root / "c").glob("*.jpg"))), 10)
        js = list(self.root.glob("blog.*.js"))
        self.assertEqual(len(js), 1)
        src = js[0].read_text(encoding="utf-8")
        self.assertIn('"lead": "/dom/lead"', src)
        self.assertNotIn("__CFG__", src)
        for bad in ("window.open", "location.href", "location.replace", "pushState", "popstate", "beforeunload",
                    "document.referrer"):
            self.assertNotIn(bad, src, bad)
        for r in self.routes:
            self.assertIn(f"/blog/{js[0].name}", self.page(r, "index.html"), r)

    def test_no_tiktok_and_no_redirect_tricks_in_pages(self):
        for r in self.routes:
            for p in (self.root / r).glob("*.html"):
                h = p.read_text(encoding="utf-8")
                self.assertNotIn("ttq", h)
                self.assertNotIn("tiktok", h.lower())
                self.assertIn('<meta name="robots" content="noindex,nofollow">', h)

    def test_teaser_creatives_are_1200x800(self):
        from PIL import Image
        for s in mc.SLUGS:
            with Image.open(self.root / "c" / f"{s}.jpg") as im:
                self.assertEqual(im.size, (1200, 800), s)
            with Image.open(self.root / "t" / f"{s}.jpg") as im:
                self.assertEqual(im.size, (360, 240), s)


class Config(unittest.TestCase):
    def test_geos_point_at_existing_routes(self):
        for geo, (cid, route) in mc.GEOS.items():
            self.assertIn(route, list(mc.LANGS) + list(mc.DERIVED), geo)
            self.assertIsInstance(cid, int)

    def test_every_geo_of_a_language_is_in_geos(self):
        listed = {g for cfg in list(mc.LANGS.values()) + list(mc.DERIVED.values()) for g in cfg["geos"]}
        self.assertEqual(listed, set(mc.GEOS))

    def test_ad_labels_are_local_words(self):
        for r, cfg in mc.LANGS.items():
            if cfg["script"] == "latin":
                self.assertFalse(re.search("[Ѐ-ӿ]", cfg["ad_label"]), r)

    def test_topics(self):
        self.assertEqual(len(mc.TOPICS), 10)
        self.assertEqual(len(set(mc.SLUGS)), 10)
        for t in mc.TOPICS:
            self.assertTrue((Path(__file__).resolve().parent / "geozo_site" / t["src"]).exists(), t["slug"])


if __name__ == "__main__":
    unittest.main()
