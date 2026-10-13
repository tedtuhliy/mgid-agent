"""Static build of the Kazakhstan version of the content site for MGID traffic: arcadiablog.com/dom/.

    python3 build.py --out /tmp/stage          # -> /tmp/stage/dom/ (index.html, rasteniya-osenyu.html, js, images)

Owner, 13.10 evening: «Запусти на этом сайте версию под Казахстан для теста, статьи обычные под аудитории 40+,
блоки органично вписать, трафик на MGID со ставкой 1 цент cpa tune, конверсию слать на каждый платный клик на Geozo».

Base: the production pages of the TikTok version (/sovety/, ops/content-arb in Tedbolt, branch claude/dr-cash-automation-20xngo),
same article text, same typography. Differences, all on purpose:
- no TikTok pixel, no beacon and no /click redirect: MGID visitors must not feed the TikTok pixel;
- the page is the article itself (teaser -> article, no showcase step), two articles that link to each other;
- Geozo blocks: our own pair dom-header / dom-feed (Geozo site 25953), so its statistics can be read apart from the
  TikTok version; at most four slots per page, none above the title, every one labelled «Реклама»;
- dom.js sends one signal per real click on a block (see the header of dom.js).
"""
import argparse
import hashlib
import html
import json
import shutil
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUTE = "dom"
BRAND = {"name": "Arcadia Blog", "tag": "советы", "mark": "A", "color": "#1f6f5c"}
LOADER = "https://cdn.ecstaticexistence.com/7czl17291/vli0pm30y8qh/786uvq768ypk0f4dm.go"
# Geozo blocks of site 25953 created 13.10 (UUIDs go into the markup, numeric ids 1283936 / 1283937 into the API)
BLOCK_HEADER = "a4ecaca6-cb0b-4e44-9323-355326c78357"      # dom-header
BLOCK_FEED = "eb58d5e5-77a6-4b0b-9a4c-b5233e12418b"        # dom-feed
# (file, article json, thumbnail used in «Читайте также»)
PAGES = [("index.html", "hranenie-produktov", "t1.jpg"), ("rasteniya-osenyu.html", "rasteniya-osenyu", "t4.jpg")]
JS_CFG = {"route": ROUTE, "lead": f"/{ROUTE}/lead", "minDwellMs": 700, "cooldownMs": 1200, "maxPerVisit": 6}
MONTHS = ["", "января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября",
          "ноября", "декабря"]
DISCLOSURE = ("Материалы носят информационный характер. На сайте размещена реклама партнёров — рекламные блоки "
              "помечены словом «Реклама». Мы используем cookies для работы сайта и рекламных блоков.")
COOKIE = "Мы используем cookies для работы сайта и рекламных блоков."
SLOT_BEFORE_H2 = {1: BLOCK_HEADER, 3: BLOCK_FEED, 6: BLOCK_FEED}      # which h2 the slot goes in front of
END_SLOT = BLOCK_FEED


def esc(s):
    return html.escape(str(s), quote=True)


def sha8(b):
    return hashlib.sha256(b).hexdigest()[:8]


def slot(uuid):
    return f'<div class="ad-slot"><span class="ad-label">Реклама</span><div data-gz-block="{uuid}"></div></div>'


def render(b):
    t = b["t"]
    if t == "p":
        return f'<p class="lead">{esc(b["x"])}</p>' if b.get("lead") else f'<p>{esc(b["x"])}</p>'
    if t == "h2":
        return f'<h2>{esc(b["x"])}</h2>'
    if t == "tip":
        return f'<div class="tip">{esc(b["x"])}</div>'
    if t == "ul":
        return "<ul>" + "".join(f"<li>{esc(i)}</li>" for i in b["x"]) + "</ul>"
    raise SystemExit(f"неизвестный тип блока {t}")


def body_html(blocks):
    out, h2 = [], 0
    for b in blocks:
        if b["t"] == "h2":
            h2 += 1
            if h2 in SLOT_BEFORE_H2:
                out.append(slot(SLOT_BEFORE_H2[h2]))
        out.append(render(b))
    return "\n".join(out)


def words(blocks):
    return sum(len((" ".join(b["x"]) if isinstance(b["x"], list) else b["x"]).split()) for b in blocks)


PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title} — {brand}</title>
<meta name="description" content="{description}">
<meta name="theme-color" content="{color}">
<meta name="robots" content="noindex,nofollow">
<link rel="preconnect" href="{origin}" crossorigin>
<link rel="dns-prefetch" href="{origin}">
<style>
{css}
</style>
<script async src="{loader}"></script>
<script src="{js}" defer></script>
</head>
<body data-page="article">
<div class="page">
  <header class="top">
    <div class="brand"><div class="brand-mark">{mark}</div><div class="brand-name">{brand} <span>· {tag}</span></div></div>
  </header>
  <main>
    <img class="hero" src="{hero}" width="1200" height="700" alt="{hero_alt}" fetchpriority="high">
    <article class="inner">
      <p class="rubric">{rubric}</p>
      <h1>{title}</h1>
      <p class="meta">{date} · {read}</p>
{body}
      <p class="note">{disclaimer}</p>
{end_slot}
      <section class="related">
        <h3>Читайте также</h3>
{related}
      </section>
    </article>
  </main>
  <footer>
    <nav>
      <a href="/about.html">О проекте</a>
      <a href="/contact.html">Контакты</a>
      <a href="/privacy.html">Конфиденциальность</a>
    </nav>
    <p>{disclosure}</p>
    <p>© {year} {brand}</p>
  </footer>
</div>
<div id="cookie" class="cookie" role="dialog" aria-label="Уведомление о cookies" hidden>
  <p>{cookie} <a href="/privacy.html">Подробнее</a></p>
  <div class="cookie-btns"><button id="cookie-ok" type="button">ОК</button></div>
</div>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out) / ROUTE
    shutil.rmtree(out, ignore_errors=True)
    (out / "img").mkdir(parents=True)

    js_src = (HERE / "dom.js").read_text(encoding="utf-8").replace("__CFG__", json.dumps(JS_CFG, ensure_ascii=False))
    js_name = f"{ROUTE}.{sha8(js_src.encode())}.js"
    (out / js_name).write_text(js_src, encoding="utf-8")
    css = (HERE / "style.css").read_text(encoding="utf-8").strip()
    origin = LOADER.split("/", 3)[0] + "//" + LOADER.split("/")[2]

    arts = {slug: json.loads((HERE / "articles" / f"{slug}.json").read_text(encoding="utf-8")) for _, slug, _ in PAGES}
    heroes = {}
    for slug, art in arts.items():
        buf = (HERE / "assets" / art["hero"]).read_bytes()
        heroes[slug] = f"{slug}.{sha8(buf)}.jpg"
        (out / heroes[slug]).write_bytes(buf)
    for f in sorted((HERE / "teasers").glob("*.jpg")):
        shutil.copy(f, out / "img" / f.name)

    today = date.today()
    for fname, slug, thumb in PAGES:
        art = arts[slug]
        related = "\n".join(
            f'        <a class="js-int" href="/{ROUTE}/{"" if o_file == "index.html" else o_file}">'
            f'<img src="/{ROUTE}/img/{o_thumb}" width="96" height="64" alt="" loading="lazy">'
            f'<span>{esc(arts[o_slug]["title"])}</span></a>'
            for o_file, o_slug, o_thumb in PAGES if o_slug != slug)
        page = PAGE.format(
            title=esc(art["title"]), brand=BRAND["name"], description=esc(art["description"]), color=BRAND["color"],
            origin=origin, css=css, loader=LOADER, js=js_name, mark=BRAND["mark"], tag=BRAND["tag"],
            hero=heroes[slug], hero_alt=esc(art["heroAlt"]), rubric=esc(art["rubric"]),
            date=f"{today.day} {MONTHS[today.month]} {today.year} г.",
            read=f"{max(2, round(words(art['body']) / 190))} мин чтения",
            body=body_html(art["body"]), disclaimer=esc(art["disclaimer"]), end_slot=slot(END_SLOT),
            related=related, disclosure=DISCLOSURE, year=today.year, cookie=COOKIE)
        (out / fname).write_text(page, encoding="utf-8")
        slots = page.count('class="ad-slot"')
        print(f"{fname}: {len(page)} знаков, слотов {slots}, статья «{art['title']}», {words(art['body'])} слов")
    print(f"собрано: {out}  js {js_name}")


if __name__ == "__main__":
    main()
