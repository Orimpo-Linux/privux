#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
export LC_ALL=C.UTF-8
if ! command -v dpkg-buildpackage >/dev/null; then
    apt-get update
    apt-get install -y --no-install-recommends build-essential debhelper dh-python pybuild-plugin-pyproject python3-all python3-setuptools python3-pyside6.qtwidgets wireguard-tools nftables iproute2 iputils-ping shellcheck desktop-file-utils procps
fi
cd /work
PYTHONPATH=src python3 -m unittest discover -s tests -v
shellcheck scripts/setup-vpn-server.sh scripts/install-vpn-client.sh vpn/vpn-helper vpn/privux-vpn
desktop-file-validate vpn/privux-vpn.desktop
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 scripts/vpn-gui-smoke.py
python3 scripts/vpn-netns-test.py
mkdir -p /build/privux /work/out
tar --exclude=.git --exclude=out --exclude=__pycache__ -cf - . | tar -xf - -C /build/privux
cd /build/privux
# Windows bind mounts expose every file as executable; debhelper .install files
# must be data, not executable helpers. Normalize only this disposable copy.
find debian -type f -exec chmod 0644 {} +
chmod 0755 debian/rules debian/privux-cli.postinst
dpkg-buildpackage -us -uc -b
cp /build/*.deb /work/out/
