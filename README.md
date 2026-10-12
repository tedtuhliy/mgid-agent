# mgid-agent
MGID/Adskeeper agent.

`index.js` / `Dockerfile` are the small health-check service. Everything about the dating tests on
MGID account 816929 (v2 client 939031) lives in `mgid/`, plain Python, standard library only.

## Spend stop-loss on Inferno (11.10)

Owner: «настрой на инферно бота который стопнет кампании после спенда в 3 бакса». `mgid/spend_stop.py` runs on
Inferno every 2 minutes (`mgid-spend-stop.timer`, code in `/opt/mgid-spend-stop/`). It pauses every ACTIVE
MGID campaign on the account whose spend **since the last reset** reaches $3. `--reset` stores every campaign's lifetime spend as its
baseline; a campaign created later counts all its spend. The reset was run on 11.10 at 20:40:49 UTC for 23 campaigns.
It never starts anything. Restarting a campaign does not reset its count; only `--reset` does. If the spend cannot
be read, nothing is paused. Limit: `MGID_SPEND_LIMIT` in the unit. Log of stops: `/var/lib/mgid-spend-stop/actions.log`.

It is not the placement guard: the guard (`mgid-guard`) stops single placements, this stops whole campaigns.
It does not cover Adskeeper or other networks.

```bash
python3 -m unittest -v mgid/test_spend_stop.py                                  # offline checks
TAILSCALE="<tailscale> --socket=<sock>" bash mgid/deploy_spend_stop_inferno.sh  # stage, dry run, swap, timer
tailscale ssh root@100.121.239.113 'systemctl disable --now mgid-spend-stop.timer'   # switch off
```

On install (11.10, 11:26) the three active campaigns (two whitelists, the LATAM CPA test) had $0.00 spend.

## Dating campaigns on CPA = 10% of the payout per geo (12.10)

Owner, 12.10: «Точней поставь 10% от выплат на гео ставку cpatune» (replaces the flat 5 cents asked earlier that day).

`mgid/cpa_share.py` sets each dating campaign's `targetCpa` bid to 10% of the cpamatica payout for its geo. The
conversion cost in the campaign settings gets the same number, and the placement guard stops a placement after 2x
that cost without a lead. The payouts come from `mgid/data/rates-<offer>.json`, saved from the offer cards by
`mgid/cpam_rates.py`.

- **One bid per campaign.** MGID cannot price geos apart inside one campaign, so a campaign on several geos gets 10%
  of the LOWEST payout among them: no geo is bid above 10% of its own payout. Exact per-geo bids mean one campaign per
  geo, which is a new campaign, not a setting.
- **Teasers are not touched** (MGID refuses CPC changes under CPA bidding).
- **Offer 9962** has one country and no payout group: its goal payout ($2.00, PL) is the PL rate. `cpam_rates.py`
  reads it that way.

Payouts from the cabinet cards, USD:

- Tinely - Mobile/Desktop [PL] SOI 18+ (Exclusive) (9962): PL 2.00
- Tinely - Mobile/Desktop [EC, CR, GT, HN, DO, PA, CL] SOI 25+ (Exclusive) (8326): CL 1.00, CR 0.80, DO 0.62, EC 0.62, GT 0.70, HN 0.80, PA 0.48
- Tinely - Mobile/Desktop [LT, LV, EE, KZ, MD, GE, AZ] SOI 18+ (Exclusive) (8394): AZ 0.20, EE 1.48, GE 0.468, KZ 0.56, LT 0.44, LV 0.32, MD 0.20

| campaign | geos | bid |
|---|---|---|
| 12502227 Tinely girls PL mobile+desktop | PL | 0.20 |
| 12502228 Tinely girls PL mobile | PL | 0.20 |
| 12502229 Tinely girls LATAM mobile+desktop | CL, CR, DO, EC, GT, HN, PA | 0.048 (PA) |
| 12502230 Tinely girls LATAM mobile | CL, CR, DO, EC, GT, HN, PA | 0.048 (PA) |
| 12502231 Tinely girls CIS mobile+desktop | KZ, LV, MD, EE, LT, GE, AZ | 0.02 (AZ) |
| 12502232 Tinely girls CIS mobile | KZ, LV, MD, EE, LT, GE, AZ | 0.02 (AZ) |
| 12510622 Tinely girls KZ mobile CPA | KZ | 0.056 |
| 12510623 Tinely girls LT mobile CPA | LT | 0.044 |
| 12510625 Tinely girls LV mobile CPA | LV | 0.032 |
| 12510626 Tinely girls EE mobile CPA | EE | 0.148 |
| 12510729 Tinely girls LATAM mobile WL - CR DO GT PA (8326) | CR, DO, GT, PA | 0.048 (PA) |
| 12510730 Tinely girls CIS mobile WL - KZ AZ MD LT (8394) | KZ, AZ, MD, LT | 0.02 (AZ) |
| 12510766 Tinely girls LATAM CPA - CR DO GT PA (8326) | CR, DO, GT, PA | 0.048 (PA) |

