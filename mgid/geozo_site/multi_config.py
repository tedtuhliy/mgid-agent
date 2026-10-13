"""Languages, geos and article topics of the multilingual site arcadiablog.com/blog/<lang>/ (MGID -> article -> Geozo blocks).

Owner, 13.10 night: «Нужно сделать сайт мультиязычным и взять все гео, что монетизирует ЛакиФид, кроме России и Беларуси;
на них нужно минимум по 10 статей на каждое гео, картинки те же самые, блоки те же самые; запустить кампании на эти гео
и языки с 1-2 креативами в самом MGID. Начни с Болгарии, Польши, Румынии, Чехии, Португалии, Италии, Испании,
немецкоговорящих Германии, Швейцарии, Австрии, Венгрии, Словакии, Словении, Сербии».

Data only, no logic: build_multi.py, check_articles.py and geozo_geos.py import it.

Why /blog/<lang>/ and not /<lang>/: arcadiablog.com already has the old gardening blog of March 2026 in /cs/, /sk/ and
/sl/ (not ours to overwrite) and nginx sends everything that starts with /ro to / (location ^~ /ro). A common prefix
avoids both.

MGID ids come from GET v2/dictionaries/countries and v2/dictionaries/languages (13.10).
LuckyFeed income is USD for 15.08-13.10, from api.luckyfeed.pro/v5/stats/full grouped by country_code.
"""

# route -> site language. `geos` are the MGID campaigns that point at the route.
LANGS = {
    "bg": {"name": "Bulgarian", "html": "bg", "ad_label": "Реклама", "script": "cyrillic", "mgid_lang": 29,
           "geos": ["BG"], "notes": "Standard Bulgarian, Cyrillic."},
    "pl": {"name": "Polish", "html": "pl", "ad_label": "Reklama", "script": "latin", "mgid_lang": 20,
           "geos": ["PL"], "notes": "Standard Polish."},
    "ro": {"name": "Romanian", "html": "ro", "ad_label": "Publicitate", "script": "latin", "mgid_lang": 17,
           "geos": ["RO"], "notes": "Standard Romanian, with proper diacritics (ă â î ș ț, comma-below forms)."},
    "cs": {"name": "Czech", "html": "cs", "ad_label": "Reklama", "script": "latin", "mgid_lang": 24,
           "geos": ["CZ"], "notes": "Standard Czech."},
    "pt": {"name": "European Portuguese", "html": "pt-PT", "ad_label": "Publicidade", "script": "latin", "mgid_lang": 8,
           "geos": ["PT"], "notes": "European Portuguese (Portugal), not Brazilian: frigorífico, casa de banho, "
                                    "telemóvel, pequeno-almoço, 'tu' avoided in favour of neutral/impersonal wording."},
    "it": {"name": "Italian", "html": "it", "ad_label": "Pubblicità", "script": "latin", "mgid_lang": 7,
           "geos": ["IT"], "notes": "Standard Italian."},
    "es": {"name": "Spanish (Spain)", "html": "es-ES", "ad_label": "Publicidad", "script": "latin", "mgid_lang": 2,
           "geos": ["ES"], "notes": "Peninsular Spanish (Spain): nevera/frigorífico, 'usted' or neutral wording."},
    "de": {"name": "German", "html": "de", "ad_label": "Anzeige", "script": "latin", "mgid_lang": 4,
           "geos": ["DE", "AT"], "notes": "Standard German (Hochdeutsch) that reads naturally in Germany and Austria; "
                                          "use 'ß' where standard German does; formal 'Sie' or neutral wording."},
    "hu": {"name": "Hungarian", "html": "hu", "ad_label": "Hirdetés", "script": "latin", "mgid_lang": 15,
           "geos": ["HU"], "notes": "Standard Hungarian."},
    "sk": {"name": "Slovak", "html": "sk", "ad_label": "Reklama", "script": "latin", "mgid_lang": 27,
           "geos": ["SK"], "notes": "Standard Slovak (not Czech!)."},
    "sl": {"name": "Slovene", "html": "sl", "ad_label": "Oglas", "script": "latin", "mgid_lang": 30,
           "geos": ["SI"], "notes": "Standard Slovene."},
    "sr": {"name": "Serbian (Latin script)", "html": "sr-Latn", "ad_label": "Reklama", "script": "latin", "mgid_lang": 35,
           "geos": ["RS"], "notes": "Serbian of Serbia, ekavian, written in the LATIN alphabet (latinica), "
                                    "with đ š č ć ž."},
}
# Switzerland reads the German pages with ss instead of ß: the route is derived from de at build time.
DERIVED = {"ch": {"from": "de", "html": "de-CH", "replace": [("ß", "ss")], "geos": ["CH"]}}

