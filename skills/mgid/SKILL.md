---
name: mgid
description: >-
  Наши закупки на MGID, два аккаунта владельца. Основной (v1 goodhits 816929 / v2 ads 939031) MGID заблокировал 14.10 (API 401);
  рабочий второй (v1 816921 / v2 939023, токен MGID_816921_TOKEN, MGID_ACCOUNT=second). Там CPA tune (targetCpa, «Target CPA»),
  тест лидгена LendingTree Mortgage Refinance CPL (1537) через RollerAds, восемь нутра-копий, цели и постбеки a.mgid.com, и службы на
  Inferno: стоп-лосс, окно оффера, лесенка ставок. Используй ВСЕГДА, когда задача касается MGID: создать или настроить кампанию,
  включить CPA tune, завести цель конверсии и постбек, UTM с click id, тизеры и причины модерации, вкладку Sources (домены) и
  фильтры площадок, лимит стоп-лосса, отчёты и часовые пояса; при номерах 816921, 939023, 816929, 939031, кампаний 12468751,
  12468752, 12520626, 12520627, 12520656–12520663, 12502227–12502232; и при дейтинге Tinely (PL, LATAM, CIS) на cpamatica.
  Нутра-партнёрки (Dr.Cash, Aray, AdCombo, ClickHub) и входы в них — скил nutra-partners. Общая справка по API Mgid/Adskeeper — в
  пользовательском скилле mgidadskeeper.
---

# MGID: два аккаунта, CPA tune, службы на Inferno

Обновлено 23.10.2026. Первая версия скила (30.09) описывала дейтинг на 816929 / 939031 и называла тот аккаунт «вторым»; с тех пор он заблокирован,
рабочим стал старый аккаунт 816921. **Здесь они называются «основной» (816929 / 939031, заблокирован) и «второй» (816921 / 939023, работает).**
Секретов в файле нет: токены в ключнике (скил `secrets`), здесь только сервис и поле.

## 1. Два аккаунта

| | основной | второй (рабочий) |
|---|---|---|
| v1 клиент (`goodhits/clients/…`) | 816929 | 816921 |
| v2 аккаунт (`/v2/ads/account/…`) | 939031 | **939023** (id в v1 и v2 разные; 17.10 первый заход в v2 дал `Invalid token`, а с 939023 со страницы «API» тот же токен заработал) |
| токен, сервис `mgid` | `MGID_816929_TOKEN` = `MGID_939031_TOKEN` | `MGID_816921_TOKEN` |
| состояние | **заблокирован 14.10** | работает с 17.10 |
| бакеты `day` / `hour` отчётов | UTC+3 | **Europe/Tirane**: UTC+2 до 25.10.2026, потом UTC+1 |
| цели конверсии | `lead` 1274200 (дейтинг), `Geozo block click` 1280981 | `lead` 1272844, `geozoclick` 1281145, `rr1537lead` 1281221, `aray_lead` 1278025, `aray_buy` 1278024 |

**Основной.** v1 отвечает `401 «Your account is blocked due to suspicious activity. Please contact your account manager…»`, v2 —
`401 AUTHENTICATION_FAILED «Identity is under godmodeBlock»`. Последний рабочий вызов 14.10 около 08:55 UTC, показы остановились около 09:35 UTC.
Накануне, 13.10 около 18:30 МСК, модераторы сняли все работавшие тизеры (43 дейтинга; MindHue отклонён раньше, ~15:15); к концу того дня из 240 тизеров аккаунта 83 были
заблокированы модератором, 157 отклонены, активных ни одного. Причину MGID не назвала. Версия владельца: взрослый контент попал на мейнстрим-офферы
(не доказано). **Не обходить:** новый аккаунт или домен «чтобы не связали» — это обход блокировки, MGID связывает аккаунты по людям, платежам, IP и контенту.
Письмо менеджеру — `mgid/MGID_SUPPORT_DRAFT.md` в репозитории tedtuhliy/mgid-agent, не отправлено.

**Второй.** Владелец сказал, что менеджер аккаунта разрешил запуск с него (формулировки я не видел, стоит попросить). v2-id 939023 и токен взяты со страницы кабинета «API»
(17.10). Токен был прислан в чат, значит раскрыт: перевыпустить в кабинете и заменить запись в ключнике, **но кнопку «Generate new token» без владельца не нажимать:
она отзывает текущий токен, и службы на Inferno встанут.** Баланс 23.10 11:56 UTC: $53.37.

