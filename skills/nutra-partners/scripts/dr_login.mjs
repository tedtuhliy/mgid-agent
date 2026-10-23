// Dr.Cash login in the Vision profile. The login page is https://dr.cash/sign-in/ (e-mail + password, the button is "Enter Dashboard");
// the cabinet is then https://affiliate.dr.cash (SPA). `partners.dr.cash`, the host in the old vault note, does NOT resolve.
// No captcha showed up on 23.10 from the Vision browser.
//   node ~/.claude/skills/secrets/vault.mjs exec drcash -- node dr_login.mjs
// The session stays in the profile; the next scripts (dr_lib.mjs) only need the tab and replay the page's own API headers.
import { connect, OUT } from './vision_cdp.mjs';

if (!process.env.DRCASH_EMAIL || !process.env.DRCASH_PASSWORD) { console.error('run through: vault.mjs exec drcash -- node dr_login.mjs'); process.exit(1); }
const { browser, ctx } = await connect();
const page = await ctx.newPage();
await page.goto('https://dr.cash/sign-in/', { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(8000);
const email = page.locator('input[type=email], input[name=email], input[placeholder*=mail i]').first();
const pass = page.locator('input[type=password]').first();
if (!(await email.count()) || !(await pass.count())) { console.log('no e-mail/password form here, url:', page.url()); await browser.close(); process.exit(1); }
await email.click(); await email.fill(process.env.DRCASH_EMAIL);
await pass.click(); await pass.fill(process.env.DRCASH_PASSWORD);
await page.waitForTimeout(800);
await page.getByRole('button', { name: /enter dashboard|log in|sign in|login|войти/i }).first().click({ timeout: 15000 });
await page.waitForTimeout(15000);
console.log('url:', page.url(), '| title:', await page.title().catch(() => '?'));
const txt = (await page.evaluate(() => document.body.innerText).catch(() => '')).replace(/\s+/g, ' ');
console.log('page text (head):', txt.slice(0, 300));
await page.screenshot({ path: `${OUT}/dr_after_login.png` });
await browser.close();
