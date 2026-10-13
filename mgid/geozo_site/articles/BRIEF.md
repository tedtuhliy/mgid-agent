# Brief for the language writers (arcadiablog.com/blog/<lang>/)

You write the content of one language version of a small home-and-garden magazine, **Arcadia Blog**. Readers are adults
aged 40+ who open an article from a news-feed teaser on a phone. The pages carry labelled advertising blocks between the
paragraphs, so the text has to be real, useful, calm and easy to read in short pieces.

You write **natively in your language** (do not translate word by word from English; the outlines below are only
what each article is about). Natural everyday vocabulary of the country, metric units, local habits.

## What to deliver

Everything goes into one folder, `geozo_site/articles/<lang>/` (the lead gives you `<lang>`), and nowhere else:

1. **Ten article files** `<slug>.json`, one per topic of the list at the end of this brief (the slug is the file name).
2. `ui.json` — the interface strings of the site (keys below).
3. `pages.json` — three short service pages: `about`, `contact`, `privacy`.
4. `teasers.json` — teaser headlines for MGID (four, see below).

Run `python3 geozo_site/check_articles.py <lang>` from the repository's `mgid/` folder until it prints `OK`. The
checker is strict about the format, not about style; style is on you.

## Article file format

```json
{
  "rubric": "Home and kitchen",
  "title": "…",
  "teaser": "One or two sentences for the list on the home page (150-220 characters).",
  "description": "One sentence for the meta description (110-160 characters).",
  "heroAlt": "What the picture shows, in your language (one sentence).",
  "body": [
    {"t": "p", "lead": true, "x": "Lead paragraph, 2-3 sentences."},
    {"t": "p", "x": "Short intro paragraph."},
    {"t": "h2", "x": "1. First section"},
    {"t": "p", "x": "…"},
    {"t": "p", "x": "…"},
    {"t": "tip", "x": "One-sentence practical tip (optional, at most one per article)."},
    {"t": "h2", "x": "Short summary"},
    {"t": "ul", "x": ["point", "point", "point", "point"]},
    {"t": "p", "x": "Closing paragraph."}
  ]
}
```

Rules of the structure (the checker enforces them):

- Block types are only `p`, `h2`, `tip`, `ul`. The first block is the lead `p` (`"lead": true`), the second a plain `p`.
- At least **6 `h2`** sections (the topic list says how many main sections), each `h2` followed by one or two `p`
  (and, in at most one section, a `tip`). End with a short summary `h2` + one `ul` of 4-6 points + one closing `p`.
- At least **14 blocks that are not `h2`**, 380-520 words in total, every paragraph 1-4 sentences (short on purpose:
  an advertising block may sit after any of them, and the reader should be able to stop after each).
- A `title` of 40-90 characters. If the title promises a number («9 simple rules», «7 tips»), the `h2` sections
  are numbered `1.`, `2.`, … and there are exactly that many. Otherwise no numbering.
- Plain text only: no HTML, no markdown, no emoji, no links, no placeholders.

## Style and content rules (important — a moderator reads these pages)

- Practical household advice that is true anywhere: kitchen and food storage, houseplants, herbs, a little gardening.
  Typical safe facts only (fridge about +2…+5 °C, freezer −18 °C, cooked food within 3-4 days, and so on).
- **No health or medical claims at all**: nothing that cures, prevents, treats, detoxes, boosts immunity, helps with
  weight, blood pressure, joints, skin, etc. Aloe and lavender are *plants to look after*, not remedies. No diets.
- No brand names, no shops, no prices, no «scientists discovered», no superlatives like «miracle», «best ever»,
  «secret», «shocking», no fear-mongering, no exclamation marks, no questions in headings meant to tease.
- Never mention advertising, the site, the teaser or a click. Do not address the reader by age.
- Each article stands alone and uses its own wording; do not repeat sentences between articles.
- Register: friendly and respectful, the way a good local household magazine writes. Use the form of address that is
  normal in print in your country, and keep it the same in all ten articles.