## 2. Доступ и клиент

- v1: `https://api.mgid.com/v1/goodhits/clients/{CID1}/…` (кампании, тизеры, UTM, отчёты), в записях только **form-тело** (JSON отвечает 200 и ничего не меняет:
  каждую запись читать обратно). v2: `https://api.mgid.com/v2/ads/account/{CID2}/…` (JSON: кампании, цели, фильтры площадок, отчёты).
- Cloudflare отвечает на питоновский User-Agent ошибкой 1010: нужен браузерный UA (клиенты ниже его ставят).
- Деньги: дневной лимит в v2 POST — доллары, в чтении v1 и v2 — ×100 (2000 = $20). Минимальный дневной бюджет $20.
- Клиент репозитория tedtuhliy/mgid-agent: `mgid/mgid_api.py` (только stdlib, работает и в сессии, и на сервере; `call`, `v1`, `v2_campaigns`, `pause`, `report`,
  `widgets_filter`, `campaign`). **`MGID_ACCOUNT=second` переключает аккаунт, токен и id во всех скриптах папки; без переменной работает основной.**

```bash
VAULT=$(ls /root/.claude/skills/synced/*/secrets/vault.mjs | head -1)       # в доках: ~/.claude/skills/secrets/vault.mjs, в этом контейнере его нет
node "$VAULT" exec mgid -- env MGID_ACCOUNT=second python3 mgid/sources_report.py 12468751,12468752 2026-10-21 2026-10-22
```
Ключник должен быть свежим (локальный файл контейнера может быть старым; свежий — git-командой из скила `secrets`).

**Ловушки API.**
- `v2 statistics/reports`: диапазон `dateRange` и бакеты читаются в зоне аккаунта и отдаются **целыми сутками**, которых диапазон коснулся (запрос за 30.09 приносил весь
  01.10). Страница не больше 1000 строк, полная страница обрезается молча: `mgid_api.report()` листает `offset`. На втором аккаунте бакет `hour` = час Тираны:
  час UTC = бакет − 2 (после 25.10 − 1). Я один раз прочитал их как МСК и промахнулся на час.
- v2-список кампаний отвечает 400, если в `filters[fields][]` просить `id` (он приходит всегда). Список v1 тизеров считает `start` с нуля (`start=1` теряет первый).
- Жизненные цифры `campaigns-stat` (`dateInterval=all`) отстают: стоп-лосс перелетает лимит на сумму, которую кампания тратит между двумя взглядами (до ~$1).
- Запись `conversionTracking` через v2 какое-то время читается как null. v1 `GET goodhits/campaigns/{id}/conversions` читает цель только у кампаний с ручной ставкой, у targetCpa
  отвечает «Please use the Ads dashboard to set up tracking»: там только v2.
- Пауза: `mgid_api.pause(cid, on=True/False)` ставит v1-флаг `whetherToBlockByClient` (1/0) и читает статус обратно. v2 `PATCH …/status` в первые секунды после
  создания отвечает 403. Запуск снимает только НАШУ паузу (`clientManuallyPaused`); чужую (`outOfClientFunds`, `managerPaused`) служба окна не трогает.
- 🔴 **Пополнение баланса запускает кампании, которые сеть остановила за нехватку денег** (`outOfClientFunds`, v2 статус `active/unfulfilled`). Первая версия этого скила
  утверждала обратное, это неверно: после пополнения на $100 10.10 «Tinely girls LATAM mobile» потратила $80 примерно за сутки (5300 кликов по 1.5¢ при лимите $2000 в сутки) и
  унесла баланс с $99 до $14, пока её не остановили. **Перед пополнением ставить нашу паузу на всё, что не должно крутиться, или снижать лимиты.**
- MGID создаёт кампанию **активной**: сразу паузить.
- Единицы лимита: перезапуск 30.09 склонировал `2000.0` из чтения, и шесть «girls»-кампаний получили $2000 в сутки вместо $20. Читать лимит обратно через v1 и считать ×100.

## 3. CPA tune (стратегия `targetCpa`): как настроить

В кабинете владельца это поле «Target CPA» (его скриншот 20.10); владелец называет это «cpa tune».

