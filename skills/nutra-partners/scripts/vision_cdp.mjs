// Shared by the Dr.Cash / Aray scripts: attach to a RUNNING Vision profile over CDP with Playwright.
//   VISION_CDP_PORT  the port printed by `vision.sh start ...` (it changes on every start)
//   VISION_HOST      tailnet address of vision-box (default 100.110.129.11)
//   OUT_DIR          where screenshots and dumps are written (default the current directory)
// Playwright lives in /opt/node-tools (not /node-tools).
import pw from '/opt/node-tools/node_modules/playwright-core/index.js';

export const OUT = process.env.OUT_DIR || '.';

export async function connect() {
  const port = process.env.VISION_CDP_PORT;
  if (!port) throw new Error('set VISION_CDP_PORT to the port printed by vision.sh start');
  const host = process.env.VISION_HOST || '100.110.129.11';
  const browser = await pw.chromium.connectOverCDP(`http://${host}:${port}`);
  return { browser, ctx: browser.contexts()[0] };
}

// Visible text of an HTML page: no scripts, no styles, no tags.
export const strip = (html) => html.replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<style[\s\S]*?<\/style>/gi, ' ')
  .replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
