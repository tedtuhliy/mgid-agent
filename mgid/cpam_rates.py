"""cpamatica payouts per geo -> data/rates-<offer>.json.

The campaign copies take their conversion cost from the cpamatica cabinet, one rate per geo (owner,
10.10: «сами ставки с кабинета cpamatica по каждому гео отдельно»). The cabinet card of an offer
keeps them in `goals[].payoutGroups`: one row per country, plus the goal's own `payout`, which is
the rate of the offer's default group (`defaultPayoutGroupName`).

    # 1. pull the card (login runs through our proxy + 2captcha, see the cpamatica skill)
    cd <Tedbolt>/mirelia_api && NM_POOL=server node cpamatica.mjs get affiliates/offers/8394 /tmp/o8394.json
    # 2. turn it into the rates file
    python3 cpam_rates.py /tmp/o8394.json

The card reports the rate in USD (`payoutCurrencyCode` 840); anything else is refused, because a
euro rate read as dollars would set every campaign's CPA wrong by the exchange rate.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"


def rates(card, goal_name=None):
    """{'offer', 'name', 'status', 'countries', 'payouts': {GEO: usd}} from an offer card."""
    o = card.get("offer", card)
    goals = [g for g in o.get("goals") or [] if float(g.get("payout") or 0) > 0]
    if goal_name:
        goals = [g for g in goals if g.get("name") == goal_name]
    if not goals:
        raise SystemExit("в карточке нет цели с выплатой больше нуля")
    g = goals[0]
    if g.get("payoutCurrencyCode") != 840:
        raise SystemExit(f"валюта выплаты {g.get('payoutCurrencyCode')}, а не USD (840)")
    pay = {}
    default = o.get("defaultPayoutGroupName")
    if default:
        pay[default] = float(g["payout"])
    for p in g.get("payoutGroups") or []:
        if p.get("payoutCurrencyCode") != 840:
            raise SystemExit(f"{p.get('name')}: валюта {p.get('payoutCurrencyCode')}, а не USD")
        pay[p["name"]] = float(p["payout"])
    return {"offer": o["id"], "name": o["name"], "status": o.get("status"), "goal": g.get("name"),
            "default_group": default, "countries": o.get("countries"), "daily_cap": o.get("dailyCaps"),
            "payouts": dict(sorted(pay.items())),
            "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}


def load(offer):
    """The saved rates of an offer."""
    return json.load(open(DATA / f"rates-{offer}.json"))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    r = rates(json.load(open(sys.argv[1]), strict=False), sys.argv[2] if len(sys.argv) > 2 else None)
    DATA.mkdir(exist_ok=True)
    out = DATA / f"rates-{r['offer']}.json"
    json.dump(r, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"{r['name']} ({r['offer']}), статус {r['status']}: {r['payouts']} -> {out}")


if __name__ == "__main__":
    main()
