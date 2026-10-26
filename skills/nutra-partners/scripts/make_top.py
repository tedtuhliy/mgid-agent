"""Top offers of Aray and Dr.Cash in one markdown file (26.10). Offline: it only reads the dumps the browser scripts wrote.

    OUT_DIR=<dir> node aray_offers.mjs dump          # aray_offers.json
    OUT_DIR=<dir> node dr_offers.mjs dump            # dr_offers.json and dr_category.json
    OUT_DIR=<dir> python3 make_top.py                # <dir>/top-offers-<date>.md

Aray has no rating, approval or EPC in its data (EPC is filled for one offer of 287), so there the "top" is by payout and by access; Dr.Cash has the
network rank (`rank`, lower is better) and the approval: 100 % approval on offers ranked 1000+ is noise (a handful of leads), so the ranking never uses
it. "Native" is read from the rules text of the offer (`source`): да = named as allowed, НЕЛЬЗЯ = named as forbidden, ? = not said, ask the manager.
The list is by the networks' numbers and is NOT a check of the landers (see SKILL.md, section 8).
"""
import os
import json, re, collections, html
from datetime import datetime, timezone
OUT = os.environ.get("OUT_DIR", ".")
def _p(*names):
    for n in names:
        if os.path.exists(os.path.join(OUT, n)): return os.path.join(OUT, n)
    raise SystemExit(f"no {names[0]} in {OUT}: run the dump scripts first")
dr = json.load(open(_p("dr_offers.json", "dr_all_offers.json"))); ar = json.load(open(_p("aray_offers.json")))
cats = {str(i["value"]): i["label"].strip() for i in json.load(open(_p("dr_category.json")))["payload"]["items"]}
STOP = {"free","low","price","lowprice","fullprice","full","lp","fp","for","tiktok","tik","tok","new","cod","cpa","premium","forte","plus","caps","capsules","drops","gel","cream","spray","balm","serum"}
def norm(name):
    n = re.sub(r"\(.*?\)", " ", name.lower()); n = re.sub(r"\s+-\s+[a-z]{2}\s*$", " ", n)
    toks = [t for t in re.findall(r"[a-zа-я0-9]+", n) if t not in STOP]
    return " ".join(toks[:2]) if toks else ""
def acc(x): return re.search(r" - ([A-Z]{2})\s*$", str(x.get("name") or ""))
def acountry(x): m = acc(x); return m.group(1) if m else "WW"
def apay(x): return float(((x.get("payout") or [{}])[0]).get("amount") or 0)
def aname(x): return re.sub(r"\s+-\s+[A-Z]{2}\s*$", "", x["name"]).strip()
def native(x):
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x.get("source") or "")).lower())
    key = "native" if "native" in t else ("teaser" if "teaser" in t else None)
    if not key:
        return "all" if re.search(r"all (traffic )?sources? (allowed|are allowed)", t) else "?"
    before = t[max(0, t.find(key) - 160):t.find(key)]
    neg = max(before.rfind(w) for w in ("prohibit", "forbid", "not allowed", "restricted", "except"))
    pos = max(before.rfind(w) for w in ("allowed traffic", "allowed:", "allowed sources", "allowed"))
    return "НЕЛЬЗЯ" if neg > pos else "да"
live = [x for x in dr if x.get("status") == 2]
for x in live: x["_nat"] = native(x)
def dline(x, rank=True):
    g = ",".join(x.get("geo_code") or [])[:14]
    return f"| {x['rank']} | {x['name'].strip()[:30]} ({x['id']}) | {g} | ${float(x['rate']):.0f} | {x['approved']:.0f}% | {cats.get(str(x.get('category_id')), '?')[:18]} | {x['_nat']} |"
out = []
w = out.append
w("# Топ офферы: Aray и Dr.Cash")
def _day(path): return datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).strftime("%d.%m.%Y")
w(f"Собрано {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}. Aray: {len(ar)} офферов (выгрузка от {_day(_p('aray_offers.json'))}). Dr.Cash: {len(dr)} офферов, активных {len(live)} (выгрузка от {_day(_p('dr_offers.json', 'dr_all_offers.json'))}).")
w("")
w("**Как считал.** У Aray в кабинете нет ни рейтинга, ни апрува, ни EPC (EPC заполнен у одного оффера из 287: Duston Gel, Чили, 0.668), поэтому там «топ» только по выплате и по доступу. У Dr.Cash есть рейтинг сети (`rank`, чем меньше, тем выше) и апрув. "
  "**Апрув 100 % у офферов с рейтингом 1000+ это шум** (десятки лидов или меньше), по нему не ранжирую. «Нативка» — по тексту правил оффера в Dr.Cash: да (прямо разрешена), НЕЛЬЗЯ (запрещена), ? (в правилах не сказано, уточнять у менеджера).")
