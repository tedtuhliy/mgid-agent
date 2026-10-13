"""Static build of the Kazakhstan version of the content site for MGID traffic: arcadiablog.com/dom/ and /dom2/.

    python3 build.py --out /tmp/stage                    # both variants -> /tmp/stage/dom/ and /tmp/stage/dom2/
    python3 build.py --out /tmp/stage --variant dom2     # only the dense one

Two variants of the same two articles (each is a uniform page for everybody, moderators included):
- dom  : the moderate layout, 4 labelled slots a page with one ad each. MGID approved the teasers that point to it on
         13.10 evening, so it is not changed after the approval.
- dom2 : the dense layout the owner asked for the same evening («Почему так мало блоков? Нужно максимально агрессивно
         ... максимум тизеров в блок»): a slot after the lead and after every second block of text, a ten-ad block at
         the end, compact cards. It has its own address, its own MGID campaign and its own moderation.

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
import re
import shutil
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUTE = "dom"
BRAND = {"name": "Arcadia Blog", "tag": "советы", "mark": "A", "color": "#1f6f5c"}
LOADER = "https://cdn.ecstaticexistence.com/7czl17291/vli0pm30y8qh/786uvq768ypk0f4dm.go"
# Geozo blocks of site 25953 created 13.10 (UUIDs go into the markup, numeric ids 1283938 / 1283939 into the API).
# Created directly with template 16003 (image on top, 16:9, no button). The first pair, dom-header / dom-feed
# (1283936 / 1283937), was made with 16006 and switched by PUT, and Geozo's render nodes kept serving the old template
# for hours, so a fresh pair was made instead.
BLOCK_HEADER = "dffc5623-f12c-4c85-8cb1-efa1a2fc617f"      # dom2-header
BLOCK_FEED = "68d5f52f-27f7-4157-b09c-c2da3a2b87b3"        # dom2-feed
# (file, article json, thumbnail used in «Читайте также»)
PAGES = [("index.html", "hranenie-produktov", "t1.jpg"), ("rasteniya-osenyu.html", "rasteniya-osenyu", "t4.jpg")]


def js_cfg(route):
    """Same keys and order as before the second variant, so the moderate build stays byte for byte what is deployed."""
    return {"route": route, "lead": RELAY, "minDwellMs": 700, "cooldownMs": 1200, "maxPerVisit": 6}


MONTHS = ["", "января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября",
          "ноября", "декабря"]
DISCLOSURE = ("Материалы носят информационный характер. На сайте размещена реклама партнёров — рекламные блоки "
              "помечены словом «Реклама». Мы используем cookies для работы сайта и рекламных блоков.")
COOKIE = "Мы используем cookies для работы сайта и рекламных блоков."
SLOT_BEFORE_H2 = {1: BLOCK_HEADER, 3: BLOCK_FEED, 6: BLOCK_FEED}      # which h2 the slot goes in front of
END_SLOT = BLOCK_FEED
# Dense variant (/dom2/), Geozo blocks of site 25953 created 13.10 20:10 UTC from the same template 16003, one column
# wide, mediaVertical = number of ads (geozo_blocks.py create NAME FEED). The panel allows 10 rows at most.
BLOCK_DENSE_A = "d267be0c-c55b-4537-9b72-dbe50ce69715"     # dom3-a, id 1283940, 3 ads: right after the lead
BLOCK_DENSE_B = "eeae7fee-98e9-4f6c-b6c3-db62ef62204e"     # dom3-b, id 1283941, 4 ads: after every second block of text
BLOCK_DENSE_C = "1174d6fa-d808-4923-8121-f589efb0e21f"     # dom3-c, id 1283942, 10 ads: end of the article
DENSE_ADS = {BLOCK_DENSE_A: 3, BLOCK_DENSE_B: 4, BLOCK_DENSE_C: 10}
VARIANTS = {"dom": {"dense": False}, "dom2": {"dense": True}}
RELAY = "/dom/lead"                    # one relay for both variants (the nginx location is exact: = /dom/lead)
DENSE_EVERY = 2                        # dense: a slot after the lead, then after every 2nd block of text


def esc(s):
    return html.escape(str(s), quote=True)


def sha8(b):
    return hashlib.sha256(b).hexdigest()[:8]


def slot(uuid, compact=False, label="Реклама"):
    cls = "ad-slot compact" if compact else "ad-slot"
    return f'<div class="{cls}"><span class="ad-label">{label}</span><div data-gz-block="{uuid}"></div></div>'


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


def body_html_dense(blocks, label="Реклама"):
    """A slot right after the lead, then after every DENSE_EVERY-th block of text (the lead counts as the first); never
    between a heading and its first paragraph, never right before the closing slot of the page. `label` is the word
    for «advertisement» in the page's language."""
    out, texts = [], 0
    last = len(blocks) - 1
    for i, b in enumerate(blocks):
        out.append(render(b))
        if b["t"] == "h2":
            continue
        texts += 1
        if i == last:
            continue
        if texts == 1:
            out.append(slot(BLOCK_DENSE_A, compact=True, label=label))
        elif texts % DENSE_EVERY == 1:
            out.append(slot(BLOCK_DENSE_B, compact=True, label=label))
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


