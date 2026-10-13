"""Build the free e-book (PDF) of a language from its ten articles.

    python3 geozo_site/make_ebooks.py --out /tmp/stage [--langs pl,de]     # -> /tmp/stage/blog/ebook/

Owner, 14.10 night: «А что может быть кроме подписки? Может скачивание электронной книги?» — a real action that goes
alongside the clicks on the ad blocks and gives MGID a conversion that is worth something to a visitor. The book is
compiled from the texts that already exist: a cover (title, subtitle, a mosaic of four photos), an introduction, a table
of contents, the ten articles as chapters, a closing page. No ads, no tracking, no registration: the offer card on the
article pages (build_multi.py) links to /blog/dl/<lang>.pdf, nginx counts the request and tells MGID about it.

Per route: ebook/<lang>.pdf, ebook/cover-<lang>.jpg (the cover as the offer card shows it), and ebook/pages.json with the
real page counts (the card prints «{pages} pages»). A route without ebook.json gets no book and no card.
The page is A5, margins by @page, page numbers by @page margin boxes (Chromium 131+; the cover has none).
"""
import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_articles as ck  # noqa: E402
import multi_config as mc  # noqa: E402

EXE = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
BRAND = {"name": "Arcadia Blog", "mark": "A", "color": "#1f6f5c", "accent": "#d9482b"}
MOSAIC = ["food-storage", "herbs-in-a-jar", "houseplants-autumn", "lavender"]      # the four photos of the cover

CSS = """
@page { size: 148mm 210mm; margin: 14mm 12mm 16mm 12mm;
        @bottom-center { content: counter(page); font: 8pt Inter, sans-serif; color: #7b857f; } }
@page cover { margin: 0; @bottom-center { content: none; } }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font: 9.4pt/1.5 Inter, "DejaVu Sans", sans-serif; color: #1b1f1d; }
.cover { page: cover; width: 148mm; height: 210mm; position: relative; overflow: hidden; background: #1f6f5c; color: #fff;
         break-after: page; }
.cover .top { height: 118mm; padding: 16mm 14mm 0; }
.cover .brand { display: flex; align-items: center; gap: 3mm; font-weight: 700; font-size: 10pt; letter-spacing: .02em; }
.cover .mark { width: 8mm; height: 8mm; border: .6mm solid #d9482b; display: flex; align-items: center; justify-content: center;
               font-weight: 700; font-size: 10pt; }
.cover h1 { font-size: 25pt; line-height: 1.12; margin: 13mm 0 5mm; font-weight: 800; }
.cover .sub { font-size: 11pt; line-height: 1.4; opacity: .9; margin: 0; }
.cover .mosaic { position: absolute; left: 0; right: 0; bottom: 0; height: 92mm; display: grid; grid-template-columns: 1fr 1fr;
                 grid-template-rows: 1fr 1fr; gap: 1mm; background: #fff; }
.cover .mosaic img { width: 100%; height: 100%; object-fit: cover; display: block; }
.sheet { break-after: page; }
.sheet h2.big { font-size: 17pt; margin: 6mm 0 6mm; line-height: 1.2; }
.intro p { font-size: 10.5pt; line-height: 1.6; }
.intro .brand { margin-top: 12mm; color: #5f6a64; font-size: 8.5pt; }
.toc ol { list-style: none; padding: 0; margin: 0; counter-reset: ch; }
.toc li { padding: 2.1mm 0; border-bottom: .2mm solid #e6e9e6; counter-increment: ch; }
.toc a { color: #1b1f1d; text-decoration: none; display: block; }
.toc .n { display: block; font-size: 7.5pt; text-transform: uppercase; letter-spacing: .08em; color: #1f6f5c; font-weight: 700; }
.toc .t { font-size: 10pt; font-weight: 600; line-height: 1.28; }
.chapter { break-before: page; }
.chapter .label { font-size: 8pt; text-transform: uppercase; letter-spacing: .1em; color: #1f6f5c; font-weight: 700; margin: 0 0 2mm; }
.chapter h1 { font-size: 18pt; line-height: 1.2; margin: 0 0 5mm; font-weight: 800; }
.chapter img.hero { width: 100%; height: 50mm; object-fit: cover; border-radius: 1.5mm; display: block; margin: 0 0 4.5mm; }
.chapter p { margin: 0 0 3mm; orphans: 3; widows: 3; }
.chapter p.lead { font-weight: 600; font-size: 10.4pt; }
.chapter h2 { font-size: 12pt; line-height: 1.28; margin: 5mm 0 1.8mm; break-after: avoid; }
.chapter .tip { background: #f1f7f4; border-left: 1.2mm solid #1f6f5c; padding: 3mm 3.4mm; margin: 0 0 3.6mm; border-radius: 1mm;
                break-inside: avoid; }
.chapter ul { margin: 0 0 3.4mm; padding-left: 5mm; }
.chapter li { margin: 0 0 1.6mm; }
.chapter .note { margin-top: 6mm; font-size: 7.8pt; color: #5f6a64; border-top: .2mm solid #e6e9e6; padding-top: 2.5mm; }
.closing { break-before: page; text-align: left; padding-top: 30mm; }
.closing h2 { font-size: 17pt; margin: 0 0 5mm; }
.closing p { font-size: 10.4pt; line-height: 1.6; }
.closing .brand { margin-top: 14mm; color: #5f6a64; font-size: 8.5pt; }
"""