**Условия.**
- Только тип кампании **`product`**. У `content` (старые A docs 12467638 и C calc 12467640) ответ 422 `BIDDING_STRATEGY_CAMPAIGN_TYPES_ERROR`, тип не меняется: нужна новая кампания.
  Лимит на домен: в `product`-кампании не больше пяти тизеров на один домен ссылки (шестой — `LS_CAB_GOODS_TEASER_ALLOWED_DOMAIN_LIMIT`).
- Нужна цель конверсии типа postback и этап `buyStage` в `conversionTracking`. Пока у кампании нет конверсий, единственный рычаг — сам target.
- Модерация тизера начинается в момент создания, даже в кампании на паузе.

**Шаги (все проверены на втором аккаунте).**

1. **Цель.** `POST /v2/ads/account/939023/targets` с телом `{"type":"postback","eventName":"lead","name":"…","description":"…","categoryId":9}`. Читать: `GET …/targets`.
   Второй аккаунт принял категории 9 (`rr1537lead`) и 18 (`aray_lead`, `aray_buy`), основной принимал только 1 и 9 (2–5 отвечали «Selected category is not available»).
   `eventName` потом стоит в `e=` постбека. Готовые цели см. таблицу выше.
2. **Кампания.** `POST /v2/ads/account/939023/campaigns`:
   ```json
   {"name": "…", "showName": "…", "type": "product", "isAutoLaunchAdsAfterApproval": false,
    "bidding": {"strategy": "targetCpa", "price": 0.05}, "sourcesOptimization": false,
    "limits": {"limitType": "budget", "dailyLimit": 20.0, "splitDailyLimitEvenly": false},
    "conversionTracking": {"type": "sensors", "decisionStage": null, "interestStage": null,
       "buyStage": {"targetId": 1281221, "deduplicateConversions": true, "conversionValue": 0.05}},
    "geoTargeting": {"countries": ["US"], "regions": {"mode": "include", "value": []}},
    "languageTargeting": {"mode": "include", "value": [<id языка>]}}
   ```
   Ответ — `id`. Сразу `pause(id)`. `price` — целевая цена конверсии (ставка), `conversionValue` — ценность лида в отчётах (у 1537 0.05, у нутры — выплата), это разные числа.
   ОС, браузеры, устройства копировать с живой кампании (поля `operatingSystemTargeting`, `browserTargeting`, `languageTargeting` читаются из v2). Читать обратно: `type`,
   `bidding.strategy`, `conversionTracking.buyStage.targetId`, `status` (paused), `isAutoLaunchAdsAfterApproval` (**MGID однажды сбросил наш флаг в false**: проверять).
3. **Click id в ссылку без перемодерации — UTM кампании.** `PUT goodhits/campaigns/{id}/utmtracking/` (форма): `utm_source`, `utm_medium`, `utm_campaign` пустые,
   `utm_custom=aff_click_id={click_id}`; читается как `aff_click_id=${CLICK_ID}`. MGID дописывает его к ссылке каждого тизера в момент клика, в том числе у тизеров на модерации.
   Чтение — поле кампании `trackingOptions` (`GET …/utmtracking/` отвечает 501). Для cpamatica-варианта см. `scripts/mgid_utm.py`.
4. **Тизеры.** `POST goodhits/clients/816921/teasers` (форма): `campaignId`, `url`, `title`, `imageLink`, `priceOfClick` (центы; 1.5 — настоящую цену клика выбирает targetCpa),
   `whetherShowGoodPrice=0`, по желанию `advertText`; категория, картинка (MGID перехостит её на imghosts.com). Макросы ссылки: `{click_id}`, `{widget_id}`, `{teaser_id}`, `{campaign_id}`.
   Подробнее о правилах тизеров — §5.
5. **Постбек.** Партнёрка или трекер вызывает `https://a.mgid.com/postback?c={click id}&e={eventName цели}&r={выплата в $}`. Тестовые постбеки с выдуманными click id в MGID не слать
   (13–14.10 их было несколько, это одна из версий блокировки основного аккаунта, не доказанная). Проверка — первый настоящий лид: у клика в трекере `earnings` > 0 и `aff_click_id` из
   32 hex-символов, потом цель в отчёте MGID.
6. **Лимиты.** Дневной лимит MGID плюс внешний стоп-лосс (§6): MGID сам не останавливает перелёт по сумме.
7. **Запуск** — снять нашу паузу (`pause(id, on=False)`); расписание — окно оффера (§6).

**Повышение target.** v2 `PATCH /v2/ads/account/939023/campaigns/{id}` телом `{"bidding":{"strategy":"targetCpa","price":X}}`, ответ 204, читать обратно. `mgid/cpa_ladder.py` делает это по часам (§6).

