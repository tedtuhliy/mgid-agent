"""Geozo publisher blocks of site 25953 (arcadiablog.com): create from the committed template with a chosen number of
ads, read, delete.

    node vault.mjs exec geozo -- python3 geozo_blocks.py create NAME FEED [--template FILE] [--site 25953] [--lang ru]
    node vault.mjs exec geozo -- python3 geozo_blocks.py get ID
    node vault.mjs exec geozo -- python3 geozo_blocks.py delete ID
    node vault.mjs exec geozo -- python3 geozo_blocks.py list [SITE]

(the vault needs CLAUDE_VAULT_FILE=~/.claude/secrets/vault.enc.json for the geozo service, see README.)

FEED is the number of ads in one block. The panel computes feedCount = mediaHorizontal * mediaVertical and limits the
template 16003 (image on top) to 10 x 10; the pages are read on phones, where the cards stand in one column, so a block is
made one column wide (mediaHorizontal 1) and mediaVertical = FEED, up to 10. The compiled CSS of a one-column block does
not depend on the row count, so the committed template needs nothing else changed.

The UUID that goes into the page markup (data-gz-block="<uuid>") is null in the POST answer, it is read with a GET.
Geozo's render nodes keep serving the old settings of a block for 20+ minutes after a PUT, so a different number of ads
means a new block, not an edit of a live one.
"""
import copy
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = "https://api.geozo.com/v1/webmaster"
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "geozo_blocks" / "block_post_16003_16x9_nobtn.json"
BTN = {"ro": "Vezi mai mult", "ru": "Подробнее", "en": "See more"}
MAX_ROWS = 10


def key():
    k = os.environ.get("GEOZO_PUBLISHER_API_KEY")
    if not k:
        raise SystemExit("нет GEOZO_PUBLISHER_API_KEY (vault exec geozo)")
    return k


def call(method, path, **kw):
    """The API drops about one connection in twenty and answers 429 under load: retry."""
    last = None
    r = None
    for i in range(5):
        try:
            r = requests.request(method, BASE + path, headers={"Private-Token": key(), "Accept": "application/json"},
                                 timeout=40, **kw)
            if r.status_code == 429:
                time.sleep(15 * (i + 1))
                continue
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(2 * (i + 1))
    if last:
        raise last
    return r


def payload(name, feed, lang="ru", template=TEMPLATE):
    if not 1 <= feed <= MAX_ROWS:
        raise SystemExit(f"FEED от 1 до {MAX_ROWS}")
    p = copy.deepcopy(json.load(open(template)))
    for side in p:
        p[side]["name"] = name
        ss = json.loads(p[side]["show_settings"])
        ss.update({"feedCount": feed, "mediaHorizontal": 1, "mediaVertical": feed,
                   "btnText": BTN[lang], "btnTextToPreview": BTN[lang]})
        p[side]["show_settings"] = json.dumps(ss, ensure_ascii=False, separators=(",", ":"))
        sc = json.loads(p[side]["styles_configuration"])
        sc.update({"mediaHorizontal": 1, "mediaVertical": feed, "btnText": BTN[lang]})
        p[side]["styles_configuration"] = json.dumps(sc, ensure_ascii=False, separators=(",", ":"))
    return p


def create(site, name, feed, lang, template):
    r = call("POST", f"/sites/{site}/blocks", json=payload(name, feed, lang, template))
    if r.status_code not in (200, 201):
        raise SystemExit(f"создание: {r.status_code} {r.text[:600]}")
    data = r.json().get("data") or {}
    bid = data.get("id")
    time.sleep(1.5)
    full = call("GET", f"/blocks/{bid}").json().get("data") or {}
    ss = json.loads(full.get("show_settings") or "{}")
    print(f"создан блок {bid} «{full.get('name')}» uuid {full.get('uuid')} шаблон {full.get('block_template_id')} "
          f"объявлений в блоке {ss.get('feedCount')}")
    return bid, full.get("uuid")


def main(argv):
    cmd = argv[0] if argv else "list"
    a = argv[1:]
    opt = {}
    for flag in ("--template", "--site", "--lang"):
        if flag in a:
            i = a.index(flag)
            opt[flag] = a[i + 1]
            del a[i:i + 2]
    if cmd == "create":
        create(int(opt.get("--site", 25953)), a[0], int(a[1]), opt.get("--lang", "ru"), opt.get("--template", TEMPLATE))
    elif cmd == "get":
        d = call("GET", f"/blocks/{a[0]}").json().get("data") or {}
        ss = json.loads(d.get("show_settings") or "{}")
        print(d.get("id"), d.get("uuid"), d.get("name"), "шаблон", d.get("block_template_id"), "объявлений", ss.get("feedCount"))
    elif cmd == "delete":
        r = call("DELETE", f"/blocks/{a[0]}")
        print(r.status_code, r.text[:300])
    elif cmd == "list":
        site = a[0] if a else 25953
        for b in call("GET", f"/sites/{site}/blocks", params={"per_page": 100}).json().get("data", []):
            full = call("GET", f"/blocks/{b['id']}").json().get("data") or {}
            ss = json.loads(full.get("show_settings") or "{}")
            print(b["id"], full.get("uuid"), b["name"], "шаблон", full.get("block_template_id"), "объявлений", ss.get("feedCount"))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
