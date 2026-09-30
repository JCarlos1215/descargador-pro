"""Restricted Squid behind an authenticated WebSocket tunnel and platform TLS."""
import os
import re
import signal
import socket
import subprocess
import time


def tunnel_token(env):
    token = env.get('WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX') or env.get('WSTUNNEL_RESTRICT_HTTP_UPGRADE_PATH_PREFIX', '')
    if not re.fullmatch(r'[a-f0-9]{64}', token):
        raise SystemExit('Configure a 64-character hexadecimal WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX.')
    return token


def wstunnel_environment(env):
    child_env = dict(env, NO_COLOR='true')
    child_env.pop('WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX', None)
    child_env['WSTUNNEL_RESTRICT_HTTP_UPGRADE_PATH_PREFIX'] = tunnel_token(env)
    return child_env


def main():
    tunnel_token(os.environ)
    port = int(os.environ.get('PORT', '8080'))
    if not 1024 <= port <= 65535:
        raise SystemExit('PORT must be between 1024 and 65535.')
    children = []

    def interrupted(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        squid = subprocess.Popen(['squid', '-N', '-f', '/app/squid.conf'])
        children.append(squid)
        for _ in range(100):
            if squid.poll() is not None:
                raise RuntimeError('Squid failed to start.')
            try:
                with socket.create_connection(('127.0.0.1', 13128), timeout=.2):
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError('Squid startup timed out.')
        children.append(subprocess.Popen([
            'wstunnel', '--log-lvl', 'off', 'server',
            '--restrict-to', '127.0.0.1:13128', f'ws://0.0.0.0:{port}',
        ], env=wstunnel_environment(os.environ)))
        print('Private cloud proxy started.', flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(.5)
        raise RuntimeError('A proxy component stopped.')
    except KeyboardInterrupt:
        pass
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    main()