**Что наблюдали (тест LendingTree Mortgage Refinance CPL (1537), США, 21–23.10; это один тест, не закон).**

| target | что получали |
|---|---|
| $0.05 | 5–7 показов в час, ни одного клика |
| $0.50–3.00 | 5–160 показов в час, кликов нет |
| $3.50–5.00 | ~10–20 кликов в час (вечер США лучший: 18–20 ч по Нью-Йорку) |

Цена клика при любом target 7–12 центов (её определяет аукцион, а не target). Моя гипотеза, не документация MGID: ставка за клик ≈ target × предсказанная доля конверсий, поэтому при доле
~0.04 % 5 центов — доли цента, ниже минимальной цены клика США (~3 цента). Итог теста: 185 кликов, $20.7, **0 лидов**; при 12 центах за клик и 0.04 % лид стоит ~$300 при среднем
платеже ~$13. Тест показывает «трубы» (клики доходят, click id ездит), а не CPA.

## 4. Кампании второго аккаунта (23.10)

Все 25 кампаний аккаунта на паузе в 11:56 UTC (старт — окно оффера в 12:00 UTC).

| кампания | id | что делает | состояние |
|---|---|---|---|
| US 1537 equity, E compare v2 | 12468751 | США, лидген LendingTree Mortgage Refinance CPL (1537), CPA tune $5.00, цель `rr1537lead`, 8 одобренных тизеров | на паузе нашей; со сброса $10.30 из $15; жизнь $124.40 |
| US 1537 equity, F compare2 v2 | 12468752 | то же, 5 одобренных тизеров | со сброса $10.44; жизнь $118.56 |
| US 1537 equity, A docs, CPA tune | 12520626 | то же, product, CPA tune $0.50 | 4 тизера, все отклонены «Content mismatch», показов нет |
| US 1537 equity, C calc, CPA tune | 12520627 | то же | 1 тизер, отклонён; 8 остальных не добавлены |
| восемь нутра-копий (AL, IT, BA) | 12520656–12520663 | CPA tune $0.05, цель `lead` 1272844 | на паузе, тизеры отклонены (подробно в скилле nutra-partners) |
| девять офферов Aray (UY, PE, EC, PY, CO) | 12525146–12525154 | CPA tune $0.05, цель `aray_lead` 1278025, ценность лида = выплата × апрув, $20 в сутки (26.10) | на паузе; 5 тизеров на модерации (Elastica UY, Vitaflex PE, Duston Gel UY, Sustarox EC, Oxys PY), у четырёх без тизеров нет честного ленда (Audix PE, Glowy Care PE, Glowy Care Serum CO, Sustarox PY); скрипт `mgid/aray_campaigns.py` |
| активные кампании не нашего чата | 12523155–12523169 и др. (45 штук, «Affstar LP», цель 1281420) | не трогать, владелец 26.10: «активные не трогай» | девять активных, остальные на паузе; стоп-лосс $15 их тоже касается |

**Лидген 1537.** Оффер RollerAds «LendingTree Mortgage Refinance CPL (1537)»: США, выплата плавает $0.50–$45 по фильтрам (T1 $45 … T6 $0.50), оплачивается пн–пт 08:00–21:00 по
Нью-Йорку (RollerAds: «EST»). Ссылка тизера: `https://bbcwebhosting.com/or/baap/aopwqk?source_id={widget_id}_{teaser_id}&aff_click_id={click_id}` (трекер-домен возвращает
RollerAds `GET /api/offers/1537/tracking-link`; он оставляет `source_id`, `aff_click_id`, `subid1`, `subid2`, остальное режет). Постбек RollerAds 1373 `mgid-1537-lead`:
`https://a.mgid.com/postback?c={affClickId}&e=rr1537lead&r={trx}`. В первый вечер (21.10) 16 из 19 кликов MGID (84 %) дошли до трекера; у оффера 4 лида за всю жизнь, все до теста, от MGID ни одного;
**цепочка RollerAds → MGID не проверена**. Открытый вопрос: окно хранится в America/New_York (EDT, UTC−4 до 1 ноября), а оффер говорит «EST» (UTC−5): если EST фиксированный, час 12:00–13:00 UTC
(с него 16 % трат: 3255 показов, 32 клика, $3.28) вне окна; вопрос за владельцем (старт в 13:00 UTC до 1 ноября безопасен при обоих прочтениях).