All 13 were written and read back: PATCH 204, and the bid and the conversion cost both read back as the new value.

Later on 12.10 the three desktop-only campaigns (12502227, 12502229, 12502231) also got the mobile OS list of their
sibling mobile campaign. Their OS targeting was the desktop ids 8, 9, 10; now it is those plus the 38 mobile ids,
41 in total, so they serve mobile and desktop. The names were changed to match. Bids and conversion cost were not
touched, and all nine of their teasers were already active.

```bash
node ~/.claude/skills/secrets/vault.mjs exec mgid -- python3 mgid/cpa_share.py 12502227 ...           # plan, changes nothing
node ~/.claude/skills/secrets/vault.mjs exec mgid -- python3 mgid/cpa_share.py --apply 12502227 ...   # PATCH, then read back
python3 -m unittest -v mgid/test_cpa_share.py                                                       # offline checks
```

## Ukraine: one CPA copy at 1 cent, sources blocklist off (12.10)

Owner, 12.10: «На Украину есть объявления? Убери блеклист и запусти Украину на cpa tune 1 цент?»

- **Offers.** Cabinet cards on 12.10. Active (status 1): Tinely - Mobile/Desktop [UA] SOI 18+ (Exclusive) (8395), $1.00;
  Gentlove - Mobile/Desktop [UA] SOI 18+ (10276), $1.00; Tinely - Mobile / Desktop [UA] PPS 18+ (11181), $12.50.
  Not approved (status 0): Sinder - Desktop/Mobile [UA] SOI (9027), $1.55; Natalie Dating - Desktop/Mobile [UA] SOI (NEW) (14564),
  $0.85; Natalie Dating - Desktop/Mobile [UA] SOI (9542), $0.60; Amurest- Mobile [UA] SOI (M+F) 18+ (10135), $0.624;
  OneAmour - Mobile / Desktop [UA] PPS 18+ (10976), $14.00.
- **Campaign.** `mgid/ua_copy.py` created Tinely girls UA mobile CPA (12511370): geo Ukraine (MGID id 1), offer 8395,
  targetCpa $0.01 and the same conversion cost in the settings, budget $20 a day. Mobile OS list and Russian language are
  copied from Tinely girls CIS mobile (12502232); the three teasers are the CIS creatives. Read back before the start, all
  matched. Started on 12.10 (`active/fulfilled`). The teasers are on moderation, so nothing is served until MGID approves
  them; auto-launch after approval is on.
- **Blocklist.** The account's sources blocklist had 103 entries, 52 of them .ua domains. It is switched off now
  (`filterType off`, 0 entries). Per the API docs it acts only with sources optimization on; that is off in all 13 dating
  campaigns and in the new one, so nothing else changed. The list is kept in `data/sources-blocklist-before-12.10.json`.
  The placement blacklist of the CIS source (243 placements) is not copied into the new campaign.
- **Spend.** The spend stop-loss counts the new campaign from zero and stops it at $3, like the others.
- **Bid.** At a $1.00 payout one cent is 1% of the payout. The 10% rule (`cpa_share.py`) would bid $0.10; the owner's
  figure is used here.
- **Creatives.** On 12.10 the ten approved teasers of the old test campaign 12478529 (account 816921, Ukrainian titles and
  images) were copied into 12511370 by `mgid/ua_transfer.py`: title and image as they are, our standard link
  (`aff_sub5=mgid`, the old one had `aff_sub5=native`). The old account was only read. The new teasers are on moderation;
  the record is in `data/ua-old-teasers.json`. Some creations hit MGID's teaser add limit (`LS_TEASER_ADD_LIMIT_ERROR`),
  so 7 of the 10 are in. `python3 ua_transfer.py --apply` adds the other three when the limit allows (tried 12:27,
  12:37, 12:47, 12:57 and 13:04 UTC, all refused). The three Russian CIS teasers (28144941–28144943) were deleted on 12.10
  (MGID restricts Russian-language teasers in Ukraine under the language law, art. 32 of Law 2704-VIII;
  they had no impressions and no statistics; a deleted teaser cannot be restored).

