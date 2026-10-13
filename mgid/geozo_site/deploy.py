"""Put the /dom/ pages and the nginx relay for block-click conversions on the Inferno server.

    python3 deploy.py static [--stage DIR] [--route dom|dom2]
                                             # build output of one variant -> /var/www/arcadiablog.com/<route>/ (nothing else
                                             # is touched; dom is the variant MGID approved, deploy it only to restore it)
    python3 deploy.py nginx                  # relay location /dom/lead + log format, with backup, nginx -t, reload
    python3 deploy.py check                  # read-only: what is on the server now

Needs `tailscale ssh` to root@100.121.239.113 (TS_BIN / TS_SOCK override the binary and the socket; the session's
userspace daemon lives in /tmp/claude-0/ts, see the inferno skill).

The relay (13.10): the page calls GET /dom/lead?c=<MGID click id> on a real click on a Geozo block; nginx calls
https://a.mgid.com/postback?c=<click id>&e=geozoclick&r=0.01 itself. e and r are fixed in the config, the click id
must match [A-Za-z0-9_.-]{6,128}, anything else gets 204. Every call is written to /var/log/nginx/arcadiablog.dom.log
with MGID's HTTP status (up=), so the first-party count of signals can be set against MGID's report and Geozo's clicks.
"""
import base64
import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOST = "root@100.121.239.113"
TS_BIN = os.environ.get("TS_BIN", "/tmp/claude-0/ts/tailscale_1.104.1_amd64/tailscale")
TS_SOCK = os.environ.get("TS_SOCK", "/tmp/claude-0/ts/ts.sock")
WEB_ROOT = "/var/www/arcadiablog.com"
WEB = WEB_ROOT + "/dom"
SITE_CONF = "/etc/nginx/sites-available/arcadiablog.com"
LOGFMT_CONF = "/etc/nginx/conf.d/arcadia-dom.conf"

LOGFMT = ('log_format arcadia_dom \'$remote_addr [$time_iso8601] "$request_uri" st=$status up=$upstream_status '
          'ut=$upstream_response_time cc=$http_cf_ipcountry ref="$http_referer" ua="$http_user_agent"\';\n')

LOCATION = r"""
    # dom: MGID -> статьи для Казахстана; клик по рекламному блоку Geozo = конверсия цели geozoclick в MGID.
    # Страница шлёт GET /dom/lead?c=<click id MGID>; postback в MGID делает nginx, e и r зафиксированы здесь.
    location = /dom/lead {
        access_log /var/log/nginx/arcadiablog.dom.log arcadia_dom;
        add_header Cache-Control "no-store" always;
        if ($arg_c !~ "^[A-Za-z0-9_.-]{6,128}$") { return 204; }
        resolver 1.1.1.1 8.8.8.8 valid=300s ipv6=off;
        resolver_timeout 3s;
        proxy_pass https://a.mgid.com/postback?c=$arg_c&e=geozoclick&r=0.01;
        proxy_ssl_server_name on;
        proxy_http_version 1.1;
        proxy_set_header Host a.mgid.com;
        proxy_set_header Connection "";
        proxy_set_header Cookie "";
        proxy_set_header User-Agent "arcadia-relay/1.0";
        proxy_connect_timeout 3s;
        proxy_read_timeout 5s;
    }
"""


def ssh(cmd, stdin=None, timeout=240):
    r = subprocess.run([TS_BIN, "--socket", TS_SOCK, "ssh", HOST, cmd], input=stdin, capture_output=True,
                       text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


def static(stage, route="dom"):
    src = Path(stage) / route
    if not (src / "index.html").exists():
        raise SystemExit(f"нет сборки в {src}: сначала python3 build.py --out {stage}")
    web = f"{WEB_ROOT}/{route}"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        t.add(src, arcname=route)
    b64 = base64.b64encode(buf.getvalue()).decode()
    new_js = next(p.name for p in src.glob(f"{route}.*.js"))
    script = f"""set -e
rm -rf /tmp/{route}_stage && mkdir -p /tmp/{route}_stage
base64 -d | tar -xz -C /tmp/{route}_stage
install -d -o www-data -g www-data -m 755 {web} {web}/img
for f in /tmp/{route}_stage/{route}/*; do [ -f "$f" ] && install -o www-data -g www-data -m 644 "$f" {web}/; done
for f in /tmp/{route}_stage/{route}/img/*; do install -o www-data -g www-data -m 644 "$f" {web}/img/; done
for f in {web}/{route}.*.js; do [ "$(basename $f)" = "{new_js}" ] || rm -f "$f"; done
rm -rf /tmp/{route}_stage
ls -la {web} {web}/img
"""
    code, out = ssh(f"bash -c {shell_quote(script)}", stdin=b64)
    print(out)
    return code


def shell_quote(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def nginx():
    patch = f"""set -e
mkdir -p /root/backups
TS=$(date -u +%Y%m%d-%H%M%S)
cp -p {SITE_CONF} /root/backups/arcadiablog.com.nginx.bak-dom-$TS
[ -f {LOGFMT_CONF} ] || cat > {LOGFMT_CONF} <<'EOF'
{LOGFMT}EOF
if ! grep -q 'location = /dom/lead' {SITE_CONF}; then
python3 - <<'PY'
p = "{SITE_CONF}"
s = open(p, encoding="utf-8").read()
loc = {LOCATION!r}
marker = "    location / {{"
assert s.count(marker) == 1, "marker location / not unique"
open(p, "w", encoding="utf-8").write(s.replace(marker, loc.lstrip("\\n") + "\\n" + marker))
PY
fi
if nginx -t 2>/tmp/nginx_t.out; then
  systemctl reload nginx && echo "nginx перечитан"
else
  cat /tmp/nginx_t.out
  cp -p /root/backups/arcadiablog.com.nginx.bak-dom-$TS {SITE_CONF}
  echo "nginx -t не прошёл, конфиг возвращён из бэкапа"; exit 1
fi
grep -n -A3 'location = /dom/lead' {SITE_CONF} | head -8
"""
    code, out = ssh(f"bash -c {shell_quote(patch)}")
    print(out)
    return code


def check():
    code, out = ssh(f"ls -la {WEB} {WEB_ROOT}/dom2 2>&1 | head -24; echo ---; grep -c 'location = /dom/lead' {SITE_CONF}; "
                    f"ls -la {LOGFMT_CONF} /var/log/nginx/arcadiablog.dom.log 2>&1 | head; echo ---; "
                    "tail -n 5 /var/log/nginx/arcadiablog.dom.log 2>/dev/null")
    print(out)
    return code


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    stage = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "/tmp/dom_stage_build"
    route = sys.argv[sys.argv.index("--route") + 1] if "--route" in sys.argv else "dom"
    if route not in ("dom", "dom2"):
        raise SystemExit("--route: dom или dom2")
    sys.exit({"static": lambda: static(stage, route), "nginx": nginx, "check": check}[cmd]())