## 5. Тизеры, модерация, площадки

**Тизеры.**
- Нет редактирования: POST на существующий id создаёт **дубль**; ссылку и картинку не поменять. Заменить = создать новый, потом удалить старый (удалённый не восстановить). Журнал созданных:
  `mgid/data/nutra-direct-created.json`, скрипты `mgid/rr1537_teasers.py`, `mgid/nutra_direct.py`.
- Лимит добавления `LS_TEASER_ADD_LIMIT_ERROR` ≈10 в сутки на кампанию; удаление его не возвращает, ретраи могут считаться: не долбить.
- Статусы v1: `onModeration`, `rejected`, `blocked`, `campaignBlocked` (одобрен в кампании на паузе), `active`. Причина отказа — `status.reason_if_drop_karantin[0]`; в тексте ссылка на
  скриншот модератора `https://i.gyazo.com/<id>.png`.
- Что видели: «Malware has been detected» (на скриншоте красная страница Chrome «Dangerous site»), «Footnotes / User awareness / Spoilers» (нутра, Италия),
  «Content mismatch» (копии 1537; почти такой же заголовок прошёл на E v2: вердикт по тизеру, не правило), «Landing page issue», блок системой без причины.
- Тизеры с выдуманными отзывами, исследованиями и обещаниями результата не запускаем (решение 23.10, подробности в скилле nutra-partners).

**Площадки (вкладка Sources).**
- Отчёт: `MGID_ACCOUNT=second python3 mgid/sources_report.py <id,id> <от> <до> [--top 50]` (v1 `goodhits/campaigns/{id}/quality-analysis-sources/?dateInterval=interval&startDate=&endDate=`,
  `sourceName` — домен, в списке только площадки с показами). Тот же список в v2 отчёте с измерением `source`; какой `widgetId` какому домену соответствует — измерения
  `widgetId` × `source`. Флаг в скрипте «CTR ≥ 5 % при ≥ 2 кликах» — только подсказка: честные новостные сайты 0.3–1.5 %.
- Фильтры: v2 `…/campaigns/{id}/sources/filters` (GET постранично, `limit=100&offset=`; `PUT` заменяет весь список; `PATCH` с `{"filterType":"except","data":[{"sourceId":N}]}` добавляет
  (upsert); `PATCH …/sources/filters/batch-delete` с `{"data":[{"sourceId":N}]}` снимает). У E v2 и F v2 `sourcesOptimization` включена и уже был список исключений из 155 площадок.
  Перед правкой сохранить список, после — прочитать обратно. Старый механизм по виджетам: v1 `widgetsFilterUid` (`include, except, uid…` добавляет, `exclude` затирает весь список) и v2
  `…/widgets/filters` (`DELETE` снимает фильтр целиком, `PATCH …/batch-delete` снимает один виджет).
- **Не блокировать площадки по CTR без просьбы владельца.** 23.10 я заблокировал шесть доменов (vitabloomy.shop, playexpedition.com, nullsite.info, thrivevia.shop, claimjustice.site, gamecheckmate.com;
  48 из 126 кликов, 30 % трат), владелец спросил «Разве они плохие и много потратили?»: вредность не доказана (ни у одной площадки нет ни одного лида), блок снят. Что видно в данных:
  vitabloomy.shop присылает каждый клик на трекер дважды (виджеты 75930494 и 75930495), у nullsite.info клики без показов.

## 6. Службы на Inferno (второй аккаунт)

Доступ: `tailscale ssh root@100.121.239.113` (ключник `inferno-vps`: `INFERNO_HOST`, `INFERNO_TS_IP`, `INFERNO_USER`, `INFERNO_SSH_KEY`; вход в tailnet — `TS_AUTHKEY`, см. скил `inferno`).
Токен для служб лежит в `/etc/mgid-second.env` (0600: `MGID_ACCOUNT=second`, `MGID_816921_TOKEN`).

