#!/bin/sh
set -eu
if [ "$(id -u)" != 0 ]; then
    echo 'Executeu amb sudo.' >&2
    exit 2
fi
cd "$(dirname "$0")/.."
apt-get update
apt-get install -y python3-pyside6.qtwidgets wireguard-tools nftables systemd-resolved polkitd pkexec iproute2 procps
install -d /usr/lib/python3/dist-packages/privux /usr/lib/privux
# Preserve the installed hardening engine; install only VPN modules.
install -m 644 src/privux/vpn_*.py /usr/lib/python3/dist-packages/privux/
if [ ! -e /usr/lib/python3/dist-packages/privux/__init__.py ]; then
    install -m 644 src/privux/__init__.py /usr/lib/python3/dist-packages/privux/
fi
install -m 755 vpn/vpn-helper /usr/lib/privux/vpn-helper
install -m 755 vpn/privux-vpn /usr/bin/privux-vpn
install -m 755 vpn/privux-vpnctl /usr/bin/privux-vpnctl
install -m 644 vpn/privux-vpn.desktop /usr/share/applications/
install -d /usr/share/plasma/systemsettings/externalmodules
install -m 644 vpn/privux-vpn-settings.desktop /usr/share/plasma/systemsettings/externalmodules/
install -m 644 vpn/org.orimpo.privux.vpn.policy /usr/share/polkit-1/actions/
install -m 644 vpn/privux-vpn-guard.service /etc/systemd/system/
install -d /etc/systemd/system/NetworkManager.service.d /etc/systemd/system/systemd-networkd.service.d
install -m 644 vpn/vpn-guard-dependency.conf /etc/systemd/system/NetworkManager.service.d/privux-vpn.conf
install -m 644 vpn/vpn-guard-dependency.conf /etc/systemd/system/systemd-networkd.service.d/privux-vpn.conf
systemctl daemon-reload
systemctl enable --now systemd-resolved privux-vpn-guard.service
echo 'Privux VPN installed. Open it from the menu. No connection has been activated.'
if grep -qw 'boot=live' /proc/cmdline; then
    echo 'LIVE SESSION: installation will be lost on reboot unless persistence is configured.'
fi
