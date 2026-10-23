// Aray offers through the cabinet's same-origin API, called from the logged-in tab (aray_login.mjs first; the tab must stay open).
// GET /api/offers?page=N&count=100&order=desc&sorting=epc&chosen_type=all -> { meta, objects: [...], api_key }. 290 offers on 23.10.
// The answer also carries the account's `api_key`: it is not saved anywhere here. ARAY_API_KEY of the vault (taken from the download links of
// landers) is NOT accepted by /api/offers as Bearer, X-Api-Key or a query parameter (8 variants tried on 18.10, all 401).
// Offer fields: id, name (the country code is the suffix: "Formelan - IT"; `countries` are numeric ids), vertical[], flow (COD...),
// payout [{country_id, amount, currency}], preview_url (the lander, often empty), epc, clicks, device, is_access_granted.
//   node aray_offers.mjs dump                       # -> $OUT_DIR/aray_offers.json
//   node aray_offers.mjs find IT,AL,BA              # offers whose name ends in " - IT" / " - AL" / " - BA"
//   node aray_offers.mjs scan IT                    # static lander check of the preview_url of those offers, inside the profile
import fs from 'node:fs';
import { connect, OUT } from './vision_cdp.mjs';
import { scan, show } from './lander_scan.mjs';

const [cmd, arg = ''] = process.argv.slice(2);
const FILE = `${OUT}/aray_offers.json`;
const byGeo = (all) => { const re = new RegExp(` - (${arg.split(',').filter(Boolean).join('|')})\\b`); return all.filter((o) => re.test(String(o.name))); };
if (cmd === 'dump' || cmd === 'scan') {
  const { browser, ctx } = await connect();
  const page = ctx.pages().find((p) => /aray\.com/.test(p.url()));
  if (!page) { console.log('no aray.com tab in the profile: run aray_login.mjs'); await browser.close(); process.exit(1); }
  if (cmd === 'dump') {
    const all = [];
    for (let p = 1; p <= 60; p++) {
      const r = await page.evaluate(async (p) => { const r = await fetch(`/api/offers?page=${p}&count=100&order=desc&sorting=epc&chosen_type=all`, { credentials: 'include' }); return { st: r.status, body: await r.text() }; }, p);
      let j = null; try { j = JSON.parse(r.body); } catch {}
      const items = (j && j.objects) || [];
      if (!items.length) { console.log('stop at page', p, 'HTTP', r.st, r.body.slice(0, 100)); break; }
      all.push(...items);
      if (items.length < 100) break;
    }
    const seen = new Set();
    const uniq = all.filter((o) => !seen.has(o.id) && seen.add(o.id));
    fs.writeFileSync(FILE, JSON.stringify(uniq));
    console.log('offers fetched', all.length, '| unique', uniq.length, '->', FILE);
  } else {
    for (const o of byGeo(JSON.parse(fs.readFileSync(FILE, 'utf8')))) {
      if (!o.preview_url) { console.log(`${o.id} ${o.name}: no preview_url`); continue; }
      try { show(`${o.id} ${o.name} ${o.preview_url}`, scan((await (await page.request.get(o.preview_url, { timeout: 45000 })).body()).toString('utf8'))); }
      catch (e) { console.log(`${o.id} ${o.name}: fetch error ${String(e).slice(0, 100)}`); }
    }
  }
  await browser.close();
} else if (cmd === 'find') {
  for (const o of byGeo(JSON.parse(fs.readFileSync(FILE, 'utf8')))) {
    const pay = (o.payout || [{}])[0];
    console.log(`${o.id} | ${o.name} | ${(o.vertical || []).join('/')} | ${o.flow} | $${pay.amount} | epc ${o.epc} | access ${o.is_access_granted}`);
  }
} else console.log('usage: node aray_offers.mjs dump | find <GEO,GEO> | scan <GEO,GEO>');