| служба (systemd timer) | что делает | код, состояние |
|---|---|---|
| `mgid-spend-stop-second` (каждые 2 мин) | **стоп-лосс:** ставит на паузу активную кампанию, чей расход с момента сброса ≥ `MGID_SPEND_LIMIT` (сейчас **$15**, один лимит на каждую кампанию аккаунта) | `/opt/mgid-spend-stop-second/`; база `/var/lib/mgid-spend-stop-second/baseline.json` (E v2 114.10, F v2 108.12); журнал `actions.log` там же |
| `mgid-offer-window-second` (каждые 5 мин) | **окно оффера:** внутри пн–пт 08:00–21:00 America/New_York (12:00–01:00 UTC летом) запускает нашу паузу, вне окна паузит; не запускает кампанию, которую держит стоп-лосс; чужую паузу не трогает | `/opt/mgid-offer-window-second/`; список кампаний `MGID_WINDOW_CAMPS` в юните (E v2, F v2, A docs, C calc); **лимит в юните должен быть равен лимиту стоп-лосса** |
| `mgid-cpa-ladder-second` (каждый час в :07) | **лесенка ставок:** кампании, у которой меньше `GOAL`=10 кликов в час, поднимает target на `STEP`=$0.50, не выше `MAX`=$5.00; не опускает; судит только то, что может крутиться (активна, есть одобренный тизер, окно открыто) | `/opt/mgid-cpa-ladder-second/`; состояние `/var/lib/mgid-cpa-ladder-second/state.json`; сейчас E v2 и F v2 на потолке $5.00 |

**Как менять лимит стоп-лосса.** Правка **на месте**: `sed` строки `Environment=MGID_SPEND_LIMIT=` в юнитах `mgid-spend-stop-second.service` и `mgid-offer-window-second.service` (одно и то же число),
`systemctl daemon-reload`, бэкапы `/root/*.service.bak-ГГГГММДД`. **Не запускать `deploy_spend_stop_second_inferno.sh` повторно: он сбрасывает baseline.** Новое «ещё $5» = старый остаток
плюс $5, потому что считается от сброса 21.10 09:52 UTC. Чтобы дать остановленной кампании новый лимит, сдвинуть её запись в baseline на текущий расход (`spend_stop.py --reset` делает это для всех кампаний сразу).
Лимит ставит владелец («Добавь ещё по 5 баксов»): $3 → $5 (21.10) → $10 (22.10) → $15 (23.10).

Развёртывание: `TAILSCALE="<tailscale> --socket=<сокет>" CLAUDE_VAULT_FILE=<ключник> bash mgid/deploy_{spend_stop_second,offer_window,cpa_ladder}_inferno.sh` (тесты, выкладка, dry run, swap,
юниты). Откат: `systemctl disable --now <служба>.timer`. Тесты: `cd mgid && MGID_ACCOUNT=second python3 -m unittest test_sources_report test_cpa_ladder test_offer_window test_spend_stop` (38; без `-I`).

Старые cron-ы `lidgen_window.py` (каждый час) и `mgid_daypart.sh` (каждые 30 мин) на Inferno **выключены 21.10**: они каждый час снова запускали кампании 1537 (бэкап
`/root/crontab.backup-20261021-before-lidgen-off`). `mgid-spend-stop` основного аккаунта не тронут и тихо падает с 401 (про `mgid-guard` того же аккаунта ожидаю то же, не проверял).

## 7. Границы (что нельзя)

- Не обходить блокировку основного аккаунта; не открывать «чистый» аккаунт или домен ради этого.
- Не слать в MGID постбеки с выдуманными click id.
- Не блокировать площадки по CTR без просьбы; не повышать лимит стоп-лосса и потолок лесенки сам, их ставит владелец.
- Не нажимать «Generate new token» без владельца.
- Тизер = модерация сразу и отклонение остаётся на аккаунте: не добавлять тизеры «на пробу», по одному на кампанию в первый раунд.
- Не запускать лендинги с выдуманными отзывами и исследованиями.
- Оффер называем по имени, номер в скобках; кампанию — с тем, что она делает.

## 8. Архив: основной аккаунт, дейтинг Tinely (30.09–14.10; заблокирован, справка по механике)

**Кампании** (все на cpamatica, ссылка `https://go.cm-trk6.com/aff_c?offer_id=<оффер>&aff_id=5084&aff_sub5=mgid&aff_sub={campaign_id}&aff_sub3={widget_id}`):

| id | гео / устройство | оффер cpamatica | ценность лида | первый запуск (на паузе) |
|---|---|---|---|---|
| 12502227 / 12502228 | PL desktop / mobile | Tinely PL (9962) | $2.00 | 12501886 / 12501887 |
| 12502229 / 12502230 | LATAM desktop / mobile | Tinely LATAM (8326) | $0.62 | 12501888 / 12501889 |
| 12502231 / 12502232 | CIS desktop / mobile | Tinely CIS (8394) | $0.44 | 12501890 / 12501891 |

