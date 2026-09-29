"""Start the web service and optional private tunnel to the owner's Mac."""
import os
import re
import signal
import socket
import subprocess
import time
from urllib.parse import urlsplit


def tunnel_command(env):
    url = env.get('MAC_TUNNEL_URL', '').strip()
    if not url:
        return None
    parsed = urlsplit(url)
    if (parsed.scheme != 'wss' or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
        raise ValueError('MAC_TUNNEL_URL debe ser una dirección wss válida sin credenciales.')
    key = env.get('WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX', '')
    if not re.fullmatch(r'[a-f0-9]{64}', key):
        raise ValueError('Falta la clave privada válida del túnel de la Mac.')
    return ['wstunnel', '--log-lvl', 'off', 'client', '--tls-verify-certificate',
            '-L', 'tcp://127.0.0.1:13128:127.0.0.1:13128', url]


def main():
    env = dict(os.environ, NO_COLOR='true')
    command = tunnel_command(env)
    children = []
    def interrupt(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    try:
        if command:
            tunnel = subprocess.Popen(command, env=env)
            children.append(tunnel)
            for _ in range(100):
                if tunnel.poll() is not None:
                    raise RuntimeError('No pudo iniciarse el cliente del túnel.')
                try:
                    with socket.create_connection(('127.0.0.1', 13128), timeout=.1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('El cliente del túnel no abrió el puerto local.')
            env['YTDLP_PROXY'] = 'http://127.0.0.1:13128'
            print('Cliente privado de la Mac iniciado.', flush=True)
        children.append(subprocess.Popen([
            'gunicorn', '--bind', f"0.0.0.0:{env.get('PORT', '10000')}",
            '--workers', '1', '--threads', '4', '--timeout', '300',
            '--access-logfile', '-', '--error-logfile', '-', 'app:app'], env=env))
        while all(child.poll() is None for child in children):
            time.sleep(1)
        raise RuntimeError('Un proceso del servicio se detuvo.')
    except KeyboardInterrupt:
        pass
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    main()