- Spelling and typography of your language (quotation marks, decimal comma/point, spacing before units, `°C`).
- Do not state specific legal, safety-authority or product-label claims. If it is about storage times, give a
  reasonable range and tell the reader to follow the label of the product.

## ui.json

All keys are required (strings unless noted):

| key | meaning |
|---|---|
| `brand_tag` | one word after the brand in the header, like «tips» / «porady» (the brand is `Arcadia Blog`) |
| `read_also` | heading of the block with links to other articles («Read also») |
| `read_min` | «{n} min read», must contain `{n}` |
| `home_title` | the `<h1>` of the home page: a short title for a home-and-garden magazine |
| `home_intro` | 1-2 sentences under it |
| `all_articles` | heading above the list of the ten articles |
| `nav_home`, `nav_about`, `nav_contact`, `nav_privacy` | footer link texts |
| `disclosure` | footer, 1-2 sentences: informational material; the site shows partners' advertising, every advertising block is marked with the word given as «ad label» below; cookies are used for the site and the advertising blocks |
| `cookie` | cookie notice, one sentence: «We use cookies for the site and the advertising blocks.» |
| `cookie_more` | «More» (link to the privacy page) |
| `cookie_ok` | «OK» |
| `disclaimer` | one sentence under every article: informational only; follow the instructions of the manufacturer and the needs of the particular plant/product |
| `months` | list of 12 month names **in the form used inside a date** («13 października», «13. Oktober»: genitive in Polish, plain in German …), January first |
| `date_fmt` | the date pattern with `{d}`, `{month}`, `{y}`: for example `{d} {month} {y}` (Polish), `{d}. {month} {y}` (German), `{y}. {month} {d}.` (Hungarian), `{d} {month} {y} г.` (Bulgarian) |

The word for **«advertisement» above blocks is fixed by the site** and not part of `ui.json` (it appears in the
`disclosure` text: use the word given to you by the lead for your language).

## pages.json

```json
{"about": {"title": "…", "paras": ["…", "…", "…"]},
 "contact": {"title": "…", "paras": ["…", "…"]},
 "privacy": {"title": "…", "paras": ["…", "…", "…", "…", "…"]}}
```

- `about`: 3 paragraphs: what the magazine is (home, kitchen, garden advice), that the texts are informational,
  that the site is financed by advertising from partners and the ads are labelled.
- `contact`: 2 paragraphs, with the e-mail `contact@arcadiablog.com` written as plain text, answer within a few working days.
- `privacy`: 5 short paragraphs: what is collected (technical data of the visit, cookies), that advertising blocks of
  partners may use cookies and similar technologies to show and measure ads, that no accounts or payments exist on the
  site, how to manage cookies in the browser, how to ask a question (the e-mail above). Plain language, no legal
  boilerplate numbers, no company names.

## teasers.json

Headlines for four articles that will be advertised in a news feed. Exactly this shape, **title ≤ 65 characters**:

```json
[{"article": "herbs-in-a-jar", "title": "…"},
 {"article": "bread-storage", "title": "…"},
 {"article": "fruit-and-vegetables", "title": "…"},
 {"article": "houseplants-autumn", "title": "…"}]
```

A headline says plainly what the article gives: «A jar of water instead of a bag: a simple way to keep herbs fresh»,
«Bread goes stale in the fridge? There is a better way». No clickbait, no all-caps, no exclamation marks, no
question that addresses the reader's age or personal traits, no promises, no «you won't believe». It must match the
article's content exactly. Natural, short and concrete.

## The ten topics (slug → what the article is about)

1. `food-storage` — **9 simple rules to keep food fresh for longer** (9 numbered sections): 1 fridge layout and
   temperature (coldest at the back/bottom, door for sauces and drinks); 2 raw meat and fish on the bottom shelf in
   closed containers; 3 herbs like flowers in a vase; 4 fruit and vegetables apart (ethylene: apples, pears,
   bananas, tomatoes; potatoes and onions apart); 5 do not wash berries, mushrooms and leaves in advance; 6 bread,
   grains and nuts; 7 freezing: fresh, in portions, dated, tight; 8 cooked food: cool within two hours, eat within
   3-4 days; 9 first in, first out and a clean fridge. Summary list.
