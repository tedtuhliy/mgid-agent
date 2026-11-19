"""NewsBreak Ads: the public Advertising API (token) and the web login of the Ad Manager, standard library only.

    node vault.mjs exec newsbreak -- python3 nb_api.py             # who am I: organizations, ad accounts, spending cap, campaigns (read only)

The vault service `newsbreak` holds NEWSBREAK_LOGIN, NEWSBREAK_PASSWORD (the owner pasted them into the chat on 19.11.2026) and NEWSBREAK_API_KEY.

Public API (documentation: Zendesk JSON of https://advertising-api.newsbreak.com/api/v2/help_center/en-us/articles.json; the HTML pages answer 403 to bots):
  base https://business.newsbreak.com/business-api/v1, header `Access-Token`, the answer is {"code": 0, "data": ...}; codes 403 no permission, 4031 not logged in, 4033 bad token,
  4034 rate limit (Basic level: 10 requests a second, 600 a minute). Money is in CENTS, times are unix seconds.
  org/admin-orgs, ad-account/getGroupsByOrgIds, balance/getAccountBudgetInfo, balance/updateAccountsBudget (the account spending cap, must be above the spend so far),
  campaign/create|update/{id}|updateStatus/{id}|delete/{id}|getList, ad-set/..., ad/..., ad/uploadAssets (multipart), event/getList/{adAccountId}, reports/getIntegratedReport.

Web login without a browser (checked 19.11): the Ad Manager signs in with Firebase (project `newsbreakads`; the web key is in the _app chunk of admanager.newsbreak.com),
then POST /api/login {accessToken, email, expInfo} -> {code: 0, token}; every internal call is `Authorization: Bearer <token>`. `GET /api/v1/users/access-token` lists the API tokens,
the same route with POST generates one (the owner's token of 01.09.2026 is ACTIVE, so none was generated).
"""
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = "https://business.newsbreak.com/business-api/v1"
ADMANAGER = "https://admanager.newsbreak.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_last = [0.0]


def _pace(gap=0.15):
    """The Basic level allows 10 requests a second: keep a gap of 150 ms between calls."""
    wait = _last[0] + gap - time.time()
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()


