# mgid-agent
MGID/Adskeeper agent.

`index.js` / `Dockerfile` are the small health-check service. Everything about the dating tests on
MGID account 816929 (v2 client 939031) lives in `mgid/`, plain Python, standard library only.

## State on the evening of 13.10: the account is blocked by MGID moderators, the old dating campaigns are paused

**Nothing has run on 816929 (v2 939031) since about 18:30 MSK.** All 240 teasers of the account are `blocked` (83,
`blocked_by: moderator`, no reason given) or `rejected` (157); none is active. Of the 83 blocked, 43 are the dating
teasers (taken down about 18:30 MSK) and 40 are the old nutra "spy" teasers (AL, IT) of campaigns that have had no
delivery since before 01.09, so those were blocked at some earlier, unknown time. What is proven: every teaser that was
serving on 13.10 went down (MindHue rejected at about 15:15, dating blocked at about 18:30). That it is an action on
the whole account is NOT proven; a bulk block of everything linking through the cpamatica tracker `go.cm-trk6.com`
(all 43 dating teasers do) fits as well. It was not the bid changes of the same afternoon: campaigns nobody touched
(CIS, KZ, Baltics) stopped in the same hour. MGID hours are MSK. (The first version of this note said "account-wide" on
the strength of the nutra blocks; the report-by-day check corrected it.)

- **Tinely girls (dating).** 12 campaigns with `blocked` teasers; the two LATAM copies 12510729 and 12510766 are
  `rejected` "Explicit content". The moderator's screenshots show the mobile lander of Tinely LATAM (offer 8326): a
  "WARNING! You will see nude photos" gate and a topless photo.
- **The 36 flow teasers of 13.10 12:42 were all rejected "Explicit content".** The screenshots (moderator in Arlington, US)
  show the offers' own landers behind the flow: "WARNING! You will see nude photos. Please be discreet." So the account
  trafficback was only part of it: with flow `0-Olte` the moderator reaches an offer's lander, and the lander is what
  is refused. Flirtooy (AU, CA, NZ) was not part of that batch and stays rejected.
- **MindHue = the push-subscription funnel monetized by ProPush** (13 campaigns `MindHue cpatune 0.01 <geo> mobile`, a
  personality quiz on the lander `omnitr.com`, not created by anything in `mgid/`; the owner called them «наши пропуш
  объявления»). All 95 teasers are `rejected`: "Suspected cloaking" (most; two campaigns "too many redirects"),
  "Landing page issue", "The webpage has formatting issues: clicking the link to continue the survey opens ...",
  "Restricted or Illegal product/service" (4, EN-MULTIGEO). They delivered from 12.10 15:00 to 13.10 about 15:15 (hour 15
  had 2065 impressions against ~8900 in the hours before): 189k impressions, 3.7k clicks, $0.37 in all, then stopped, three
  hours before the Tinely block. They are left `active`; with every teaser rejected nothing is served.
- **Old account 816921.** 175 teasers: 62 `campaignBlocked`, 106 `rejected`, 7 `blocked`; none active. Its v2 answers 401
  with that token, v1 works.
- **Why MindHue is rejected (checked the same evening, `omnitr.com/mgidcis/`).** The page is the same file for every
  visitor (mobile, desktop, no parameters, raw macros: identical 33443 bytes), so nothing is hidden from anyone. What it
  does on a click is what MGID refuses: its own `survey.js` fires a tab-under on EVERY answer (the current tab goes to the
  offer, a new tab reopens the quiz on the next step); `reverse.js` takes over the back button after the first click
  (`pushState` + `popstate` -> redirect, `back_count` 10); `autoexit.js` redirects the tab after 90 s without interaction;
  the final "REVEAL" is a popunder plus a redirect (`pushScript.js`, the ProPush push SDK, is included too, but the page
  config carries no push zone, so it looks inactive here). The moderator texts match: "Clicking the link to continue the survey opens an
  additional link", "too many redirects", "Suspected cloaking" (68 of 95). Fixing it means changing the page for
  everyone (no tab-under, back or auto exit; a visible link to the offer), which removes the monetization it was built
  for. It must not be done by showing moderators another page.
- **Dr.Cash nutra.** The owner asked whether a new campaign on the Dr.Cash nutra can be launched. The keychain has no
  Dr.Cash or AdCombo entry (vault refreshed over git, 92 services), and the stream link and creatives of that bundle are
  not known here. The old nutra copies (AL, IT, BA "spy" campaigns, AdCombo links on `uewhbgfvds.cc` and `axdsz.pro`)
  ran on this account with real volume (IT weight loss: 166k impressions, 3661 clicks, $58.58 on one teaser; no delivery
  since before 01.09) and their teasers are `blocked` by a moderator, at an unknown earlier time. Nothing new was
  submitted: whether a clean new teaser passes is not known, and one more rejection on this account is a cost; a test
  needs the Dr.Cash stream link and creatives, and a link that does not go through `go.cm-trk6.com`.

**Owner, 13.10 evening: «Можешь стопнуть все старые объявления».** The 14 active Tinely girls campaigns were paused with
the v1 flag (`mgid_api.pause`), each read back `paused/clientManuallyPaused`: 12502227, 12502228, 12502229, 12502230,
12502231, 12502232, 12510622, 12510623, 12510625, 12510626, 12510729, 12510730, 12510766, 12511469. All were
`active/unfulfilled` before. To start one again: `pause(cid, False)`. The guard watches only active campaigns, so it
has nothing to do until they are started. MindHue and the old paused campaigns were not touched; the bids of the same day
stay (PL 1.60, LATAM 0.336, UA 0.30, CIS 0.12, KZ 0.168, LT 0.22, LV 0.16, EE 0.74).

