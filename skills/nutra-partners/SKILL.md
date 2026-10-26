---
name: nutra-partners
description: >-
  Нутра-партнёрки для связок на MGID — Dr.Cash (affiliate.dr.cash), Aray (aray.com), AdCombo, ClickHub: где лежат доступы
  (в ключнике, только имена полей, значений в файле нет), как в них войти (облачный браузер Vision на vision-box через tailnet,
  Cloudflare), как читать офферы, выплаты и лендинги через их API, какие метки класть в ссылку, как настроить CPA tune
  (targetCpa) под нутра-кампанию на MGID, как проверить ленд и домен до модерации и как читать скриншоты модераторов. Используй
  ВСЕГДА, когда задача касается нутра-партнёрок или офферов на здоровье, суставы, давление, похудение, варикоз; слов «aray»,
  «адкомбо», «adcombo», «dr cash», «drcash», «клик хаб», «clickhub»; новых ссылок и лендингов для нутра-тизеров; отклонённых
  нутра-связок (Албания, Италия, Босния: Osteflex, Hypertea, Varcosin, Cortitron, Cardiotensive, ToxicOFF, Matcha Slim,
  Nautubone); облачного браузера Vision на coolify. Сам MGID (API, CPA tune, службы) — в скилле mgid, проверка цепочки связки —
  в nutra-bundle-check.
---

# Нутра-партнёрки для MGID: доступы, входы, CPA tune

Составлено 23.10.2026 по тому, что реально делалось в сессии (22–23.10). Всё, что не проверено, помечено «не проверено».
**Проверено 26.10 боевым прогоном:** `ts_tun_up.sh` (с `TS_DIR=/tmp/claude-0/ts`, чтобы взять уже скачанную сборку Tailscale), `vision.sh` (list, start, stop),
`aray_login.mjs`, `aray_offers.mjs dump`, `aray_cards.mjs`, `aray_landers.mjs` отработали; сессия Aray **сохраняется в профиле Vision между остановкой и запуском** (повторный вход не понадобился). Не прогонялись
заново: `dr_*.mjs` и `aray_offers.mjs scan`.
**Паролей, токенов и ключей в файле нет, так задумано:** они лежат в ключнике (скил `secrets`), здесь только сервис и поле.

## 0. Коротко

| партнёрка | доступ | вход | данные | ключник |
|---|---|---|---|---|
| **Dr.Cash** | есть (аккаунт infodreamer66, менеджер Kirill, баланс $1136.25 на 23.10) | `https://dr.cash/sign-in/` → кабинет `https://affiliate.dr.cash` | API `https://drcash.io/v1/*`, 3704 оффера | `drcash`: `DRCASH_EMAIL`, `DRCASH_PASSWORD` |
| **Aray** | есть | `https://aray.com/login` (Cloudflare: только настоящий Chrome) | `/api/offers` того же сайта, 290 офферов | `aray`: `ARAY_EMAIL`, `ARAY_PASSWORD`, `ARAY_API_KEY` |
| **AdCombo** | **нет** | `adcombo.com` за Cloudflare, 403 | — | в ключнике никогда не было |
| **ClickHub** | **нет** | `clickhub.in` | — | скил `clickhub` есть, `CLICKHUB_LOGIN`/`CLICKHUB_PASSWORD` в ключнике нет |

Остальные сети в ключнике нутру не продают: Zeydoo (опросы, финансы), Traforce (Affise «Victoriya», только дейтинг), LuckyFeed
(монетизация статей, не оффер-сеть), cpamatica / ApproachX / iMonetizeIt (дейтинг).

🔴 **Заметка в ключнике у `drcash` устарела:** там сказано «кабинет partners.dr.cash, хост режется сетевой политикой окружения Claude (CONNECT 502)». Такого хоста
нет вообще (`ERR_NAME_NOT_RESOLVED` даже в браузере во Франкфурте, прокси песочницы просто отвечал 502 на несуществующее имя), настоящий вход — `dr.cash/sign-in`,
кабинет — `affiliate.dr.cash`. Моё «режется политикой» от 22.10 было неверным, владельцу об этом сказано. Саму заметку в ключнике я не менял (ключник живёт в репозитории Tedbolt,
в этой сессии доступа туда нет): стоит поправить текст заметки при случае.

## 1. Правила

- Значения секретов не печатать и не класть в файлы, чат, git, командную строку. Только `vault.mjs exec <сервис> -- …`, токены в
  заголовках — через stdin (`curl -K -`). Значение, пришедшее в чат, считается раскрытым: сказать один раз, предложить перевыпуск,
  сохранить в ключник и запушить его (скил `secrets`).
- Создавать потоки в партнёрке, отправлять тизеры на модерацию и запускать кампании — только по просьбе владельца. Тизер уходит на
  модерацию в момент создания, даже в кампании на паузе, и каждое отклонение остаётся на аккаунте (на 23.10 отклонено 40+).