**Перезапуск 30.09 ~22:30 UTC:** на тизерах первого запуска были мужчины (владелец: «убери мужиков вообще … блеклисты неактуальны»). До паузы работала только CIS mobile 12501891:
$10.85, 4 лида на $2.24 (0.21x). `scripts/mgid_relaunch.py [--apply] [старый id …]` создаёт новые: v2 `POST /campaigns` клоном живых настроек (тип product, `manualBidding` 0.045, лимит 2000, гео, ОС, язык,
цель 1274200 **сразу в теле создания**), UTM как в `scripts/mgid_utm.py`, 3 тизера на кампанию (фото 1200×800 только с женщинами, лицо в кадре, категория 108, 1.5¢ за клик; заголовки по гео:
PL «Poznaj singielki w {City}», LATAM «Conoce solteras en {City}», CIS «Одинокие девушки в г. {City} — кто онлайн»). Итог — `references/relaunch-3009.json`.

**Язык браузера (01.10).** Таргетинг: v1 `PUT goodhits/campaigns/{id}/targetings/browserslanguage`, форма `targets=include,<id>&enabledFlag=1`; читается v1 GET того же адреса или v2 `languageTargeting`.
Id из v2 `dictionaries/languages`: 39 русский, 20 польский, 2 испанский, 63 казахский, 44 грузинский, 37 азербайджанский, 17 румынский. Грузия ~750 → ~350 и Азербайджан ~380 → ~190 показов в час;
Казахстан и Молдова почти не изменились. Экономика СНГ: Казахстан 361 клик, $5.42, 6 лидов Tinely CIS (8394) по $0.56 (0.62x); Грузия, Азербайджан и Молдова 738 кликов, $11.07, ноль лидов;
безубыток Казахстана — CR 2.7 % при 1.5¢ и 1.8 % при 1.0¢. Обвал показов СНГ 30.09–01.10 в 13–14 UTC (16 000 → 2 400 в час на всех 2 375 площадках) причину не получил.

**Как лид возвращался в MGID (cpamatica).** 1) Цель `lead` 1274200 (buy, с дедупом) в каждой кампании; у существующей ставится v2 `PATCH` с `conversionTracking`. 2) UTM кампании:
`utm_source=mgid utm_medium=native utm_campaign={campaign_id} utm_custom=click_id={click_id}&source=mgid_{campaign_id}_{widget_id}`. 3) Глобальный постбек cpamatica (только одобренные лиды, все офферы)
вызывает `https://flyblog.online/exocpa/postback?cid={click_id}&src={source}&payout={payout}&cur={currency}&tx={transaction_id}&st={status}`: макросов `aff_sub` в нём нет, поэтому кампания и площадка едут
внутри `source`. 4) Мидлварь на Inferno (`/var/www/postback-middleware/pb_server.py`, ветка mgidpb; патчи `scripts/mgid_pb_patch.py`, `scripts/mgid_pb_patch2.py`):
`src=mgid_<кампания>_<площадка>` → строка в `mgid_leads` (sqlite `accumulator_exocpa.db`, дедуп по tx) и `https://a.mgid.com/postback?c=<click id>&e=lead&r=<выплата в $>` (3 попытки, `MGIDPB_CONV`);
без click id лид пишется без отправки (`MGIDPB_NOCID`); отклонённый пропускается (`MGIDPB_SKIP`); без source — `mgid_nosrc` и ветка ExoClick как раньше.
**Откат мидлвари:** `cd /var/www/postback-middleware && cp pb_server.py.bak-20260930-mgidpb pb_server.py && systemctl restart pb-middleware.service` (до обоих проходов; `.bak-20260930-mgidpb2` —
после первого). Мидлварь не в git, код живёт на сервере.