def esc(s):
    return html.escape(str(s), quote=True)


def load(route):
    """(ui, ebook, articles) of a route; ch is derived from de, like in build_multi."""
    import build_multi as bm
    derived = mc.DERIVED.get(route)
    src = derived["from"] if derived else route
    d = ck.ART / src
    ui = json.loads((d / "ui.json").read_text(encoding="utf-8"))
    eb = json.loads((d / "ebook.json").read_text(encoding="utf-8"))
    arts = {s: json.loads((d / f"{s}.json").read_text(encoding="utf-8")) for s in mc.SLUGS}
    if derived:
        def swap(t):
            for a, b in derived["replace"]:
                t = t.replace(a, b)
            return t
        ui, eb, arts = (bm.walk(x, swap) for x in (ui, eb, arts))
    return ui, eb, arts


def block(b):
    t = b["t"]
    if t == "p":
        return f'<p class="lead">{esc(b["x"])}</p>' if b.get("lead") else f"<p>{esc(b['x'])}</p>"
    if t == "h2":
        return f"<h2>{esc(b['x'])}</h2>"
    if t == "tip":
        return f'<div class="tip">{esc(b["x"])}</div>'
    if t == "ul":
        return "<ul>" + "".join(f"<li>{esc(i)}</li>" for i in b["x"]) + "</ul>"
    raise SystemExit(f"неизвестный тип блока {t}")


def small_images(tmp_dir):
    """The photos of the book at 800 px and quality 72: a book of 0.6 MB instead of 2 MB downloads in a second on a phone."""
    from PIL import Image
    d = Path(tmp_dir)
    d.mkdir(parents=True, exist_ok=True)
    for t in mc.TOPICS:
        out = d / f"{t['slug']}.jpg"
        if not out.exists():
            Image.open(HERE / "assets" / f"{t['slug']}.jpg").convert("RGB").resize((800, 467), Image.LANCZOS).save(
                out, quality=72, optimize=True)
    return d


