"""Static build of the multilingual site arcadiablog.com/blog/<lang>/ (MGID traffic -> article -> Geozo blocks).

    python3 geozo_site/build_multi.py --out /tmp/stage                 # every language that has a valid folder
    python3 geozo_site/build_multi.py --out /tmp/stage --langs pl,bg   # only these routes (ch needs de)
    python3 geozo_site/build_multi.py --out /tmp/stage --check         # only validate the folders

Owner, 13.10 night: «Нужно сделать сайт мультиязычным ... минимум по 10 статей на каждое гео, картинки те же самые, блоки
те же самые». Per route <lang>: index.html (home with the list of the ten articles), ten article pages, about / contact /
privacy. The article pages use the dense layout of /dom2/ (a slot after the lead and after every second block of text, a
ten-ad block at the end, the same three Geozo blocks, compact cards) with the label «advertisement» in the local language.
The home and the service pages carry no ad slots and do not load the Geozo loader.

Output tree (shared files once, so that a language is only its HTML):
  blog/blog.<hash>.js      dom.js with the relay config (the same /dom/lead relay as the Kazakhstan pages)
  blog/h/<slug>.<hash>.jpg hero 1200x700            blog/t/<slug>.jpg  list thumbnail 360x240
  blog/c/<slug>.jpg        teaser creative 1200x800 (what MGID fetches)
  blog/<lang>/*.html
Switzerland (ch) is the German text with ss for ß, built from the de folder.
"""
import argparse
import hashlib
import html
import json
import re
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build as kz  # noqa: E402  the Kazakhstan build: blocks, loader, brand, rendering of article blocks
import check_articles as ck  # noqa: E402
import make_ebooks as mb  # noqa: E402
import multi_config as mc  # noqa: E402

ROOT = "blog"
BRAND = kz.BRAND
LOADER = kz.LOADER
CSS_FILES = ["style.css", "dense.css", "multi.css"]

PAGE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title} — {brand}</title>
<meta name="description" content="{description}">
<meta name="theme-color" content="{color}">
<meta name="robots" content="noindex,nofollow">
{ads_head}<style>
{css}
</style>
<script src="{js}" defer></script>
</head>
<body data-page="{kind}">
<div class="page">
  <header class="top">
    <a class="brand js-int" href="{home}"><div class="brand-mark">{mark}</div><div class="brand-name">{brand} <span>· {tag}</span></div></a>
  </header>
  <main>
{main}
  </main>
  <footer>
    <nav>
      <a class="js-int" href="{home}">{nav_home}</a>
      <a class="js-int" href="{about}">{nav_about}</a>
      <a class="js-int" href="{contact}">{nav_contact}</a>
      <a class="js-int" href="{privacy}">{nav_privacy}</a>
    </nav>
    <p class="langs">{langs}</p>
    <p>{disclosure}</p>
    <p>© {year} {brand}</p>
  </footer>
</div>
<div id="cookie" class="cookie" role="dialog" aria-label="Cookies" hidden>
  <p>{cookie} <a class="js-int" href="{privacy}">{cookie_more}</a></p>
  <div class="cookie-btns"><button id="cookie-ok" type="button">{cookie_ok}</button></div>
</div>
</body>
</html>
"""

CHOOSER = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{brand}</title>
<meta name="description" content="{brand}: home, kitchen and garden.">
<meta name="theme-color" content="{color}">
<meta name="robots" content="noindex,nofollow">
<style>
{css}
</style>
</head>
<body data-page="chooser">
<div class="page">
  <header class="top">
    <div class="brand"><div class="brand-mark">{mark}</div><div class="brand-name">{brand}</div></div>
  </header>
  <main>
    <div class="inner home">
      <h1>{brand}</h1>
      <div class="cards langlist">
{items}
      </div>
    </div>
  </main>
  <footer><p>© {year} {brand}</p></footer>
</div>
</body>
</html>
"""

ADS_HEAD = """<link rel="preconnect" href="{origin}" crossorigin>
<link rel="dns-prefetch" href="{origin}">
<script async src="{loader}"></script>
"""


def esc(s):
    return html.escape(str(s), quote=True)


def sha8(b):
    return hashlib.sha256(b).hexdigest()[:8]


def walk(o, fn):
    if isinstance(o, str):
        return fn(o)
    if isinstance(o, list):
        return [walk(x, fn) for x in o]
    if isinstance(o, dict):
        return {k: walk(v, fn) for k, v in o.items()}
    return o


def load_lang(route):
    """(ui, pages, articles{slug: dict}, teasers) of a route; ch is derived from de."""
    derived = mc.DERIVED.get(route)
    src = derived["from"] if derived else route
    d = ck.ART / src
    ui = json.loads((d / "ui.json").read_text(encoding="utf-8"))
    pages = json.loads((d / "pages.json").read_text(encoding="utf-8"))
    arts = {s: json.loads((d / f"{s}.json").read_text(encoding="utf-8")) for s in mc.SLUGS}
    teasers = json.loads((d / "teasers.json").read_text(encoding="utf-8"))
    if derived:
        def swap(t):
            for a, b in derived["replace"]:
                t = t.replace(a, b)
            return t
        ui, pages, arts, teasers = (walk(x, swap) for x in (ui, pages, arts, teasers))
    return ui, pages, arts, teasers


