// Does a tracking link of an Aray offer open the lander we think it opens? For each `offerId:al[:ap]` the link of the offer card is rebuilt with that
// lander (and pre-lander), opened in the Vision profile, and the hidden `template_name` of the page it ends on is compared with the `preland_name` of the
// chosen lander's preview in the card (they are the same code). Marker values in subid / subacc / subacc2 show that the labels survive.
// Every call is a real click in the statistics of the offer (a datacenter IP): use it sparingly. Needs aray_cards.json.
//   OUT_DIR=. VISION_CDP_PORT=<port> node aray_linkcheck.mjs 3959:9124:-1 3988:9338:-1 4081:9550 4047:9576:-1
import fs from 'node:fs';
import { connect, OUT } from './vision_cdp.mjs';

const cards = JSON.parse(fs.readFileSync(`${OUT}/aray_cards.json`, 'utf8'));
const code = (x) => { const u = (x && x.previews && x.previews[0]) || ''; return (u.match(/preland_name=([A-Za-z0-9]+)/) || [])[1]; };
const { browser, ctx } = await connect();
for (const spec of process.argv.slice(2)) {
  const [id, al, ap] = spec.split(':');
  const o = (cards[id] || {}).o;
  if (!o || !o.tracking_url) { console.log(`${spec}: no tracking_url in the card`); continue; }
  const u = new URL(o.tracking_url);
  u.searchParams.delete('al'); u.searchParams.delete('ap');
  if (al) u.searchParams.set('al', al);
  if (ap) u.searchParams.set('ap', ap);
  const mark = `ZQM${id}`;
  u.searchParams.set('subid', mark + 'a'); u.searchParams.set('subacc', mark + 'b'); u.searchParams.set('subacc2', mark + 'c');
  const land = (o._lands || []).find((x) => String(x.id) === al), pre = (o._prelands || []).find((x) => String(x.id) === ap);
  const want = (ap && ap !== '-1') ? code(pre) : code(land);   // ap=-1 is «No prelanding» of the offer page; with no ap at all the account's saved pre-lander is used
  const page = await ctx.newPage();
  await page.goto(u.toString(), { waitUntil: 'load', timeout: 60000 }).catch((e) => console.log('  goto err', String(e).slice(0, 100)));
  await page.waitForTimeout(3500);
  const got = await page.evaluate(() => {
    const h = (n) => { const e = document.querySelector(`input[name="${n}"]`); return e ? e.value : null; };
    return { tpl: h('template_name'), al: h('al'), subid: h('subid'), subacc: h('subacc'), subacc2: h('subacc2'), title: document.title, words: (document.body.innerText || '').split(/\s+/).length, host: location.host, path: location.pathname.replace(/\/[A-Za-z0-9]{8,}\//, '/<x>/') };
  }).catch(() => ({}));
  const ok = want && got.tpl === want;
  console.log(`${spec} ${o.name}: ${ok ? 'PASS' : 'FAIL'} | expected template ${want} got ${got.tpl} | al ${got.al} | ${got.host}${got.path} | "${(got.title || '').slice(0, 40)}" ${got.words} words | labels: subid ${got.subid === mark + 'a'}, subacc ${got.subacc === mark + 'b'}, subacc2 ${got.subacc2 === mark + 'c'}`);
  await page.close();
}
await browser.close();