- **Second campaign (12.10).** `mgid/ua_v2.py` created Tinely girls UA mobile CPA v2 (12511469): geo Ukraine, offer 8395,
  targetCpa and conversion cost $0.01, $20 a day, mobile OS list of the CIS source, **no language targeting**. The first
  campaign had copied the browser language of the CIS source (Russian only, value [39]); the campaign that delivered 557
  clicks in Ukraine had none. The ten Ukrainian teasers (titles and images of 12478529, our link) are in it, on
  moderation. Started on 12.10 (`active/fulfilled`). The first campaign 12511370 is paused, not deleted.

## Earlier: all dating campaigns on CPA 1 cent (11.10)

Owner: «мужские удали, все остальные запускай, сбрось 3 бакса начиная с сейчас, считай».

- **Deleted** the six men's campaigns 12501886–12501891 (Tinely dating, men's creatives). Teasers went with them.
- **Switched** the twelve remaining campaigns (girls 12502227–12502232, whitelists 12510729–12510730, CPA copies
  12510622, 12510623, 12510625, 12510626) to `targetCpa` $0.01 with conversion cost 0.01, with
  `mgid/cpa_cent.py` (removed on 12.10, replaced by `mgid/cpa_share.py`). Each was read back. The LATAM CPA test (12510766) already had the same settings.