def fmt_date(ui, day):
    return ui["date_fmt"].format(d=day.day, month=ui["months"][day.month - 1], y=day.year)


def article_date(slug, today):
    return today - timedelta(days=2 + sum(ord(c) for c in slug) % 24)


def words(body):
    return kz.words(body)


def book_card(route, eb, pages):
    """The offer card of the free e-book: not an ad (no label, own colour), a plain link to /blog/dl/<route>.pdf; the script
    adds click_id and source to it like to any internal link, nginx counts the request and tells MGID."""
    href = f"/{ROOT}/dl/{route}.pdf"
    return (f'<aside class="book"><a class="book-cover js-int" href="{href}" tabindex="-1" aria-hidden="true">'
            f'<img src="/{ROOT}/ebook/cover-{route}.jpg" width="84" height="119" alt="" loading="lazy"></a>'
            f'<div class="book-body"><p class="book-title">{esc(eb["cta_title"])}</p><p class="book-text">{esc(eb["cta_text"])}</p>'
            f'<p class="book-meta">{esc(eb["cta_meta"].format(pages=pages))}</p>'
            f'<a class="book-btn js-int" href="{href}">{esc(eb["cta_button"])}</a></div></aside>')


def build(out_root, langs, force=False, ebooks=True):
    out = Path(out_root) / ROOT
    shutil.rmtree(out, ignore_errors=True)
    for sub in ("h", "t", "c"):
        (out / sub).mkdir(parents=True)
    pages = {}
    if ebooks:
        want = mb.routes_with_book(langs)
        pages = mb.build(want, out_root) if want else {}

    # shared files
    js_src = (HERE / "dom.js").read_text(encoding="utf-8").replace("__CFG__", json.dumps(kz.js_cfg(ROOT), ensure_ascii=False))
    js_name = f"{ROOT}.{sha8(js_src.encode())}.js"
    (out / js_name).write_text(js_src, encoding="utf-8")
    heroes, hero_file = {}, {}
    for t in mc.TOPICS:
        slug = t["slug"]
        buf = (HERE / "assets" / f"{slug}.jpg").read_bytes()
        hero_file[slug] = f"{slug}.{sha8(buf)}.jpg"
        (out / "h" / hero_file[slug]).write_bytes(buf)
        creative = HERE / "teasers" / f"{slug}.jpg"
        shutil.copy(creative, out / "c" / f"{slug}.jpg")
        im = Image.open(creative).convert("RGB").resize((360, 240), Image.LANCZOS)
        im.save(out / "t" / f"{slug}.jpg", quality=80, optimize=True)
    css = "\n".join((HERE / f).read_text(encoding="utf-8").strip() for f in CSS_FILES)
    origin = LOADER.split("/", 3)[0] + "//" + LOADER.split("/")[2]
    ads_head = ADS_HEAD.format(origin=origin, loader=LOADER)
    today = date.today()
    built = []
    langs_html = " ".join(
        f'<a lang="{mc.HTML_LANG.get(r, r)}" hreflang="{mc.HTML_LANG.get(r, r)}" href="/{ROOT}/{r}/">{esc(mc.NATIVE[r])}</a>'
        for r in langs)

    for route in langs:
        cfg = mc.LANGS.get(route) or {"html": mc.DERIVED[route]["html"], "ad_label": mc.LANGS[mc.DERIVED[route]["from"]]["ad_label"]}
        ui, pages_json, arts, teasers = load_lang(route)
        card = ""
        if route in pages:
            _, eb, _ = mb.load(route)
            card = book_card(route, eb, pages[route])
        base = f"/{ROOT}/{route}/"
        d = out / route
        d.mkdir(parents=True)
        label = cfg["ad_label"]

        def page(kind, title, description, main, with_ads):
            return PAGE.format(
                lang=cfg["html"], title=esc(title), brand=BRAND["name"], description=esc(description), color=BRAND["color"],
                ads_head=ads_head if with_ads else "", css=css, js=f"/{ROOT}/{js_name}", kind=kind, home=base,
                mark=BRAND["mark"], tag=esc(ui["brand_tag"]), main=main,
                about=base + "about.html", contact=base + "contact.html", privacy=base + "privacy.html",
                nav_home=esc(ui["nav_home"]), nav_about=esc(ui["nav_about"]), nav_contact=esc(ui["nav_contact"]),
                nav_privacy=esc(ui["nav_privacy"]), langs=langs_html, disclosure=esc(ui["disclosure"]), year=today.year,
                cookie=esc(ui["cookie"]), cookie_more=esc(ui["cookie_more"]), cookie_ok=esc(ui["cookie_ok"]))

        # the ten articles
        for i, t in enumerate(mc.TOPICS):
            slug = t["slug"]
            a = arts[slug]
            others = [mc.TOPICS[(i + k) % len(mc.TOPICS)]["slug"] for k in (1, 2, 3)]
            related = "\n".join(
                f'        <a class="js-int" href="{base}{o}.html"><img src="/{ROOT}/t/{o}.jpg" width="96" height="64" alt="" '
                f'loading="lazy"><span>{esc(arts[o]["title"])}</span></a>' for o in others)
            main = f"""    <img class="hero" src="/{ROOT}/h/{hero_file[slug]}" width="1200" height="700" alt="{esc(a['heroAlt'])}" fetchpriority="high">
    <article class="inner">
      <p class="rubric">{esc(a['rubric'])}</p>
      <h1>{esc(a['title'])}</h1>
      <p class="meta">{esc(fmt_date(ui, article_date(slug, today)))} · {esc(ui['read_min'].format(n=max(2, round(words(a['body']) / 190))))}</p>
{kz.body_html_dense(a['body'], label=label, inserts={2: card} if card else None)}
      <p class="note">{esc(ui['disclaimer'])}</p>
{card}
{kz.slot(kz.BLOCK_DENSE_C, compact=True, label=label)}
      <section class="related">
        <h3>{esc(ui['read_also'])}</h3>
{related}
      </section>
    </article>"""
            (d / f"{slug}.html").write_text(
                page("article", a["title"], a["description"], main, True), encoding="utf-8")

        # home with the list
        cards = "\n".join(
            f'        <a class="js-int" href="{base}{t["slug"]}.html"><img src="/{ROOT}/t/{t["slug"]}.jpg" width="120" height="80" '
            f'alt="" loading="lazy"><span><span class="t">{esc(arts[t["slug"]]["title"])}</span>'
            f'<span class="d">{esc(arts[t["slug"]]["teaser"])}</span></span></a>' for t in mc.TOPICS)
        main = f"""    <div class="inner home">
      <h1>{esc(ui['home_title'])}</h1>
      <p class="intro">{esc(ui['home_intro'])}</p>
{card}
      <h2>{esc(ui['all_articles'])}</h2>
      <div class="cards">
{cards}
      </div>
    </div>"""
        (d / "index.html").write_text(page("home", ui["home_title"], ui["home_intro"], main, False), encoding="utf-8")

        # service pages
        for key in mc.PAGE_KEYS:
            p = pages_json[key]
            body = "\n".join(f"      <p>{esc(x)}</p>" for x in p["paras"])
            main = f"""    <div class="inner text">
      <h1>{esc(p['title'])}</h1>
{body}
      <a class="back js-int" href="{base}">← {esc(ui['nav_home'])}</a>
    </div>"""
            (d / f"{key}.html").write_text(page("text", p["title"], p["paras"][0][:150], main, False), encoding="utf-8")
        n_words = sum(words(a["body"]) for a in arts.values())
        slots = sum((d / f"{t['slug']}.html").read_text(encoding="utf-8").count('class="ad-slot') for t in mc.TOPICS)
        print(f"{route}: 10 статей ({n_words} слов), слотов {slots}, ярлык «{label}», html lang {cfg['html']}")
        built.append(route)
    # /blog/ itself: a plain language chooser (no ads, no loader)
    (out / "index.html").write_text(CHOOSER.format(
        css=css, brand=BRAND["name"], mark=BRAND["mark"], color=BRAND["color"], js=f"/{ROOT}/{js_name}", year=today.year,
        items="\n".join(f'      <a class="js-int" lang="{mc.HTML_LANG.get(r, r)}" href="/{ROOT}/{r}/">{esc(mc.NATIVE[r])}</a>'
                        for r in built)), encoding="utf-8")
    print(f"собрано: {out}  js {js_name}  языков {len(built)}")
    return built


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--langs", default="", help="comma separated routes, default: every language folder that exists (+ ch with de)")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-ebook", action="store_true", help="skip the PDF books (and so the offer cards): quick builds")
    ap.add_argument("--force", action="store_true", help="build a language even if the checker reports errors")
    a = ap.parse_args(argv)
    want = [x for x in a.langs.split(",") if x]
    if not want:
        want = [r for r in mc.LANGS if (ck.ART / r).is_dir()]
        if "de" in want:
            want.append("ch")                  # Switzerland comes with German
    good = []
    for r in want:
        src = mc.DERIVED[r]["from"] if r in mc.DERIVED else r
        errs, _ = ck.check_lang(src)
        if errs and not a.force:
            print(f"{r}: пропускаю, ошибок {len(errs)} (первая: {errs[0]})")
            continue
        good.append(r)
    if a.check:
        print("годятся:", good)
        return good
    return build(a.out, good, a.force, ebooks=not a.no_ebook)


if __name__ == "__main__":
    main()