def call(method, path, body=None, params=None, token=None, form=None):
    """One call of the public API. Returns (HTTP status, parsed JSON or text). `form` = (fields dict, file field name, path) for a multipart upload."""
    _pace()
    url = BASE + path + (("?" + urllib.parse.urlencode(params, doseq=True)) if params else "")
    h = {"Access-Token": token or os.environ["NEWSBREAK_API_KEY"], "accept": "application/json", "User-Agent": UA}
    data = None
    if form is not None:
        fields, fname, fpath = form
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        ctype = mimetypes.guess_type(fpath)[0] or "application/octet-stream"
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{fname}"; filename="{os.path.basename(fpath)}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()
                     + open(fpath, "rb").read() + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        data = b"".join(parts)
        h["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw[:1] in ("{", "[") else raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw[:400]


def ok(res):
    """The data of an answer with code 0, else a RuntimeError with the platform's message."""
    st, d = res
    if st != 200 or not isinstance(d, dict) or d.get("code") != 0:
        raise RuntimeError(f"NewsBreak: HTTP {st} {json.dumps(d, ensure_ascii=False)[:400]}")
    return d.get("data")


def orgs():
    return ok(call("GET", "/org/admin-orgs"))["list"]


def ad_accounts(org_ids):
    return [a for g in ok(call("GET", "/ad-account/getGroupsByOrgIds", params={"orgIds": list(org_ids)}))["list"] for a in g["adAccounts"]]


def budget_info(account_id):
    rows = ok(call("POST", "/balance/getAccountBudgetInfo", {"accountIds": [str(account_id)]}))["list"]
    return rows[0] if rows else None


def set_spending_cap(account_id, cents):
    """The account-level spending cap in cents (must be above what the account has spent). Returns the message of the platform."""
    return ok(call("POST", "/balance/updateAccountsBudget", {"adAccountsBudgetUpdate": [{"adAccountId": str(account_id), "budget": int(cents)}]}))["list"][0]["message"]


def campaigns(account_id):
    return ok(call("GET", "/campaign/getList", params={"adAccountId": account_id, "pageNo": 1, "pageSize": 100}))["list"]


def ad_sets(account_id, campaign_ids=None):
    p = {"adAccountId": account_id, "pageNo": 1, "pageSize": 100}
    if campaign_ids:
        p["campaignIds"] = list(campaign_ids)
    return ok(call("GET", "/ad-set/getList", params=p))["list"]


def ads(account_id, ad_set_ids=None):
    p = {"adAccountId": account_id, "pageNo": 1, "pageSize": 100}
    if ad_set_ids:
        p["adSetIds"] = list(ad_set_ids)
    return ok(call("GET", "/ad/getList", params=p))["list"]


def create_campaign(account_id, name, objective, status="OFF"):
    return ok(call("POST", "/campaign/create", {"adAccountId": str(account_id), "name": name, "objective": objective, "status": status}))


def create_ad_set(body):
    return ok(call("POST", "/ad-set/create", body))


def create_ad(body):
    return ok(call("POST", "/ad/create", body))


def upload_asset(account_id, path, media_name=None):
    """Upload an image to the NewsBreak CDN; returns the assetUrl that `ad/create` accepts."""
    fields = {"adAccountId": str(account_id)}
    if media_name:
        fields.update({"saveToMediaLibrary": "true", "mediaName": media_name})
    st, d = call("POST", "/ad/uploadAssets", form=(fields, "asset", path))
    if st == 409 and isinstance(d, dict) and (d.get("data") or {}).get("assetUrl"):
        return d["data"]["assetUrl"]        # «media with the same content already exists»: the answer carries the URL of the existing one
    return ok((st, d))["assetUrl"]


def set_status(kind, object_id, status):
    """kind: campaign | ad-set | ad; status ON or OFF."""
    return ok(call("PUT", f"/{kind}/updateStatus/{object_id}", {"status": status}))


def delete(kind, object_id):
    return ok(call("DELETE", f"/{kind}/delete/{object_id}"))


def web_events(account_id):
    return ok(call("GET", f"/event/getList/{account_id}", params={"os": ""}))["list"]


# ---- the web login of the Ad Manager (internal API, cookie-less Bearer) -------------------------------------------------------------------------------------

def _post_json(url, body, headers=None):
    h = {"content-type": "application/json", "User-Agent": UA, "Origin": ADMANAGER, "Referer": ADMANAGER + "/"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode() or "null")
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw[:300]


def firebase_key():
    """The web key of the Ad Manager's Firebase project, read from its public bundle (it is the key of a browser app, not a secret)."""
    req = urllib.request.Request(ADMANAGER + "/signin", headers={"User-Agent": UA})
    html = urllib.request.urlopen(req, timeout=60).read().decode()
    for src in re.findall(r'src="(https://static\.newsbreak\.com/nova/_next/static/chunks/pages/_app-[^"]+\.js)"', html):
        js = urllib.request.urlopen(urllib.request.Request(src, headers={"User-Agent": UA}), timeout=120).read().decode(errors="ignore")
        m = re.search(r'apiKey:"(AIza[^"]+)"', js)
        if m:
            return m.group(1)
    raise RuntimeError("the Firebase key was not found in the Ad Manager bundle")


def session_token():
    """Sign in like the web app: Firebase email+password, then /api/login. Returns the Bearer token of the internal API."""
    email, pw = os.environ["NEWSBREAK_LOGIN"], os.environ["NEWSBREAK_PASSWORD"]
    st, d = _post_json("https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + firebase_key(), {"email": email, "password": pw, "returnSecureToken": True})
    if st != 200:
        raise RuntimeError(f"Firebase sign-in: HTTP {st} {json.dumps(d)[:200]}")
    st, d = _post_json(ADMANAGER + "/api/login", {"accessToken": d["idToken"], "email": email, "expInfo": "{}"})
    if st != 200 or not isinstance(d, dict) or d.get("code") != 0:
        raise RuntimeError(f"Ad Manager login: HTTP {st} {json.dumps(d)[:200]}")
    return d["token"]


def internal(method, path, token, body=None):
    h = {"Authorization": "Bearer " + token, "User-Agent": UA, "accept": "application/json", "Origin": ADMANAGER, "Referer": ADMANAGER + "/"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["content-type"] = "application/json"
    req = urllib.request.Request(ADMANAGER + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw[:1] in ("{", "[") else raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw[:300]


def main():
    o = orgs()
    print("organizations:", [(x["id"], x["name"]) for x in o])
    accs = ad_accounts([x["id"] for x in o])
    for a in accs:
        print("ad account:", a["id"], a["name"])
        print("  spending cap:", budget_info(a["id"]))
        c = campaigns(a["id"])
        print("  campaigns:", [(x["id"], x["name"], x.get("status"), x.get("onlineStatus")) for x in c])


if __name__ == "__main__":
    main()
