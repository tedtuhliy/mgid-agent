// Dr.Cash offers through the cabinet's own API. All of them: 3704 on 23.10. `limit` is capped at 50 and only `offset` pages
// (the `page` and `country` parameters are ignored), so the whole catalogue is dumped once and searched offline.
//   node dr_offers.mjs dump                                  # -> $OUT_DIR/dr_offers.json
//   node dr_offers.mjs find 'cortitron|matcha' [IT,AL,BA]    # regex on the name, optional geo codes, over the saved dump
// Fields of an offer: id, name, name_composite, geo_code[], rate (payout), price + price_currency (price of the product), approved (%),
// category_id, decision_id (1 CPA, 2 Trial, 3 SS, 4 Trial+Upsell, 6 CPL), status, rank, transit, link, material_link.
import fs from 'node:fs';
import { withDr } from './dr_lib.mjs';
import { OUT } from './vision_cdp.mjs';

const [cmd, ...rest] = process.argv.slice(2);
const FILE = `${OUT}/dr_offers.json`;
if (cmd === 'dump') {
  await withDr(async ({ api }) => {
    const all = [];
    for (let off = 0; off < 20000; off += 50) {
      const r = await api(`/v1/offer?limit=50&offset=${off}&sort_by=rank&sort_type=ASC`);
      const items = ((r.json || {}).payload || {}).items || [];
      all.push(...items);
      if (items.length < 50) break;
    }
    const seen = new Set();
    const uniq = all.filter((x) => !seen.has(x.id) && seen.add(x.id));
    fs.writeFileSync(FILE, JSON.stringify(uniq));
    console.log('offers fetched', all.length, '| unique', uniq.length, '->', FILE);
    const cat = await api('/v1/filter/category');        // id -> name of the categories, for make_top.py
    fs.writeFileSync(`${OUT}/dr_category.json`, JSON.stringify(cat.json));
    console.log('categories ->', `${OUT}/dr_category.json`, '(HTTP ' + cat.st + ')');
  });
} else if (cmd === 'find') {
  const re = new RegExp(rest[0] || '.', 'i');
  const geos = (rest[1] || '').split(',').filter(Boolean);
  const all = JSON.parse(fs.readFileSync(FILE, 'utf8'));
  for (const o of all.filter((o) => re.test(`${o.name} ${o.name_composite}`) && (!geos.length || (o.geo_code || []).some((g) => geos.includes(g))))) {
    console.log(`${o.id} | ${o.name} | ${(o.geo_code || []).join(',')} | payout $${Number(o.rate).toFixed(0)} | approve ${o.approved}% | price ${o.price} ${o.price_currency} | category ${o.category_id} | decision ${o.decision_id}`);
  }
} else console.log('usage: node dr_offers.mjs dump | find <name regex> [GEO,GEO]');
