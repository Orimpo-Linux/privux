"""Linux-only backend state/failure tests, using fake commands and a temp root."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

if sys.platform == 'linux':
    from privux import vpn_backend as backend
from test_vpn import CONF


@unittest.skipUnless(sys.platform == 'linux', 'Linux root backend')
class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        for name, value in [('BASE', base), ('STATE', base / 'state.json'), ('ACTIVE', base / 'pvpn.conf')]:
            patcher = patch.object(backend, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(backend, 'status', side_effect=lambda state: state)
        patcher.start()
        self.addCleanup(patcher.stop)

    def import_profile(self):
        with patch('sys.stdin', io.StringIO(CONF)):
            backend.execute('import', ['lab'])

    def test_import_permissions_and_no_overwrite(self):
        self.import_profile()
        self.assertEqual(backend.profile('lab').stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError):
            self.import_profile()

    def test_no_path_traversal(self):
        for name in ['../root', '/tmp/x', 'x.conf', 'x\nPostUp=id', '']:
            with self.assertRaises(ValueError):
                backend.profile(name)

    def test_connect_failure_retains_kill_switch(self):
        self.import_profile()
        backend.write(backend.STATE, json.dumps({'kill_switch': True, 'selected': None}))
        with patch.object(backend, 'up', return_value=False), patch.object(backend, 'set_firewall') as fw, \
             patch.object(backend, 'run', side_effect=RuntimeError('failure')), patch.object(backend, 'disconnect'):
            with self.assertRaises(RuntimeError):
                backend.execute('connect', ['lab'])
            fw.assert_called_once_with(True, '192.0.2.1:51820')
        self.assertTrue(backend.read_state()['kill_switch'])

    def test_disconnect_keeps_blocking(self):
        backend.write(backend.STATE, json.dumps({'kill_switch': True, 'selected': None}))
        with patch.object(backend, 'disconnect'), patch.object(backend, 'set_firewall') as fw:
            backend.execute('disconnect', [])
            fw.assert_called_once_with(True)

    def test_restore_does_not_connect(self):
        backend.write(backend.STATE, json.dumps({'kill_switch': True, 'selected': 'lab'}))
        with patch.object(backend, 'set_firewall') as fw, patch.object(backend, 'run') as run:
            backend.execute('restore', [])
            fw.assert_called_once_with(True)
            run.assert_not_called()
