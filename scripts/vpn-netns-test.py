"""Run as root on disposable Linux CI; exercises real wg-quick and nftables.

No user network is changed: all interfaces and firewall rules live in netns.
resolvectl is mocked because netns has no separate systemd-resolved instance.
"""
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def run(*args, input=None, check=True):
    result = subprocess.run(args, input=input, text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(re.sub(r'[A-Za-z0-9+/]{43}=', '[REDACTED]', result.stderr))
    return result


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'backend':
        from privux import vpn_backend as b
        base = Path(sys.argv[2])
        b.BASE, b.STATE, b.ACTIVE = base, base / 'state.json', base / 'pvpn.conf'
        actual = b.run
        def command(tool, *a, **k):
            if tool == 'resolvectl':
                return subprocess.CompletedProcess([], 0, '', '')
            check = k.pop('check', True)
            result = actual(tool, *a, check=False, **k)
            if check and result.returncode:
                raise RuntimeError(re.sub(r'[A-Za-z0-9+/]{43}=', '[REDACTED]', result.stderr))
            return result
        b.run = command
        print(json.dumps(b.execute(sys.argv[3], sys.argv[4:])))
        return
    if os.geteuid() != 0:
        raise RuntimeError('Run as root in disposable Linux')
    suffix = str(os.getpid())
    server, client = 'pvs' + suffix, 'pvc' + suffix
    env_path = str(Path(__file__).resolve().parents[1] / 'src')
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        os.chmod(base, 0o700)
        def ns(name, *args, **kwargs):
            return run('ip', 'netns', 'exec', name, *args, **kwargs)
        def backend(action, *args, input=None):
            return ns(client, 'env', 'PYTHONPATH=' + env_path, 'python3', str(Path(__file__).resolve()),
                      'backend', str(base), action, *args, input=input)
        try:
            run('ip', 'netns', 'add', server)
            run('ip', 'netns', 'add', client)
            run('ip', 'link', 'add', 'pvs0', 'type', 'veth', 'peer', 'name', 'pvc0')
            run('ip', 'link', 'set', 'pvs0', 'netns', server)
            run('ip', 'link', 'set', 'pvc0', 'netns', client)
            for name, interface, ip in [(server, 'pvs0', '192.0.2.1/24'), (client, 'pvc0', '192.0.2.2/24')]:
                ns(name, 'ip', 'link', 'set', 'lo', 'up')
                ns(name, 'ip', 'addr', 'add', ip, 'dev', interface)
                ns(name, 'ip', '-6', 'addr', 'add', '2001:db8::' + ('1' if name == server else '2') + '/64', 'dev', interface, 'nodad')
                ns(name, 'ip', 'link', 'set', interface, 'up')
            ns(client, 'ip', 'route', 'add', 'default', 'via', '192.0.2.1')
            ns(client, 'ip', '-6', 'route', 'add', 'default', 'via', '2001:db8::1')
            keys = [run('wg', 'genkey').stdout.strip() for _ in range(2)]
            pubs = [run('wg', 'pubkey', input=k).stdout.strip() for k in keys]
            config = base / 'server.conf'
            config.write_text(f'[Interface]\nPrivateKey = {keys[0]}\nListenPort = 51820\n[Peer]\nPublicKey = {pubs[1]}\nAllowedIPs = 10.77.0.2/32\n')
            ns(server, 'ip', 'link', 'add', 'srvwg', 'type', 'wireguard')
            ns(server, 'wg', 'setconf', 'srvwg', str(config))
            ns(server, 'ip', 'addr', 'add', '10.77.0.1/24', 'dev', 'srvwg')
            ns(server, 'ip', 'link', 'set', 'srvwg', 'up')
            conf = f'[Interface]\nPrivateKey = {keys[1]}\nAddress = 10.77.0.2/32\nDNS = 9.9.9.9\n[Peer]\nPublicKey = {pubs[0]}\nEndpoint = 192.0.2.1:51820\nAllowedIPs = 0.0.0.0/0, ::/0\nPersistentKeepalive = 25\n'
            backend('import', 'lab', input=conf)
            ns(client, 'ping', '-c', '1', '-W', '2', '192.0.2.1')
            backend('kill-switch', 'on')
            assert ns(client, 'ping', '-c', '1', '-W', '1', '192.0.2.1', check=False).returncode != 0, 'IPv4 leak'
            assert ns(client, 'ping', '-6', '-c', '1', '-W', '1', '2001:db8::1', check=False).returncode != 0, 'IPv6 leak'
            backend('connect', 'lab')
            ns(client, 'ping', '-c', '2', '-W', '3', '10.77.0.1')
            state = json.loads(backend('status').stdout)
            assert state['handshake_age'] is not None and state['handshake_age'] < 10, 'No handshake'
            # A dropped VPN interface must never restore the physical default route.
            ns(client, 'ip', 'link', 'set', 'pvpn', 'down')
            assert ns(client, 'ping', '-I', 'pvc0', '-c', '1', '-W', '1', '192.0.2.1', check=False).returncode != 0, 'Leak on failure'
            backend('disconnect')
            backend('restore')
            assert ns(client, 'ping', '-c', '1', '-W', '1', '192.0.2.1', check=False).returncode != 0, 'Leak after restore'
            backend('kill-switch', 'off')
            ns(client, 'ping', '-c', '1', '-W', '2', '192.0.2.1')
            print('PASS: handshake, encrypted ping, IPv4/IPv6 block, interface failure, restore, recovery')
        finally:
            for name in [client, server]:
                run('ip', 'netns', 'delete', name, check=False)


if __name__ == '__main__':
    main()