- Владелец читает с телефона и по-русски; оффер называем по имени, номер в скобках: «Cortitron IT (32535)», кампанию — с тем, что
  она делает: «IT, мобайл native, Cortitron, CPA tune 5 центов».
- **Решение 23.10 (моё, владельцу сообщено): не запускать тизеры на лендах с выдуманными отзывами с именами, выдуманными
  исследованиями и обещаниями результата** (например «perdere 25 chili in 28 giorni»), что бы ни решила модерация: одобрение не
  делает страницу честной. Ленды Dr.Cash для Cortitron / Matcha Slim / Nautubone такие (12 страниц прочитаны). Владелец это решение
  не отменял; если отменит, это его слово, а не моё.
- Не обходить блокировку основного аккаунта MGID (816929 / 939031) новыми аккаунтами и доменами «чтобы не связали».
- В MGID не слать тестовые постбеки с выдуманными click id.

## 2. Как попасть внутрь: облачный браузер Vision

Зачем. Из песочницы вход не проходит: headless Chromium не проходит Cloudflare у Aray (`/auth/login` отвечает «Just a moment…»), прокси
песочницы отказывает даже `*.challenges.cloudflare.com`; `nutra.aray.com` сбрасывает соединение. Настоящий Chrome в профиле Vision на
`vision-box` (Coolify, Hostinger 31.97.180.182, внутри tailnet 100.110.129.11) проходит.

Порядок (скрипты в `scripts/`, все секреты внутри `vault.mjs exec`). Путь к ключнику в этом контейнере:
```bash
export VAULT=$(ls /root/.claude/skills/synced/*/secrets/vault.mjs | head -1)   # в доках встречается ~/.claude/skills/secrets/vault.mjs, здесь его нет
```

1. **Ключник свежий.** Локальный файл контейнера может быть старым (снимок 13.10 без `aray` и `drcash`). Свежий берётся одной
   git-командой из скила `secrets` (нужны переменные окружения `CLAUDE_VAULT_PASSPHRASE` и `GITHUB_ALL_REPOS_PAT`); потом либо
   положить его в `~/.claude/secrets/vault.enc.json`, либо `export CLAUDE_VAULT_FILE=<путь>`. Через Google Drive не тянуть (46 КБ base64
   в разговор, двадцать минут).
2. **tailnet с настоящим TUN:** `bash scripts/ts_tun_up.sh` (ключ `tailscale` / `TS_AUTHKEY`, многоразовый до **29.10.2026**; после этой даты
   нужен новый). Userspace-tailscaled для curl/ssh/CDP к адресам tailnet не годится. Узел называется `cc-mgid-arcadia-vb`.
3. **Профиль.** `bash scripts/vision.sh list` — что запущено. Запустить: `bash scripts/vision.sh start <folder> <profile>` → в ответе
   `"port":N`, это CDP-порт, **он меняется при каждом запуске**.
   - наш профиль **geozo3**: папка `4eb2852c-84f8-4068-a6a5-420f68d91720`, профиль `0927ff00-f776-4fd0-9fcf-10ad36e30354`. Соединение
     прямое, выход в интернет = IP бокса (Hostinger, Франкфурт, датацентр).
   - профиль **GEOZO TEDDY** (`b19965a8-23b4-468a-aaf9-7dfc630a2ca6`, прокси NodeMaven США) отвечает `Proxy error`; причина не
     проверена (пакет NodeMaven пуст с 20.10, но связь с ошибкой не доказана).
   - профиль **TikTok DE3** (папка `b9ad5b65-9127-487c-bcd8-c02d1cab09f0`, профиль `78336bcd-6a8f-4719-9dad-a14d526ebbe4`) — **чужой запущенный
     аккаунт, не трогать.** Останавливать только то, что запустил сам.
4. **CDP:** `export VISION_CDP_PORT=<N>; export OUT_DIR=<папка>`; скрипты подключаются через `playwright-core` из `/opt/node-tools`
   (не `/node-tools`). Первая вкладка профиля уже открыта (`panel.geozo.com`), свои страницы открывать новой вкладкой.
5. **Вход:** `node "$VAULT" exec drcash -- node scripts/dr_login.mjs`, то же для `aray` и `aray_login.mjs`. Сессия
   остаётся в профиле, вкладку не закрывать. Скрипты чтения (`dr_offers.mjs`, `dr_landers.mjs`, `aray_offers.mjs`) секретов не требуют, им нужны
   только `VISION_CDP_PORT` и залогиненная вкладка.
