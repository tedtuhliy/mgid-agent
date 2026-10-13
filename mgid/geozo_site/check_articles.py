"""Format and sanity check of the language folders geozo_site/articles/<lang>/ (see articles/BRIEF.md).

    python3 geozo_site/check_articles.py            # every folder that exists
    python3 geozo_site/check_articles.py pl bg      # only these

Strict about the format (the generator relies on it), loose about style: style problems that a script can only
suspect are printed as WARN and do not fail the run. Exit code 1 when there is at least one ERROR.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import multi_config as mc  # noqa: E402

ART = HERE / "articles"
NUMBERED = {"food-storage": 9, "houseplants-autumn": 7}      # numbered sections: the title promises the number
ARTICLE_KEYS = ["rubric", "title", "teaser", "description", "heroAlt", "body"]
# characters that the language must show somewhere in its ten articles, and characters that betray a sibling language
MUST = {"bg": "ъщчшжя", "pl": "ąęłśżćńó", "ro": "ăâîșț", "cs": "řěůčžš", "pt": "ãçõéê", "it": "àèìòù", "es": "ñáéíóú",
        "de": "äöü", "hu": "őűáéíóö", "sk": "äľĺŕôčšž", "sl": "čšž", "sr": "čšžćđ"}
FORBID = {"sk": "řěů", "cs": "ĺľŕôä", "pl": "ăřěůșț", "sl": "ćđ", "sr": "", "pt": "ñ", "es": "ãõ", "it": "ñãõ",
          "ro": "ş" + "ţ", "hu": "ãõñł"}                      # ş/ţ are the cedilla forms, wrong for Romanian
HEALTHY = re.compile(r"\bdetox|\bimmun|\bimun|\bdiabet|\bcholester|\bkolester|\bcancer|\btumo|\brheum|\barthr|\bartrit|"
                     r"\bslimm|\bmiracle|\bcure\b|\bheals?\b|\btherap|\bterap|\blečen|\bleczen|\bliječ|\bgyógy|"
                     r"\bvindec|\bcurar\b|\blecui|\bheilt\b|\bheilung|\bguar[ií]r|\bguaris|\blijek|лечени|лекува|имунит|детокс",
                     re.I)
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿]")
BAD_MARKUP = re.compile(r"<[^>]*>|\*\*|^#|\]\(|https?://|www\.|\{|\}")


def words(blocks):
    n = 0
    for b in blocks:
        n += len(" ".join(b["x"]).split()) if isinstance(b["x"], list) else len(b["x"].split())
    return n


def texts(blocks):
    for b in blocks:
        for t in (b["x"] if isinstance(b["x"], list) else [b["x"]]):
            yield b["t"], t


def letters(s):
    return [c for c in s if c.isalpha()]


def script_share(s):
    ls = letters(s)
    if not ls:
        return 0.0
    return sum(1 for c in ls if "Ѐ" <= c <= "ӿ") / len(ls)


def check_lang(lang):
    errs, warns = [], []
    cfg = mc.LANGS[lang]
    d = ART / lang

    def E(m):
        errs.append(m)

    def W(m):
        warns.append(m)

    if not d.is_dir():
        return [f"нет папки {d}"], []
    alltext = []
    titles = Counter()
    paras = Counter()
    for slug in mc.SLUGS:
        f = d / f"{slug}.json"
        if not f.exists():
            E(f"{slug}: нет файла")
            continue
        try:
            a = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            E(f"{slug}: JSON не читается: {e}")
            continue
        for k in ARTICLE_KEYS:
            if k not in a:
                E(f"{slug}: нет поля {k}")
        if any(k not in a for k in ARTICLE_KEYS):
            continue
        for k in ("rubric", "title", "teaser", "description", "heroAlt"):
            if not isinstance(a[k], str) or not a[k].strip():
                E(f"{slug}: поле {k} пустое")
        body = a["body"]
        if not isinstance(body, list) or not body:
            E(f"{slug}: body пустой")
            continue
        types = [b.get("t") for b in body]
        if any(t not in ("p", "h2", "tip", "ul") for t in types):
            E(f"{slug}: недопустимые типы блоков {sorted(set(types) - {'p', 'h2', 'tip', 'ul'})}")
            continue
        if not body[0].get("lead") or types[0] != "p":
            E(f"{slug}: первый блок должен быть p с lead:true")
        if len(body) < 2 or types[1] != "p" or body[1].get("lead"):
            E(f"{slug}: второй блок должен быть обычным p")
        h2s = [b["x"] for b in body if b["t"] == "h2"]
        nonh2 = [b for b in body if b["t"] != "h2"]
        if len(h2s) < 6:
            E(f"{slug}: разделов h2 {len(h2s)}, нужно не меньше 6")
        if not 14 <= len(nonh2) <= 26:
            E(f"{slug}: блоков не-h2 {len(nonh2)}, нужно 14-26")
        if sum(1 for t in types if t == "ul") != 1:
            E(f"{slug}: нужен ровно один список ul")
        else:
            ul = next(b for b in body if b["t"] == "ul")
            if not isinstance(ul["x"], list) or not 4 <= len(ul["x"]) <= 6:
                E(f"{slug}: в ul должно быть 4-6 пунктов")
            i = body.index(ul)
            if i == 0 or types[i - 1] != "h2" or types[-1] != "p" or i != len(body) - 2:
                E(f"{slug}: порядок конца: h2, ul, закрывающий p")
        if sum(1 for t in types if t == "tip") > 1:
            E(f"{slug}: больше одного tip")
        for i, b in enumerate(body):
            if b["t"] == "h2" and i + 1 < len(body) and body[i + 1]["t"] == "h2":
                E(f"{slug}: два h2 подряд")
            if b["t"] in ("p", "tip", "h2") and not isinstance(b["x"], str):
                E(f"{slug}: x блока {b['t']} должен быть строкой")
        w = words(body)
        if not 360 <= w <= 600:
            E(f"{slug}: слов {w}, нужно 380-520 (допуск 360-600)")
        elif not 380 <= w <= 520:
            W(f"{slug}: слов {w}")
        if not 40 <= len(a["title"]) <= 90:
            E(f"{slug}: заголовок {len(a['title'])} знаков, нужно 40-90")
        if not 110 <= len(a["teaser"]) <= 260:
            E(f"{slug}: teaser {len(a['teaser'])} знаков, нужно 110-260")
        if not 80 <= len(a["description"]) <= 190:
            E(f"{slug}: description {len(a['description'])} знаков, нужно 80-190")
        if "!" in a["title"] or any("!" in h for h in h2s):
            E(f"{slug}: восклицательный знак в заголовке")
        n = NUMBERED.get(slug)
        numbered = [h for h in h2s if re.match(r"\d+\.\s", h)]
        if n:
            want = [f"{i}. " for i in range(1, n + 1)]
            if [h[:len(w_)] for h, w_ in zip(numbered, want)] != want or len(numbered) != n:
                E(f"{slug}: нужны ровно {n} пронумерованных разделов «1.»…«{n}.», найдено {len(numbered)}")
        elif numbered:
            E(f"{slug}: разделы не должны быть пронумерованы")
        for kind, t in list(texts(body)) + [("title", a["title"]), ("teaser", a["teaser"]),
                                            ("description", a["description"]), ("heroAlt", a["heroAlt"]),
                                            ("rubric", a["rubric"])]:
            if BAD_MARKUP.search(t):
                E(f"{slug}: разметка/ссылка/плейсхолдер в тексте: {t[:60]!r}")
            if EMOJI.search(t):
                E(f"{slug}: эмодзи в тексте: {t[:60]!r}")
            if kind == "p" and len(t) > 760:
                W(f"{slug}: абзац {len(t)} знаков: {t[:50]!r}")
            if kind == "p":
                paras[t] += 1
            alltext.append(t)
            m = HEALTHY.search(t)
            if m:
                W(f"{slug}: подозрение на лечебное обещание «{m.group(0)}»: …{t[max(0, m.start() - 30):m.end() + 30]}…")
        titles[a["title"]] += 1
        # numbers in the title promise
    for t, c in titles.items():
        if c > 1:
            E(f"повторяется заголовок {t!r}")
    for t, c in paras.items():
        if c > 1:
            E(f"абзац повторяется {c} раза: {t[:60]!r}")

    # script and language markers over everything written
    joined = "\n".join(alltext)
    sh = script_share(joined)
    if cfg["script"] == "cyrillic" and sh < 0.85:
        E(f"доля кириллицы {sh:.0%}, нужен болгарский на кириллице")
    if cfg["script"] == "latin" and sh > 0.01:
        E(f"кириллица в латинском тексте: {sh:.1%}")
    if alltext:
        low = joined.lower()
        found = [c for c in MUST.get(lang, "") if c in low]
        if len(found) < max(2, len(MUST.get(lang, "")) // 2):
            E(f"не видно характерных букв языка: нашлись {''.join(found)!r} из {MUST.get(lang, '')!r}")
        bad = [c for c in FORBID.get(lang, "") if c in low]
        if bad:
            E(f"символы чужого языка {''.join(bad)!r}")

    # ui.json
    f = d / "ui.json"
    if not f.exists():
        E("нет ui.json")
    else:
        try:
            ui = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            ui = {}
            E(f"ui.json не читается: {e}")
        for k in mc.UI_KEYS:
            if k not in ui or (isinstance(ui[k], str) and not ui[k].strip()):
                E(f"ui.json: нет ключа {k}")
        if ui:
            if "{n}" not in str(ui.get("read_min", "")):
                E("ui.json: read_min без {n}")
            if not (isinstance(ui.get("months"), list) and len(ui["months"]) == 12 and all(isinstance(x, str) and x for x in ui["months"])):
                E("ui.json: months должен быть списком из 12 строк")
            df = str(ui.get("date_fmt", ""))
            if not all(x in df for x in ("{d}", "{month}", "{y}")):
                E("ui.json: date_fmt должен содержать {d}, {month} и {y}")
            if cfg["ad_label"].lower() not in str(ui.get("disclosure", "")).lower():
                E(f"ui.json: в disclosure нет слова-метки «{cfg['ad_label']}»")
            for k in ("brand_tag", "cookie_ok"):
                if len(str(ui.get(k, ""))) > 30:
                    W(f"ui.json: {k} длинный")
            flat = [x for v in ui.values() for x in (v if isinstance(v, list) else [v]) if isinstance(x, str)]
            for x in flat:
                if BAD_MARKUP.search(x.replace("{n}", "").replace("{d}", "").replace("{month}", "").replace("{y}", "")):
                    E(f"ui.json: разметка или ссылка в строке {x[:60]!r}")

    # pages.json
    f = d / "pages.json"
    if not f.exists():
        E("нет pages.json")
    else:
        try:
            pg = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            pg = {}
            E(f"pages.json не читается: {e}")
        want_n = {"about": 3, "contact": 2, "privacy": 5}
        for k in mc.PAGE_KEYS:
            p = pg.get(k) or {}
            if not isinstance(p.get("title"), str) or not p["title"].strip():
                E(f"pages.json: у {k} нет title")
            ps = p.get("paras")
            if not (isinstance(ps, list) and len(ps) == want_n[k] and all(isinstance(x, str) and x.strip() for x in ps)):
                E(f"pages.json: у {k} должно быть {want_n[k]} абзаца(ов)")
        if "contact@arcadiablog.com" not in json.dumps(pg.get("contact", {}), ensure_ascii=False):
            E("pages.json: в contact нет contact@arcadiablog.com")

    # teasers.json
    f = d / "teasers.json"
    if not f.exists():
        E("нет teasers.json")
    else:
        try:
            tz = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            tz = []
            E(f"teasers.json не читается: {e}")
        if sorted(x.get("article") for x in tz if isinstance(x, dict)) != sorted(mc.TEASER_SLUGS):
            E(f"teasers.json: нужны статьи {mc.TEASER_SLUGS}")
        for x in tz:
            t = (x or {}).get("title", "")
            if not 20 <= len(t) <= 65:
                E(f"teasers.json: заголовок {len(t)} знаков (нужно 20-65): {t!r}")
            if "!" in t:
                E(f"teasers.json: восклицательный знак: {t!r}")
            if any(len(w_) >= 4 and w_.isupper() for w_ in re.findall(r"\w+", t)):
                E(f"teasers.json: слово заглавными: {t!r}")
            if BAD_MARKUP.search(t) or EMOJI.search(t):
                E(f"teasers.json: разметка или эмодзи: {t!r}")
            m = HEALTHY.search(t)
            if m:
                W(f"teasers.json: подозрение на лечебное обещание «{m.group(0)}»: {t!r}")
    return errs, warns


def main(argv):
    langs = argv or [l for l in mc.LANGS if (ART / l).is_dir()]
    bad = 0
    for lang in langs:
        if lang not in mc.LANGS:
            print(f"{lang}: нет в multi_config.LANGS")
            bad += 1
            continue
        errs, warns = check_lang(lang)
        for w in warns:
            print(f"WARN  {lang}: {w}")
        for e in errs:
            print(f"ERROR {lang}: {e}")
        print(f"{lang}: {'OK' if not errs else str(len(errs)) + ' ошибок'}" + (f", предупреждений {len(warns)}" if warns else ""))
        bad += bool(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
