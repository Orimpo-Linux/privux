#!/usr/bin/env bash
# Read-only Privux VPN acceptance diagnostics for Debian 13.
# Never print WireGuard keys, profile contents, or public IPs.
set -uo pipefail
failures=0
warnings=0
require_connected=0
if [[ ${1:-} == --require-connected ]]; then require_connected=1
elif [[ $# -gt 0 ]]; then echo "Usage: $0 [--require-connected]" >&2; exit 2
fi
pass() { printf 'PASS: %s\n' "$1"; }
warn() { printf 'WARN: %s\n' "$1"; warnings=$((warnings+1)); }
fail() { printf 'FAIL: %s\n' "$1"; failures=$((failures+1)); }
command -v systemctl >/dev/null || { fail 'systemd is required'; exit 1; }
if [[ -r /etc/os-release ]]; then
  . /etc/os-release
  [[ ${VERSION_ID:-} == 13 ]] && pass 'Debian 13 version' || warn 'Not Debian 13; validate compatibility manually'
fi
for cmd in wg nft ip resolvectl pkexec; do
  command -v "$cmd" >/dev/null && pass "$cmd installed" || fail "$cmd missing"
done
[[ -x /usr/lib/privux/vpn-helper ]] && pass 'Privux privileged helper installed' || fail 'Privux helper missing'
[[ -f /usr/share/polkit-1/actions/org.orimpo.privux.vpn.policy ]] && pass 'Polkit policy installed' || fail 'Polkit policy missing'
[[ -f /usr/share/applications/privux-vpn.desktop ]] && pass 'Desktop entry installed' || warn 'Desktop entry missing'
if systemctl is-enabled --quiet privux-vpn-guard.service; then pass 'Boot guard enabled'; else fail 'Boot guard not enabled'; fi
if systemctl is-active --quiet privux-vpn-guard.service; then pass 'Boot guard active'; else fail 'Boot guard inactive'; fi
if systemctl is-active --quiet systemd-resolved.service; then pass 'systemd-resolved active'; else warn 'systemd-resolved inactive'; fi
if ip link show pvpn >/dev/null 2>&1; then
  pass 'VPN interface pvpn exists'
  if command -v wg >/dev/null; then
    # A timestamp is not a secret; avoid printing endpoints or keys.
    handshake=$(wg show pvpn latest-handshakes 2>/dev/null | awk '{if ($2>0) ok=1} END {print ok+0}')
    [[ $handshake == 1 ]] && pass 'WireGuard handshake recorded' || fail 'No WireGuard handshake recorded'
  fi
  if resolvectl status pvpn >/dev/null 2>&1; then pass 'Resolver has VPN link'; else fail 'Resolver has no VPN link'; fi
else
  if (( require_connected )); then fail 'VPN interface pvpn absent'; else warn 'VPN disconnected; connection tests skipped'; fi
fi
if [[ $EUID -eq 0 ]]; then
  if nft list table inet privux_vpn >/dev/null 2>&1; then
    pass 'Privux VPN firewall table present'
  else
    if (( require_connected )); then fail 'Privux VPN firewall table missing'; else warn 'No Privux VPN firewall table (may be normal if kill switch is off)'; fi
  fi
else
  warn 'Run with sudo to inspect VPN nftables table; no changes are made'
fi
echo "Result: $failures failure(s), $warnings warning(s)."
echo 'NOTE: This does not test traffic leaks or prove that the VPN server is trustworthy.'
(( failures == 0 ))
