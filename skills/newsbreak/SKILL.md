---
name: newsbreak
description: Наша закупка нативного трафика на NewsBreak (кабинет admanager.newsbreak.com, API business.newsbreak.com): вход без браузера, API-ключ, создание кампаний, групп и объявлений через API, минимальные ставки и бюджеты, жёсткий лимит расхода аккаунта, ссылки RollerAds с метками NewsBreak, проверка меток. Использовать ВСЕГДА, когда задача касается NewsBreak: создать или проверить кампанию, поднять лимит, включить или выключить, снять статистику, подключить оффер.
---

# NewsBreak: доступ, API, тест свипов (19.11.2026)

Репозиторий `tedtuhliy/mgid-agent`, папка `newsbreak/` (ветка `claude/optimistic-feynman-at3shp`): `nb_api.py` (клиент), `nb_sweeps.py` (тест свипов), `ra_client.py` (ссылки RollerAds),
`data/nb-sweeps.json` (тексты, лимиты), `data/nb-created.json` (id созданного и ссылки на картинки в библиотеке), `test_nb.py` (13 тестов без сети).
Запуск: `node ~/.claude/skills/secrets/vault.mjs exec newsbreak rollerads -- python3 -I nb_sweeps.py …`.

## 1. Доступ

Ключник, service **`newsbreak`**: `NEWSBREAK_LOGIN` (infodreamer66@gmail.com), `NEWSBREAK_PASSWORD`, `NEWSBREAK_API_KEY` (36 символов, токен рекламного API).
Логин и пароль владелец прислал в чат 19.11.2026 (значит, они в переписке; **пароль тот же, что у cpamatica** — сменить оба). API-ключ выпущен владельцем 01.09.2026 (Ad Manager → Tools → Advertising API),
`ACTIVE`, лимит 10 запросов в секунду (уровень Basic); новый не выпускали.

**Вход без браузера** (проверено живьём): Firebase `signInWithPassword` (проект `newsbreakads`, веб-ключ Firebase лежит в публичном `_app-*.js` кабинета) → `POST https://admanager.newsbreak.com/api/login`
`{accessToken, email, expInfo: "{}"}` → `{code: 0, token}`; дальше внутренний API `https://admanager.newsbreak.com/api/v1/...` с `Authorization: Bearer <token>`. Через него читается и выпускается токен:
`GET /api/v1/users/access-token` (список; поле `id` и есть токен), там же `fullApiList` (35 разрешённых методов). Код: `nb_api.session_token()`, `nb_api.internal()`.

**Документация публична только как Zendesk JSON** (страницы `…/hc/…` отвечают ботам 403):
`https://advertising-api.newsbreak.com/api/v2/help_center/en-us/articles.json?per_page=100` (справочник API, 39 статей) и `https://adhelp.newsbreak.com/api/v2/help_center/en-us/articles.json?per_page=100`
(справка кабинета, 163 статьи: макросы, постбеки, политики, ставки).

## 2. Публичный API

База `https://business.newsbreak.com/business-api/v1`, заголовок `Access-Token`, ответ `{"code": 0, "data": …}` (коды ошибок: 403, 4031 не вошли, 4033 плохой токен, 4034 лимит запросов). **Деньги в центах, время в секундах.**

| Что | Метод и путь |
|---|---|
| организации, аккаунты | `GET org/admin-orgs`, `GET ad-account/getGroupsByOrgIds?orgIds=` |
| лимит расхода аккаунта | `POST balance/getAccountBudgetInfo {accountIds}`, `POST balance/updateAccountsBudget {adAccountsBudgetUpdate: [{adAccountId, budget}]}` (больше, чем уже потрачено) |
| кампания | `POST campaign/create {adAccountId, name, objective, status}`, `PUT campaign/update/{id}`, `PUT campaign/updateStatus/{id} {status}`, `DELETE campaign/delete/{id}`, `GET campaign/getList` |
| группа | `POST ad-set/create` (budgetType DAILY/TOTAL, budget, startTime, endTime, bidType, bidRate, trackingId, targeting, platforms, status), `PUT ad-set/update|updateStatus/{id}`, `DELETE`, `GET ad-set/getList` |
| объявление | `POST ad/create {adSetId, name, status, creative: {type, headline, assetUrl, description, callToAction, brandName, clickThroughUrl}}`, `PUT ad/update|updateStatus/{id}`, `GET ad/getList` |
| картинка | `POST ad/uploadAssets` (multipart: `asset`, `adAccountId`, `saveToMediaLibrary`, `mediaName`) → `assetUrl` на CDN NewsBreak; повтор того же файла: 409 с URL уже загруженного |
| события | `GET event/getList/{adAccountId}?os=` (пусто на 19.11), отчёты `POST reports/getIntegratedReport` |

Цели кампании: `WEB_TRAFFIC` (ставка только CPC, события не нужны), `WEB_CONVERSION` (MAX_CONVERSION, TARGET_CPA, … и `trackingId` веб-события, то есть пиксель или постбек из Event Management), `REACH` (CPM).
Площадки группы: `["NEWSBREAK"]` (приложение и сайт NewsBreak), по умолчанию `APP_AND_WEB_UNLIMITED` (плюс партнёры).

