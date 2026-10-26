// Full cards of Aray offers (the offers we have access to carry the tracking link, landers, pre-landers, creatives, restrictions), read from the
// logged-in tab (aray_login.mjs first). Read only. The `api_key` of the card is dropped; the file keeps our own tracking link: do not commit it.
//   node aray_cards.mjs 4840,3988,4098        # -> $OUT_DIR/aray_cards.json and a summary on the screen
// Offers without access answer with a short card (no tracking_url, _lands, creatives).
import fs from 'node:fs';
import { connect, OUT } from './vision_cdp.mjs';

const ids = (process.argv[2] || '').split(',').filter(Boolean).map(Number);
if (!ids.length) { console.log('usage: node aray_cards.mjs <offer id>[,<offer id>...]'); process.exit(1); }
const { browser, ctx } = await connect();
const page = ctx.pages().find((p) => /aray\.com/.test(p.url()));
if (!page) { console.log('no aray.com tab in the profile: run aray_login.mjs'); await browser.close(); process.exit(1); }
const cards = await page.evaluate(async (ids) => {
  const out = {};
  for (const id of ids) {
    const r = await fetch(`/api/offers/${id}`, { credentials: 'include' });
    const j = await r.json().catch(() => null);
    const o = (j && (j.object || j.offer || j)) || {};
    delete o.api_key;
    out[id] = { st: r.status, o };
  }
  return out;
}, ids);
fs.writeFileSync(`${OUT}/aray_cards.json`, JSON.stringify(cards, null, 1));
const short = (v, n = 160) => JSON.stringify(v).slice(0, n);
for (const [id, { st, o }] of Object.entries(cards)) {
  console.log(`\n=== ${id} ${o.name} | HTTP ${st} | access ${o.is_access_granted} | countries ${short(o.countries, 40)} | payout ${short((o.payout || [])[0] && { amount: o.payout[0].amount, cur: o.payout[0].currency }, 60)}`);
  if (o.tracking_url) { const u = new URL(o.tracking_url); console.log(`  tracking: ${u.origin}${u.pathname} params: ${[...u.searchParams.keys()].join(',')} (value lengths ${[...u.searchParams.values()].map((v) => v.length).join(',')})`); }
  for (const k of ['hold_period', 'restrictions', 'action_flow', 'prelands_enabled', 'subpub_required', 'preclick_url', 'block_order_page_reopening', 'dont_use_global_postback']) if (o[k] !== undefined && o[k] !== null && o[k] !== '') console.log(`  ${k}: ${short(o[k], 200)}`);
  for (const k of ['_lands', '_prelands', 'creatives', 'selected_lands', 'selected_prelands', 'schedules']) {
    const v = o[k];
    if (Array.isArray(v)) console.log(`  ${k}: ${v.length}${v[0] ? ' | first: ' + short(v[0], 260) : ''}`);
    else if (v && typeof v === 'object') console.log(`  ${k}: object keys ${Object.keys(v).slice(0, 12).join(',')}`);
  }
  for (const k of ['scripts', 'scripts_params', 'widgets']) if (o[k] && typeof o[k] === 'object') console.log(`  ${k}: ${short(o[k], 300)}`);
}
await browser.close();
