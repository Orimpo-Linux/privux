"""Registry of Privux hardening options.

Every option is independent, has a default value and knows how to *render* the
configuration files it needs for each possible value. A profile (today only
"High privacy"; "Standard" or "Paranoid" in the future) is nothing more than a
set of values for these options.

Rendering is a pure function: value -> {absolute path: file content}. A content
of ``None`` means "this file must not exist for this value". Keeping rendering
pure is what lets the engine plan, apply and check status without special cases,
and lets the tests run against a temporary root.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

MARKER = "Managed by Privux"
HASH_HEADER = f"# {MARKER}. Manual edits are overwritten; use `privux set` instead.\n"
SLASH_HEADER = f"// {MARKER}. Manual edits are overwritten; use `privux set` instead.\n"

BOOL = ("on", "off")
_TRUE = {"on", "true", "yes", "y", "1", "si", "sí"}
_FALSE = {"off", "false", "no", "n", "0"}

Files = dict[str, "str | None"]


def _(text: str) -> str:
    """Translation hook. User-facing strings are Catalan; gettext comes later."""
    return text


@dataclass(frozen=True)
class Option:
    id: str
    category: str  # network | system | browser | updates (matches the future panel sections)
    summary: str
    default: str
    choices: tuple[str, ...]
    render: Callable[[str], Files]
    # Commands run after files change (only on the real system, never in a test root).
    post: tuple[tuple[str, ...], ...] = ()

    @property
    def is_bool(self) -> bool:
        return self.choices == BOOL

    def normalize(self, raw: str) -> str:
        value = str(raw).strip().lower()
        if self.is_bool:
            if value in _TRUE:
                return "on"
            if value in _FALSE:
                return "off"
        elif value in self.choices:
            return value
        raise ValueError(
            _("valor no vàlid per a {id}: {value!r} (valors possibles: {choices})").format(
                id=self.id, value=raw, choices=", ".join(self.choices)
            )
        )

    def all_paths(self) -> set[str]:
        """Every path this option may manage, for any of its values."""
        paths: set[str] = set()
        for choice in self.choices:
            paths.update(self.render(choice))
        return paths

    def known_contents(self) -> dict[str, set[str]]:
        """Every content this option can write, per path (used to recognise our own files)."""
        known: dict[str, set[str]] = {}
        for choice in self.choices:
            for path, content in self.render(choice).items():
                if content is not None:
                    known.setdefault(path, set()).add(content)
        return known


# --------------------------------------------------------------------------- firewall

_NFT_PATH = "/etc/nftables.conf"

_NFT_ON = """\
# Inbound traffic is denied by default; everything the machine starts is allowed.
# Only the table 'inet privux' is touched, so Docker/libvirt/Podman rules survive.
table inet privux
delete table inet privux
table inet privux {
	chain input {
		type filter hook input priority filter; policy drop;
		iifname "lo" accept
		ct state invalid drop
		ct state established,related accept
		# IPv6 does not work without neighbour discovery and path MTU messages.
		icmpv6 type { destination-unreachable, packet-too-big, time-exceeded, parameter-problem, nd-router-advert, nd-neighbor-solicit, nd-neighbor-advert } accept
		# DHCP replies (v4 server -> client, v6 link-local).
		udp sport 67 udp dport 68 accept
		ip6 saddr fe80::/10 ip6 daddr fe80::/10 udp dport 546 accept
		# Echo requests (ping) are intentionally not answered.
	}
	chain forward {
		# Forwarding is off in the kernel by default; containers and VMs need it open.
		type filter hook forward priority filter; policy accept;
	}
	chain output {
		type filter hook output priority filter; policy accept;
	}
}
"""

_NFT_OFF = """\
# Firewall disabled: only the Privux table is removed.
table inet privux
delete table inet privux
"""


def _render_firewall(value: str) -> Files:
    return {_NFT_PATH: HASH_HEADER + (_NFT_ON if value == "on" else _NFT_OFF)}


# --------------------------------------------------------------------------- DNS

DNS_PROVIDERS = {
    "quad9": "9.9.9.9#dns.quad9.net 149.112.112.112#dns.quad9.net "
    "2620:fe::fe#dns.quad9.net 2620:fe::9#dns.quad9.net",
    # Same operator as quad9 but without malicious-domain blocking.
    "quad9-unfiltered": "9.9.9.10#dns10.quad9.net 149.112.112.10#dns10.quad9.net "
    "2620:fe::10#dns10.quad9.net 2620:fe::fe:10#dns10.quad9.net",
    "mullvad": "194.242.2.2#dns.mullvad.net 2a07:e340::2#dns.mullvad.net",
}


def _render_dns(value: str) -> Files:
    path = "/etc/systemd/resolved.conf.d/90-privux-dns.conf"
    if value == "off":
        return {path: None}
    return {
        path: HASH_HEADER
        + "[Resolve]\n"
        + f"DNS={DNS_PROVIDERS[value]}\n"
        + "FallbackDNS=\n"
        + "DNSOverTLS=yes\n"
        + "DNSSEC=allow-downgrade\n"
        + "Domains=~.\n"
    }


# --------------------------------------------------------------------------- MAC

def _render_mac(value: str) -> Files:
    path = "/etc/NetworkManager/conf.d/90-privux-mac.conf"
    if value == "off":
        return {path: None}
    # "stable" = a different MAC for every connection profile (network), constant for that
    # network. The hardware MAC is never exposed, and captive portals and DHCP leases keep
    # working across reconnects, unlike "random" which changes on every connection.
    return {
        path: HASH_HEADER
        + "[device-mac-randomization]\n"
        + "wifi.scan-rand-mac-address=yes\n\n"
        + "[connection-mac-randomization]\n"
        + "wifi.cloned-mac-address=stable\n"
        + "ethernet.cloned-mac-address=stable\n"
    }


# --------------------------------------------------------------------------- kernel

_SYSCTLS = [
    ("kernel.kptr_restrict", "2", "hide kernel pointers"),
    ("kernel.dmesg_restrict", "1", "dmesg only for root"),
    ("kernel.kexec_load_disabled", "1", "no kexec after boot"),
    ("kernel.unprivileged_bpf_disabled", "1", "no eBPF for unprivileged users"),
    ("net.core.bpf_jit_harden", "2", "harden the eBPF JIT"),
    ("kernel.yama.ptrace_scope", "1", "ptrace only on your own children (gdb -p needs sudo)"),
    ("fs.protected_symlinks", "1", "protect against symlink races in /tmp"),
    ("fs.protected_hardlinks", "1", "protect against hardlink attacks"),
    ("fs.protected_fifos", "2", "protect FIFOs in sticky directories"),
    ("fs.protected_regular", "2", "protect regular files in sticky directories"),
    # Loose (2) instead of strict (1) on purpose: strict reverse-path filtering can drop
    # legitimate traffic on multi-homed hosts and on WireGuard policy routing.
    ("net.ipv4.conf.all.rp_filter", "2", "loose reverse-path filtering (VPN friendly)"),
    ("net.ipv4.conf.default.rp_filter", "2", ""),
    ("net.ipv4.conf.all.accept_redirects", "0", "ignore ICMP redirects"),
    ("net.ipv4.conf.default.accept_redirects", "0", ""),
    ("net.ipv6.conf.all.accept_redirects", "0", ""),
    ("net.ipv6.conf.default.accept_redirects", "0", ""),
    ("net.ipv4.conf.all.send_redirects", "0", "this is not a router"),
    ("net.ipv4.conf.all.accept_source_route", "0", "ignore source-routed packets"),
    ("net.ipv6.conf.all.accept_source_route", "0", ""),
    ("net.ipv4.tcp_syncookies", "1", "SYN flood protection"),
    ("net.ipv4.tcp_rfc1337", "1", "protect against TIME-WAIT assassination"),
    ("net.ipv4.icmp_echo_ignore_broadcasts", "1", "ignore broadcast pings"),
]


def _render_kernel(value: str) -> Files:
    path = "/etc/sysctl.d/90-privux.conf"
    if value == "off":
        return {path: None}
    lines = [HASH_HEADER]
    for key, val, comment in _SYSCTLS:
        if comment:
            lines.append(f"# {comment}\n")
        lines.append(f"{key} = {val}\n")
    return {path: "".join(lines)}


# --------------------------------------------------------------------------- Firefox

_UBLOCK_ID = "uBlock0@raymondhill.net"


def _render_firefox(value: str) -> Files:
    path = "/etc/firefox/policies/policies.json"
    if value == "off":
        return {path: None}
    policies = {
        "policies": {
            "DisableTelemetry": True,
            "DisableFirefoxStudies": True,
            "EnableTrackingProtection": {
                "Value": True,
                "Locked": False,
                "Cryptomining": True,
                "Fingerprinting": True,  # blocks known fingerprinting scripts
                "EmailTracking": True,
            },
            # System-wide DNS (DNS over TLS) is used instead of Firefox's own resolver.
            "DNSOverHTTPS": {"Enabled": False, "Locked": False},
            "ExtensionSettings": {
                _UBLOCK_ID: {
                    "installation_mode": "force_installed",
                    "install_url": "https://addons.mozilla.org/firefox/downloads/latest/ublock-origin/latest.xpi",
                }
            },
            # Deliberately NOT enabled: privacy.resistFingerprinting. It breaks too many sites.
            "Preferences": {
                "browser.contentblocking.category": {"Value": "strict", "Status": "default"},
            },
        }
    }
    return {path: json.dumps(policies, indent=2) + "\n"}


# --------------------------------------------------------------------------- updates

def _render_updates(value: str) -> Files:
    path = "/etc/apt/apt.conf.d/52privux-auto-upgrades"
    if value == "off":
        return {path: None}
    return {
        path: SLASH_HEADER
        + 'APT::Periodic::Update-Package-Lists "1";\n'
        + 'APT::Periodic::Unattended-Upgrade "1";\n'
        # Never reboot behind the user's back; the panel will ask instead.
        + 'Unattended-Upgrade::Automatic-Reboot "false";\n'
    }


# --------------------------------------------------------------------------- registry

OPTIONS: tuple[Option, ...] = (
    Option(
        id="firewall",
        category="network",
        summary=_("Tallafocs: denega les connexions entrants (nftables)"),
        default="on",
        choices=BOOL,
        render=_render_firewall,
        post=(("systemctl", "enable", "nftables"), ("systemctl", "reload-or-restart", "nftables")),
    ),
    Option(
        id="dns",
        category="network",
        summary=_("DNS xifrat (DNS sobre TLS): proveïdor, o 'off' per usar el de la xarxa"),
        default="quad9",
        choices=(*DNS_PROVIDERS, "off"),
        render=_render_dns,
        post=(("systemctl", "enable", "systemd-resolved"), ("systemctl", "restart", "systemd-resolved")),
    ),
    Option(
        id="mac_randomization",
        category="network",
        summary=_("Adreça MAC diferent per a cada xarxa (cal desactivar-ho en alguns portals captius)"),
        default="on",
        choices=BOOL,
        render=_render_mac,
        post=(("nmcli", "general", "reload", "conf"),),
    ),
    Option(
        id="kernel_hardening",
        category="system",
        summary=_("Endureix el nucli i la pila de xarxa (sysctl)"),
        default="on",
        choices=BOOL,
        render=_render_kernel,
        post=(("sysctl", "--system"),),
    ),
    Option(
        id="firefox_hardening",
        category="browser",
        summary=_("Firefox: sense telemetria, protecció contra seguiment estricta i uBlock Origin"),
        default="on",
        choices=BOOL,
        render=_render_firefox,
    ),
    Option(
        id="auto_updates",
        category="updates",
        summary=_("Instal·la automàticament les actualitzacions de seguretat"),
        default="on",
        choices=BOOL,
        render=_render_updates,
    ),
)

OPTIONS_BY_ID: dict[str, Option] = {o.id: o for o in OPTIONS}
