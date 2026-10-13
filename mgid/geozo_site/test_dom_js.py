"""Browser test of dom.js on a fresh build: a fake ad link inside a slot, the Geozo loader blocked, /dom/lead stubbed.

    python3 test_dom_js.py          # needs Python playwright and a Chromium (CHROME env, default /opt/pw-browsers/...)

Checks: no signal in the first 0.7 s, one signal per real click, cooldown, script-made clicks ignored, links outside
the slots ignored, at most 6 per visit, nothing without a click_id or with a junk one, internal links keep the
attribution, the slot is marked filled even when the loader REPLACES its container (it does), and the «Реклама»
label then shows. Nothing leaves the machine: Geozo and MGID requests are aborted or stubbed.
"""
import os
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

tmp = tempfile.TemporaryDirectory()
sys.argv = ["build.py", "--out", tmp.name]
build.main()


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=tmp.name))
threading.Thread(target=srv.serve_forever, daemon=True).start()
PORT = srv.server_address[1]

BASE = f"http://127.0.0.1:{PORT}"
EXE = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
results = []

def check(name, ok, extra=""):
    results.append(ok); print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra else ""))

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=EXE, args=["--no-sandbox"])
    def new_page(url):
        ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=False, locale="ru-RU")
        page = ctx.new_page()
        leads = []
        def route(r):
            u = r.request.url
            if "ecstaticexistence" in u:
                return r.abort()
            if "/dom/lead" in u:
                leads.append(u); return r.fulfill(status=200, content_type="image/gif", body=b"GIF89a")
            if u.startswith(BASE + "/dom/lead"):
                leads.append(u); return r.fulfill(status=204)
            return r.continue_()
        page.route("**/*", route)
        page.goto(url, wait_until="load")
        page.evaluate("""() => { const d = document.querySelector('.ad-slot > div'); d.innerHTML = '<a id="fakead" href="javascript:void(0)" style="display:block;height:80px;background:#ccc">fake ad</a>'; }""")
        return page, leads

    # 1. with click id
    page, leads = new_page(BASE + "/dom/?click_id=TESTCLICK123456&source=mgid_77_88")
    page.wait_for_timeout(300)
    page.click("#fakead")                       # too early (< minDwellMs): no signal
    page.wait_for_timeout(300)
    check("click in the first 0.7 s is ignored", len(leads) == 0, leads)
    page.wait_for_timeout(700)
    page.click("#fakead"); page.wait_for_timeout(300)
    check("first real click sends one lead", len(leads) == 1 and "c=TESTCLICK123456" in leads[0] and "n=1" in leads[0], leads)
    page.click("#fakead"); page.wait_for_timeout(200)
    check("second click inside the cooldown sends nothing", len(leads) == 1, len(leads))
    page.wait_for_timeout(1200)
    page.click("#fakead"); page.wait_for_timeout(300)
    check("click after the cooldown sends the second lead", len(leads) == 2 and "n=2" in leads[1], leads)
    page.evaluate("document.getElementById('fakead').click()"); page.wait_for_timeout(200)
    check("script-made click (isTrusted=false) is ignored", len(leads) == 2, len(leads))
    page.evaluate("""() => { const a = document.createElement('a'); a.id='plain'; a.href='javascript:void(0)'; a.textContent='plain link outside slots'; a.style.cssText='display:block;height:60px'; document.querySelector('article').appendChild(a); }""")
    page.wait_for_timeout(1300)
    page.click("#plain"); page.wait_for_timeout(200)
    check("link outside an ad slot sends nothing", len(leads) == 2, len(leads))
    check("slot is marked filled and its label shows", page.evaluate("document.querySelector('.ad-slot').classList.contains('filled') && getComputedStyle(document.querySelector('.ad-label')).display !== 'none'"))
    hrefs = page.evaluate("Array.from(document.querySelectorAll('a.js-int')).map(a => a.getAttribute('href'))")
    check("internal links carry click_id and source", all("click_id=TESTCLICK123456" in h and "source=mgid_77_88" in h for h in hrefs) and len(hrefs) == 1, hrefs)
    for i in range(6):
        page.wait_for_timeout(1300); page.click("#fakead")
    page.wait_for_timeout(300)
    check("no more than maxPerVisit=6 per visit", len(leads) == 6, len(leads))
    page.context.close()

    # 2. no click id (moderator / direct visit): nothing is sent
    page, leads = new_page(BASE + "/dom/")
    page.wait_for_timeout(1000); page.click("#fakead"); page.wait_for_timeout(300)
    check("visit without click_id sends nothing", len(leads) == 0, leads)
    page.context.close()

    # 3. junk click id is dropped
    page, leads = new_page(BASE + "/dom/?click_id=%3Cscript%3E&source=x")
    page.wait_for_timeout(1000); page.click("#fakead"); page.wait_for_timeout(300)
    check("junk click_id is dropped", len(leads) == 0, leads)
    page.context.close()

    # 4. second article page
    page, leads = new_page(BASE + "/dom/rasteniya-osenyu.html?click_id=TESTCLICK654321&source=mgid_5_6")
    page.wait_for_timeout(1000); page.click("#fakead"); page.wait_for_timeout(300)
    check("second article sends a lead too", len(leads) == 1 and "TESTCLICK654321" in leads[0], leads)
    page.context.close()

    # 5. dense variant /dom2/: same script, same relay (/dom/lead), many slots, internal links stay inside /dom2/
    page, leads = new_page(BASE + "/dom2/?click_id=TESTCLICK777777&source=mgid_9_9")
    page.wait_for_timeout(1000); page.click("#fakead"); page.wait_for_timeout(300)
    check("dense page sends a lead to the shared relay", len(leads) == 1 and "/dom/lead?c=TESTCLICK777777" in leads[0], leads)
    n = page.evaluate("document.querySelectorAll('.ad-slot.compact').length")
    check("dense page has the compact slots", n >= 8, n)
    hrefs = page.evaluate("Array.from(document.querySelectorAll('a.js-int')).map(a => a.getAttribute('href'))")
    check("dense internal link stays under /dom2/ and carries the attribution",
          len(hrefs) == 1 and hrefs[0].startswith("/dom2/") and "click_id=TESTCLICK777777" in hrefs[0], hrefs)
    # a real click on a link inside any later slot counts too (the loader fills every slot, not just the first)
    page.evaluate("""() => { const d = document.querySelectorAll('.ad-slot.compact')[3].querySelector('div');
        d.innerHTML = '<a id="fakead2" href="javascript:void(0)" style="display:block;height:80px;background:#ccc">fake ad 2</a>'; }""")
    page.wait_for_timeout(1300)
    page.click("#fakead2"); page.wait_for_timeout(300)
    check("a click in a later slot sends a lead", len(leads) == 2 and "n=2" in leads[1], leads)
    page.context.close()
    b.close()
print(f"{sum(results)} / {len(results)} passed")
sys.exit(0 if all(results) else 1)