# how a language names itself (language switcher in the footer, /blog/ chooser)
NATIVE = {"bg": "Български", "pl": "Polski", "ro": "Română", "cs": "Čeština", "pt": "Português", "it": "Italiano",
          "es": "Español", "de": "Deutsch", "ch": "Deutsch (Schweiz)", "hu": "Magyar", "sk": "Slovenčina",
          "sl": "Slovenščina", "sr": "Srpski"}
HTML_LANG = {"ch": "de-CH"}

# MGID: geo -> (country id, route that its teasers point to)
GEOS = {
    "BG": (27, "bg"), "PL": (19, "pl"), "RO": (13, "ro"), "CZ": (16, "cs"), "PT": (35, "pt"), "IT": (22, "it"),
    "ES": (18, "es"), "DE": (3, "de"), "AT": (36, "de"), "CH": (37, "ch"), "HU": (39, "hu"), "SK": (47, "sk"),
    "SI": (172, "sl"), "RS": (165, "sr"),
}

# LuckyFeed income, USD, 15.08-13.10 (for the order of the waves and the report; not a bid input)
LF_INCOME = {"BG": 2446, "HU": 1757, "RO": 1239, "CZ": 787, "PL": 519, "RS": 494, "DE": 444, "HR": 297, "PT": 167,
             "SK": 155, "IT": 126, "FR": 64, "NL": 29, "ES": 26, "SI": 9, "AT": 9, "CH": 1}

# The ten articles. Images: make_images.py cuts assets/<slug>.jpg (hero, 1200x700) and teasers/<slug>.jpg (list thumbnail
# and MGID creative, 1200x800) from `src`; `crop` is (left, top, right, bottom) in the source, None = centre crop.
# `teaser` marks the articles that the writer also gives a teaser title for (food ones: they click best, see the KZ test).
TOPICS = [
    {"slug": "food-storage", "src": "assets/food-hero.jpg", "crop": None, "teaser": False, "sections": 9,
     "title": "9 simple rules to keep food fresh for longer"},
    {"slug": "herbs-in-a-jar", "src": "teasers/t1.jpg", "crop": None, "teaser": True, "sections": 6,
     "title": "Parsley, dill and coriander stay fresh for weeks: the jar method"},
    {"slug": "fruit-and-vegetables", "src": "teasers/t2.jpg", "crop": None, "teaser": True, "sections": 6,
     "title": "Fruit and vegetables: what to keep together and what to keep apart"},
    {"slug": "bread-storage", "src": "teasers/t3.jpg", "crop": None, "teaser": True, "sections": 6,
     "title": "How to store bread so that it stays fresh and soft"},
    {"slug": "houseplants-autumn", "src": "teasers/t4.jpg", "crop": None, "teaser": True, "sections": 7,
     "title": "Houseplants in autumn: 7 tips to get them through to spring"},
    {"slug": "windowsill-herbs", "src": "teasers/t5.jpg", "crop": None, "teaser": False, "sections": 6,
     "title": "Herbs on the windowsill: what grows well indoors and how to look after it"},
    {"slug": "repotting", "src": "teasers/t6.jpg", "crop": None, "teaser": False, "sections": 6,
     "title": "Repotting houseplants: when, how and what to avoid"},
    {"slug": "lavender", "src": "assets/src/lavender-field.jpg", "crop": None, "teaser": False, "sections": 6,
     "title": "Growing lavender: sun, soil and pruning"},
    {"slug": "aloe-care", "src": "assets/src/aloe-vera-hero.jpg", "crop": None, "teaser": False, "sections": 6,
     "title": "Aloe vera at home: light, watering and repotting"},
    # the bowls of dried herbs of the spice-jar photo; the crop leaves out the brand logos on the jars and the label that
    # still shows in its top right corner is blurred (boxes in source pixels)
    {"slug": "drying-herbs", "src": "assets/src/herbs-kitchen.jpg", "crop": (0, 368, 830, 853), "teaser": False,
     "blur": [(560, 280, 860, 540)], "sections": 6, "title": "How to dry and store herbs at home"},
]
SLUGS = [t["slug"] for t in TOPICS]
TEASER_SLUGS = [t["slug"] for t in TOPICS if t["teaser"]]

# ui.json (written by the language writer): every key is required. ad_label is NOT in it: it comes from LANGS above.
UI_KEYS = ["brand_tag", "read_also", "read_min", "home_title", "home_intro", "all_articles", "nav_home", "nav_about",
           "nav_contact", "nav_privacy", "disclosure", "cookie", "cookie_more", "cookie_ok", "disclaimer", "months",
           "date_fmt"]
PAGE_KEYS = ["about", "contact", "privacy"]       # pages.json: {key: {"title": str, "paras": [str, ...]}}