## 3. Минимумы платформы (проверено 19.11 пробными группами, потом удалены)

- **CPC не ниже $0.10** (9 центов: «illegal bid rate too small»).
- **DAILY-бюджет группы не ниже $10** (1000 центов); **TOTAL не ниже $10 за каждый календарный день полёта** ($20 для суток через полночь, $80 за семь дней).
- Заголовок до 90 знаков, картинка лучше 16:9, текст в стиле новостей без «кричащих» слов; модерация объявления 1–2 рабочих дня (`auditStatus PENDING`, она идёт и у выключенных).
- Жёсткий потолок денег: **лимит расхода аккаунта** (`updateAccountsBudget`), его выставили в $10; он выше любых бюджетов групп.
- Баланс аккаунта 19.11 **$0** (`GET /api/v1/balance-accounts/{id}`: `topUp 0`): пока владелец не пополнит, ничего не крутится.

## 4. Ссылка объявления и метки

Хост ссылки оффера заменяется на **eventsbytlcltd.com** (кастомный домен команды баинга для US-свипов и лидгена, 19.11; по умолчанию green-planet.live), путь с кодом и подписью остаётся (`nb_sweeps.click_url`).
`<ссылка оффера RollerAds>?source_id=nb-__FLIGHT_ID__-__CREATIVE_ID__&aff_click_id=__CALLBACK_PARAM__`. Макросы NewsBreak пишутся **с двумя подчёркиваниями** (`__NAME__`): `__CALLBACK_PARAM__` — id клика
(`nvss_<32 hex>_<19 цифр>`), `__FLIGHT_ID__` — id группы, `__CREATIVE_ID__` — id объявления, `__CAMPAIGN_ID__`, `__OS__`. Трекер RollerAds хранит `source_id` и `aff_click_id` целиком, в том числе такой длины
(тест-клик 19.11: 42 и 57 знаков вернулись из `aff-clicks` без изменений). **Отчёт `/api/statistics/aff-clicks` асинхронный**: первый вызов пустой, повторять через 7 секунд (и фильтры вида `оператор|значение`;
429 при частых вызовах). Конверсию по тесту читать у RollerAds по `source_id`; постбек в NewsBreak для кампании WEB_TRAFFIC не нужен.
Для оптимизации по конверсиям позже: событие-постбек в Event Management (`http://business.newsbreak.com/tracking/attribute?callback=<id>&event_type=<тип>&nb_value=<сумма>`) и постбек оффера RollerAds
(`callback={affClickId}`, `nb_value={trx}`; на аккаунте RollerAds не больше 10 постбеков, занято 7). Осторожно: постбеки оффера RollerAds срабатывают на каждую конверсию оффера и бьют в `a.mgid.com` с чужим id.

## 5. Тест свипов (19.11)

Аккаунт: организация и аккаунт «Bohdan Shevchenko» (`2094796504817250305`, `2094796504854999041`). Построено **выключенным**: кампания 2123401971659223042 «US | Level Reward $1000 (RollerAds 1282) | NB traffic CPC min»,
группа 2123401974553292802 (DAILY $10, CPC $0.10, 14 суток, `NEWSBREAK`, iOS и Android, 18–64, США), три объявления (2123401977279590401, 2123401978739208194, 2123401980278517761), на модерации.
Остальные офферы без ссылки (нет доступа в RollerAds) пропущены; 2139 ждёт апрува креативов рекла. **Когда ссылки появятся: `nb_sweeps.py --build`** (идемпотентно, сам найдёт созданное).
Картинки (12 штук 16:9) лежат в Media Library аккаунта, URL в `data/nb-created.json`.

**Запуск** (по слову владельца, после пополнения баланса): `nb_api.set_status("ad", id, "ON")`, затем группа и кампания; экстренно `nb_sweeps.py --all-off`; лимит аккаунта поднимать `nb_api.set_spending_cap(account, cents)`.
Стоп-лосс MGID на NewsBreak не распространяется: защита здесь лимит аккаунта и бюджет группы.

## 6. Ловушки

- **Креативы:** без выдуманных отзывов, заработков и поддельных скриншотов баланса (обман и нарушение правил площадок), без логотипов (проверять картинку глазами), заголовок описывает продукт и условия, не обещает доход. Образцы команды баинга (истории от первого лица с суммами) не повторяем.
- Трекер отвечает 204 на тест-клик с адреса дата-центра для офферов с гео и фильтром (2139, 2176, 2238, 2239); посадочную с такого адреса не прочитать.
- Ссылки уже созданных объявлений меняет `nb_sweeps.py --refresh-links` (`PUT ad/update` с полным `creative`).

- WebFetch и браузерные заголовки не открывают справку (403), JSON Zendesk открывается обычным запросом.
- `ad-set/create` возвращает `deliveryRate ASAP` при запросе `EVENLY` для CPC; `endTime` в прошлом не даст включить группу.
- Внутренний `/api/v1/locations*` без параметров отвечает 500; для США использовать `location: ["all"]`.
- Удаление (`DELETE …/delete/{id}`) ставит `onlineStatus DELETED`, из списка пропадает.
