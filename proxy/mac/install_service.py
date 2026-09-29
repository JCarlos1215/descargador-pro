"""Install the current user's private proxy LaunchAgent."""
import os
from pathlib import Path
import plistlib
import subprocess
import sys

root = Path(__file__).resolve().parent
runtime = root / 'runtime'
runtime.mkdir(mode=0o700, exist_ok=True)
label = 'com.descargadorpro.privateproxy'
agent = Path.home() / 'Library/LaunchAgents' / f'{label}.plist'
agent.parent.mkdir(parents=True, exist_ok=True)
if agent.exists():
    raise SystemExit('El servicio ya existe; revisa su configuración antes de reemplazarlo.')
config = {
    'Label': label,
    'ProgramArguments': ['/usr/bin/caffeinate', '-i', sys.executable, str(root / 'run.py')],
    'WorkingDirectory': str(root.parent.parent),
    'EnvironmentVariables': {'PATH': '/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin'},
    'RunAtLoad': True,
    'KeepAlive': True,
    'ThrottleInterval': 30,
    'StandardOutPath': str(runtime / 'service.log'),
    'StandardErrorPath': str(runtime / 'service-error.log'),
}
with agent.open('wb') as stream:
    plistlib.dump(config, stream)
agent.chmod(0o600)
subprocess.run(['launchctl', 'bootstrap', f'gui/{os.getuid()}', str(agent)], check=True)
print('Servicio de proxy instalado e iniciado.')
