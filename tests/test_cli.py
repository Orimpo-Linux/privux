import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from privux.cli import EXIT_DRIFT, EXIT_OK, EXIT_USAGE, main
from privux.engine import host_path


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main(["--root", str(self.root), *argv])
            except SystemExit as exit_:  # argparse errors
                code = exit_.code
        return code, out.getvalue(), err.getvalue()

    def test_status_is_the_default_command(self):
        code, out, _ = self.run_cli()
        self.assertEqual(code, EXIT_DRIFT)  # nothing applied yet
        self.assertIn("firewall", out)

    def test_status_json_is_stable_for_the_panel(self):
        code, out, _ = self.run_cli("status", "--json")
        data = json.loads(out)
        self.assertEqual(code, EXIT_DRIFT)
        self.assertFalse(data["ok"])
        first = data["options"][0]
        for key in ("id", "category", "summary", "value", "default", "is_default", "choices", "state", "files"):
            self.assertIn(key, first)

    def test_apply_then_status_ok(self):
        code, out, _ = self.run_cli("apply")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("escrit: /etc/nftables.conf", out)
        code, out, _ = self.run_cli("status")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Tot correcte", out)

    def test_apply_dry_run_writes_nothing(self):
        code, out, _ = self.run_cli("apply", "--dry-run")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("s'escriuria", out)
        self.assertEqual(list(self.root.rglob("*")), [])

    def test_set_saves_and_applies_one_option(self):
        code, out, _ = self.run_cli("set", "dns", "mullvad")
        self.assertEqual(code, EXIT_OK)
        _, value, _ = self.run_cli("get", "dns")
        self.assertEqual(value.strip(), "mullvad")
        conf = host_path(self.root, "/etc/systemd/resolved.conf.d/90-privux-dns.conf").read_text()
        self.assertIn("dns.mullvad.net", conf)
        # only that option was applied
        self.assertFalse(host_path(self.root, "/etc/nftables.conf").exists())

    def test_set_off_and_reset(self):
        self.run_cli("apply")
        self.run_cli("set", "firewall", "no")
        self.assertIn("delete table", host_path(self.root, "/etc/nftables.conf").read_text())
        self.assertNotIn("policy drop", host_path(self.root, "/etc/nftables.conf").read_text())
        self.run_cli("reset", "firewall")
        self.assertIn("policy drop", host_path(self.root, "/etc/nftables.conf").read_text())
        self.assertEqual(self.run_cli("get", "firewall")[1].strip(), "on")

    def test_set_rejects_bad_input(self):
        code, _, err = self.run_cli("set", "firewall", "maybe")
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("valor no vàlid", err)
        code, _, err = self.run_cli("set", "nope", "on")
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("opció desconeguda", err)

    def test_list_json(self):
        code, out, _ = self.run_cli("list", "--json")
        self.assertEqual(code, EXIT_OK)
        ids = [o["id"] for o in json.loads(out)]
        self.assertIn("dns", ids)


if __name__ == "__main__":
    unittest.main()
