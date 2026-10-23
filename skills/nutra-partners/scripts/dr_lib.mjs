// Dr.Cash through a logged-in Vision profile. There is no public API key: the cabinet (SPA) calls https://drcash.io/v1/* with an
// Authorization header of its own. We open a cabinet page, take that header from the page's own request and replay every call as a fetch()
// made INSIDE the page. The header is never printed or saved.
//
//   import { withDr } from './dr_lib.mjs';
//   await withDr(async ({ api, page }) => { const r = await api('/v1/offer/32535'); console.log(r.st, r.json.payload.item.name); });
//
// api(path, method = 'GET', body = null) -> { st, json, text }. Logged out -> throws "no auth header captured": run dr_login.mjs first.
import { connect } from './vision_cdp.mjs';

export async function withDr(fn) {
  const { browser, ctx } = await connect();
  const page = ctx.pages().find((p) => /affiliate\.dr\.cash/.test(p.url())) || await ctx.newPage();
  let hdr = null;
  page.on('request', async (r) => {
    if (!hdr && /drcash\.io\/v1\//.test(r.url())) {
      const h = await r.allHeaders();
      if (h.authorization) hdr = { authorization: h.authorization, accept: h.accept || 'application/json', 'content-type': h['content-type'] || 'application/json' };
    }
  });
  await page.goto('https://affiliate.dr.cash/offer?sort_by=rank&sort_type=ASC', { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(2500);
  if (!hdr) { await browser.close(); throw new Error('no auth header captured (logged out? run dr_login.mjs)'); }
  const api = (path, method = 'GET', body = null) => page.evaluate(async ({ path, method, body, hdr }) => {
    const r = await fetch('https://drcash.io' + path, { method, headers: hdr, body: body ? JSON.stringify(body) : undefined });
    const t = await r.text();
    let j = null; try { j = JSON.parse(t); } catch {}
    return { st: r.status, json: j, text: j ? '' : t.slice(0, 300) };
  }, { path, method, body, hdr });
  try { return await fn({ api, page, ctx, browser }); } finally { await browser.close(); }
}
