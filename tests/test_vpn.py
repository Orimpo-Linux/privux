import base64
import unittest
from privux.vpn_config import parse, render, firewall

KEY = base64.b64encode(bytes(range(32))).decode()
CONF = f'''[Interface]
PrivateKey = {KEY}
Address = 10.77.0.2/32
DNS = 9.9.9.9
[Peer]
PublicKey = {KEY}
Endpoint = 192.0.2.1:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
'''


class ProfileTests(unittest.TestCase):
    def test_roundtrip(self):
        self.assertEqual(parse(CONF), parse(render(parse(CONF))))

    def test_reject_shell_hooks_and_unknown_fields(self):
        for field in ['PreUp', 'PostUp', 'PreDown', 'PostDown', 'SaveConfig', 'Table', 'FwMark']:
            with self.subTest(field=field), self.assertRaises(ValueError):
                parse(CONF.replace('Address =', field + ' = touch /tmp/pwned\nAddress ='))

    def test_reject_duplicates(self):
        with self.assertRaises(ValueError):
            parse(CONF + 'Endpoint = 192.0.2.2:51820\n')
        with self.assertRaises(ValueError):
            parse(CONF + '[Peer]\n')

    def test_reject_invalid_values(self):
        for old, new in [('192.0.2.1:51820', 'example.com:51820'),
                         ('192.0.2.1:51820', '192.0.2.1:0'),
                         ('192.0.2.1:51820', '1.2.3.4; touch /tmp/pwned:51820'),
                         ('9.9.9.9', '9.9.9.9; id'),
                         ('10.77.0.2/32', '999.1.1.1/32'),
                         ('0.0.0.0/0, ::/0', '0.0.0.0/0'),
                         (KEY, 'invalid'), ('25', '999999')]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                parse(CONF.replace(old, new))

    def test_ipv6_endpoint(self):
        parsed = parse(CONF.replace('192.0.2.1:51820', '[2001:db8::1]:51820'))
        self.assertIn('ip6 daddr 2001:db8::1', firewall(parsed['Peer']['Endpoint']))

    def test_fail_closed_firewall(self):
        rules = firewall('192.0.2.1:51820')
        self.assertIn('policy drop', rules)
        self.assertIn('meta mark 51821 ip daddr 192.0.2.1 udp dport 51820', rules)
        self.assertNotIn('ct state established', rules)
        self.assertNotIn('udp dport 53', rules)
        self.assertNotIn('192.0.2.1', firewall())

    def test_size_limit(self):
        with self.assertRaises(ValueError):
            parse(CONF + '#' * 16385)