- **MGID refuses teaser CPC changes under CPA bidding** ("CPC changes are not allowed with CPA bidding strategy
  campaign"), so the teasers keep their old CPC; the algorithm sets the click price.
- **Relaunched** the paused ones at 20:41 UTC: 12502227–12502232 and 12510622. The rest were already active.
  The wallet was $13.94 at the time.
- Conversion cost 0.01 means the placement guard stops a placement after $0.02 without a lead, as for the
  LATAM CPA test. Expect many placements to be blacklisted quickly.

## LATAM CPA test, one campaign (11.10)

`mgid/latam_cpa.py`: **Tinely girls LATAM CPA - CR DO GT PA (8326)**, campaign 12510766. Geos CR, DO, GT, PA
(the ones with approved leads), targetCpa $0.01 as the owner set it, no whitelist, $20 a day. The conversion
cost in the settings is $0.01 too, so the guard stops a placement after $0.02 without a lead of this
campaign. Teasers are the LATAM creatives at 1.0¢, on moderation at launch.

On 11.10 the owner asked to stop every other active MGID campaign except the two whitelist copies. The
KZ CPA copy (12510622) was paused; the rest were already paused. The wallet was $13.94 before the launch.

## Whitelist copies of the girls campaigns (11.10)

Owner: «запусти вайтлист копии с теми же крео, по минималкам ставкам по cpc, те же гео что дали лиды,
на тех же площадках, задача отбить минуса». `mgid/whitelist_copies.py` makes one copy per offer (the
teaser link carries the offer id, the conversion cost is one number per campaign):

| copy | source | offer | geos | placements | CPC (teaser) | bid (campaign) | conversion cost |
|---|---|---|---|---|---|---|---|
| Tinely girls CIS mobile WL - KZ AZ MD LT (8394) (12510730) | 12502232 | 8394 | KZ AZ MD LT | 7 | 1.5¢ | $0.015 | $0.44 |
| Tinely girls LATAM mobile WL - CR DO GT PA (8326) (12510729) | 12502230 | 8326 | CR DO GT PA | 8 | 1.0¢ | $0.01 | $0.62 |

Both: `manualBidding`, $20 a day, the source's OS and language, the source's three teasers (same images,
title and link), UTM as in the other copies, v2 widget filter `only` with the lead placements.

- **The minimum CPC is per geo.** MGID refused a campaign bid of 1.0¢ on the CIS geos ("bidding.price
  must be >= 0.015") and accepted 1.0¢ on LATAM.
- **The lead placements** are the approved cpamatica leads of the source campaign (`aff_sub3` =
  `{widget_id}`), 30.09 to 11.10. Dating CIS (12501891) is not in it: its creatives are men's.
- **Teasers were rejected on the KZ copy** (12510622): "Restricted or Illegal product/service", no
  further detail from MGID. The LT, LV and EE copies carry the same rejected teasers (paused). The two
  whitelist copies' teasers were still on moderation at 11.10 with the same creatives and title.
  Nothing is served until a teaser is approved.
- **What the history says.** Those 15 placements (30.09 to 11.10): spend $4.64, 310 clicks, 17 leads,
  revenue $10.04, i.e. +$5.40 in sample. Everything else on the account: spend about $101, revenue
  $2.24, i.e. -$99. The whitelist is a cut of the loss, not a recovery: it sells about 26 clicks a day,
  so at 1.0-1.5¢ it spends about $0.4 a day, and the in-sample surplus is about $0.45 a day before the
  selection bias (the placements were picked for having leads) is taken out. $93 would take years.
- **The wallet is shared** with the KZ copy and is $13.94 (11.10).

**Guard for whitelists.** The guard used to read a whitelist as a blacklist: its placements counted as
"already blocked" and nothing was cut. Now a placement on an `only` list that spends 2 conversion
costs without a lead of that campaign is removed from the list (v2 `batch-delete`, read back). The
last placement of a list is never removed: the campaign is paused instead, because what an emptied
`only` filter turns into was not tested. Spend outside the list is reported (`MGIDG_WARN`).
Tests: `test_guard.py`, 19 offline checks. The removal was tested live on the LATAM copy (one
placement off and back on, the list read back identical).

```bash
node ~/.claude/skills/secrets/vault.mjs exec mgid -- python3 mgid/whitelist_copies.py           # plan
node ~/.claude/skills/secrets/vault.mjs exec mgid -- python3 mgid/whitelist_copies.py --apply   # create, check, start
node ~/.claude/skills/secrets/vault.mjs exec mgid -- python3 mgid/whitelist_copies.py --apply --only CIS
```

**MGID answers slowly from Inferno.** `quality-analysis` took 13 s there (under a second from a
sandbox), so a guard run took 3 to 4 minutes, and one run hit the 240 s start timeout. The unit now
allows 900 s, and the deploy's dry run has a 900 s limit and no stdin.

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
with the lead) with `targetCpa` bidding and a $20 daily budget. Created paused, teasers on moderation.

**State since 11.10 (owner: «стопни пока все кроме казахстана»):** only KZ (12510622) is started; LT, LV
and EE stay paused, and so are all six older «Tinely girls» campaigns. Teasers of the KZ copy were still on moderation after a day, so no
traffic until they are approved. The v2 read of `isAutoLaunchAdsAfterApproval` always says `false`
(also on the 30.09 campaigns whose teasers did start by themselves), so it cannot confirm a PATCH;
check that the approved teasers are `active` instead.

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

## Analytics by geo and placement

`mgid/analytics.py`: spend, clicks and impressions from MGID (v2 report by country and by placement),
leads and money from cpamatica (`cpamatica.mjs conv`), joined by country and by campaign + placement
(`aff_sub3` carries `{widget_id}`). Also replays the 2 x CPA rule over the history.

```bash
node ~/.claude/skills/secrets/vault.mjs exec mgid -- python3 mgid/analytics.py \
    --conv <Tedbolt>/mirelia_api/.mirelia/cpam-conv.json --out /tmp/mgid-report
```

Reading of 11.10 (30.09 to 11.10, spend $105.56, 21 leads, $12.28):
- Kazakhstan is the only geo near break-even: 9 leads on 587 clicks, CR 1.53% (95% interval 0.8 to
  2.9%) against 2.7% needed at 1.5¢ and 1.8% at the 1.0¢ minimum. At that CR the break-even CPC is
  0.86¢, below the minimum, so it only works if the real CR sits in the upper half of the interval.
- LATAM cannot work at these payouts: 9 leads on 5417 clicks, CR 0.17% (0.09 to 0.32%) against ~2%.
  Not one of its seven geos reaches break-even even at its upper bound.
- Georgia, Azerbaijan and Moldova took 60% of the CIS spend; AZ and MD pay $0.20 a lead, which needs
  a 7.5% CR at 1.5¢.
- Placement blocking is a weak lever on this traffic. LATAM mobile spent $81 over 586 placements
  (top 10 = 18%, top 50 = 62%); the 21 placements over the 2 x CPA line held only $3.00 above the
  line. The money is lost by the geo, not by a few placements.

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
- **A top-up restarts campaigns that the network stopped for lack of funds** (`outOfClientFunds`,
  v2 status `active/unfulfilled`): the `mgid` skill says they stay paused, and that is wrong. After
  the $100 top-up of 10.10 «Tinely girls LATAM mobile» spent $80 in about a day (5300 clicks at 1.5¢,
  9 leads) on its $2000 daily limit and took the balance from $99 to $14 before it was paused. Before
  topping up, pause what should not run, or lower the limits.