def build_variant(route, dense, out_root):
    out = Path(out_root) / route
    shutil.rmtree(out, ignore_errors=True)
    (out / "img").mkdir(parents=True)

    js_src = (HERE / "dom.js").read_text(encoding="utf-8").replace("__CFG__", json.dumps(js_cfg(route), ensure_ascii=False))
    js_name = f"{route}.{sha8(js_src.encode())}.js"
    (out / js_name).write_text(js_src, encoding="utf-8")
    css = (HERE / "style.css").read_text(encoding="utf-8").strip()
    if dense:
        css += "\n" + (HERE / "dense.css").read_text(encoding="utf-8").strip()
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
            f'        <a class="js-int" href="/{route}/{"" if o_file == "index.html" else o_file}">'
            f'<img src="/{route}/img/{o_thumb}" width="96" height="64" alt="" loading="lazy">'
            f'<span>{esc(arts[o_slug]["title"])}</span></a>'
            for o_file, o_slug, o_thumb in PAGES if o_slug != slug)
        page = PAGE.format(
            title=esc(art["title"]), brand=BRAND["name"], description=esc(art["description"]), color=BRAND["color"],
            origin=origin, css=css, loader=LOADER, js=js_name, mark=BRAND["mark"], tag=BRAND["tag"],
            hero=heroes[slug], hero_alt=esc(art["heroAlt"]), rubric=esc(art["rubric"]),
            date=f"{today.day} {MONTHS[today.month]} {today.year} г.",
            read=f"{max(2, round(words(art['body']) / 190))} мин чтения",
            body=body_html_dense(art["body"]) if dense else body_html(art["body"]), disclaimer=esc(art["disclaimer"]),
            end_slot=slot(BLOCK_DENSE_C, compact=True) if dense else slot(END_SLOT),
            related=related, disclosure=DISCLOSURE, year=today.year, cookie=COOKIE)
        (out / fname).write_text(page, encoding="utf-8")
        slots = page.count('class="ad-slot')
        ads = sum(DENSE_ADS.get(u, 1) for u in re.findall(r'data-gz-block="([0-9a-f-]+)"', page))
        print(f"{route}/{fname}: {len(page)} знаков, слотов {slots}, объявлений до {ads}, статья «{art['title']}», "
              f"{words(art['body'])} слов")
    print(f"собрано: {out}  js {js_name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--variant", choices=sorted(VARIANTS) + ["all"], default="all")
    a = ap.parse_args()
    for route, cfg in VARIANTS.items():
        if a.variant in ("all", route):
            build_variant(route, cfg["dense"], a.out)


if __name__ == "__main__":
    main()
