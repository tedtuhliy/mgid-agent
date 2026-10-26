// Landers and pre-landers of Aray offers we have access to, read from the preview pages (cpa-preview.pro: no click is registered on the offer) inside
// the Vision profile and checked with lander_scan.scan(): words that sit next to a rejection («testimonios», «estudios», «garantizado», doctors, fake news look...)
// and scripts (push subscription, back-button hijack, obfuscation). A static check: it does not run the page the way a visitor from the target country
// would see it, and a clean result is not a clearance. Needs aray_cards.json (aray_cards.mjs first).
//   OUT_DIR=. VISION_CDP_PORT=<port> node aray_landers.mjs 4840,3959[,...]     # all active landers and pre-landers of those offers
import fs from 'node:fs';
import { connect, OUT } from './vision_cdp.mjs';
import { scan, show } from './lander_scan.mjs';

const ids = (process.argv[2] || '').split(',').filter(Boolean);
const cards = JSON.parse(fs.readFileSync(`${OUT}/aray_cards.json`, 'utf8'));
const { browser, ctx } = await connect();
const page = ctx.pages().find((p) => /aray\.com/.test(p.url())) || await ctx.newPage();
const report = {};
for (const id of ids) {
  const o = (cards[id] || {}).o;
  if (!o) { console.log(`${id}: not in aray_cards.json`); continue; }
  console.log(`\n##### ${id} ${o.name} (selected land ${JSON.stringify(o.selected_lands)}, preland ${JSON.stringify(o.selected_prelands)})`);
  report[id] = { name: o.name, pages: [] };
  const list = [...(o._lands || []).map((x) => ['land', x]), ...(o._prelands || []).map((x) => ['preland', x])].filter(([, x]) => x.is_active !== false);
  for (const [kind, x] of list) {
    const u = (x.previews || [])[0];
    if (!u) { console.log(`  [${kind}] ${x.id} ${x.name}: no preview`); continue; }
    try {
      // the preview host answers 403 «You cannot send traffic to preview URL» unless the request comes from the cabinet: a Referer is enough
      const r = await page.request.get('https://' + u.replace(/^https?:\/\//, ''), { timeout: 60000, headers: { referer: 'https://aray.com/' } });
      const html = (await r.body()).toString('utf8');
      const sc = scan(html);
      show(`  [${kind}] ${x.id} ${String(x.name).slice(0, 60)}${x.selected ? ' (SELECTED)' : ''} | HTTP ${r.status()}`, sc);
      report[id].pages.push({ kind, id: x.id, name: x.name, status: r.status(), ...sc });
    } catch (e) { console.log(`  [${kind}] ${x.id} ${x.name}: fetch error ${String(e).slice(0, 100)}`); }
  }
}
fs.writeFileSync(`${OUT}/aray_landers.json`, JSON.stringify(report, null, 1));
console.log(`\nsaved ${OUT}/aray_landers.json`);
await browser.close();