6. **Конец работы:** `bash scripts/vision.sh stop <folder> <profile>` (только свой), `bash scripts/ts_down.sh` (останавливает демона и
   пытается удалить узел из tailnet владельца через `TS_API_TOKEN`), стереть временные файлы. Скрин и дампы остаются в `OUT_DIR`.
   🔴 **На 26.10 `TS_API_TOKEN` в ключнике недействителен** (Tailscale отвечает 401 «API token invalid»), так что узел удалить нельзя: он остаётся в tailnet
   офлайн (`cc-mgid-arcadia-vb`, `cc-mgid-arcadia-vb-1`; повторный вход получает имя с суффиксом `-1`, пока старая запись жива). Первая версия `ts_cleanup.mjs`
   в этом случае молча печатала «none left»; теперь скрипт падает с кодом 2 и говорит, что узел не удалён. Лечится новым API-токеном в ключнике (админка
   Tailscale: Settings → Keys) или ручным удалением в Machines. **Чужие узлы (`cc-aff-kz` и остальные `cc-`, `ccr-`, `claude-`) не трогать.**
   Многоразовый ключ `TS_AUTHKEY` действует до 29.10.2026. `ts_down.sh` при неудачном удалении **оставляет файл состояния** (`$TS_DIR/tun.state`): следующий `ts_tun_up.sh` в этом контейнере входит тем же узлом, а не плодит ещё одну запись.

Что мешало и чем лечится:
- Приложение Vision на боксе блокирует окно «**A new version of Vision is available!**»: нажимать **No**. «Yes» перезапускает приложение
  и роняет профили.
- Запуск профиля кнопкой в GUI не сработал, API (`vision.sh start`) сработал. GUI на боксе: ssh `root@100.110.129.11` (ключ
  `VISION_BOX_SSH_KEY` из `vision-box`, в ключнике хранится **без завершающего перевода строки**, при записи в файл 0600 добавить `\n`),
  дисплей `DISPLAY=:99`, `xdotool`, скриншот `import -window root`.
- Токен локального API (`browser-vision` / `VISION_API_TOKEN`, JWT до 24.08.2027) и пароль Vision были присланы в чат 22.09, то есть раскрыты: при случае перевыпустить.
- Выход с бокса = датацентр Франкфурта. **Реальный посетитель из Италии/США может увидеть другую версию ленда.** Трекер RollerAds (`bbcwebhosting.com`) на адрес
  датацентра отвечает редиректом на `127.0.0.1`; трекеры AdCombo из песочницы отвечали нормально (302, потом ленд 200), но ленд мог отдать «датацентровую» версию.
  Чтобы увидеть то, что видит человек, нужен резидентный прокси целевого гео (у NodeMaven пакет пуст с 20.10, HTTP 402; ISP-пул отвечает 407).

## 3. Dr.Cash

**Вход.** `https://dr.cash/sign-in/` (поля e-mail и пароль, кнопка «Enter Dashboard»; `scripts/dr_login.mjs`), затем SPA
`https://affiliate.dr.cash`. Капчи 23.10 не было. Разделы кабинета: Dashboard, Leads, Campaigns, Statistics, Instruments, Offers, Finance, Blog.

**API.** Публичного ключа нет. Кабинет сам ходит на `https://drcash.io/v1/*` с заголовком `Authorization`, который ставит страница. Метод: в
залогиненной вкладке перехватить заголовок собственного запроса страницы и дальше вызывать `fetch` **внутри страницы** (`scripts/dr_lib.mjs`,
`withDr`). Заголовок нигде не печатается и не сохраняется.

| вызов | что даёт |
|---|---|
| `GET /v1/offer?limit=50&offset=N&sort_by=rank&sort_type=ASC` | список офферов в `payload.items`. `limit` не больше 50, листается только `offset` (`page` и `country` игнорируются) |
| `GET /v1/offer/{id}` | карточка в `payload.item` |
| `GET /v1/template?limit=50&offer_id={id}&type=2` | ленды (`type=1` — прокладки): `id`, `name` (a-1…), `preview_url` на `template.drcash.pro`, `arch_url` (zip на `static.statthroat.tech`) |
| `GET /v1/filter/country`, `/category`, `/decision` | справочники; `decision`: 1 CPA, 2 Trial, 3 SS, 4 Trial+Upsell, 6 CPL |
| `GET /v1/domain?limit=50&type=2` | домены аккаунта: doctor*.com с CNAME ok (не меньше 12); `type=1` пусто |
| `GET /v1/postback/task?is_global=true` | глобальные постбеки аккаунта |
| `GET /v1/profile`, `/v1/balance`, `/v1/manager-info/{id}` | профиль, баланс, менеджер |

Поля оффера: `id`, `name`, `name_composite`, `geo_code[]`, `rate` (выплата), `price` + `price_currency` (цена продукта), `approved` (% апрува), `category_id`,
`decision_id`, `status`, `rank`, `link`, `material_link`. Выгрузить всё и искать: `node scripts/dr_offers.mjs dump`, потом
`node scripts/dr_offers.mjs find 'cortitron|matcha' IT,AL,BA`. Ленды оффера прочитать и проверить: `node scripts/dr_landers.mjs 32535,32364,31602`.

**Поток (кампания) и ссылка.** В UI: Campaigns → «Create campaign» (`/stream/new?offer_id=<id>`): оффер, тип «Affiliate link», имя, галочки
лендов (id вида 80603 / a-5), домен, постбек. Форма Cortitron IT (32535) открывалась, **не отправлялась**: ссылку потока и поля
меток я в этой сессии не получал. По скилу `nutra-bundle-check`: `/l` отдаёт ленд, `/p` — прокладку; метки `sub1` (id тизера), `sub2` (площадка),
`sub5` (click id), разделитель макросов обычный `&`, не `%26`. **Пока не пришла первая конверсия, атрибуция не проверена**: первый лид
разбирать поштучно по карточке.

