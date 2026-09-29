"""Run a loopback-only media proxy and a private outbound tunnel on macOS."""
import os
import fcntl
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / 'runtime'


def main():
    os.umask(0o077)
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    lock = (RUNTIME / 'run.lock').open('w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('El proxy ya está ejecutándose.')
    binaries = {name: shutil.which(name) for name in ('squid', 'wstunnel', 'cloudflared')}
    if not all(binaries.values()):
        raise SystemExit('Instala primero: brew install squid wstunnel cloudflared')
    token_file = RUNTIME / 'tunnel-key.txt'
    if not token_file.exists():
        token_file.write_text(secrets.token_hex(32))
    token = token_file.read_text().strip()
    if not re.fullmatch(r'[a-f0-9]{64}', token):
        raise SystemExit('La clave local no tiene el formato esperado.')
    conf = RUNTIME / 'squid.conf'
    conf.write_text(f'''http_port 127.0.0.1:13128
visible_hostname descargador-mac
pid_filename {RUNTIME / 'squid.pid'}
acl local_client src 127.0.0.1/32
acl CONNECT method CONNECT
acl SSL_ports port 443
acl private_dst dst 0.0.0.0/8 10.0.0.0/8 100.64.0.0/10 127.0.0.0/8 169.254.0.0/16 172.16.0.0/12 192.168.0.0/16 224.0.0.0/4 240.0.0.0/4
acl private_v6 dst ::/128 ::1/128 fc00::/7 fe80::/10 ff00::/8
acl permitted_sites dstdomain .youtube.com .youtu.be .googlevideo.com .ytimg.com .youtube-nocookie.com .soundcloud.com .sndcdn.com
http_access deny !local_client
http_access deny !CONNECT
http_access deny !SSL_ports
http_access deny private_dst
http_access deny private_v6
http_access deny !permitted_sites
http_access allow local_client
http_access deny all
cache deny all
cache_store_log none
access_log none
cache_log {RUNTIME / 'squid-cache.log'}
logfile_rotate 0
shutdown_lifetime 1 seconds
''')
    children = []
    logs = []
    def stop(*_):
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for log in logs:
            log.close()
    def spawn(name, args, env=None):
        log = (RUNTIME / f'{name}.log').open('w')
        logs.append(log)
        child = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, env=env)
        children.append(child)
        return child
    def interrupted(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        spawn('squid', [binaries['squid'], '-N', '-f', str(conf)])
        env = dict(os.environ, NO_COLOR='true', WSTUNNEL_RESTRICT_HTTP_UPGRADE_PATH_PREFIX=token)
        spawn('wstunnel', [binaries['wstunnel'], '--log-lvl', 'off', 'server', '--restrict-to', '127.0.0.1:13128', 'ws://127.0.0.1:18080'], env)
        # Force HTTP/2 for cloudflared's own transport if UDP is unavailable.
        spawn('cloudflared', [binaries['cloudflared'], 'tunnel', '--no-autoupdate', '--protocol', 'http2', '--url', 'http://127.0.0.1:18080'])
        published = False
        print('Iniciando proxy privado en 127.0.0.1:13128...', flush=True)
        while True:
            if any(child.poll() is not None for child in children):
                raise RuntimeError('Un componente se detuvo. Consulta proxy/mac/runtime/*.log')
            if not published:
                content = (RUNTIME / 'cloudflared.log').read_text()
                match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', content)
                if match:
                    url = match[0].replace('https://', 'wss://')
                    (RUNTIME / 'render.env').write_text(
                        f'MAC_TUNNEL_URL={url}\nWSTUNNEL_HTTP_UPGRADE_PATH_PREFIX={token}\nYTDLP_PROXY=http://127.0.0.1:13128\n')
                    (RUNTIME / 'tunnel-url.txt').write_text(url)
                    print('Túnel creado. Configuración privada guardada en proxy/mac/runtime/render.env', flush=True)
                    published = True
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop()


if __name__ == '__main__':
    main()
