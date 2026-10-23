// Landers (type 2) and pre-landers (type 1) of Dr.Cash offers, read inside the Vision profile and checked with lander_scan.scan().
//   OUT_DIR=. node dr_landers.mjs 32535,32364,31602     # offer ids -> prints a summary, writes dr_landers.json
// A template: id, name (a-1...), preview_url (https://template.drcash.pro/<uuid>), arch_url (zip on static.statthroat.tech), layout_type.
// 23.10: the 12 landers of Cortitron IT, Matcha Slim IT and Nautubone BA carried invented testimonials with names, invented research
// and promises ("perdere 25 chili in 28 giorni"): not used. Read them again before any new use, the partner changes templates silently.
import fs from 'node:fs';
import { withDr } from './dr_lib.mjs';
import { OUT } from './vision_cdp.mjs';
import { scan, show } from './lander_scan.mjs';

const OFFERS = (process.argv[2] || '').split(',').filter(Boolean);
if (!OFFERS.length) { console.log('usage: node dr_landers.mjs <offer id>[,<offer id>...]'); process.exit(1); }
await withDr(async ({ api, page }) => {
  const report = {};
  for (const id of OFFERS) {
    const o = await api(`/v1/offer/${id}`);
    const off = ((o.json || {}).payload || {}).item || {};
    console.log(`\n=== offer ${id}: ${off.name} | geo ${(off.geo_code || []).join(',')} | payout $${off.rate && Number(off.rate).toFixed(0)} | approved ${off.approved}% | price ${off.price} ${off.price_currency}`);
    report[id] = { name: off.name, geo: off.geo_code, templates: {} };
    for (const type of [1, 2]) {
      const t = await api(`/v1/template?limit=50&offer_id=${id}&type=${type}`);
      const items = ((t.json || {}).payload || {}).items || [];
      console.log(`  template type ${type} (${type === 1 ? 'pre-landers' : 'landers'}): ${items.length}`);
      for (const it of items) {
        let r = null;
        try { r = scan((await (await page.request.get(it.preview_url, { timeout: 60000 })).body()).toString('utf8')); }
        catch (e) { console.log(`   fetch error ${it.id}: ${String(e).slice(0, 100)}`); }
        if (r) { show(`   [${type}] ${it.name} (${it.id}) ${it.preview_url}`, r); report[id].templates[`${type}:${it.id}`] = { name: it.name, url: it.preview_url, ...r }; }
      }
    }
  }
  fs.writeFileSync(`${OUT}/dr_landers.json`, JSON.stringify(report, null, 1));
  console.log(`\nsaved ${OUT}/dr_landers.json`);
});
