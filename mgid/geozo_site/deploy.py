"""Put the /dom/ pages and the nginx relay for block-click conversions on the Inferno server.

    python3 deploy.py static [--stage DIR] [--route dom|dom2|blog] [--full]
                                             # build output of one route -> /var/www/arcadiablog.com/<route>/ (nothing else
                                             # is touched; dom is the variant MGID approved, deploy it only to restore it;
                                             # blog is the multilingual site of build_multi.py, /blog/<lang>/)
    python3 deploy.py nginx                  # relay location /dom/lead + log format, with backup, nginx -t, reload;
                                             # and the e-book download /blog/dl/<lang>.pdf with the MGID postback mirror
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
sys.path.insert(0, str(HERE))
import multi_config as mc  # noqa: E402

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


BOOK_LOCATION = r"""
    # blog: free e-book (PDF). A download with an MGID click id (?click_id=<32 hex>, put there by the page script) is a
    # conversion of the goal «E-book download» (event ebook): the mirror sub-request tells a.mgid.com/postback while the
    # visitor gets the file. No click id, no signal. The log line carries MGID's status (up=) of the postback.
    location ~ "^/blog/dl/(?<bl>@@LANGS@@)\.pdf$" {
        access_log /var/log/nginx/arcadiablog.dom.log arcadia_dom;
        mirror /_ebook_pb;
        mirror_request_body off;
        add_header Cache-Control "private, no-store" always;
        add_header Content-Disposition 'attachment; filename="arcadia-blog-$bl.pdf"' always;
        add_header X-Robots-Tag "noindex" always;
        rewrite ^ /blog/ebook/$bl.pdf break;
    }
    location = /_ebook_pb {
        internal;
        access_log /var/log/nginx/arcadiablog.dom.log arcadia_dom;
        log_subrequest on;
        if ($arg_click_id !~ "^[A-Za-z0-9_.-]{6,128}$") { return 204; }
        resolver 1.1.1.1 8.8.8.8 valid=300s ipv6=off;
        resolver_timeout 3s;
        proxy_pass https://a.mgid.com/postback?c=$arg_click_id&e=ebook&r=0.05;
        proxy_ssl_server_name on;
        proxy_http_version 1.1;
        proxy_set_header Host a.mgid.com;
        proxy_set_header Connection "";
        proxy_set_header Cookie "";
        proxy_set_header User-Agent "arcadia-relay/1.0";
        proxy_connect_timeout 3s;
        proxy_read_timeout 5s;
    }
""".replace("@@LANGS@@", "|".join(sorted(list(mc.LANGS) + list(mc.DERIVED))))    # only the languages that have a book


BOOK_LOCATION_LINE = [l for l in BOOK_LOCATION.splitlines() if "blog/dl/(?<bl>" in l][0]


def ssh(cmd, stdin=None, timeout=240):
    r = subprocess.run([TS_BIN, "--socket", TS_SOCK, "ssh", HOST, cmd], input=stdin, capture_output=True,
                       text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


def remote_hashes(web):
    code, out = ssh(f"cd {web} 2>/dev/null && find . -type f -print0 | xargs -0 -r sha256sum", timeout=300)
    res = {}
    for line in out.splitlines():
        h, _, rel = line.partition("  ")
        if len(h) == 64 and rel.startswith("./"):
            res[rel[2:]] = h
    return res


def static(stage, route="dom", full=False):
    """Upload the changed files of stage/<route>/ to /var/www/arcadiablog.com/<route>/ (merge, nothing else on the server is
    touched; stale <route>.<hash>.js files of older builds are removed). A file is sent only when its sha256 differs from
    the one on the server (--full sends everything): a build of thirteen languages is 6 MB of HTML and pictures, and the
    tunnel carries about 35 KB/s."""
    import hashlib
    src = Path(stage) / route
    if not (src / "index.html").exists() and route != "blog":
        raise SystemExit(f"нет сборки в {src}: сначала python3 build.py --out {stage}")
    if route == "blog" and not any(src.glob("*/index.html")):
        raise SystemExit(f"нет сборки в {src}: сначала python3 build_multi.py --out {stage}")
    web = f"{WEB_ROOT}/{route}"
    have = {} if full else remote_hashes(web)
    send = []
    for f in sorted(src.rglob("*")):
        if f.is_file():
            rel = f.relative_to(src).as_posix()
            if have.get(rel) != hashlib.sha256(f.read_bytes()).hexdigest():
                send.append((f, rel))
    new_js = next((p.name for p in src.glob(f"{route}.*.js")), None)
    print(f"файлов в сборке {sum(1 for f in src.rglob('*') if f.is_file())}, к отправке {len(send)}, "
          f"{sum(f.stat().st_size for f, _ in send) // 1024} КБ")
    if not send and not new_js:
        return 0
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for f, rel in send:
            t.add(f, arcname=f"{route}/{rel}")
    b64 = base64.b64encode(buf.getvalue()).decode() if send else ""
    cleanup = (f'for f in {web}/{route}.*.js; do [ "$(basename $f)" = "{new_js}" ] || rm -f "$f"; done' if new_js else "true")
    script = f"""set -e