2. `herbs-in-a-jar` — **Parsley, dill and coriander stay fresh for weeks: the jar method** (6 sections): trim the
   stems and remove tired leaves; a jar with 2-3 cm of water, a loose bag on top, in the fridge; change the water
   every two days; do not wash before storing; the exception: basil dislikes cold (room temperature); alternatives:
   damp paper towel in a container, freezing chopped herbs in ice-cube trays with a little water or oil; use soft
   leaves in soups and sauces.
3. `fruit-and-vegetables` — **Fruit and vegetables: what to keep together and what to keep apart** (6): the idea of
   ethylene in plain words; who produces it and who suffers (apples, bananas, tomatoes vs leafy greens, cucumbers,
   carrots, broccoli); potatoes and onions apart and dark and airy; tomatoes do not like the fridge; the two
   crisper drawers (humid for vegetables, dry for fruit); cut produce in closed containers; look through the
   stock once a week and remove what is spoiling.
4. `bread-storage` — **How to store bread so that it stays fresh and soft** (6): why the fridge dries bread out
   faster; bread bin, linen bag or paper, crusty vs soft loaves, cut side down; slicing and freezing with parchment
   between the slices, toasting from frozen; reviving a stale loaf (a few drops of water, 10 minutes in a hot oven);
   keeping the bread bin clean and dry; mould: throw it away; using stale bread (croutons, breadcrumbs, French toast).
5. `houseplants-autumn` — **Houseplants in autumn: 7 tips to get them through to spring** (7 numbered sections):
   more light and clean leaves; water less but check the soil; humidity near radiators (tray with wet pebbles, group
   plants); keep away from drafts and heaters; cut back feeding; check for pests weekly; do not rush repotting.
6. `windowsill-herbs` — **Herbs on the windowsill: what grows well indoors and how to look after it** (6): basil,
   mint, parsley, chives, thyme; light (south/east window, 4-6 hours, a desk lamp in winter); pots with drainage;
   water when the top 1-2 cm are dry; pinch tips to keep plants bushy and harvest no more than a third; common
   problems (stretched stems, yellow leaves); feed lightly once a month in the growing season.
7. `repotting` — **Repotting houseplants: when, how and what to avoid** (6): signs that a plant needs a bigger pot
   (roots at the drainage holes, water runs straight through, growth stops); the best time is spring to early summer,
   not winter rest; a pot only 2-3 cm wider; fresh suitable mix and drainage; the steps (water the day before, loosen
   the roots, trim dead ones, place, fill, water, keep out of strong sun for a week); do not feed straight away; when
   not to repot (flowering, sick plant); top-dressing as the alternative.
8. `lavender` — **Growing lavender: sun, soil and pruning** (6): full sun; light, well-drained, rather poor soil; plant
   in spring 40-60 cm apart; water sparingly once rooted; prune lightly after flowering, never into old bare wood;
   frost is less dangerous than wet feet in winter; pots with gravelly mix; cut the flowers at the bud stage and dry them
   for home decoration and scented sachets (fragrance only); the usual mistakes (rich soil, overwatering, shade).
9. `aloe-care` — **Aloe vera at home: light, watering and repotting** (6): only plant care. Bright indirect light, a
   little direct sun is fine; water thoroughly then let the soil dry out completely; gritty mix, drainage holes, a
   terracotta pot; winter rest, no frost (keep above about 10 °C); signs of too much water (soft, glassy leaves) and
   too little (thin, curled leaves); separating the offsets; repotting every two to three years.
10. `drying-herbs` — **How to dry and store herbs at home** (6): when to harvest (morning after the dew, before
    flowering); small bundles hung upside down in a dark airy place; trays or screens; the oven at the lowest
    temperature with the door ajar; how to know that they are dry (they crumble); airtight jars away from light and
    heat, labelled with the date, about a year; crush just before use; which herbs dry well (oregano, thyme, rosemary,
    sage, mint, dill) and which are better frozen (basil, parsley, coriander, chives).
