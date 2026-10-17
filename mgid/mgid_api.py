"""MGID client for the mainstream-dating account: v1 goodhits client 816929, v2 ads account 939031.

One Bearer token serves both APIs: `MGID_816929_TOKEN` (vault service `mgid`; on Inferno it sits in
/etc/mgid-guard.env). Standard library only, so the same file runs in a session and on the server.

Derived from the `mgid` skill of the Tedbolt repo (.claude/skills/mgid/scripts/mgid_api.py). What is
new here: campaigns are DISCOVERED from the account instead of being listed by hand, and the
conversion cost (CPA) is read from each campaign's own settings.

Things this API does that cost time the first round:
- Cloudflare answers Python's default User-Agent with error 1010 (a 403 HTML page), so every call
  carries a browser UA.
- v1 PATCH/PUT take a form body. A JSON body answers 200 and changes nothing, so every write is
  read back.
- v2 lists need `filters[fields][]=...` (and 400 if you ask for `id`, which always comes back) and
  v2 reports need `dateRange` as an RFC datetime.
- Money units differ between the two APIs for the daily budget: v2 POST takes dollars, v1 and the
  v2 read-back show it x100. Read a limit back through v1 before trusting it.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# Two accounts of the owner. `main` (v1 816929 / v2 939031) was blocked by MGID on 14.10 (API 401, «Identity is under godmodeBlock»).
# `second` is the older account (v1 816921); its v2 client id 939023 and its token come from the cabinet page «API» (owner, 17.10);
# the owner says the account manager allowed running from it. MGID_ACCOUNT=second makes every script of this folder use it
# (ids, token, and the per-account data files of geozo_geos.py); the default stays `main`.
ACCOUNTS = {
    "main": {"cid1": 816929, "cid2": 939031, "token": "MGID_816929_TOKEN"},
    "second": {"cid1": 816921, "cid2": 939023, "token": "MGID_816921_TOKEN"},
}
ACCOUNT = os.environ.get("MGID_ACCOUNT", "main")
if ACCOUNT not in ACCOUNTS:
    raise SystemExit(f"MGID_ACCOUNT={ACCOUNT!r}: нет такого аккаунта, есть {sorted(ACCOUNTS)}")
CID1, CID2 = ACCOUNTS[ACCOUNT]["cid1"], ACCOUNTS[ACCOUNT]["cid2"]
TOKEN_ENV = ACCOUNTS[ACCOUNT]["token"]
V1 = "https://api.mgid.com/v1/"
V2 = "https://api.mgid.com/v2/ads/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")

# Conversion target "lead" (postback, buy stage) that every dating campaign carries. The guard
# picks its campaigns by this target, so a new copy is covered the moment it is launched.
TARGET = 1274200

V2_FIELDS = ("name", "type", "bidding", "status", "limits", "geoTargeting", "conversionTracking",
             "operatingSystemTargeting", "languageTargeting", "browserTargeting")


def call(method, url, body=None, form=False, timeout=90):
    """(status, parsed json | text). Never raises on HTTP errors: the caller decides."""
    h = {"Authorization": "Bearer " + os.environ[TOKEN_ENV],
         "Accept": "application/json", "User-Agent": UA}
    data = None
    if body is not None:
        if form:
            data = urllib.parse.urlencode(body).encode()
            h["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    try:
        return status, json.loads(raw or b"null")
    except ValueError:
        return status, raw.decode("utf-8", "replace")[:600]


def v1(method, path, body=None, **q):
    url = V1 + path + ("?" + urllib.parse.urlencode(q) if q else "")
    return call(method, url, body, form=body is not None)


def v2_campaigns(fields=V2_FIELDS):
    """{campaign id: v2 row} for every campaign of the account, paged."""
    out, off, page = {}, 0, 100
    while True:
        q = "&".join(f"filters[fields][]={f}" for f in fields) + f"&limit={page}&offset={off}"
        st, d = call("GET", V2 + f"account/{CID2}/campaigns?{q}")
        if st != 200 or not isinstance(d, dict):
            raise RuntimeError(f"v2 campaigns: {st} {json.dumps(d, ensure_ascii=False)[:300]}")
        rows = d.get("data") or []
        out.update({int(x["id"]): x for x in rows})
        if len(rows) < page:
            return out
        off += page


def buy_cpa(row):
    """Conversion cost of a campaign as set in its own conversion tracking: (target id, $ or None)."""
    buy = ((row.get("conversionTracking") or {}).get("buyStage")) or {}
    v = buy.get("conversionValue")
    return buy.get("targetId"), (float(v) if v else None)


def v1_conversion(cid):
    """Same thing through v1 `conversions`; v2 reads can lag behind a write (the skill saw null
    for a while after a PATCH). Only campaigns on manual bidding answer here: a targetCpa campaign
    gets {"errors": ["Please use the Ads dashboard to set up tracking"]}, so for those v2 is the
    only place the conversion cost can be read. (target id, $ or None)."""
    st, d = v1("GET", f"goodhits/campaigns/{cid}/conversions")
    for x in d if st == 200 and isinstance(d, list) else []:
        if x.get("stage") == "buy":
            p = x.get("price")
            return x.get("target_id"), (float(p) if p else None)
    return None, None


def pause(cid, on=True):
    """Pause (`on`) or start a campaign with the v1 flag, and return the status read back.

    v2 `PATCH .../status` is the documented way, but it answered 403 "Access Denied" for a
    campaign created two seconds earlier (10.10) and works a moment later. The v1 flag has no such
    window and is what the other guards use. Starting only clears OUR pause: a campaign without
    funds stays paused by the network (`outOfClientFunds`)."""
    v1("PATCH", f"goodhits/clients/{CID1}/campaigns/{cid}", {"whetherToBlockByClient": 1 if on else 0})
    return campaign(cid, ("id", "status")).get("status") or {}


def widgets_filter(cid):
    """(filter type, {widget uid: sourceIds}) of a campaign, read through v2 and paged: the v2 default
    page is 20 rows, so a list longer than that would be cut silently without the loop."""
    typ, out, off = None, {}, 0
    while True:
        st, d = call("GET", V2 + f"account/{CID2}/campaigns/{cid}/widgets/filters?limit=100&offset={off}")
        if st != 200 or not isinstance(d, dict):
            raise RuntimeError(f"widgets filter {cid}: {st} {json.dumps(d, ensure_ascii=False)[:200]}")
        typ = d.get("filterType")
        rows = d.get("data") or []
        out.update({str(x["widgetUid"]): x.get("sourceIds") or [] for x in rows})
        if len(rows) < 100:
            return typ, out
        off += 100


def whitelist_set(cid, uids):
    """Replace the whole widget filter with a whitelist (`only`): only these placements are served.
    PUT replaces, so nothing from an earlier list survives."""
    return call("PUT", V2 + f"account/{CID2}/campaigns/{cid}/widgets/filters",
                {"filterType": "only", "data": [{"widgetUid": int(u)} for u in sorted(uids)]})


def whitelist_remove(cid, uids):
    """Take placements off a whitelist. The spec says the filter type is kept unless the list becomes
    empty; what an emptied `only` filter turns into was NOT tested. So a caller must never remove the
    last placement: pause the campaign instead (see mgid_guard)."""
    return call("PATCH", V2 + f"account/{CID2}/campaigns/{cid}/widgets/filters/batch-delete",
                {"data": [{"widgetUid": int(u)} for u in sorted(uids)]})


def campaign(cid, fields=("id", "name", "status", "widgetsFilterUid", "trackingOptions", "limitsFilter")):
    st, d = v1("GET", f"goodhits/clients/{CID1}/campaigns/{cid}",
               fields="[" + ",".join(f"'{x}'" for x in fields) + "]")
    return d if st == 200 and isinstance(d, dict) else {}


def blacklist(cid):
    """Blocked widget uids of a campaign, as strings, and the filter type."""
    f = campaign(cid, ("id", "widgetsFilterUid")).get("widgetsFilterUid") or {}
    out = set()
    for w in f.get("widgets") or []:
        out.update(map(str, w.keys()) if isinstance(w, dict) else [str(w)])
    return out, f.get("filterType")


def block(cid, uids):
    """Add widgets to the campaign's exclusion list. `include` APPENDS to what is there;
    `exclude` would overwrite the whole list, i.e. silently unblock everything blocked before."""
    return v1("PATCH", f"goodhits/clients/{CID1}/campaigns/{cid}",
              {"widgetsFilterUid": "include, except, " + ", ".join(sorted(uids))})


def _num(x):
    return float(x.get("amount") if isinstance(x, dict) else (x or 0))


def widget_spend(cid, interval="all", since=None):
    """{widget uid: (clicks, spent $)} for one campaign.

    Without `since`: v1 quality-analysis over `interval` (checked against campaigns-stat to the cent on
    the older account); `all` covers the campaign's lifetime. With `since` ('YYYY-MM-DD', an MGID day,
    UTC+3): the v2 report by placement from that day to today. quality-analysis takes only fixed
    intervals, and the guard has to count from the day the CPA bidding began (see mgid_guard)."""
    if since:
        till = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
        out = {}
        for r in report(since, till, ("clicks", "spent"), ("campaignId", "widgetId"), [cid]):
            uid = str(r.get("widgetId"))
            c, s = out.get(uid, (0, 0.0))
            out[uid] = (c + int(_num(r.get("clicks"))), s + _num(r.get("spent")))
        return out
    st, d = v1("GET", f"goodhits/campaigns/{cid}/quality-analysis/", campaignId=cid, dateInterval=interval)
    if st != 200 or not isinstance(d, dict) or d.get("errors"):
        raise RuntimeError(f"quality-analysis {cid}: {st} {json.dumps(d, ensure_ascii=False)[:200]}")
    out = {}
    for per in d.values():
        for rows in (per or {}).values():
            for uid, v in (rows or {}).items() if isinstance(rows, dict) else []:
                out[str(uid)] = (int(v.get("clicks") or 0), float(v.get("spent") or 0))
    return out


def report(frm, till, metrics, dims, camps=None, limit=1000):
    """v2 custom report rows. frm/till: 'YYYY-MM-DD', whole MGID days, which are UTC+3 days.

    The API moves the range into UTC+3 and returns every whole day it touches, and its `day` and
    `hour` buckets are UTC+3 too. The old `{till}T23:59:59+00:00` is 02:59 of the NEXT day there,
    so a one-day query for 30.09 came back with all of 01.10 (probed 01.10). A page holds at most
    1000 rows and a full one is cut silently, so this pages with `offset` (two CIS campaigns by
    day x hour x placement over one day were 7983 rows)."""
    q = [("metrics[]", m) for m in metrics] + [("dimensions[]", x) for x in dims]
    q += [("filters[dateRange][dateFrom]", f"{frm}T00:00:00.000+03:00"),
          ("filters[dateRange][dateTo]", f"{till}T23:59:59.000+03:00"), ("limit", str(limit))]
    q += [("filters[campaigns][]", str(c)) for c in camps or []]
    out = []
    for off in range(0, 30 * limit, limit):
        st, d = call("GET", V2 + f"account/{CID2}/statistics/reports?"
                     + urllib.parse.urlencode(q + [("offset", str(off))]))
        if st != 200 or not isinstance(d, dict):
            raise RuntimeError(f"v2 report: {st} {json.dumps(d, ensure_ascii=False)[:200]}")
        rows = d.get("data") or []
        out += rows
        if len(rows) < limit:
            return out
    raise RuntimeError(f"v2 report: more than {len(out)} rows, narrow the query")