**Open.** Only MGID support can lift the block (the moderator sets `blocked`), and a lander the moderators accept is
needed: each offer has several landers (`pages` in the offer card, e.g. Tinely LP_2 / LP_10, Singles-meets GZH...), so the
first step is to look at them and pick the ones without nudity or the "nude photos" gate. No cloaking: every visitor,
moderators included, gets the same page.

## Content-arbitrage test: MGID (Kazakhstan) -> arcadiablog.com/dom -> Geozo blocks (13.10 evening)

Owner: «Давай попробуем запустить на cpa tune с ценой в 1 цент контент арбитраж, у нас апрувнули на geozo паблишерский
сайт, цель за лид сделать клик на самих блоках geozo», then «Запусти на этом сайте версию под Казахстан для теста, статьи
обычные под аудитории 40+, блоки органично вписать, трафик на мгид со ставкой в 1 цент cpa tune. Нужно будет слать
конверсию на каждый учтённый платный клик на geozo».

```
MGID teaser (KZ, Russian, mobile, targetCpa $0.01)
  -> https://arcadiablog.com/dom/[article].html?click_id={click_id}&source=mgid_{campaign_id}_{widget_id}
     article for 40+ with 4 labelled Geozo slots (none above the title)
  -> real click on an ad link inside a slot -> GET /dom/lead?c=<click_id>  (same origin)
  -> nginx relay -> https://a.mgid.com/postback?c=<click_id>&e=geozoclick&r=0.01   (goal 1280981, no dedup)
```

- **Site.** The Geozo publisher site arcadiablog.com (id 25953) is Confirmed (status 3). New folder `/var/www/arcadiablog.com/dom/`
  on Inferno, built by `mgid/geozo_site/build.py` (two articles that link to each other: food storage, house plants in
  autumn; the first is the TikTok version's text, the second is new), deployed by `geozo_site/deploy.py static`. The
  TikTok versions `/sovety/` and `/sfaturi/` are untouched. No TikTok pixel, no beacon, no redirect, no pop-up and no back-button tricks on
  `/dom/` (the build test fails if the script contains any), unlike the omnitr.com quiz that MGID rejected.
- **Geozo blocks.** Two own blocks so the statistics of this traffic are apart from TikTok's: `dom2-header` (id 1283938,
  uuid dffc5623-f12c-4c85-8cb1-efa1a2fc617f) and `dom2-feed` (id 1283939, uuid 68d5f52f-27f7-4157-b09c-c2da3a2b87b3), template
  16003 (image on top, 16:9, no button, no fake counters). The first pair (1283936 / 1283937) was made with 16006 "Post", which
  draws a fake clock chip and fake like/comment/share counters on every ad, and was switched by PUT; Geozo's render nodes kept
  serving the old template (and, in between, the broken narrow image-left 16001) for 20+ minutes in a random mix, so a fresh
  pair was created directly with 16003 and the first pair deleted. Bodies of all nine format-16 templates were captured with the
  local panel mock (Tedbolt branch claude/dr-cash-automation-20xngo, ops/geozo/webmaster); the one in use is
  `geozo_site/geozo_blocks/block_post_16003_16x9_nobtn.json`, applied with `webmaster.py create-block`/`put-block` (the
  image-left body is kept next to it). Not tested by Geozo's moderation, which only reads the site.