w("")
w("## 1. Aray: офферы, к которым у нас уже есть доступ (25)")
w("| оффер (id) | гео | вертикаль | выплата |"); w("|---|---|---|---|")
for x in sorted([x for x in ar if x.get("is_access_granted")], key=lambda x: -apay(x)):
    w(f"| {aname(x)} ({x['id']}) | {acountry(x)} | {', '.join(x.get('vertical') or [])[:26]} | ${apay(x):.1f} |")
w("")
w("## 2. Aray: самые высокие выплаты, доступа нет (нужен запрос через Tickets)")
w("| оффер (id) | гео | вертикаль | выплата |"); w("|---|---|---|---|")
for x in sorted([x for x in ar if not x.get("is_access_granted") and x.get("flow") == "COD"], key=lambda x: -apay(x))[:25]:
    w(f"| {aname(x)} ({x['id']}) | {acountry(x)} | {', '.join(x.get('vertical') or [])[:26]} | ${apay(x):.1f} |")
w("")
w("## 2б. Aray по гео, где мы сейчас работаем (доступа нет, выплата за лид)")
for g in ["TR", "AZ", "UZ", "KZ", "IT"]:
    xs = sorted([x for x in ar if acountry(x) == g], key=lambda x: -apay(x))
    w(f"- **{g}** ({len(xs)}): " + "; ".join(f"{aname(x)} ({x['id']}) ${apay(x):.0f}" + ("" if not x.get("is_access_granted") else ", доступ есть") for x in xs))
w("")
w("## 3. Dr.Cash: топ-25 по рейтингу сети (все гео)")
w("| рейтинг | оффер (id) | гео | выплата | апрув | категория | нативка |"); w("|---|---|---|---|---|---|---|")
for x in sorted([x for x in live if x["_nat"] != "НЕЛЬЗЯ"], key=lambda x: x["rank"])[:25]:
    w(dline(x))
w("")
w("## 4. Dr.Cash: топ-5 по рейтингу в каждом гео")
for g in ["TR", "AZ", "UZ", "KZ", "AM", "GE", "KG", "LV", "IT", "AL", "BA", "PL", "ES", "DE", "RO", "BG", "CZ", "HU", "PT"]:
    xs = sorted([x for x in live if g in (x.get("geo_code") or []) and x["_nat"] != "НЕЛЬЗЯ"], key=lambda x: x["rank"])[:5]
    w(f"\n**{g}** (активных офферов {sum(1 for x in live if g in (x.get('geo_code') or []))})")
    if not xs: w("нет офферов"); continue
    w("| рейтинг | оффер (id) | выплата | апрув | категория | нативка |"); w("|---|---|---|---|---|---|")
    for x in xs:
        w(f"| {x['rank']} | {x['name'].strip()[:30]} ({x['id']}) | ${float(x['rate']):.0f} | {x['approved']:.0f}% | {cats.get(str(x.get('category_id')), '?')[:18]} | {x['_nat']} |")
w("")
w("## 5. Один и тот же продукт в обеих сетях (в том же гео), по рейтингу Dr.Cash")
w("Показывает, где платят больше и есть ли у нас доступ в Aray.")
w("| рейтинг Dr.Cash | продукт, гео | Dr.Cash: выплата, апрув | Aray: выплата, доступ |"); w("|---|---|---|---|")
A = collections.defaultdict(list)
for x in ar:
    if acc(x): A[(norm(x["name"]), acountry(x))].append(x)
best = {}
for x in live:
    for g in (x.get("geo_code") or []):
        k = (norm(x["name"]), g)
        if k[0] and k in A and (k not in best or x["rank"] < best[k][0]["rank"]): best[k] = (x, A[k])
for (n, g), (x, al) in sorted(best.items(), key=lambda kv: kv[1][0]["rank"])[:40]:
    a = max(al, key=apay)
    w(f"| {x['rank']} | {x['name'].strip()[:24]}, {g} | ${float(x['rate']):.0f}, {x['approved']:.0f}% (id {x['id']}) | ${apay(a):.1f}, {'доступ есть' if a.get('is_access_granted') else 'нет доступа'} (id {a['id']}) |")
w("")
w("## Оговорки")
w("- Это список по цифрам сетей, **не проверка лендов**. Ленды Dr.Cash под наши прошлые связки (Cortitron IT, Matcha Slim IT, Nautubone BA) 23.10 оказались с выдуманными отзывами и исследованиями; топ по рейтингу этого не отсеивает. Перед запуском любой оффер из списка читаем по чек-листу скила nutra-partners.")
w("- Рейтинг Dr.Cash общий по сети: наверху польские офферы «free» с выплатой $22–25 и апрувом 14–33 %, они же самые конкурентные.")
w("- В Aray доступ к 262 из 287 офферов нужно запрашивать тикетом «Offer request for …» (в июле одобряли от того же дня до 4 дней). Запрос тикета я не создавал.")
w("- Выплата Aray — за лид на COD (оплата при получении), апрув у Aray в кабинете не показывается.")
dest = os.path.join(OUT, "top-offers-" + datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".md")
open(dest, "w", encoding="utf-8").write("\n".join(out) + "\n")
print(len(out), "lines ->", dest)
