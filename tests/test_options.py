import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from privux.options import DNS_PROVIDERS, MARKER, OPTIONS, OPTIONS_BY_ID


class RegistryTests(unittest.TestCase):
    def test_ids_are_unique(self):
        self.assertEqual(len(OPTIONS), len(OPTIONS_BY_ID))

    def test_defaults_are_valid_choices(self):
        for option in OPTIONS:
            self.assertIn(option.default, option.choices, option.id)

    def test_default_profile_is_high_privacy(self):
        # Decision of the team: Quad9 by default, everything else on.
        self.assertEqual(OPTIONS_BY_ID["dns"].default, "quad9")
        for option in OPTIONS:
            if option.is_bool:
                self.assertEqual(option.default, "on", option.id)

    def test_no_two_options_manage_the_same_file(self):
        seen = {}
        for option in OPTIONS:
            for path in option.all_paths():
                self.assertNotIn(path, seen, f"{path} used by {option.id} and {seen.get(path)}")
                seen[path] = option.id

    def test_all_paths_are_absolute_and_under_etc(self):
        for option in OPTIONS:
            for path in option.all_paths():
                self.assertTrue(path.startswith("/etc/"), path)

    def test_text_files_carry_the_marker(self):
        for option in OPTIONS:
            for choice in option.choices:
                for path, content in option.render(choice).items():
                    if content is not None and not path.endswith(".json"):
                        self.assertIn(MARKER, content, f"{option.id}={choice}")

    def test_normalize(self):
        firewall = OPTIONS_BY_ID["firewall"]
        self.assertEqual(firewall.normalize(" Sí "), "on")
        self.assertEqual(firewall.normalize("NO"), "off")
        with self.assertRaises(ValueError):
            firewall.normalize("maybe")
        with self.assertRaises(ValueError):
            OPTIONS_BY_ID["dns"].normalize("google")


class ContentTests(unittest.TestCase):
    def test_firefox_policy_is_valid_json_and_keeps_usability_limit(self):
        content = OPTIONS_BY_ID["firefox_hardening"].render("on")["/etc/firefox/policies/policies.json"]
        policies = json.loads(content)["policies"]
        self.assertTrue(policies["DisableTelemetry"])
        self.assertIn("uBlock0@raymondhill.net", policies["ExtensionSettings"])
        self.assertNotIn("resistFingerprinting", content)

    def test_dns_uses_tls_and_named_servers(self):
        for provider in DNS_PROVIDERS:
            content = OPTIONS_BY_ID["dns"].render(provider)["/etc/systemd/resolved.conf.d/90-privux-dns.conf"]
            self.assertIn("DNSOverTLS=yes", content)
            for server in DNS_PROVIDERS[provider].split():
                self.assertIn("#dns", server)  # every server carries its TLS name

    def test_off_values_remove_files(self):
        for option_id in ("dns", "mac_randomization", "kernel_hardening", "firefox_hardening", "auto_updates"):
            option = OPTIONS_BY_ID[option_id]
            off = "off"
            self.assertTrue(all(c is None for c in option.render(off).values()), option_id)

    def test_firewall_off_only_deletes_our_table(self):
        content = OPTIONS_BY_ID["firewall"].render("off")["/etc/nftables.conf"]
        self.assertIn("delete table inet privux", content)
        self.assertNotIn("flush ruleset", content)

    def test_firewall_on_never_flushes_other_tables(self):
        content = OPTIONS_BY_ID["firewall"].render("on")["/etc/nftables.conf"]
        self.assertNotIn("flush ruleset", content)
        self.assertIn("policy drop", content)

    def test_nftables_syntax_if_possible(self):
        """Ask nft itself to parse the ruleset (needs the binary and netlink access)."""
        if shutil.which("nft") is None:
            self.skipTest("nft not installed")
        with tempfile.TemporaryDirectory() as tmp:
            for value in ("on", "off"):
                path = Path(tmp) / f"{value}.nft"
                path.write_text(OPTIONS_BY_ID["firewall"].render(value)["/etc/nftables.conf"])
                done = subprocess.run(["nft", "-c", "-f", str(path)], capture_output=True, text=True)
                if "Operation not permitted" in done.stderr or "Permission denied" in done.stderr:
                    self.skipTest("nft cannot run here (no CAP_NET_ADMIN)")
                self.assertEqual(done.returncode, 0, done.stderr)


if __name__ == "__main__":
    unittest.main()
