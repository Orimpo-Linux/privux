# Privux VPN — release acceptance and deployment gates

This checklist is **not** a certification or a claim that the VPN is ready for production.
Do not merge/release until an operator records the results on real Debian 13 machines.
The client remains opt-in; never activate the kill switch or a VPN connection on install.

## Automated, read-only diagnostics

On a **disposable** Debian 13 Privux VM with the VPN installed:

```sh
sudo bash scripts/vpn-acceptance-check.sh
```

After importing a test profile and connecting:

```sh
sudo bash scripts/vpn-acceptance-check.sh --require-connected
```

A zero exit code means only that the listed local prerequisites passed. It does
**not** verify traffic isolation, DNS leaks, server trust, or end-to-end Internet
access. The script prints no keys or configuration files.

## Manual acceptance gates — record pass/fail and evidence

- [ ] Use a **dedicated** Debian 13 server VM and separate Privux VM; set up
  the two-adapter VirtualBox lab from [VPN-PRIMEROS-PASOS.md](VPN-PRIMEROS-PASOS.md).
- [ ] Verify KDE launcher, Qt GUI, Polkit authentication, profile import,
  connect/disconnect, and that GUI reports a recent handshake.
- [ ] Confirm the VPN server's `wg show orimpo0` and client's
  `wg show pvpn` handshake and counters **without sharing keys**.
- [ ] Verify Internet routing from the client, with server-side packet capture
  if needed; matching public IPs on two NAT VMs are not proof of routing.
- [ ] Confirm `resolvectl status pvpn` reports the profile DNS and `~.`;
  independently test for DNS leaks, including browser behavior.
- [ ] With kill switch on, stop the server; check IPv4, IPv6 and DNS cannot
  bypass the tunnel. Test both tunnel drop and explicit disconnect.
- [ ] Reboot with kill switch on and confirm **no traffic escapes before VPN
  reconnection**. This requires a real boot test, not a namespace-only test.
- [ ] Turn off kill switch using the documented recovery command and verify
  normal networking returns.
- [ ] Test no-VPN installation, malformed profile rejection, no accidental
  key disclosure, multi-user permissions, updates and package removal.
- [ ] Test the freshly built ISO in VirtualBox and an **installed** Debian 13
  Privux environment; a Live session may lose changes after reboot.
- [ ] Have a separate reviewer inspect nftables, Polkit and privileged helper
  behavior before describing the service as secure.

## Public Orimpo service: not yet deployed

A public service needs hosting, reachable UDP endpoint(s), per-device key
issuance/revocation, monitoring, updates, backups, incident response, abuse
handling, privacy/log retention policy, capacity planning, and legal review.
Do not publish the lab profile or its private keys. The test server script is
single-client IPv4-only and **must not** be presented as production hosting.
No account provisioning or payment service exists in this branch.

## Release decision

Record test date, ISO commit, Debian version, client/server network topology,
tester, redacted evidence, failures and follow-up issue links in a release
tracking issue. CI passing is necessary but not sufficient. Keep this PR draft
until the above gates are completed.
