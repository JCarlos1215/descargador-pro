"""Check the public tunnel without printing its authentication key."""
import os
from pathlib import Path
import socket
import subprocess
import time

root = Path(__file__).resolve().parent / 'runtime'
url = (root / 'tunnel-url.txt').read_text().strip()
token = (root / 'tunnel-key.txt').read_text().strip()

for label, key in [('authorized', token), ('unauthorized', 'invalid-key')]:
    env = dict(os.environ, NO_COLOR='true', WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX=key)
    client = subprocess.Popen(['wstunnel', '--log-lvl', 'off', 'client', '--tls-verify-certificate', '-L', 'tcp://127.0.0.1:13129:127.0.0.1:13128', url], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                with socket.create_connection(('127.0.0.1', 13129), timeout=.1):
                    break
            except OSError:
                if client.poll() is not None:
                    raise RuntimeError('Tunnel client failed to start')
                time.sleep(.1)
        result = subprocess.run(['curl', '--max-time', '20', '-x', 'http://127.0.0.1:13129', '-sS', '-o', '/dev/null', '-w', '%{http_code}', 'https://www.youtube.com/robots.txt'], capture_output=True, text=True)
        success = result.returncode == 0 and result.stdout == '200'
        if success != (label == 'authorized'):
            raise RuntimeError(f'{label}: unexpected result (curl={result.returncode}, HTTP={result.stdout})')
        print(f'{label}: PASS', flush=True)
    finally:
        client.terminate()
        client.wait(timeout=10)