**Постбек.** В аккаунте есть глобальный `https://a.mgid.com/postback?c={sub5}&e=lead&r={payment}`, но `is_approved: false`: пока Dr.Cash его не
одобрит, лиды в MGID не уйдут. Одобрение просить у менеджера Kirill (это просьба владельца, не моя).

**Что нашлось под отклонённые связки (23.10):**

| связка (была на AdCombo) | в Dr.Cash |
|---|---|
| Cortitron IT, суставы | **Cortitron — CPA — [IT] (32535)**, выплата $33, продукт 49 EUR |
| Matcha Slim IT, похудение | **Matcha Slim IT (32364)**, $27 |
| Nautubone BA, суставы | **Nautubone BA (31602)**, $21, апрув 49.73 %, и (31542), $24, те же шаблоны |
| Osteflex AL, Hypertea AL | нет для Албании |
| Cardiotensive IT, ToxicOFF IT | нет; есть только Cardiotens Plus (другой продукт) |
| Varcosin AL | только HR, RS, SI |

Ленды этих офферов (Cortitron a-1…a-5, Matcha Slim a-1…a-4, Nautubone a-1…a-3, `template.drcash.pro`): выдуманные отзывы с именами
(«Vittoria Massano», «Sara Marinelli», «studentessa di medicina che ha inventato un rimedio»), выдуманные исследования
(«Testato dagli scienziati», «Centro Internazionale di Ricerca sulla Salute Umana», «17 godina kliničkih ispitivanja»), обещания («perdere 25 chili in 28
giorni», «CortiTron è un vero miracolo»); ассеты грузятся с `static.statthroat.tech`, части с `feleo.net`, `kfodjeos.com`, `cdn.ahacdu.com`. Те же признаки,
по которым модераторы уже отклоняли эти связки («Footnotes», «User awareness»). Решение: не использовать (см. §1).

## 4. Aray

**Вход.** `https://aray.com/login` (поля `email` и `password`, кнопка «Sign in»; `scripts/aray_login.mjs`). `POST /auth/login` за Cloudflare managed
challenge: из песочницы не проходит, в Chrome профиля Vision проходит за секунды. Нутра-кабинет `nutra.aray.com` из песочницы недоступен;
из Vision не пробовал.

**API** (тот же сайт, из залогиненной вкладки, `credentials: 'include'`): `GET /api/offers?page=N&count=100&order=desc&sorting=epc&chosen_type=all` →
`{meta, objects, api_key}`; ещё `/api/offers/{id}`, `/api/orders`. `api_key` из ответа не сохранять и не печатать. Ключ `ARAY_API_KEY` из ключника
взят из download-ссылок лендов и **как Bearer, X-Api-Key или параметр в `/api/offers` не принимается** (восемь вариантов, везде 401).
Поля оффера: `id`, `name` (страна — суффикс « - IT»; `countries` — числовые id), `vertical[]`, `flow` (COD…), `payout [{country_id, amount, currency}]`,
`preview_url` (ленд, часто пусто), `epc`, `clicks`, `device`, `is_access_granted`. Выгрузить и искать: `node scripts/aray_offers.mjs dump`,
`… find IT,AL,BA`; статическая проверка лендов: `… scan IT` (**не запускалась**: после выгрузки профиль был остановлен).

**Кабинет (26.10).** Аккаунт Infodreamer68, менеджер Sergey Aray. Меню: News (пусто), My campaigns, Offers, Statistics, Postbacks, Domains, Tickets, Payouts, Bonus, Orders.
История небольшая: в My campaigns одна кампания «[3567] Sustarox PE - Adskeeper test» на оффер 3759; **заказов с 1 января 2026 два** (оба Elastica - UY, июль, последний 29.07; что было раньше, не смотрел); доступно к
выплате **$11.00**, выплат не было; доменов и постбек-логов нет; в Tickets четыре старых тикета (заявки на доступ к офферам за май–июль 2026, в первом пометка «New answer»;
я их не открывал, чтобы не менять статус «прочитано»). Постбеки Aray настраиваются в разделе Postbacks (Settings, Testing, логи), трекер-домен ссылок — `cpa-gate.pro`.
**Доступ к офферам:** из 287 офферов доступ есть к 25 (LatAm COD: Duston Gel, Oxys, Elastica, Vitaflex, Cardiwell…, плюс Aimour 60% CPS $65 и Prostanore ID $32);
к остальным 262 доступ **запрашивается тикетом «Offer request for <оффер>»** (в мае и июле одобряли от того же дня до четырёх дней). В карточке оффера с доступом есть
`tracking_url` (наша ссылка), `_lands`, `_prelands`, `creatives`, `hold_period`, `restrictions`, `iframe_form`; без доступа поля урезаны. **Апрува, рейтинга и EPC в данных нет**
(`epc`/`clicks` заполнены только у Duston Gel - CL: 0.668 и 542641, смысл цифр не ясен), поэтому «топ» в Aray можно собрать только по выплате и по доступу.
Свод «топ офферы» по обеим сетям (рейтинг Dr.Cash, выплаты Aray, один продукт в обеих сетях, топ-5 по каждому гео) делает `python3 scripts/make_top.py` из дампов
`aray_offers.mjs dump` и `dr_offers.mjs dump` (файл `top-offers-<дата>.md` в `OUT_DIR`; версия от 26.10 отправлена владельцу). Апрув 100 % у офферов Dr.Cash с рейтингом 1000+ — шум,
ранжировать надо по `rank`. Свод не проверяет ленды (раздел 8).

