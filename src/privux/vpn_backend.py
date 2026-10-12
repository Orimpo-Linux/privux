"""Small root backend. Fixed paths, validated profiles, no shell execution."""
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

from .vpn_config import parse, render, firewall

BASE = Path('/etc/privux/vpn')
STATE = BASE / 'state.json'
ACTIVE = Path('/etc/wireguard/pvpn.conf')
BIN = {'wg': '/usr/bin/wg', 'wg-quick': '/usr/bin/wg-quick',
       'nft': '/usr/sbin/nft', 'resolvectl': '/usr/bin/resolvectl'}


def run(tool, *args, input=None, check=True):
    result = subprocess.run([BIN[tool], *args], input=input, text=True,
                            capture_output=True, timeout=35,
                            env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C'})
    if check and result.returncode:
        # wg-quick traces commands, potentially including sensitive config.
        raise RuntimeError(f'{tool}: ordre fallida ({result.returncode}); revisa el sistema')
    return result


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def profile(name):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,32}', name):
        raise ValueError('Nom: 1–32 lletres, números, guió o guió baix')
    return BASE / (name + '.conf')


def read_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {'kill_switch': False, 'selected': None}


def up():
    return run('wg', 'show', 'pvpn', 'public-key', check=False).returncode == 0


def set_firewall(enabled, endpoint=None):
    if enabled:
        run('nft', '-f', '-', input=firewall(endpoint))
    else:
        run('nft', '-f', '-', input='table inet privux_vpn\ndelete table inet privux_vpn\n')


def disconnect():
    if up():
        run('wg-quick', 'down', str(ACTIVE))


def status(state):
    active = up()
    handshakes = run('wg', 'show', 'pvpn', 'latest-handshakes', check=False).stdout.splitlines() if active else []
    stamps = [int(x.split()[-1]) for x in handshakes if x.split()]
    last = max(stamps, default=0)
    protected = run('nft', 'list', 'table', 'inet', 'privux_vpn', check=False).returncode == 0
    return {**state, 'profiles': sorted(x.stem for x in BASE.glob('*.conf')),
            'interface_up': active, 'handshake_age': int(time.time()) - last if last else None,
            'kill_switch_active': protected}


def execute(action, args):
    state = read_state()
    if action == 'import' and len(args) == 1:
        path = profile(args[0])
        if path.exists():
            raise ValueError('Aquest perfil ja existeix; utilitza un altre nom')
        config = parse(sys.stdin.read(16385))
        write(path, render(config))
    elif action == 'connect' and len(args) == 1:
        config = parse(profile(args[0]).read_text())
        if up():
            raise ValueError('Desconnecta abans de canviar el servidor')
        # Persist intent before touching network; reboot will fail closed.
        state['selected'] = args[0]
        write(STATE, json.dumps(state))
        set_firewall(state['kill_switch'], config['Peer']['Endpoint'])
        # DNS is installed through resolved, no resolvconf or imported hooks.
        dns = config['Interface'].pop('DNS').split(', ')
        config['Interface']['FwMark'] = '51821'
        write(ACTIVE, render(config))
        try:
            run('wg-quick', 'up', str(ACTIVE))
            run('resolvectl', 'dns', 'pvpn', *dns)
            run('resolvectl', 'domain', 'pvpn', '~.')
            run('resolvectl', 'default-route', 'pvpn', 'yes')
            # External profiles supply plain DNS; override global DoT for this link.
            run('resolvectl', 'dnsovertls', 'pvpn', 'no')
        except Exception:
            disconnect()
            raise
    elif action == 'disconnect' and not args:
        disconnect()
        set_firewall(state['kill_switch'])
    elif action == 'kill-switch' and args in [['on'], ['off']]:
        state['kill_switch'] = args[0] == 'on'
        if state['kill_switch']:
            write(STATE, json.dumps(state))
        selected = state.get('selected')
        ep = parse(profile(selected).read_text())['Peer']['Endpoint'] if selected and up() else None
        set_firewall(state['kill_switch'], ep)
        write(STATE, json.dumps(state))
    elif action == 'restore' and not args:
        # Restore blocking only: never autoconnect a VPN at boot.
        set_firewall(state['kill_switch'])
    elif action != 'status' or args:
        raise ValueError('Ordre VPN no vàlida')
    return status(state)


def main():
    try:
        if os.geteuid() != 0:
            raise PermissionError('Cal autenticació d’administrador')
        os.umask(0o077)
        BASE.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(BASE, 0o700)
        with (BASE / 'lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = execute(sys.argv[1] if len(sys.argv) > 1 else 'status', sys.argv[2:])
        print(json.dumps(data))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(json.dumps({'error': str(error)}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