- **Conversion = a real click on an ad link in a slot** (`dom.js`): trusted event, at least 0.7 s after load, at least 1.2 s
  between signals, at most 6 per visit, only with a valid click id (MGID's are 32 hex characters). It is the closest thing
  to «each counted paid click» that exists: Geozo's publisher API has no per-click callback, only aggregates
  (`GET /v1/webmaster/stats`, needs `filters[date_from]`, `filters[date_to]`, `groups[]`, `order_by[0][column]`,
  `order_by[0][direction]`). Set our count (relay log) against Geozo's clicks to see how many clicks it did not count.
- **Relay.** nginx location `= /dom/lead` in `/etc/nginx/sites-available/arcadiablog.com` (backup in /root/backups, `nginx -t` before
  reload), log `/var/log/nginx/arcadiablog.dom.log` with MGID's HTTP status (`up=`). MGID answers 200 and a 1x1 GIF to any click
  id, real or not, so only the report of the campaign shows whether a conversion was counted.
- **MGID.** Postback target `Geozo block click` (id 1280981, eventName geozoclick), created with `POST /v2/ads/account/939031/targets`;
  not the dating target 1274200, so mgid-guard does not judge this campaign. Campaign **12512609** «Arcadia KZ content mobile CPA 0.01»
  (`mgid/geozo_campaign.py --apply`, then `--teasers`, then `--start`): KZ, Russian, mobile OS list, targetCpa $0.01 with conversion value
  $0.01 and deduplication OFF (every counted click is a conversion), type `product` because MGID refuses targetCpa on `content`
  (BIDDING_STRATEGY_CAMPAIGN_TYPES_ERROR). Five teasers, ids 28159839-28159842 and 28159844 (photos that show what the title says);
  the sixth was refused with LS_CAB_GOODS_TEASER_ALLOWED_DOMAIN_LIMIT, so five is the limit per landing domain in a campaign.
  Started 13.10 at 22:57 MSK while the teasers were `onModeration` (auto-launch after approval is on). The real cap of the test is
  `mgid-spend-stop` (pauses any active campaign at $3 spend); MGID's own daily minimum here is $20. Wallet at start: $12.90.
- **Report.** `geozo_report.py` prints MGID by hour (spend, clicks, conversions), page views and signals from the logs, and
  Geozo's block statistics.
- **Found on the way.** On the TikTok pages `/sovety/` and (same code) `/sfaturi/` the «Реклама» label never shows: the
  loader replaces the block container, and `template/site.js` keeps a reference to the old one, so the slot is never marked
  filled. `dom.js` looks the container up again on each check. The TikTok versions were not changed.
- **Risks to read before scaling.** The site was approved for «TikTok Ads (paid), audience 45+, GEO RO/KZ»; MGID is another source.
  OpenRouter's balance is empty (images need at least $1), so the second article uses photos already on the site.

### The dense layout /dom2/ and its own campaign (13.10 evening)

Owner: «Почему так мало блоков? Нужно максимально агрессивно для максимальной монетизации блоки расставить и максимум тизеров
в блок». Four slots with one ad each was a deliberate start (moderation, readability); the Geozo panel allows **10 x 10 ads in a
block of template 16003** (feedCount = mediaHorizontal x mediaVertical; on a phone the cards stand in one column, so 10 is the
ceiling). So:

- Three new blocks of the same template, one column wide, made with `geozo_site/geozo_blocks.py create NAME FEED` (a changed number
  of ads means a new block: Geozo's render nodes serve the old settings of an edited block for 20+ minutes, and a new block needs
  a few minutes before every node knows it, in between it answers 200 with an empty body): `dom3-a` (id 1283940, 3 ads, right after
  the lead), `dom3-b` (1283941, 4 ads, after every second block of text), `dom3-c` (1283942, 10 ads, end of the article).
- `dense.css`: compact cards (thumbnail left, headline right, 3-10 of them take a third of a screen to two, not one screen per ad).
  Selectors by substring of the class because the loader gives the classes a random prefix.
- A page now has 8-9 slots and 37-41 ads (the moderate one: 4 slots, 4 ads). All slots keep the label «Реклама»; none above the
  title; never between a heading and its text; never two in a row.
- **Not done in place.** The moderate pages `/dom/` had just been approved by MGID (teasers `active`). Editing an approved landing page
  into an ad-heavier one would be moderation evasion even though every visitor sees the same page, so the dense version has its own
  address `/dom2/`, its own campaign **12512618** «Arcadia KZ content mobile CPA 0.01 dense» (`geozo_campaign.py --variant dom2`), its
  own six teasers (28159916-28159921) and its own moderation: MGID moderators opened it within two minutes and approved all six
  teasers in about seven (all `active` at 20:29 UTC). `/dom/` stays byte for byte what was approved (`build.py` reproduces it;
  `test_geozo_site.py` checks that the dense blocks never leak into it).
- Two layouts side by side is also the A/B test: same teasers, same bid, same geo.
- **First real chain (14.10 00:49 MSK).** One visitor from Kazakhstan (nginx `cc=KZ`, Android 10 Chrome, referrer clck.mgid.com) came
  to the dense page and clicked ad blocks four times (two within the first 20 s, two more 13 minutes later in the same open tab);
  the relay logged four signals with `up=200` and MGID's report showed two conversions of the goal at the time (the report lags).
  MGID's price of that click was $0.0001, so the one-cent target is far above what Kazakhstan costs; the limit is volume
  (about 500 impressions an hour), not price. One visitor proves the chain, not the rate. The other visits in the log are MGID's
  moderators (referrer clck.mgid.com/ghits/<teaser>, Android 8 / Android 16 WebView, IPs outside Kazakhstan).

### Multilingual site /blog/<lang>/ and 14 geo campaigns (13.10 night)

Owner: «Нужно сделать сайт мультиязычным и взять все гео, что монетизирует ЛакиФид, кроме России и Беларуси; на них минимум по
10 статей на каждое гео, картинки те же самые, блоки те же самые; запустить кампании на эти гео и языки с 1-2 креативами в самом
MGID. Начни с Болгарии, Польши, Румынии, Чехии, Португалии, Италии, Испании, немецкоговорящих Германии, Швейцарии, Австрии,
Венгрии, Словакии, Словении, Сербии». (Казахстан-вопрос «показы есть?»: да, см. отчёт `geozo_report.py`.)

**Geos.** LuckyFeed income by country, USD wallet, 15.08-13.10 (`api.luckyfeed.pro/v5/stats/full`, `groups[0]=country_code`; RU/BY/KZ
are on the rouble wallet and not in this list): BG $2446, HU $1757, RO $1239, CZ $787, PL $519, RS $494, DE $444, **HR $297**, PT $167,
SK $155, IT $126, **FR $64**, **NL $29**, ES $26, SI $9, AT $9, CH $1 (GB $7, MX $6, BE $2, TR $1, GR $1 and 130 rows of zero). The
owner's fourteen are all in the list; Croatia (8th by income), France and the Netherlands are not in his list: next wave.

**Site.** `arcadiablog.com/blog/<lang>/`, 12 routes plus `ch`: bg pl ro cs pt it es de hu sk sl sr; Austria uses `/blog/de/`,
Switzerland `/blog/ch/` = the German text with ss for ß. Why `/blog/` and not `/<lang>/`: the server already holds the old
gardening blog (March 2026) in `/cs/`, `/sk/`, `/sl/` and nginx redirects everything that starts with `/ro` to `/`
(`location ^~ /ro`); neither is touched. `/blog/` is a plain language chooser; each route has a home page with the ten
articles, the ten articles, about / contact / privacy, a footer language switcher; the home and the service pages carry no ads
and do not load the Geozo loader. The article pages use the dense layout (same three blocks, label «advertisement» in the local
word: Реклама, Reklama, Publicitate, Publicidade, Pubblicità, Publicidad, Anzeige, Hirdetés, Oglas) and the same relay
(`/dom/lead`, one signal per real click on a block).
- Code: `geozo_site/multi_config.py` (languages, geos, MGID ids, the ten topics), `build_multi.py` (build; shared hashed script, hero
  1200x700, list thumbnail 360x240, teaser creative 1200x800 once under `/blog/{h,t,c}/`), `make_images.py`, `check_articles.py`,
  `deploy.py static --route blog` (the whole tree, ~2.5 min). Tests: `test_multi_site.py` (synthetic folders, 14 checks).
- **Texts.** Ten topics (food storage x4, herbs in a jar, bread, houseplants x3, windowsill herbs, repotting, lavender, aloe
  care, drying herbs), outlined in `articles/BRIEF.md`; twelve parallel writers each wrote their language natively (about 4300
  words, ten articles, `ui.json`, `pages.json`, `teasers.json`), the checker enforces format, length, script, language markers and
  flags health-claim stems. No health claims, no brands, no prices. Nobody native has proofread them: Hungarian and Slovak writers
  said so, Italian and Romanian writers noticed that the aloe photo looks more like an agave.
- **Images.** The same photos as the Kazakhstan test plus three of the old blog (lavender field, aloe leaf, dried herbs; the
  spice-jar photo is cropped to the bowls and the brand label is blurred). Ten topics, ten pictures.

**Campaigns** (`mgid/geozo_geos.py`; `--apply` creates them paused with the teasers, `--start` starts, `--status`): one per geo,
mobile, targetCpa on goal 1280981 (no dedup), language of the geo, type `product`, daily limit $20, cap $3 by mgid-spend-stop. Two
teasers each: always the jar-of-water herbs article and a second one that rotates (bread, fruit and vegetables, houseplants) from geo
to geo so that the first data also says which article wins.

| geo | campaign | targetCpa now (start) | teasers |
|---|---|---|---|
| BG | 12512632 | 0.03 (0.01) | 28160036, 28160037 |
| PL | 12512633 | 0.05 (0.02) | 28160038, 28160039 |
| CZ | 12512634 | 0.05 (0.02) | 28160040, 28160041 |
| PT | 12512635 | 0.02 | 28160042, 28160043 |
| IT | 12512636 | 0.02 | 28160044, 28160045 |
| ES | 12512638 | 0.02 | 28160046, 28160047 |
| DE | 12512639 | 0.10 (0.04) | 28160048, 28160050 |
| CH | 12512640 | 0.05 | 28160051, 28160066 |
| AT | 12512641 | 0.10 (0.04) | 28160068, 28160069 |
| RS | 12512643 | 0.01 | 28160070, 28160071 |
| RO | 12512647 | 0.03 (0.01) | 28160088, 28160089 |
| HU | 12512648 | 0.04 (0.015) | 28160090, 28160091 |
| SK | 12512649 | 0.03 (0.01) | 28160092, 28160093 |
| SI | 12512650 | 0.03 (0.01) | 28160094, 28160095 |
| KZ (`/blog/ru/`, 14.10 night) | 12512714 | 0.01 | 28161033, 28161034, 28161035, 28161036 |

The bids were a first guess, not a measurement: the cheap geos started at the one cent of the Kazakhstan test, the geos with a
higher floor price higher. **14.10 ~01:25 MSK**: after 80 minutes of approved teasers and no impressions at all in BG RO SK SI HU PL
CZ DE AT the target was raised (`geozo_geos.py --set-cpa BG=0.03,...`, PATCH of `bidding` plus the new value in the campaign name);
PT ES IT CH delivered at the starting values (a few dozen impressions an hour at MGID's $0.0001 click) and keep them, RS waits for its
moderation. The values live in `CPA` in `geozo_geos.py`, the starting ones in `START_CPA`. Wallet at launch $12.90, 16 campaigns with a
$3 cap each: the wallet runs out first.

**Report.** `geozo_report.py` is one row per campaign (MGID impressions / clicks / spend / conversions, page views and distinct
32-character click ids from the nginx log by the campaign id in `source=mgid_<campaign>_`, relay signals and MGID's answer to
them). Geozo's `/stats` has answered 429 ("Whoops, looks like something went wrong") to every valid query so far, so Geozo clicks and
revenue are still unread: until they are, nobody knows what a block click earns in these geos. Probed 13.10: the valid `groups[]`
values are `date`, `site_id`, `block_id`, `country_code` (they pass validation and then fail with 429; `day`, `country`, `geo`,
`block`, `site`, `hour` get a 422 `validation.in`), with and without `filters[site_id]`, for one day and for a week. The panel
of the Geozo cabinet shows the numbers; its login is not in the vault. NodeMaven cannot be used from this container to test the Geozo fill per geo (the agent
proxy swallows the nested CONNECT), the first live traffic is the test.

**Open.** Whether MGID approves all 28 teasers; whether Geozo fills blocks in each geo and what it pays (LuckyFeed income is another
product and says nothing about Geozo's CPC); the Geozo site was approved for «TikTok 45+, RO/KZ», so the manager should be told that
the traffic now also comes from MGID and from fourteen more geos; German-speaking pages have no Impressum (the DE writer's note);
LuckyFeed's HR, FR, NL for the next wave.

### A second action next to the clicks: the free e-book (14.10 night)

Owner: «у нас просто контент арбитраж, а он запрещён по CPA-tune модели, тоесть нам нужно добавить на сайте ещё действие, которое будет
параллельно кликам. Сбор имейл, например, или что-то в этом роде ... мы пытаемся стать compliant для MGID и использовать их CPA tune»,
then «А что может быть кроме подписки? Может скачивание электронной книги?», and after the book was live: «Сделай так, что мы всё льём
на версии с книгой, конверсии шлём как раньше за каждый клик, но теперь плюс скачивание книги, и всё». What exactly MGID's rules say
about arbitrage inside CPA tune is **not known** (the question to MGID support is drafted, not sent); this is the part that does not
depend on the answer: a real, free action of the visitor that is not a click on an ad, counted next to the clicks.

- **The book.** Every language has a free PDF compiled from its own ten articles (`geozo_site/make_ebooks.py`): A5, cover with a
  mosaic of four photos, «about this book», contents, the ten articles as chapters, a closing page, no ads inside, no registration, no
  e-mail; 34 pages, about 850 KB (photos at 800 px). The strings (title, subtitle, introduction, the offer card's text) are written by
  the language's writer into `articles/<lang>/ebook.json` (`articles/EBOOK_BRIEF.md`, checked by `check_articles.py`); Switzerland derives
  from German like everything else. Output goes under `blog/ebook/` (`<lang>.pdf`, `cover-<lang>.jpg`, `pages.json` with the real page
  counts for the card); `build_multi.py` calls it, `--no-ebook` skips it (a route without `ebook.json` gets no book and no card).
  Chromium writes a new creation date into every PDF, so a rebuild changes the bytes of all books: to upload only what changed, copy
  the unchanged `ebook/<lang>.pdf` and `cover-<lang>.jpg` of the previous stage over the new build before `deploy.py static`.
- **The card.** `<aside class="book">` after the second block of text and again before the last ad slot of every article, and on the
  home page; it is not an ad (no label, own colour, outside `.ad-slot`, so a tap on it never sends the ad-click signal: tested), a plain
  link to `/blog/dl/<lang>.pdf` that `dom.js` decorates with `click_id` and `source` like every internal link.
- **Counting: the download is one more conversion of the same goal as a block click.** nginx location
  `~ "^/blog/dl/(?<bl>bg|ch|...)\.pdf$"` (the alternation is exactly the list of real routes; a made-up language gets a plain 404 and no
  signal; the regex must be quoted, a bare `{2}` makes `nginx -t` fail) serves `blog/ebook/$bl.pdf` as an attachment
  (`Cache-Control: private, no-store`, `X-Robots-Tag: noindex`) and `mirror`s the request to the internal location `= /_ebook_pb`, which
  calls `https://a.mgid.com/postback?c=<click_id>&e=geozoclick&r=0.01` (exactly what the block relay `/dom/lead` sends, goal 1280981 «Geozo
  block click», deduplication off, so a campaign's conversions are block clicks plus downloads and its CPA tune is not restarted) and
  returns 204 when there is no valid click id (a download without an MGID click is not reported). **One postback per click id and
  minute** (`limit_req_zone $arg_click_id zone=arcadia_book:2m rate=1r/m` in conf.d, `limit_req` in the mirror location, status 429):
  a second tap or a script does not make a second conversion, the visitor still gets the file (tested live: first request `up=200`,
  next two `st=429 up=-`, other click id `up=200`). The log `arcadiablog.dom.log` has two lines per download: the request (`up=-`) and the
  postback (`up=<MGID status>` or `st=429`; `log_subrequest on`). `deploy.py nginx` is idempotent: it adds the locations, rewrites the
  location line and the mirror block of older versions, adds the zone (backup, `nginx -t`, reload, automatic rollback).
- **The separate goal.** `E-book download` (id **1280985**, event `ebook`, category «Other» = 9; v2 postback targets accept only
  categories 1 and 9, "Selected category is not available" for 2-5) exists (`geozo_geos.py --make-goal ebook`) but **no campaign uses it**:
  the first version of the mirror sent `e=ebook` and the plan was to switch the campaigns' goal to the download (`--goal ebook --only ..`,
  still in the script, the learning starts over); the owner chose «clicks as before plus the download» instead. The count of downloads
  is in our log (`скач`), not in MGID's report.
- **Everything on the version with the book.** The fourteen geo campaigns already point to `/blog/<lang>/`. Kazakhstan did not: the
  approved `/dom/` and `/dom2/` have no book and are not edited (an approved page is never made heavier). So `ru` is a route
  (`GEOS["KZ"] = (5, "ru")`, MGID language 39, ten articles, ui, pages, teasers and `ebook.json` written by a Russian writer for
  readers in Kazakhstan, 34-page book) and Kazakhstan has a campaign of its own, **12512714** «Arcadia KZ blog content mobile CPA 0.01»
  (`geozo_geos.py` geo `KZ`, name tag «blog» so it is never mixed up with the two older ones; four teasers 28161033-28161036 with the
  Russian headlines of the herbs, bread, fruit-and-vegetables and houseplants articles; targetCpa $0.01 on the same goal; created
  paused, started with auto-launch after approval). MGID approved all four teasers within about ten minutes of the start (22:54 UTC = 01:54 MSK, 14.10), and then the
  two older Kazakhstan campaigns (12512609 on `/dom/`, 12512618 on `/dom2/`) were paused by hand (`pause()` of `mgid_api.py`); their
  pages stay on the server and the old teasers still open them.
- **Verified live (14.10):** PDF with attachment headers, 34 pages in all 14 routes; fake click id gives mirror line `up=200`, repeats
  `st=429`; no click id gives 204 and no call; a made-up language gives 404 and no line; offer card 2x per article; the Russian pages and
  the language switcher. `geozo_report.py` shows `скач` (downloads with a click id) and `ebook200` (postbacks answered 200) per campaign;
  MGID's `конв` of a campaign should be about `up=200` + `ebook200`.
- **Not done / for the owner:** an e-mail newsletter as another action (needs an e-mail service provider and a legal operator's name
  and address on the site); a cookie banner that asks before the ad scripts load (the current one only informs) and an Impressum for
  the German-speaking pages: both matter before EU traffic is scaled.

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

## Mainstream dating tests, 15 campaigns prepared paused (12.10)

Owner, 12.10: «Подготовь все гео на тест» for the approved offers that had no campaign on MGID yet. `mgid/mainstream_tests.py`
creates them paused (`--apply`; the plan without `--apply` creates nothing): UTM, three women-alone creatives each with the
title in the geo's language, mobile OS list, $20 a day (the MGID minimum), and the bid at 30% of the payout.
Read back: bids and conversion cost equal, geo right, campaign language matches the creative (Spanish, English, French,
German, Danish, Norwegian), all 45 teasers on moderation. Nothing runs until the owner says so.

| campaign | offer | geo | payout | bid |
|---|---|---|---|---|
| 12511741 Tinely ES mobile CPA | Tinely - Mobile/Desktop [ES] SOI 18+ (Exclusive) (9960) | ES | $1.35 | $0.405 |
| 12511742 Tinely ZA mobile CPA | Tinely - Mobile/Desktop [ZA] SOI 25+ (Exclusive) (8331) | ZA | $0.78 | $0.234 |
| 12511743 Tinely HT mobile CPA | Tinely - Mobile/Desktop [HT] SOI 25+ (Exclusive) (8330) | HT | $0.23 | $0.069 |
| 12511744 Tinely CO mobile CPA | Tinely - Mobile/Desktop [CO] SOI 25+ (Exclusive) (8329) | CO | $0.19 | $0.057 |
| 12511745 Date4you US mobile CPA | Date4you - Desktop/Mobile [US] SOI (Mainstream) (5368) | US | €1.60 ≈ $1.84 | $0.552 |
| 12511746 iDates GB mobile CPA | iDates - Desktop/Mobile [UK] SOI (Mainstream) (5655) | GB | €1.84 ≈ $2.12 | $0.6348 |
| 12511747 iDates DE mobile CPA | iDates - Desktop/Mobile [DE] SOI (Mainstream) (5656) | DE | €1.60 ≈ $1.84 | $0.552 |
| 12511748 Singles-Meets US mobile CPA | Singles-Meets - Desktop/Mobile [US] SOI (Mainstream) (9047) | US | €1.56 ≈ $1.79 | $0.5382 |
| 12511751 Singles-meets US mobile CPA | Singles-meets - Desktop/Mobile [US] SOI (9014) | US | €1.56 ≈ $1.79 | $0.5382 |
| 12511753 Singles-meets DK mobile CPA | Singles-meets - Desktop/Mobile [DK] SOI (9018) | DK | €3.40 ≈ $3.91 | $1.173 |
| 12511755 SingleMeets NO mobile CPA | SingleMeets - Desktop/Mobile [NO] SOI (10233) | NO | €3.50 ≈ $4.03 | $1.2075 |
| 12511758 Singles-Meets IE mobile CPA | Singles-Meets - Desktop/Mobile [Multi-Geo] SOI (Mainstream) (9045), IE only | IE | €2.35 ≈ $2.70 | $0.8107 |
| 12511761 Flirtooy AU mobile CPA | Flirtooy (Mainstream) - Desktop/Mobile [WW] SOI+revShare (8978), AU only | AU | $5 | $1.50 |
| 12511763 Flirtooy CA mobile CPA | Flirtooy (Mainstream), CA only (8978) | CA | $4 | $1.20 |
| 12511764 Flirtooy NZ mobile CPA | Flirtooy (Mainstream), NZ only (8978) | NZ | $4 | $1.20 |

- **EUR payouts** are converted at 1.15 USD per EUR, an estimate: the dated rates found were 1.14–1.16 (late July to early
  August 2026), with no quote for today. Check before starting and correct the bids if the rate has moved.
- **Not in this batch:** the other geos of Singles-Meets Multi-Geo (CZ, DK, GR, IL, IT, NL, SE, UK) and of Flirtooy
  (UK, SE, NL, NO at $5; DE, CH, AT, US, IT, ES, FR at $4; others $2), which need a campaign and a title per geo; the
  adult-recommended Tinely offers (AR, MX, BR, IL, UK male-only) and the Gentlove offers.

### Moderation of the first batch, and the cpamatica flow behind the new teasers (13.10)

**Result.** Of the 15 campaigns none passed: all 42 teasers of 14 campaigns were rejected, "Explicit content", with
screenshot links; Date4you US (12511745) showed `campaignBlocked`. The screenshots (three of six opened) are not our
photos but pages after the click: a nude-photo warning ("Tits Tok"), "PICK THE HOTTEST SEX POSE", a "START SEXTING" chat.

**Cause.** Owner, 13.10: «Да они скорей всего зашли на трафикбек ссылки». Checked with `cpamatica.mjs redirect` from the
server pool (exit DE, which cpamatica geolocates as UK): the direct link of Tinely ES (9960) and of Tinely CIS (8394), which
did pass moderation on 30.09, goes `aff_c?offer_id=<n>` -> `aff_c?offer_id=8978&...&last=3` -> flirtoooy.com/direct_short.
So a click that cpamatica cannot hand to the offer (outside its geo or device, a datacenter address, a capped or paused
offer) goes to the account's trafficback, **Flirtooy WW (8978)**, whose pages are explicit although the card says
"(Mainstream)". Even the Mainstream Dating Smartlink WW (6011) opened directly went there from that address.

**What cpamatica allows.** A flow can have its own last offer (the trafficback), but it must be an OFFER from the
catalogue: the cabinet FAQ says "Select the last offer (trafficback) ... We recommend using general smartlinks". A URL such as
google.com cannot be set; that would need our own redirect by country on Inferno (CF-IPCountry), not built.

**Flow `0-Olte`** (owner: «Создай flow», then «Те что откровенны сами по себе мы не делай»). Created with
`cpamatica.mjs post flow '{"data":{"lastOffer":6011,"lastOfferPages":[0],"offers":null,"comment":"..."}}'`, offers added
with `cpamatica.mjs flowadd 0-Olte plan.json` (read back in `mgid/data/flow-0-Olte.json`): 26 entries, one per offer and
geo, for mobile (`device_type_mobile, iOs, Android`) and for desktop/tablet, Tinely PL (9962) added for Poland, and as last
offer the Mainstream Dating Smartlink WW (6011) in place of the adult smartlink. **Flirtooy (8978) is not in it**: its
landing pages are explicit themselves, so its three campaigns (12511761 AU, 12511763 CA, 12511764 NZ) stay as they were,
paused. The three US offers (5368, 9047, 9014) rotate on US traffic.

```
https://go.cm-trk6.com/aff_f?h=0-Olte&aff_sub5=mgid&aff_sub={campaign_id}&aff_sub3={widget_id}
```

Tests (`redirect` from the pool, mobile and desktop): flow -> iDates UK (5655) -> bl.idates.com, with `click_id`,
`source`, `aff_sub`, `aff_sub3` handed on to the offer link, so MGID's UTM and the postback pipeline still work. The flow
link answered 400 for the first few minutes after creation, then worked.

**Not covered.** The last offer 6011 accepts 220 countries but **not UK, CA, AU, NZ, IE, PL, MX, ZA**. UK, IE, ZA and PL
are covered by the flow's own entries, CA, AU, NZ and MX are not: a click from there (or on an offer that is capped or
paused) can still reach the account trafficback, i.e. Flirtooy. The only complete cure is our own country gate in front.

**Teasers.** `mgid/flow_teasers.py --apply` (12:42 MSK): 3 new teasers per campaign (same photos and titles) with the flow
link in the 12 campaigns except Flirtooy, all `onModeration`, the 36 rejected ones they replace deleted (including the
three `campaignBlocked` of Date4you US). `data/flow-teasers.json`. Campaigns stay paused.

## Dating campaigns on CPA = 30% of the payout per geo (12.10)

Owner, 12.10: «Точней поставь 10% от выплат на гео ставку cpatune» (replaces the flat 5 cents asked earlier that day).
Later the same day: 20% («Давай поставим может тогда 20% от лида ставку на дейтинг? Но на Украине оставь 1 цент
ставку»), then Ukraine alone at 5 cents («Очень дёшево покупаем Украину поставь там 5 центов»), then all dating geos at
30%: «Подними все до 30% от выплаты ставки по всем гео дейтинг». Ukraine is in the list too: its payout is $1.00, so its
bid is $0.30.

`mgid/cpa_share.py` sets each dating campaign's `targetCpa` bid to 30% of the cpamatica payout for its geo. The
conversion cost in the campaign settings gets the same number, and the placement guard stops a placement after 2x
that cost without a lead, so its threshold follows the new bid. The payouts come from `mgid/data/rates-<offer>.json`,
saved from the offer cards by `mgid/cpam_rates.py`.

- **One bid per campaign.** MGID cannot price geos apart inside one campaign, so a campaign on several geos gets 30%
  of the LOWEST payout among them: no geo is bid above 30% of its own payout. Exact per-geo bids mean one campaign per
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
| 12502227 Tinely girls PL mobile+desktop | PL | 0.60 |
| 12502228 Tinely girls PL mobile | PL | 0.60 |
| 12502229 Tinely girls LATAM mobile+desktop | CL, CR, DO, EC, GT, HN, PA | 0.144 (PA) |
| 12502230 Tinely girls LATAM mobile | CL, CR, DO, EC, GT, HN, PA | 0.144 (PA) |
| 12502231 Tinely girls CIS mobile+desktop | KZ, LV, MD, EE, LT, GE, AZ | 0.06 (AZ) |
| 12502232 Tinely girls CIS mobile | KZ, LV, MD, EE, LT, GE, AZ | 0.06 (AZ) |
| 12510622 Tinely girls KZ mobile CPA | KZ | 0.168 |
| 12510623 Tinely girls LT mobile CPA | LT | 0.132 |
| 12510625 Tinely girls LV mobile CPA | LV | 0.096 |
| 12510626 Tinely girls EE mobile CPA | EE | 0.444 |
| 12510729 Tinely girls LATAM mobile WL - CR DO GT PA (8326) | CR, DO, GT, PA | 0.144 (PA) |
| 12510730 Tinely girls CIS mobile WL - KZ AZ MD LT (8394) | KZ, AZ, MD, LT | 0.06 (AZ) |
| 12510766 Tinely girls LATAM CPA - CR DO GT PA (8326) | CR, DO, GT, PA | 0.144 (PA) |
| 12511469 Tinely girls UA mobile CPA v2 (8395) | UA | 0.30 |

All 14 (the 13 dating campaigns and the Ukraine one) were rewritten at 30% on 12.10 and read back: PATCH 204, and the bid and the conversion cost both read back as the new value. Earlier the same day they were at 10%, then 20%; Ukraine was at 1 cent, then 5.

Later on 12.10 the three desktop-only campaigns (12502227, 12502229, 12502231) also got the mobile OS list of their
sibling mobile campaign. Their OS targeting was the desktop ids 8, 9, 10; now it is those plus the 38 mobile ids,
41 in total, so they serve mobile and desktop. The names were changed to match. Bids and conversion cost were not
touched, and all nine of their teasers were already active.

**13.10, bids by region (owner).** «Нужно на cis поднять ставку в 2 раза», «На польшу поставить половину от выплаты
ставку», «Латам тоже на 10% от выплаты подними ставку». The last one is read as +10 points of the payout on top of
the 30% (a bid cannot be "raised" by setting 10%); say if 0.158 (10% more of the old bid) was meant. Each PATCH was
read back (204, bid and conversion cost equal). The guard's threshold follows (2 x the new cost); a higher cost only
loosens it, so the statistics window stays at 12.10.

| region | campaigns | share of the lowest payout | bid before -> now |
|---|---|---|---|
| CIS (x2) | 12502231, 12502232, 12510730 | 0.6 of AZ $0.20 | 0.06 -> 0.12 |
| Poland | 12502227, 12502228 | 0.5 of PL $2.00 | 0.60 -> 1.00 |
| LATAM | 12502229, 12502230, 12510729, 12510766 | 0.4 of PA $0.48 | 0.144 -> 0.192 |
| Baltics (later, same day) | 12510623 LT, 12510625 LV, 12510626 EE | 0.5 of LT $0.44, LV $0.32, EE $1.48 | 0.132 -> 0.22, 0.096 -> 0.16, 0.444 -> 0.74 |

Owner, 13.10, after the first three: «Я Балтике подними до 50% от выплаты также». The Baltic copies were not part of
«cis» and had stayed at 30%. The KZ copy (12510622) is not Baltic and keeps its 30%; the owner's message quoted its id
together with the others, so say if it was meant too (50% of $0.56 = 0.28).
`cpa_share.py --share 0.6|0.5|0.4` reproduces the new numbers; without `--share` it puts a campaign back to 30%.

**13.10, second round (owner).** «Подними ставки на польшу и ещё на 30% от стоимости конверсии но Украину поставь 30
центов ставку», then «На латам тоже подними ставку ещё на 30%». «Another 30% of the conversion cost» is read the way the
LATAM «+10% of the payout» was: +30 points of the payout on top of the share the region already had. If +30% of the
old bid was meant, that is Poland 1.30 and LATAM 0.25 (`--share 0.65` and `--share 0.52` put them there). Each PATCH was
read back (204, bid and conversion cost equal). The guard's threshold follows the cost (2 x the new cost) and a higher
cost only loosens it, so the statistics window stays at 12.10.

| region | campaigns | share of the lowest payout | bid before -> now |
|---|---|---|---|
| Poland | 12502227, 12502228 | 0.8 of PL $2.00 (50% + 30 points) | 1.00 -> 1.60 |
| LATAM | 12502229, 12502230, 12510729, 12510766 | 0.7 of PA $0.48 (40% + 30 points) | 0.192 -> 0.336 |
| Ukraine | 12511469 | 0.3 of UA $1.00 (the default share) | 0.20, conversion cost empty -> 0.30, both |

The Ukraine campaign is not at the 0.30 of the 12.10 table above: on 13.10 it read targetCpa 0.20 with an empty
conversion cost (not written by `cpa_share.py`). The guard had been using its bid as the cost (a CPA campaign without a
cost falls back to its price, threshold $0.40); now both settings are 0.30 and the threshold is $0.60. The first Ukraine
campaign 12511370 is paused and stays at $0.01. The payout at 80% leaves Poland $0.40 a lead below its $2.00.

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
- **Bid.** At a $1.00 payout one cent is 1% of the payout. The 20% rule (`cpa_share.py`) would bid $0.20; the owner's
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
  or MGID's own buy conversion. Judged per campaign, on the statistics window (below): spend and leads
  from `MGID_GUARD_SINCE`, 12.10, not from the campaign's first day.
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
conversion cost), `MGID_GUARD_SINCE=2026-10-12` (statistics window), `MGID_OFFERS` (offers that can be MGID leads).

**Statistics window since 12.10 (owner, 13.10).** «Статистики по ограничению площадок нужно собирать со вчера,
когда мы поставили везде cpa tune формат, и теперь данные новые по новой цене клика нужно собрать, так что все
площадки верни». Spend and leads now count from `MGID_GUARD_SINCE` (an MGID day, UTC+3), not from the
campaign's first day. Spend per placement comes from the v2 report (`widget_spend(cid, since=...)`), leads from
`mgid_leads` with `ts >= since_utc()` (12.10 00:00 UTC+3 is 11.10 21:00 UTC) and from MGID's own buy conversions
of the same window. The HOLD check still compares with the newest lead that had a placement, of all time.

Why. The twelve campaigns went to `targetCpa` $0.01 with a conversion cost of $0.01 on the evening of 11.10
(about 20:40 UTC), so the threshold fell to 2 x $0.01 = $0.02, and the guard judged the lifetime money of the
old price (manual clicks, about 1.5 cents) by it. Replayed on 12.10 (placements with a lead are left out):

| campaign | placements that ever spent | spent $0.02 or more, no lead | in the block list |
|---|---|---|---|
| Tinely girls LATAM mobile (12502230) | 592 | 580 | 579 |
| Tinely girls CIS mobile (12502232) | 257 | 243 | 243 |

So 98% and 95% of the placements that had ever carried traffic were closed within hours. The list only grows, so
the later rise of the cost to 30% of the payout did not reopen them, and the volume fell from about 186 clicks an
hour on 11.10 to 10-50 on 12.10.

13.10: the six exclusion lists (839 placements: 579 + 243 + 9 + 4 + 2 + 2) were removed with v2
`DELETE .../campaigns/{id}/widgets/filters` and read back (filter `off`, domains, IPs and limits unchanged). With
the old code the guard put back exactly the 64 and 25 placements over the 30% thresholds ($0.288 and $0.12)
within 8 minutes, so the new code was deployed first (`deploy_guard_inferno.sh`, the unit carries
`MGID_GUARD_SINCE`; the dry run on the box found 0 placements to block), and then the 64 + 25 were removed. The
whitelists 12510729 and 12510730 were not touched. **When the conversion cost in the settings changes again, move
`MGID_GUARD_SINCE` to that day**, or the old spend is judged by the new threshold and the same thing repeats.

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