**Недельный топ Aray (апрув).** Раз в неделю Aray публикует в Telegram-канале `t.me/araycpa` («ARAY.COM | Партнёрская», 2.8 тыс. подписчиков) пост «ТОП ОФФЕРОВ ОТ ARAY <даты>»: список по объёму лидов
с апрувом и список по апруву. Неделя 19–25.10.2026: по объёму Vitaflex PE 30 %, FlexiGo CL 27 %, Sustarox EC 30 %, Audix PE 29 %, Glowy Care PE, CL и Serum CO по 28 %; по апруву Elastica UY 46 %, Duston Gel UY 42 %,
Sustarox PY 38 %, Oxys PY 35 %. Веб-превью канала выключено (`t.me/s/araycpa` отвечает 302), раздел News в кабинете пуст, так что текст поста приносит владелец скриншотом. Это **единственный источник апрува** по
офферам Aray (в данных кабинета его нет). Оценка лида: EV = выплата × апрув, это потолок target CPA для необработанного лида. Свод по скриншоту и нашему доступу делается скриптами ниже (**счётчики слов лендов не заменяют чтения глазами**: 26.10 по ним Audix PE land3 и Glowy Care PE cream выглядели терпимо, а в тексте «лучшие израильские учёные», «фармпрепарат», выдуманный косметолог «Versua Clinic» и «клинические исследования»); из 11 офферов недели
доступ есть к 9, нет к FlexiGo CL (4891) и Glowy Care CL (4907).

**Постбеки Aray → MGID уже настроены** (глобальные, Postbacks → Settings): лид `http://a.mgid.com/postback?c={subid}&e=aray_lead&r={revenue}`, подтверждение `…&e=aray_buy&r={revenue}`; цели в MGID второго аккаунта
`aray_lead` 1278025 и `aray_buy` 1278024. Кнопку «Make test» в Aray не нажимать: это боевой постбек в MGID с выдуманным click id.

**Ссылка и метки.** Карточка оффера с доступом (`aray_cards.mjs`) отдаёт `tracking_url`: `https://uh76404db1uh.cpa-gate.pro/?target=<токен оффера>&al=<id ленда>&ap=<id прокладки>` (`al` и `ap` — выбранные у нас ленд и
прокладка; токен привязан к нашему аккаунту, в git и в чужие руки не отдавать). **Проверено 26.10 на Vitaflex PE:** трекер пропускает на ленд все параметры ссылки, а форма заказа (`POST /order/create/`) получает
`subid`, `subacc`, `subacc2`, `sub1` скрытыми полями; поэтому в тизер идёт `&subid={click_id}&subacc={widget_id}&subacc2={teaser_id}`. **Не проверено до первого настоящего заказа:** что `{subid}` постбека берётся именно из
параметра `subid`; подмена `al` и `ap` на другие id (проверялась только ссылка с id по умолчанию). Проверка пробной ссылкой оставляет клики в статистике Aray (мои метки `ZQM…`), форму не отправлять.

