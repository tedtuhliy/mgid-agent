// Deletes every cc-mgid-arcadia-* node that is not connected to control (this session's daemon is stopped), then lists what is left.
// Run through the vault: node vault.mjs exec tailscale -- node ts_cleanup.mjs   (needs TS_API_TOKEN)
const T = process.env.TS_API_TOKEN;
if (!T) { console.error('TS_API_TOKEN is not set (run through vault.mjs exec tailscale)'); process.exit(1); }
const H = { Authorization: 'Bearer ' + T };
const list = async () => (await (await fetch('https://api.tailscale.com/api/v2/tailnet/-/devices?fields=all', { headers: H })).json()).devices || [];
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
