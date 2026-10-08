import tempfile
import unittest
from pathlib import Path

from privux.config import CONFIG_PATH, Config, effective_values
from privux.engine import BACKUP_SUFFIX, apply_option, host_path, option_state, plan_option
from privux.options import OPTIONS, OPTIONS_BY_ID


class EngineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def apply_all(self, values=None):
        values = values or {o.id: o.default for o in OPTIONS}
        return [apply_option(o, values[o.id], self.root) for o in OPTIONS]

    def test_fresh_system_is_pending_then_ok_after_apply(self):
        for option in OPTIONS:
            self.assertEqual(option_state(plan_option(option, option.default, self.root)), "pending", option.id)
        self.apply_all()
        for option in OPTIONS:
            self.assertEqual(option_state(plan_option(option, option.default, self.root)), "ok", option.id)

    def test_apply_is_idempotent(self):
        self.apply_all()
        for result in self.apply_all():
            self.assertFalse(result.changed, result.option)

    def test_dry_run_touches_nothing(self):
        for option in OPTIONS:
            apply_option(option, option.default, self.root, dry_run=True)
        self.assertEqual(list(self.root.rglob("*")), [])

    def test_manual_edit_of_our_file_is_detected_and_fixed(self):
        option = OPTIONS_BY_ID["kernel_hardening"]
        apply_option(option, "on", self.root)
        target = host_path(self.root, "/etc/sysctl.d/90-privux.conf")
        target.write_text(target.read_text() + "kernel.sysrq = 1\n")
        # still carries the Privux marker, so it is "ours" and just pending
        self.assertEqual(option_state(plan_option(option, "on", self.root)), "pending")
        apply_option(option, "on", self.root)
        self.assertNotIn("sysrq", target.read_text())
        self.assertFalse(Path(str(target) + BACKUP_SUFFIX).exists())

    def test_foreign_file_is_backed_up_once_before_overwrite(self):
        option = OPTIONS_BY_ID["firewall"]
        target = host_path(self.root, "/etc/nftables.conf")
        target.parent.mkdir(parents=True)
        target.write_text("flush ruleset\n# distro default\n")
        self.assertEqual(option_state(plan_option(option, "on", self.root)), "modified")
        apply_option(option, "on", self.root)
        backup = Path(str(target) + BACKUP_SUFFIX)
        self.assertEqual(backup.read_text(), "flush ruleset\n# distro default\n")
        # changing the option again must not overwrite the original backup
        apply_option(option, "off", self.root)
        self.assertEqual(backup.read_text(), "flush ruleset\n# distro default\n")

    def test_off_removes_our_file_but_never_a_foreign_one(self):
        option = OPTIONS_BY_ID["mac_randomization"]
        path = "/etc/NetworkManager/conf.d/90-privux-mac.conf"
        apply_option(option, "on", self.root)
        self.assertTrue(host_path(self.root, path).exists())
        apply_option(option, "off", self.root)
        self.assertFalse(host_path(self.root, path).exists())

        host_path(self.root, path).write_text("[main]\nmine=1\n")
        result = apply_option(option, "off", self.root)
        self.assertEqual(host_path(self.root, path).read_text(), "[main]\nmine=1\n")
        self.assertEqual(result.actions[0].action, "kept")

    def test_switching_dns_provider_rewrites_the_file(self):
        option = OPTIONS_BY_ID["dns"]
        path = host_path(self.root, "/etc/systemd/resolved.conf.d/90-privux-dns.conf")
        apply_option(option, "quad9", self.root)
        self.assertIn("dns.quad9.net", path.read_text())
        apply_option(option, "mullvad", self.root)
        self.assertIn("dns.mullvad.net", path.read_text())
        self.assertNotIn("quad9", path.read_text())

    def test_post_commands_never_run_against_a_test_root(self):
        result = apply_option(OPTIONS_BY_ID["firewall"], "on", self.root)
        self.assertEqual(result.warnings, [])


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_defaults_when_no_file(self):
        values, warnings = effective_values(self.root)
        self.assertEqual(values, {o.id: o.default for o in OPTIONS})
        self.assertEqual(warnings, [])

    def test_roundtrip(self):
        Config(self.root).save({"firewall": "off", "dns": "mullvad"})
        values, warnings = effective_values(self.root)
        self.assertEqual(values["firewall"], "off")
        self.assertEqual(values["dns"], "mullvad")
        self.assertEqual(warnings, [])

    def test_bad_entries_warn_and_fall_back_to_defaults(self):
        Config(self.root).save({"firewall": "banana", "nonexistent": "on"})
        values, warnings = effective_values(self.root)
        self.assertEqual(values["firewall"], "on")
        self.assertEqual(len(warnings), 2)

    def test_config_lives_in_etc_privux(self):
        self.assertEqual(Config(self.root).path, self.root / CONFIG_PATH.lstrip("/"))


if __name__ == "__main__":
    unittest.main()