**Запрос доступа к офферу (26.10, работает).** Страница оффера `https://aray.com/offers/offer-details?id=<id>`: кнопка «Request approval» открывает окно «Describe your traffic, please» (поле и «Send request»);
отправка делает `PUT /api/offers/<id>` и заводит тикет «Offer request for <оффер>» (в списке Tickets: #2799 FlexiGo - CL и #2800 Glowy Care - CL от 26.10, текст по-русски: платный нативный трафик MGID, гео, сначала тест).
Раньше одобряли от того же дня до четырёх дней. Это исходящее действие под аккаунтом владельца: только по его слову. Скрипт-образец: `aray_request4.mjs` в журнале сессии не сохранён, кнопка и поле ищутся по тексту.

**Прокладка по умолчанию и `ap=-1`.** Если в ссылке нет `ap`, трекер ведёт на прокладку, которая сохранена у нас в карточке оффера (`selected_prelands`), и `ap=0` не помогает. Параметр **`ap=-1`** соответствует пункту
«[-1] No prelanding» на странице оффера и ведёт прямо на ленд (проверено 26.10 на Duston Gel UY, Sustarox EC, Elastica UY; у Vitaflex PE и Oxys PY сохранённых прокладок нет и `ap` не нужен). Проверка ссылки: `aray_linkcheck.mjs
<оффер>:<al>[:<ap>]` открывает ссылку в профиле Vision и сравнивает скрытое поле `template_name` страницы с кодом превью ленда (`preland_name`) из карточки; метки `subid`, `subacc`, `subacc2` доезжают до формы.
Каждая проверка это настоящий клик в статистике оффера (с IP датацентра): 26.10 их было 11 с метками `ZQM…`.

**Кампании MGID по офферам Aray** делает `mgid/aray_campaigns.py` (репозиторий mgid-agent) по данным `mgid/data/aray-offers.json`: девять кампаний 12525146–12525154 (`product`, targetCpa $0.05, цель `aray_lead` 1278025 с ценностью лида = выплата × апрув,
страна и испанский, $20 в сутки, на паузе); тизеры по одному и только там, где ленд не выдумка (Elastica UY, Vitaflex PE, Duston Gel UY, Sustarox EC, Oxys PY), заголовок по тексту упаковки, картинка — снимок упаковки из Aray (`thumbs` карточки,
качается с `aray.com/offer_preview/...` без входа) 1200×800 на плоском фоне (Pillow), хостинг pixeldrain (ключник, сервис `pixeldrain`, `PIXELDRAIN_API_KEY`, загрузка `PUT https://pixeldrain.com/api/file/<имя>` с Basic-авторизацией, пустой логин).

**Ленды и прокладки.** В карточке `_lands` (type 3) и `_prelands` (type 2); у каждого `previews[0]` на `cpa-preview.pro`. Превью отвечает **403 «You cannot send traffic to preview URL», пока в запросе нет `Referer: https://aray.com/`**;
с ним отдаёт страницу, клик по офферу не засчитывается. `aray_landers.mjs <id,id,…>` разбирает все ленды и прокладки офферов статически (слова про отзывы, исследования, обещания, врачей, срочность, вид «новостей» на
испанском, итальянском и английском; скрипты: подписка на пуши, перехват «назад», обфускация, iframe) и пишет `aray_landers.json`. На 26.10 из 45 страниц девяти офферов рекламные статьи с отзывами, врачами и
исследованиями («Blog Today», «Healthcare academy (white doctor)», «world news», «Grandma», «True Life Story», «elle bellezza» и прокладки с именами) стоят **у нас по умолчанию** у Duston Gel UY, Sustarox EC (прокладка),
Audix PE, Sustarox PY и Glowy Care Serum CO; короткие товарные страницы есть у Elastica UY (9576), Duston Gel UY (9124), Sustarox EC (9338), Oxys PY (9550), Vitaflex PE и Glowy Care PE (единственные). Во **всех** страницах есть общие
скрипты платформы (подписка на пуши через `pushnginx.latest-news.pro`, перехват «назад»); показываются ли они посетителю, по коду не видно, для модерации MGID это риск: смотреть живым браузером из нужного гео.
Домены платформы: трекер `cpa-gate.pro`, ленды `cpa-lands.pro`, прокладки `cpa-preland.pro`, превью `cpa-preview.pro`, общий JS `s2.crstnst.com`; Safe Browsing 26.10: первые, `crstnst.com` и `latest-news.pro` чисты, у `cpa-preland.pro` и
`cpa-preview.pro` данных нет.

**Правила офферов и зоны доставки.** Описание LatAm-офферов: «NO local stars on creatives (landings, prelandings and banners)» (никаких местных знаменитостей) и «target only the regions where delivery is possible, otherwise your
lead will not be approved»; ссылка на открытую таблицу Google с зонами доставки (`…/export?format=csv` читается и из песочницы): PE (1466 индексов, много департаментов), EC (23 провинции, 150 городов), PY (258 городов), CO (две вкладки,
какая «без доставки», не разобрано), UY (локалидады по департаментам). Холд 0 дней, расписаний и капов в описании нет.

**Италия, COD (для AL и BA в Aray офферов нет):** Formelan (4431) $37, Menstill Plus (4428) $37, Nano Slim (4679) $42 (похудение), ProstAktiv (4293) $37,
Revinelle FullPrice (4861) $33, Revinelle LowPrice (4860) $31, Varilux Premium (4302) $37, Vigor Max Nature (4426) $37. Это не те продукты, что были в
связках (кроме категории), ленды не читал.

## 5. AdCombo и ClickHub: доступа нет

- **AdCombo** — сеть всех восьми отклонённых связок. Ссылки тизеров: трекеры `uh1fadd1a6uh.uewhbgfvds.cc` (Osteflex, Hypertea, Varcosin, ToxicOFF, Matcha Slim)
  и `uh1fadd1a6uh.axdsz.pro` (Cortitron, Cardiotensive, Nautubone), `?rid=<id>&subacc={click_id}&subacc2={widget_id}`. Они отвечают 302 и ведут на ленды
  `ljslfkjs.cc` (AL), `cortitron-03.health-line.me` (IT), `tyblk.info` (BA). Логина нет и не было ни в ключнике, ни в его истории (107 версий с 31.07),
  ни на Drive; `adcombo.com` и `api.adcombo.com` отвечают Cloudflare 403. Чтобы обновить ссылки или поставить S2S-постбек
  `https://a.mgid.com/postback?c={subacc}&e=lead&r=<выплата>`, нужен логин владельца; получив, сразу положить в ключник (сервис `adcombo`) и запушить.
- **ClickHub** — нутра-сеть под Европу, выплаты в евро (скил `clickhub`). Логина в ключнике нет.

## 6. Восемь нутра-копий на втором аккаунте MGID (816921 / 939023), CPA tune $0.05, всё на паузе

Созданы 20.10 (репозиторий tedtuhliy/mgid-agent: `mgid/nutra_direct.py`, данные `mgid/data/nutra-direct-copies.json`, журнал созданных тизеров
`mgid/data/nutra-direct-created.json`). Источник — кампании основного аккаунта (заблокирован), восстановлены из журнала
сессии 13.10. Автозапуск после одобрения выключен. Цель `lead` (1272844), ценность лида = выплата источника.

| кампания | id | ценность лида | тизеры на 23.10 |
|---|---|---|---|
| AL Osteflex, суставы | 12520656 | 17.0 | 5, все отклонены («Malware has been detected») |
| AL Hypertea, давление | 12520657 | 18.5 | 6, отклонены (Malware) |
| AL Varcosin, варикоз | 12520658 | 17.0 | 4, заблокированы системой без причины |
| IT Cortitron, суставы | 12520659 | 39.0 | 7, отклонены («Footnotes / User awareness») |
| IT Cardiotensive, давление | 12520660 | 45.5 | 6, отклонены (+ «Spoilers») |
| IT ToxicOFF, паразиты | 12520661 | 26.0 | 6, отклонены |
| IT Matcha Slim, похудение | 12520662 | 32.0 | 6, отклонены |
| BA Nautubone, суставы | 12520663 | 24.0 | нет (прошлые 4 были отклонены за malware) |

**Почему отклонили (разбор 22–23.10).** Причина лежит в v1-тизере: `status.reason_if_drop_karantin[0]`, в тексте ссылка на скриншот модератора
`https://i.gyazo.com/<id>.png`.
- **Албания и Босния, «Malware has been detected».** Скриншоты — красная страница Chrome «Dangerous site» (Safe Browsing) на ссылке.
- **Италия, «Footnotes / User awareness / Spoilers».** Скриншот Cardiotensive: история мужчины с инсультом и серые плашки «18+ Click» вместо картинок. Это
  содержимое ленда, а не домен: новая ссылка на тот же ленд будет отклонена снова, нужен другой ленд (свой прилендинг со сноской перед страницей заказа,
  без шоковых картинок и обещаний лечения, см. `nutra-bundle-check`). Статически этих плашек и истории в трёх лендах я не увидел: ленды отдают
  разным посетителям разные версии, воспроизвести скриншот отсюда нельзя.

**Проверка доменов Google Safe Browsing (23.10, `bash scripts/safebrowsing.sh <хост>`):**
`tyblk.info` (ленд Боснии) — **статус 2 «часть страниц небезопасна», горит второй флаг, скан 23.10 05:07 UTC**: для Боснии вердикт модератора подтверждается.
Чисто (статус 1): `ljslfkjs.cc` (ленд Албании), `uewhbgfvds.cc`, `axdsz.pro`, `cortitron-03.health-line.me` и `health-line.me`, `bbcwebhosting.com`,
`template.drcash.pro`, `drcash.pro`, `statthroat.tech`, `feleo.net`, `kfodjeos.com`, `ahacdu.com`. Албанский «Malware» этим не объяснён: пометка
могла быть временной или на другой вариант ленда (датацентр увидел у Hypertea страницу на чешском, у Cardiotensive «новостную»: варианты разные).
**Поправка к моему отчёту от 23.10:** там было «tyblk.info — нет ответа». Это неверно: четвёртый подряд запрос получил от Google страницу «302 Moved» (капча на `google.com/sorry`) при
частых запросах, и я принял её за «нет ответа». Настоящий ответ — статус 2 выше. **Между запросами держать ≥ 5 секунд** (`safebrowsing.sh` ждёт сам и пишет «RATE-LIMITED», если его отрезали).

## 7. CPA tune для нутры на MGID: настройка

Полностью и с кодом — в скилле `mgid`, §3. Для нутры, сжато:

1. Кампания только типа **`product`** (content не принимает CPA tune: 422 `BIDDING_STRATEGY_CAMPAIGN_TYPES_ERROR`, тип не меняется, значит нужна новая кампания).
2. Тело `POST /v2/ads/account/939023/campaigns`:
   ```json
   {"name": "...", "showName": "...", "type": "product", "isAutoLaunchAdsAfterApproval": false,
    "bidding": {"strategy": "targetCpa", "price": 0.05}, "sourcesOptimization": false,
    "limits": {"limitType": "budget", "dailyLimit": 20.0, "splitDailyLimitEvenly": false},
    "conversionTracking": {"type": "sensors", "decisionStage": null, "interestStage": null,
       "buyStage": {"targetId": 1272844, "deduplicateConversions": true, "conversionValue": 39.0}},
    "geoTargeting": {"countries": ["IT"], "regions": {"mode": "include", "value": []}},
    "languageTargeting": {"mode": "include", "value": [<id языка>]}}
   ```
   `price` — целевая цена конверсии (5 центов по слову владельца), `conversionValue` — ценность лида для отчёта (у нутры — выплата), это разные числа.
   `dailyLimit` в долларах при создании (в чтении v1 ×100). MGID создаёт кампанию **активной**: сразу пауза (`whetherToBlockByClient=1`).
3. Ссылка тизера обязана донести click id до партнёрки: AdCombo `subacc={click_id}` и `subacc2={widget_id}`; Dr.Cash `sub5={click_id}` (под глобальный
   постбек) и `sub1={teaser_id}`, `sub2={widget_id}`. Макросы MGID: `{click_id}`, `{widget_id}`, `{teaser_id}`, `{campaign_id}`. Добавить click id к уже
   созданным тизерам, не пересоздавая их, можно UTM кампании (`PUT goodhits/campaigns/{id}/utmtracking/`, `utm_custom=<параметр партнёра>={click_id}`; MGID
   дописывает его в момент клика, перемодерации нет; так сделано для RollerAds, для AdCombo и Dr.Cash не проверялось).
4. Тизеры: v1 `POST goodhits/clients/816921/teasers` (форма): `campaignId`, `url`, `title`, `imageLink`, `priceOfClick` (1.5 цента, реальную цену клика выбирает
   targetCpa), `whetherShowGoodPrice=0`. **В первый раунд по одному тизеру на кампанию.** Редактировать тизер нельзя (POST по существующему id создаёт дубль),
   лимит добавления ≈10 в сутки на кампанию (`LS_TEASER_ADD_LIMIT_ERROR`), удаление лимит не возвращает.
5. Постбек партнёрки на `https://a.mgid.com/postback?c={click id}&e=lead&r=<выплата>` (`e` — `eventName` цели). Без одобрения постбека лиды не вернутся (Dr.Cash: §3).
6. **Ставка и трафик.** При $0.05 кампании практически не получают показов (5–7 в час в тесте LendingTree Mortgage Refinance CPL (1537)); клики пошли лишь с $3.5–5.
   Для нутры калибровка не делалась: экономику связки считать до запуска (`nutra-bundle-check`, проход 6: клики до окупаемости и нужный CR). Повышать вручную
   (`PATCH bidding`) или лесенкой (`mgid/cpa_ladder.py`, +$0.50 в час, потолок $5), решение о потолке за владельцем.
7. Стоп-лосс на Inferno (`mgid-spend-stop-second`, сейчас $15 на кампанию с момента сброса) и окно оффера — служба сама не знает про нутра-копии: добавлять
   их id в `MGID_WINDOW_CAMPS`, только если у оффера есть расписание.

## 8. Чек-лист перед модерацией (по порядку)

1. Оффер: гео, выплата, апрув, модель (`decision`), цена продукта; экономика связки.
2. Ленд: `node scripts/dr_landers.mjs <оффер>` или `node scripts/lander_scan.mjs <url>`; прочитать глазами хотя бы первые экраны и отзывы. Стоп-слова: имена
   «реальных людей» с отзывами, «исследования/клиника/учёные» без источника, обещания цифр, шок-картинки и истории о болезнях, таймеры «осталось N».
   Скан ничего не гарантирует: чистый скан не значит, что страницу пропустят, а грязный не значит, что нет.
3. Домены: `bash scripts/safebrowsing.sh <трекер> <ленд>` для каждого варианта ленда, на который ссылка может редиректить.
4. Ссылка открывается и несёт метки (проход 5 `nutra-bundle-check`): браузером, а не curl; при первом лиде разобрать карточку.
5. Название кампании описывает то, что в ней крутится; бренд в тизере совпадает с продуктом оффера.
6. Один тизер на кампанию в первый раунд, кампания на паузе, автозапуск выключен. Остальное — после вердикта модерации.

## 9. Что открыто (на 23.10)

- Новых ссылок для отклонённых связок нет: AdCombo без логина, ленды Dr.Cash отклонены мной по честности, Aray даёт только итальянские COD под другие продукты.
- Решения владельца: проверить ленды Aray (8 итальянских) тем же скриптом; проверка Албании в чистом браузере (на общем боксе Vision нельзя, там чужой TikTok); пересоздать
  тизеры; одобрение глобального постбека Dr.Cash у менеджера.
- Задача «перенаправить нутра-кампании на новые ссылки» (CPA tune 5 центов, на паузе) ждёт ссылок.
