#!/usr/bin/env bash
# Google Safe Browsing status of hosts, DOMAIN level, no key. The moderators' «Malware has been detected» screenshots were Chrome's red
# «Dangerous site» page, so this is the first check of a teaser link and of the lander behind it (the tracker redirects: check the
# tracker host AND the lander it lands on, for every variant you can see).
#
#   bash safebrowsing.sh host [host ...]
#
# The answer is )]}' and then [["sb.ssr", status, 5 flags, last scan (ms), host, ...]]. Status as seen on 23.10: 1 = nothing found,
# 2 = some pages of the site are unsafe (tyblk.info: second flag true), 3 = the site is unsafe (Google's own test site
# testsafebrowsing.appspot.com: status 3 and the first three flags true), 6 = no data. Which flag is which category is not decoded.
# The scan time says how fresh the verdict is. A flag can be temporary or tied to one URL, and «clean» is not a clearance.
# RATE LIMIT: after ~10 requests in a row Google answers with a captcha page («sorry»), which is NOT "no answer" and NOT "clean":
# the script pauses between hosts and says so when it is cut off. (On 23.10 a first look took such a page for "no answer" for tyblk.info.)
for h in "$@"; do
  r=$(curl -sS -m 25 "https://transparencyreport.google.com/transparencyreport/api/v3/safebrowsing/status?site=$h" 2>/dev/null | tail -1)
  python3 - "$h" "$r" <<'PY'
import json, sys
from datetime import datetime, timezone
host, raw = sys.argv[1], sys.argv[2]
NAMES = {1: "nothing found", 2: "SOME PAGES UNSAFE", 3: "UNSAFE", 6: "no data"}
try:
    row = json.loads(raw)[0]
    code, flags, ts = row[1], row[2:7], row[7]
    when = datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%d.%m %H:%M UTC") if ts else "-"
    print(f"{host}: status {code} ({NAMES.get(code, '?')}), flags {'none' if not any(flags) else flags}, last scan {when}")
except Exception:
    cut = "sorry" in raw.lower() or "<html" in raw.lower()
    print(f"{host}: " + ("RATE-LIMITED by Google (captcha page): wait a minute and ask again" if cut else "no answer"))
PY
  sleep 5
done
