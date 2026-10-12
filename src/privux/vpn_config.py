"""Strict WireGuard profile parser; imported files never execute shell hooks."""
import base64
import ipaddress
import re


def key(value):
    try:
        if len(base64.b64decode(value, validate=True)) != 32:
            raise ValueError()
    except Exception:
        raise ValueError("Clau WireGuard no vàlida") from None
    return value


def endpoint(value):
    # Numeric endpoints make the firewall deterministic, without pre-tunnel DNS.
    match = re.fullmatch(r'(\[[0-9a-fA-F:]+\]|[0-9.]+):([0-9]+)', value)
    if not match:
        raise ValueError("Endpoint: utilitza una IP numèrica i un port (IP:51820)")
    addr = ipaddress.ip_address(match[1].strip('[]'))
    port = int(match[2])
    if not 1 <= port <= 65535:
        raise ValueError("Port no vàlid")
    return str(addr), port


def parse(text):
    if len(text.encode()) > 16384:
        raise ValueError("Configuració massa gran")
    sections = {'Interface': {}, 'Peer': {}}
    current = None
    seen = set()
    allowed = {'Interface': {'PrivateKey', 'Address', 'DNS', 'MTU'},
               'Peer': {'PublicKey', 'PresharedKey', 'Endpoint', 'AllowedIPs', 'PersistentKeepalive'}}
    for line in text.splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        if line.startswith('['):
            current = line.strip('[]')
            if current not in sections or current in seen or line != '[' + current + ']':
                raise ValueError("Cal una Interface i un únic Peer")
            seen.add(current)
            continue
        if current is None or '=' not in line:
            raise ValueError("Format .conf no vàlid")
        name, value = (x.strip() for x in line.split('=', 1))
        if name not in allowed[current] or name in sections[current] or not value:
            raise ValueError("Opció no admesa o duplicada: " + name)
        sections[current][name] = value
    for section, names in [('Interface', ['PrivateKey', 'Address', 'DNS']),
                           ('Peer', ['PublicKey', 'Endpoint', 'AllowedIPs'])]:
        if any(n not in sections[section] for n in names):
            raise ValueError("Falten opcions obligatòries a " + section)
    for section, name in [('Interface', 'PrivateKey'), ('Peer', 'PublicKey'), ('Peer', 'PresharedKey')]:
        if name in sections[section]:
            key(sections[section][name])
    for section, name, parser in [('Interface', 'Address', ipaddress.ip_interface),
                                  ('Interface', 'DNS', ipaddress.ip_address),
                                  ('Peer', 'AllowedIPs', lambda x: ipaddress.ip_network(x, strict=False))]:
        values = [str(parser(x.strip())) for x in sections[section][name].split(',')]
        sections[section][name] = ', '.join(values)
    # This first client is a privacy VPN, not a split-tunnel network manager.
    if set(sections['Peer']['AllowedIPs'].split(', ')) != {'0.0.0.0/0', '::/0'}:
        raise ValueError("Aquesta versió requereix AllowedIPs = 0.0.0.0/0, ::/0")
    endpoint(sections['Peer']['Endpoint'])
    for section, name, minimum, maximum in [('Interface', 'MTU', 1280, 1500),
                                           ('Peer', 'PersistentKeepalive', 0, 65535)]:
        if name in sections[section]:
            value = sections[section][name]
            if not value.isdecimal() or not minimum <= int(value) <= maximum:
                raise ValueError("Valor no vàlid: " + name)
    return sections


def render(sections):
    return '\n\n'.join('[' + s + ']\n' + '\n'.join(k + ' = ' + v for k, v in values.items())
                       for s, values in sections.items()) + '\n'


def firewall(peer_endpoint=None):
    extra = ''
    if peer_endpoint:
        addr, port = endpoint(peer_endpoint)
        family = 'ip6' if ':' in addr else 'ip'
        # Mark is assigned to WireGuard's outer packets, not arbitrary UDP.
        extra = f'        meta mark 51821 {family} daddr {addr} udp dport {port} accept\n'
    return '''table inet privux_vpn
delete table inet privux_vpn
table inet privux_vpn {
    chain output {
        type filter hook output priority -50; policy drop;
        oifname "lo" accept
        oifname "pvpn" accept
        udp sport 68 udp dport 67 ip daddr 255.255.255.255 accept
        ip6 daddr fe80::/10 icmpv6 type { nd-neighbor-solicit, nd-neighbor-advert } accept
        ip6 daddr ff02::/16 icmpv6 type { nd-router-solicit, nd-neighbor-solicit, nd-neighbor-advert } accept
''' + extra + '''    }
    chain forward {
        type filter hook forward priority -50; policy drop;
    }
}
'''