**Сторож площадок `mgid-guard`** (Inferno, раз в 5 минут, `scripts/mgid_guard.py`): площадка, потратившая в кампании ≥ $0.30 за всю жизнь без лида, уходит в блок этой кампании. Расход по площадкам —
v1 `goodhits/campaigns/{id}/quality-analysis/?campaignId={id}&dateInterval=all`; лид засчитывается по таблице мидлвари `mgid_leads` или по конверсии MGID (v2 отчёт `conversionsBuy`,
`dimensions[]=campaignId,widgetId`); судится каждая кампания отдельно; ключ площадки обрезается до ведущих цифр; **HOLD** (лид без source позже последнего MGID-лида с площадкой) —
ничего не режет, пишет `MGIDG_HOLD` (развёрнутый 30.09 сторож с 01.10 19:30 сидел в HOLD и ничего не блокировал: проверка «лид без source» считала лиды смартлинка Exclusive Adult
Smartlink WW (16588), то есть чужих закупок с тем же глобальным постбеком; теперь смотрит только офферы из `MGID_OFFERS`); блок только добавляет (v1 `PATCH` `widgetsFilterUid=include, except, uid…`, после записи список читается). Несуществующий uid: HTTP 200 с
`WIDGETS_WITH_THESE_UIDS_DO_NOT_EXIST` (настоящие из того же вызова добавляются; сторож запоминает такие uid). Снять площадку через v1 нельзя (`exclude, off` при `filterType: except` даёт
`ERROR_CANT_EXCLUDE_DIFFERENT_FILTER_TYPE`, пустой `exclude, except` — `WIDGETS_UIDS_CANNOT_BE_EMPTY`), работает v2 (§5). Файлы: `/opt/mgid-guard/`, токен `/etc/mgid-guard.env`, состояние `/var/lib/mgid-guard/{state.json,actions.log}`;
`scripts/deploy_guard_inferno.sh --env`, `mgid-guard-status`, порог — `Environment=MGID_GUARD_THRESH=` в юните.

**Учёт.** В Tedbolt: `mirelia_api/cpamall.py` (`MGID_CAMPS`, метка `aff_sub5=mgid` в `SRC_BOOK`, `mgid_spend()` читает оба аккаунта токенами `MGID_816921_TOKEN` и `MGID_816929_TOKEN`);
выручка — из cpamatica по `aff_sub`=id кампании и `aff_sub3`=площадка. `buying/revenue` самого MGID — наша цель постбека, не деньги. Скрипты `mirelia_api/mgidblock.py`, `mgidguard.py` в Tedbolt
относятся к 816921 до 30.09 и не равны рабочим скриптам репозитория mgid-agent.

**Контент-арбитраж Geozo (13–17.10, справка; подробности в README репозитория, раздел «Content-arbitrage test»).** Цепочка: тизер MGID (Казахстан, русский, мобайл, targetCpa $0.01) →
`https://arcadiablog.com/dom/<статья>.html?click_id={click_id}&source=mgid_{campaign_id}_{widget_id}` (статья 40+ с размеченными блоками Geozo) → настоящий клик по рекламе в слоте →
`GET /dom/lead?c=<click_id>` → nginx-релей на Inferno → `https://a.mgid.com/postback?c=<click_id>&e=geozoclick&r=0.01`. Сайт `arcadiablog.com` подтверждён в Geozo под TikTok-трафик (45+, RO/KZ), MGID
для него другой источник: риск. На основном аккаунте цель `Geozo block click` 1280981, кампании на 14 гео и KZ-блог (12512609, 12512618, 12512632…); они недоступны с 14.10. На втором аккаунте
цель `geozoclick` 1281145 и кампания 12516093 «Arcadia KZ blog content mobile CPA 0.01» (на паузе; тот же релей шлёт `e=geozoclick`). Скрипты: `geozo_geos.py` (кампании по гео, лесенка ставок,
`--status`), `geozo_campaign.py`, `geozo_report.py`, `geozo_site/` (сайт). Кампании `product`, цель без дедупликации (каждый учтённый клик — конверсия).

## 9. Файлы

- Репозиторий tedtuhliy/mgid-agent, папка `mgid/` (ветка с этой работой — `claude/optimistic-feynman-at3shp`): `mgid_api.py`, `spend_stop.py`, `offer_window.py`, `cpa_ladder.py`, `sources_report.py`,
  `nutra_direct.py`, `rr1537_teasers.py`, `mgid_geo_copies.py`, `geozo_geos.py`, `deploy_*_inferno.sh`, `README.md` (журнал, новое сверху), `data/`.
- Tedbolt `.claude/skills/mgid/`: этот файл, `scripts/` (дейтинг основного аккаунта: `mgid_api.py`, `mgid_guard.py`, `mgid_pb_patch*.py`, `mgid_relaunch.py`, `mgid_utm.py`, `deploy_guard_inferno.sh`), `references/relaunch-3009.json`.
