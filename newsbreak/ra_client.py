"""The cabinet session of RollerAds (`/api/offers/*` is closed to the API key), the part the NewsBreak test needs: the card of an offer and its tracking link.

Same flow as mgid/rr_sweeps.py (login `{user_login, user_password}`, cookies); kept separate so that the NewsBreak tool does not need the MGID tokens.
Vault service `rollerads`: ROLLERADS_LOGIN, ROLLERADS_PASSWORD.
"""
import http.cookiejar
import json
import os
import urllib.error
import urllib.request

BASE = "https://my.rollerads.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


class RollerAds:
    def __init__(self):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        st, _ = self.req("POST", "/api/auth/login", {"user_login": os.environ["ROLLERADS_LOGIN"], "user_password": os.environ["ROLLERADS_PASSWORD"]})
        if st != 200:
            raise SystemExit(f"RollerAds login: HTTP {st}")

    def req(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        h = {"accept": "application/json", "User-Agent": UA, "Origin": BASE, "Referer": BASE + "/"}
        if data:
            h["content-type"] = "application/json"
        r = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
        try:
            with self.op.open(r, timeout=60) as resp:
                raw = resp.read().decode()
                return resp.status, (json.loads(raw) if raw[:1] in ("{", "[") else raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            return e.code, (json.loads(raw) if raw[:1] in ("{", "[") else raw)

    def card(self, oid):
        st, d = self.req("GET", f"/api/offers/{oid}")
        return (d.get("response") if isinstance(d, dict) else None) if st == 200 else None

    def tracker(self, oid):
        """The tracking link of the offer, or None when the cabinet refuses it (no access: 403, private offer: 404)."""
        st, d = self.req("GET", f"/api/offers/{oid}/tracking-link")
        return ((d.get("response") or {}).get("tracking_link") if isinstance(d, dict) else None) if st == 200 else None