rm -rf /tmp/{route}_stage && mkdir -p /tmp/{route}_stage
{"base64 -d | tar -xz -C /tmp/" + route + "_stage" if send else "true"}
install -d -o www-data -g www-data -m 755 {web}
[ -d /tmp/{route}_stage/{route} ] && cp -a /tmp/{route}_stage/{route}/. {web}/ || true
chown -R www-data:www-data {web}
find {web} -type d -exec chmod 755 {{}} +
find {web} -type f -exec chmod 644 {{}} +
{cleanup}
rm -rf /tmp/{route}_stage
ls {web} | head -30
find {web} -type f | wc -l
"""
    code, out = ssh(f"bash -c {shell_quote(script)}", stdin=b64, timeout=1500)
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
if ! grep -q 'location = /_ebook_pb' {SITE_CONF}; then
python3 - <<'PY'
p = "{SITE_CONF}"
s = open(p, encoding="utf-8").read()
loc = {BOOK_LOCATION!r}
marker = "    location / {{"
assert s.count(marker) == 1, "marker location / not unique"
open(p, "w", encoding="utf-8").write(s.replace(marker, loc.lstrip("\\n") + "\\n" + marker))
PY
fi
python3 - <<'PY'
import re
p = "{SITE_CONF}"
s = open(p, encoding="utf-8").read()
new = {BOOK_LOCATION_LINE!r}
s2 = re.sub(r'    location ~ "\\^/blog/dl/\\(\\?<bl>[^\\n]*\\\\\\.pdf\\$" \\{{', new, s)
if s2 != s:
    open(p, "w", encoding="utf-8").write(s2)
    print("строка location скачивания обновлена")
PY
if nginx -t 2>/tmp/nginx_t.out; then
  systemctl reload nginx && echo "nginx перечитан"
else
  cat /tmp/nginx_t.out
  cp -p /root/backups/arcadiablog.com.nginx.bak-dom-$TS {SITE_CONF}
  echo "nginx -t не прошёл, конфиг возвращён из бэкапа"; exit 1
fi
grep -n -A3 'location = /dom/lead' {SITE_CONF} | head -6
grep -n -A4 'blog/dl/' {SITE_CONF} | head -8
"""
    code, out = ssh(f"bash -c {shell_quote(patch)}")
    print(out)
    return code


def check():
    code, out = ssh(f"ls -la {WEB} {WEB_ROOT}/dom2 {WEB_ROOT}/blog 2>&1 | head -40; echo ---; grep -c 'location = /dom/lead' {SITE_CONF}; "
                    f"ls -la {LOGFMT_CONF} /var/log/nginx/arcadiablog.dom.log 2>&1 | head; echo ---; "
                    "tail -n 5 /var/log/nginx/arcadiablog.dom.log 2>/dev/null")
    print(out)
    return code


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    stage = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "/tmp/dom_stage_build"
    route = sys.argv[sys.argv.index("--route") + 1] if "--route" in sys.argv else "dom"
    if route not in ("dom", "dom2", "blog"):
        raise SystemExit("--route: dom, dom2 или blog")
    sys.exit({"static": lambda: static(stage, route, "--full" in sys.argv), "nginx": nginx, "check": check}[cmd]())
