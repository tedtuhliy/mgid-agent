# mgid-agent
MGID/Adskeeper agent.

`index.js` / `Dockerfile` are the small health-check service. Everything about the dating tests on
MGID account 816929 (v2 client 939031) lives in `mgid/`, plain Python, standard library only.

## Tinely: Kazakhstan and the Baltics, CPA bidding (10.10)

The only cpamatica offer that has paid us in these geos is **Tinely [LT, LV, EE, KZ, MD, GE, AZ] SOI 18+ (8394)**:
7 leads from Kazakhstan ($0.56) and 1 from Lithuania ($0.44), all from the two CIS-mobile tests of
30.09 to 01.10. One campaign per geo, because the cabinet rate differs by geo and the guard judges
every campaign by its own conversion cost.

| geo | campaign | cabinet rate = CPA target = conversion cost |
|---|---|---|
| KZ | 12510622 Tinely girls KZ mobile CPA | $0.56 |
| LT | 12510623 Tinely girls LT mobile CPA | $0.44 |
| LV | 12510625 Tinely girls LV mobile CPA | $0.32 |
| EE | 12510626 Tinely girls EE mobile CPA | $1.48 |

Copy of the live CIS-mobile campaign 12502232 (mobile OS list, Russian browser language, three
women-only teasers, the same cpamatica link, UTM that returns click id, campaign and placement
with the lead) with `targetCpa` bidding and a $20 daily budget. All four are **paused**, teasers are on
moderation, nothing starts by itself.

```bash
cd mgid
node ~/.claude/skills/secrets/vault.mjs exec mgid -- python3 mgid_geo_copies.py           # plan
node ~/.claude/skills/secrets/vault.mjs exec mgid -- python3 mgid_geo_copies.py --apply   # create / complete, then read back
node ~/.claude/skills/secrets/vault.mjs exec mgid -- python3 mgid_geo_copies.py --sync-rates   # CPA <- cabinet rates
node ~/.claude/skills/secrets/vault.mjs exec mgid -- python3 mgid_geo_copies.py --resume       # start (needs balance > 0)
```

**Rates come from the cpamatica cabinet, per geo.** `data/rates-8394.json` is the offer card's
`payoutGroups` (fetched 10.10). To refresh after a cabinet change:

```bash
cd <Tedbolt>/mirelia_api && NM_POOL=server node cpamatica.mjs get affiliates/offers/8394 /tmp/o8394.json
python3 mgid/cpam_rates.py /tmp/o8394.json && python3 mgid/mgid_geo_copies.py --sync-rates
```

`CPA_SHARE` in `mgid_geo_copies.py` is the share of the cabinet rate used as the target. It is 1.0, as
asked (bid = cabinet rate), so the best case is break-even; set 0.7 to leave a margin.

## Placement guard on Inferno: two conversion costs without a lead

`mgid/mgid_guard.py`, systemd timer `mgid-guard` every 5 minutes, code in `/opt/mgid-guard/`.

> a placement that has spent **2 x the campaign's conversion cost** with no lead goes to that
> campaign's block list

- The conversion cost is read from the **campaign settings** (`conversionTracking.buyStage.conversionValue`
  in v2; the targetCpa price if that is empty). No cpamatica access at run time.
- Campaigns are found, not listed: every active campaign whose buy stage is the dating target 1274200.
  A copy is covered as soon as it is started.
- A lead counts from either source: the middleware table `mgid_leads` (placement comes from the UTM)
  or MGID's own buy conversion. Judged per campaign, spend over the campaign's lifetime.
- The block list only grows, every write is read back. HOLD (nothing is blocked) when the UTM may have
  stopped reaching cpamatica or the tables are unreadable.

```bash
tailscale ssh root@100.121.239.113 mgid-guard-status            # thresholds, holds, every block
tailscale ssh root@100.121.239.113 journalctl -u mgid-guard -n 30 -o cat
bash mgid/deploy_guard_inferno.sh                               # redeploy: stage, dry run on the box, backup, swap
python3 -m unittest -v mgid/test_guard.py                       # offline checks of the rule
```

Rollback: `cp /opt/mgid-guard/backup-<utc>/*.py /opt/mgid-guard/ && systemctl start mgid-guard.service`.
Knobs in the unit: `MGID_GUARD_MULT=2`, `MGID_GUARD_THRESH=0.30` (only for a campaign with no
conversion cost), `MGID_OFFERS` (offers that can be MGID leads).

Derived from the `mgid` skill of the Tedbolt repo (`.claude/skills/mgid/scripts`), whose flat $0.30 rule it replaces.

## Things found on the way

- The guard that was deployed on 30.09 had been in **HOLD since 01.10 19:30**, blocking nothing. Its
  "lead without source" check counted leads of the smartlink 16588 (other buys, same global
  postback), which can never be MGID leads. It now looks only at the offers in `MGID_OFFERS`.
- v1 `conversions` answers "Please use the Ads dashboard to set up tracking" for a `targetCpa`
  campaign: its conversion cost can only be read through v2.
- Daily budget units: v2 POST takes dollars, v1 and the v2 read-back show it x100. The 30.09
  relaunch cloned `2000.0` from a read-back, so the six "girls" campaigns carry **$2000 a day** each
  (v1 `dailyLimit` 200000) instead of $20.
- MGID creates a campaign active; v2 `PATCH .../status` answered 403 for a campaign created two
  seconds earlier. `pause()` uses the v1 flag and reads the status back.
