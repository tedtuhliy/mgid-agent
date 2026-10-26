// Deletes every cc-mgid-arcadia-* node that is not connected to control (this session's daemon is stopped), then lists what is left.
// Run through the vault: node vault.mjs exec tailscale -- node ts_cleanup.mjs   (needs TS_API_TOKEN)
const T = process.env.TS_API_TOKEN;
if (!T) { console.error('TS_API_TOKEN is not set (run through vault.mjs exec tailscale)'); process.exit(1); }
const H = { Authorization: 'Bearer ' + T };
const list = async () => {
  const r = await fetch('https://api.tailscale.com/api/v2/tailnet/-/devices?fields=all', { headers: H });
  if (!r.ok) {   // a bad token must not look like "nothing to delete" (on 26.10 TS_API_TOKEN answered 401 «API token invalid» and the first version of this script printed "none left")
    console.error(`Tailscale API answered HTTP ${r.status}: ${(await r.text()).replace(/[A-Za-z0-9_-]{30,}/g, '<tok>').slice(0, 200)}`);
    console.error('The node was NOT deleted. Delete cc-mgid-arcadia-* by hand (admin console, Machines) or put a valid TS_API_TOKEN into the vault service `tailscale`.');
    process.exit(2);
  }
  return (await r.json()).devices || [];
};
for (const m of (await list()).filter((x) => (x.name || '').split('.')[0].startsWith('cc-mgid-arcadia-'))) {
  const host = m.name.split('.')[0];
  if (m.connectedToControl === false) {
    const del = await fetch('https://api.tailscale.com/api/v2/device/' + m.id, { method: 'DELETE', headers: H });
    console.log(`${host}: offline -> deleted, HTTP ${del.status}`);
  } else console.log(`${host}: connected, kept`);
}
await new Promise((r) => setTimeout(r, 4000));
const left = (await list()).filter((x) => (x.name || '').split('.')[0].startsWith('cc-mgid-arcadia-'));
console.log('cc-mgid-arcadia-* nodes left:', left.map((x) => x.name.split('.')[0]).join(', ') || 'none');
