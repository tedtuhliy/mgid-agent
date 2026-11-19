"""Minimal client of the Geozo advertiser API (api.geozo.com/v1/advertiser): only what the sweeps test needs.

Header `Private-Token`, vault service `geozo` (GEOZO_API_TOKEN). Every call answers `(HTTP status, body)`; `(None, error)` when the transport died
(about one call in twenty dies mid-handshake, hence the retries). The full client and the traps live in the skill `geozo`; the ones that matter here:
100 teasers a day per account (00:00 UTC, no endpoint shows the rest: `reached_limit`), a teaser title is 30..65 characters, status 6 = archived (cannot be restarted),
`campaign_type_id` and `traffic_source_id` cannot be changed after creation, `PUT campaigns/{id}` must resend `traffic_source_id`, a bid is per country (`invalid_min_bid` = below the floor).
"""
import json
import os
import time

import requests

API = "https://api.geozo.com/v1/advertiser"


class Geozo:
    def __init__(self, tries=6, timeout=90):
        self.h = {"Private-Token": os.environ["GEOZO_API_TOKEN"], "Accept": "application/json"}
        self.tries, self.timeout = tries, timeout

    def req(self, method, path, **kw):
        last = None
        headers = {**self.h, **(kw.pop("headers", None) or {})}
        for a in range(self.tries):
            try:
                r = requests.request(method, f"{API}/{path.lstrip('/')}", headers=headers, timeout=self.timeout, **kw)
                try:
                    return r.status_code, r.json()
                except ValueError:
                    return r.status_code, r.text
            except Exception as e:                                  # noqa: BLE001 - any transport fault
                last = e
                time.sleep(1.5 * (a + 1))
        return None, str(last)[:120]

    def get(self, path, params=None):
        st, d = self.req("GET", path, params=params)
        return d if st == 200 and isinstance(d, dict) else {}

    def send(self, method, path, body):
        return self.req(method, path, data=json.dumps(body), headers={"Content-Type": "application/json"})

    # ---- reading
    def balance(self):
        return float(((self.get("balance").get("data")) or {}).get("current_balance") or 0)

    def campaigns(self):
        out, page = [], 1
        while True:
            j = self.get("campaigns", {"page": page})
            out += j.get("data", [])
            if page >= ((j.get("meta") or {}).get("last_page") or 1):
                return out
            page += 1

    def campaign(self, cid):
        return self.get(f"campaigns/{cid}").get("data", {})

    def groups(self, cid):
        return self.get(f"campaigns/{cid}/ad_groups", {"per_page": 50}).get("data", [])

    def group(self, gid):
        return self.get(f"ad_groups/{gid}").get("data", {})

    def ad(self, aid):
        return self.get(f"ads/universal/{aid}").get("data", {})

    def stats(self, date_from, date_to, group_by="ad_id", order="clicks_count", per_page=20000):
        p = {"filters[date_from]": date_from, "filters[date_to]": date_to, "groups[0]": group_by,
             "order_by[0][column]": order, "order_by[0][direction]": "desc", "per_page": per_page}
        return self.get("stats/tmp_with_postbacks", p).get("data", {}).get("result", [])

    # ---- writing
    def create_campaign(self, body):
        return self.send("POST", "campaigns", body)

    def update_campaign(self, cid, body):
        return self.send("PUT", f"campaigns/{cid}", body)

    def create_group(self, cid, body):
        return self.send("POST", f"campaigns/{cid}/ad_groups", body)

    def create_teaser(self, gid, title, url, bid, square, wide):
        """(ad_id, None) or (None, 'LIMIT' | 'MINBID' | 'net' | the text of the refusal)."""
        st, d = self.req("POST", f"ad_groups/{gid}/ads/teaser/create",
                         files={"media_content_file_square[file]": ("s.jpg", square, "image/jpeg"),
                                "media_content_file_horizontal[file]": ("h.jpg", wide, "image/jpeg")},
                         data={"title": title, "original_url": url, "primary_source_url": url, "one_bid_for_all_geo": str(bid)})
        if st is None:
            return None, "net"
        text = json.dumps(d) if not isinstance(d, str) else d
        if st == 200 and isinstance(d, dict):
            return d.get("id") or (d.get("data") or {}).get("id"), None
        if "reached_limit" in text:
            return None, "LIMIT"
        if "invalid_min_bid" in text:
            return None, "MINBID"
        return None, text[:200]

    def set_bid(self, ad_ids, bid):
        return self.send("PUT", "ads/all/bid", {"ids": [int(a) for a in ad_ids], "one_bid_for_all_geo": str(bid)})

    def stop(self, ad_ids):
        return self.send("PUT", "ads/all/stop", {"ids": [int(a) for a in ad_ids]})

    def start(self, ad_ids):
        return self.send("PUT", "ads/all/start", {"ids": [int(a) for a in ad_ids]})
