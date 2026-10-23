// Aray login in the Vision profile: https://aray.com/login (fields `email` and `password`, button "Sign in").
// POST /auth/login sits behind a Cloudflare managed challenge: headless Chromium from the sandbox never gets past «Just a moment...»
// (the sandbox proxy even refuses challenges.cloudflare.com), the real Chrome of the Vision profile passes it in a few seconds.
//   node ~/.claude/skills/secrets/vault.mjs exec aray -- node aray_login.mjs
import { connect, OUT } from './vision_cdp.mjs';

if (!process.env.ARAY_EMAIL || !process.env.ARAY_PASSWORD) { console.error('run through: vault.mjs exec aray -- node aray_login.mjs'); process.exit(1); }
const { browser, ctx } = await connect();
const page = await ctx.newPage();
const codes = [];
page.on('response', (r) => { if (/aray\.com\/(auth|api)\//.test(r.url())) codes.push(`${r.status()} ${r.request().method()} ${r.url().replace('https://aray.com', '').slice(0, 60)}`); });
await page.goto('https://aray.com/login', { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
await page.waitForTimeout(7000);
await page.locator('input[name=email]').first().fill(process.env.ARAY_EMAIL);
await page.locator('input[name=password]').first().fill(process.env.ARAY_PASSWORD);
await page.waitForTimeout(1500);
await page.getByRole('button', { name: /sign in/i }).first().click({ timeout: 15000 });
await page.waitForTimeout(20000);
console.log('url:', page.url(), '| title:', await page.title().catch(() => '?'));
console.log('requests:', codes.slice(-6).join(' | '));
await page.screenshot({ path: `${OUT}/aray_after_login.png` });
await browser.close();   // the tab stays open in the profile: aray_offers.mjs looks for a tab on aray.com