def book_html(route, ui, eb, arts, lang_html, img_dir=None):
    base = Path(img_dir) if img_dir else HERE / "assets"
    img = lambda slug: (base / f"{slug}.jpg").resolve().as_uri()                       # noqa: E731
    mosaic = "".join(f'<img src="{img(s)}" alt="">' for s in MOSAIC)
    toc = "".join(
        f'<li><a href="#c{i}"><span class="n">{esc(eb["chapter"])} {i}</span><span class="t">{esc(arts[t["slug"]]["title"])}</span></a></li>'
        for i, t in enumerate(mc.TOPICS, 1))
    chapters = "".join(
        f'<section class="chapter" id="c{i}"><p class="label">{esc(eb["chapter"])} {i}</p><h1>{esc(arts[t["slug"]]["title"])}</h1>'
        f'<img class="hero" src="{img(t["slug"])}" alt="{esc(arts[t["slug"]]["heroAlt"])}">'
        + "".join(block(b) for b in arts[t["slug"]]["body"])
        + f'<p class="note">{esc(ui["disclaimer"])}</p></section>'
        for i, t in enumerate(mc.TOPICS, 1))
    return f"""<!DOCTYPE html><html lang="{lang_html}"><head><meta charset="utf-8"><title>{esc(eb['title'])}</title>
<style>{CSS}</style></head><body>
<section class="cover"><div class="top"><div class="brand"><div class="mark">{BRAND['mark']}</div>{BRAND['name']}</div>
<h1>{esc(eb['title'])}</h1><p class="sub">{esc(eb['subtitle'])}</p></div><div class="mosaic">{mosaic}</div></section>
<section class="sheet intro"><h2 class="big">{esc(eb['title'])}</h2><p>{esc(eb['intro'])}</p>
<p class="brand">© 2026 {BRAND['name']}</p></section>
<section class="sheet toc"><h2 class="big">{esc(eb['toc'])}</h2><ol>{toc}</ol></section>
{chapters}
<section class="closing"><h2>{esc(eb['closing_title'])}</h2><p>{esc(eb['closing_text'])}</p>
<p class="brand">{BRAND['name']} · arcadiablog.com</p></section>
</body></html>"""


def build(routes, out_root):
    """Write ebook/<route>.pdf, ebook/cover-<route>.jpg and ebook/pages.json under out_root/blog; returns {route: pages}."""
    from playwright.sync_api import sync_playwright
    from pypdf import PdfReader
    from PIL import Image
    import io
    out = Path(out_root) / "blog" / "ebook"
    out.mkdir(parents=True, exist_ok=True)
    img_dir = small_images(out / "_img")
    pages = {}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=EXE, args=["--no-sandbox"])
        for route in routes:
            ui, eb, arts = load(route)
            lang_html = (mc.LANGS.get(route) or {"html": mc.DERIVED[route]["html"]})["html"]
            doc = book_html(route, ui, eb, arts, lang_html, img_dir)
            tmp = out / f"_{route}.html"
            tmp.write_text(doc, encoding="utf-8")
            page = b.new_page(viewport={"width": 560, "height": 794})
            page.goto(tmp.resolve().as_uri(), wait_until="load")
            page.wait_for_timeout(300)
            pdf = out / f"{route}.pdf"
            page.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
            png = page.locator(".cover").screenshot()
            page.close()
            tmp.unlink()
            im = Image.open(io.BytesIO(png)).convert("RGB").resize((280, 397), Image.LANCZOS)
            im.save(out / f"cover-{route}.jpg", quality=84, optimize=True)
            pages[route] = len(PdfReader(str(pdf)).pages)
            print(f"{route}: {pages[route]} стр., {pdf.stat().st_size // 1024} КБ, «{eb['title']}»")
        b.close()
    shutil.rmtree(img_dir, ignore_errors=True)
    (out / "pages.json").write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return pages


def routes_with_book(routes=None):
    got = []
    for r in routes or (list(mc.LANGS) + list(mc.DERIVED)):
        src = mc.DERIVED[r]["from"] if r in mc.DERIVED else r
        if (ck.ART / src / "ebook.json").exists():
            got.append(r)
    return got


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--langs", default="")
    a = ap.parse_args(argv)
    want = [x for x in a.langs.split(",") if x] or None
    routes = routes_with_book(want)
    if not routes:
        raise SystemExit("нет ни одного ebook.json")
    build(routes, a.out)


if __name__ == "__main__":
    main()
