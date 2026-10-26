// Static check of a lander (what is in its HTML). No JavaScript is run, so a real visitor can get another variant (AdCombo and Dr.Cash
// landers serve variants), and the grey «18+ Click» placeholders of a moderator's screenshot do NOT show up here: a clean result is
// not a clearance. It counts the signs that got our nutra teasers rejected («Footnotes», «User awareness», «Spoilers», «Malware»)
// and prints the first place where each one sits.
//   node lander_scan.mjs <url> [<url> ...]        # plain fetch from where you run it (the sandbox)
// dr_landers.mjs and aray_offers.mjs use scan() from inside the Vision profile, for hosts the sandbox cannot reach.
import { pathToFileURL } from 'node:url';

export const PATTERNS = {
  medical_disclaimer: /non (è|e') (un )?farmaco|non sono farmaci|integratore alimentare|disclaimer|avvertenz|informativa|footnote|nota legale|not a drug|not intended|results may vary|aviso legal|descargo|no es un medicamento|no sustituye|resultados (pueden|podr[ií]an) variar|consulte (a su|con su) m[eé]dico/gi,
  individual_results: /risultati (possono|individuali|variano|non sono garantiti)|può variare|possono variare|individual results|resultados (individuales|var[ií]an)/gi,
  testimonials: /recension|testimonian|valutazione dei clienti|feedback|le mie esperienze|ho provato|recenzij|opinion|testimoni|rese[ñn]a|comentari|valoraci[oó]n|mi experiencia|lo prob[eé]/gi,
  research_claims: /studi |studio |scienz|clinic|ricerca|laborator|universit|testato|ispitivanj|kliničk|trial|estudio|cient[ií]fic|cl[ií]nic|investigaci|laboratorio|universidad|comprobad|dermat[oó]log|ortoped|reumat[oó]log/gi,
  miracle_promises: /perdere \d+ ?(kg|chili)|elimin[ao] (il )?dolor|guarisc|miracol|garantit|cura (definitiva|completa)|100 ?%|milagro|garantiz|garant[ií]a|desaparec|sin dolor|cura definitiva|resultados? (inmediat|r[aá]pid|garantizad)/gi,
  shock_words: /morte|miracol|tragedia|ictus|stroke|paraly|cancer|cancro|amput|infarto|dialisi|insopportab|cirug[ií]a|operaci[oó]n|silla de ruedas|par[aá]lisis|invalidez|c[aá]ncer|muerte/gi,
  urgency: /countdown|offerta scade|offerta finisce|ponuda završava|scade|timer|solo hoy|[uú]ltimas unidades|oferta (termina|finaliza)|cuenta regresiva|quedan \d+|\d+ (personas|usuarios) (est[aá]n|viendo)/gi,
  authority: /\bdr\.? |\bdra\.? |doctor|m[eé]dico|especialista|profesor|farmac[eé]utic|reumat/gi,
  fake_news_look: /peri[oó]dico|noticias|reportaje|advertorial|patrocinad|sponsored|entrevista|exclusiv[oa]|urgente/gi,
};

// Things in the HTML that can fail moderation or that the visitor does not expect: scripts, not words.
export function flags(html) {
  const f = [];
  if (/Notification\.requestPermission|serviceWorker\.register|pushnginx|onesignal|pushwoosh|web-?push|pw_subscribing/i.test(html)) f.push('push-подписка');
  if (/history\.pushState|onpopstate|beforeunload/i.test(html)) f.push('перехват «назад»');
  if (/back_url|dbbtn_|dpush_/i.test(html)) f.push('скрипт возврата платформы');
  if (/atob\(|eval\(|document\.write\(unescape|fromCharCode/i.test(html)) f.push('обфускация');
  if (/<iframe/i.test(html)) f.push('iframe');
  return f;
}

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
    counts, where, flags: flags(html),
    hosts: [...new Set((html.match(/https?:\/\/[a-z0-9.-]+/gi) || []).map((h) => h.replace(/^https?:\/\//, '')))].slice(0, 12),
  };
}

export function show(label, r) {
  const hit = Object.entries(r.counts).filter(([, v]) => v).map(([k, v]) => `${k}:${v}`).join(' ') || 'nothing found';
  console.log(`${label}\n   ${r.bytes}B ${r.words}w forms ${r.forms} inputs ${r.inputs} imgs ${r.imgs} lang ${r.lang} | ${hit}\n   title: ${r.title}\n   hosts: ${r.hosts.join(', ')}${r.flags && r.flags.length ? '\n   flags: ' + r.flags.join(', ') : ''}`);
  for (const [k, v] of Object.entries(r.where)) if (/shock|research|miracle|testimonials|disclaimer|authority|fake_news/.test(k)) console.log(`   ${k}: …${v}…`);
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
