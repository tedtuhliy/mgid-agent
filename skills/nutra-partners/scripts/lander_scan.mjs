// Static check of a lander (what is in its HTML). No JavaScript is run, so a real visitor can get another variant (AdCombo and Dr.Cash
// landers serve variants), and the grey «18+ Click» placeholders of a moderator's screenshot do NOT show up here: a clean result is
// not a clearance. It counts the signs that got our nutra teasers rejected («Footnotes», «User awareness», «Spoilers», «Malware»)
// and prints the first place where each one sits.
//   node lander_scan.mjs <url> [<url> ...]        # plain fetch from where you run it (the sandbox)
// dr_landers.mjs and aray_offers.mjs use scan() from inside the Vision profile, for hosts the sandbox cannot reach.
import { pathToFileURL } from 'node:url';

export const PATTERNS = {
  medical_disclaimer: /non (è|e') (un )?farmaco|non sono farmaci|integratore alimentare|disclaimer|avvertenz|informativa|footnote|nota legale|not a drug|not intended|results may vary/gi,
  individual_results: /risultati (possono|individuali|variano|non sono garantiti)|può variare|possono variare|individual results/gi,
  testimonials: /recension|testimonian|valutazione dei clienti|feedback|le mie esperienze|ho provato|recenzij|opinion/gi,
  research_claims: /studi |studio |scienz|clinic|ricerca|laborator|universit|testato|ispitivanj|kliničk|trial/gi,
  miracle_promises: /perdere \d+ ?(kg|chili)|elimin[ao] (il )?dolor|guarisc|miracol|garantit|cura (definitiva|completa)|100 ?%/gi,
  shock_words: /morte|miracol|tragedia|ictus|stroke|paraly|cancer|cancro|amput|infarto|dialisi|insopportab/gi,
  urgency: /countdown|offerta scade|offerta finisce|ponuda završava|scade|timer/gi,
};

export function scan(html) {
  const txt = html.replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
  const counts = {}, where = {};
  for (const [k, re] of Object.entries(PATTERNS)) {
    const m = txt.match(re);
    counts[k] = m ? m.length : 0;
    if (m) { const i = txt.indexOf(m[0]); where[k] = txt.slice(Math.max(0, i - 70), i + 110); }
  }
  return {
    bytes: html.length, words: txt.split(' ').length,
    forms: (html.match(/<form/gi) || []).length,
    inputs: (html.match(/<input[^>]*type=["']?(text|tel|phone)/gi) || []).length,
    imgs: (html.match(/<img/gi) || []).length,
    lang: ((html.match(/<html[^>]*lang=["']?([a-zA-Z-]+)/i) || [])[1]) || '?',
    title: ((html.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] || '').replace(/\s+/g, ' ').trim().slice(0, 80),
    counts, where,
    hosts: [...new Set((html.match(/https?:\/\/[a-z0-9.-]+/gi) || []).map((h) => h.replace(/^https?:\/\//, '')))].slice(0, 12),
  };
}

export function show(label, r) {
  const hit = Object.entries(r.counts).filter(([, v]) => v).map(([k, v]) => `${k}:${v}`).join(' ') || 'nothing found';
  console.log(`${label}\n   ${r.bytes}B ${r.words}w forms ${r.forms} inputs ${r.inputs} imgs ${r.imgs} lang ${r.lang} | ${hit}\n   title: ${r.title}\n   hosts: ${r.hosts.join(', ')}`);
  for (const [k, v] of Object.entries(r.where)) if (/shock|research|miracle|testimonials|disclaimer/.test(k)) console.log(`   ${k}: …${v}…`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36';
  for (const u of process.argv.slice(2)) {
    try {
      const r = await fetch(u, { redirect: 'follow', headers: { 'user-agent': UA } });
      show(`${u} -> HTTP ${r.status} ${r.url}`, scan(await r.text()));
    } catch (e) { console.log(`${u}: fetch error ${String(e).slice(0, 120)}`); }
  }
}
