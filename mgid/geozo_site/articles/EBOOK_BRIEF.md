# Brief: the free e-book of Arcadia Blog

Each language has a free PDF e-book that is compiled from its ten articles: a cover, a short introduction, a table of
contents and the ten articles as chapters. It is offered on every article page («Download the free e-book») and it
needs **no registration and no e-mail**: the visitor taps the button and gets the PDF. The book itself is assembled by
a script; you write **the strings of the book and of the offer card** into `articles/<lang>/ebook.json` (UTF-8, real
characters, no `\u` escapes):

| key | what it is | length |
|---|---|---|
| `title` | cover title of the book: ten practical guides for the home, kitchen and garden | 20-80 |
| `subtitle` | the line under the title, e.g. «Food storage, herbs, houseplants and a little gardening» | 20-140 |
| `intro` | page 2, «About this book»: what is inside, for whom, how to use it; 2-3 plain sentences; mention that the advice is general and that the manufacturer's information and the needs of the particular plant or product come first | 150-520 |
| `toc` | the heading «Contents» | 3-30 |
| `chapter` | the word «Chapter» (printed as «Chapter 3») | 3-20 |
| `cta_title` | headline of the offer card on the article pages, e.g. «Free e-book: ten practical guides» | 8-60 |
| `cta_text` | one sentence under it: what the visitor gets; say that no registration is needed | 40-200 |
| `cta_meta` | a small line that contains the placeholder `{pages}` (the script puts the real page count there), e.g. «PDF · {pages} pages · free · no registration» | 8-90 |
| `cta_button` | the button text, e.g. «Download the PDF» | 4-30 |
| `closing_title` | heading of the last page, e.g. «Thank you for reading» | 4-60 |
| `closing_text` | last page: thanks; the book is for information only, follow the manufacturer's instructions and what the particular plant needs; more articles are on the Arcadia Blog site | 60-320 |

Rules:

- Native, calm, practical, the same register and form of address as the language's `ui.json` and articles. Read the
  titles of the ten articles in `articles/<lang>/` so that the book title and the intro match what is really inside.
- Everything must be literally true: free, a PDF, no registration, no e-mail, nothing to pay.
- No exclamation marks, no emoji, no markup or links, no superlatives, no urgency («limited», «only today»),
  no «secret», no health or medical promises.

Check: `python3 geozo_site/check_articles.py <lang>` from the `mgid/` folder (it checks `ebook.json` when the file exists).
