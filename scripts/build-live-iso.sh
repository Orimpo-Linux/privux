#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ${EUID} -ne 0 ]]; then
  echo "Run with sudo: sudo bash scripts/build-live-iso.sh" >&2
  exit 1
fi
for cmd in lb rsync unzip python3; do
  command -v "$cmd" >/dev/null || { echo "Missing dependency: $cmd" >&2; exit 1; }
done
mkdir -p "$ROOT/build/live"
cd "$ROOT/build/live"
rsync -a --delete "$ROOT/iso/" ./
# Extract approved artwork from the uploaded archive; do not commit binaries again.
if [[ -f "$ROOT/privux-branding-assets.zip" ]]; then
  unzip -oq "$ROOT/privux-branding-assets.zip" "iso/config/includes.chroot/usr/share/privux/branding/*" -d "$ROOT/build/branding-extracted"
  install -d config/includes.chroot/usr/share/privux/branding
  cp "$ROOT/build/branding-extracted/iso/config/includes.chroot/usr/share/privux/branding/"*.png config/includes.chroot/usr/share/privux/branding/
  for asset in boot.png splash.png login.png; do
    test -s "config/includes.chroot/usr/share/privux/branding/$asset" || { echo "Missing branding: $asset" >&2; exit 1; }
  done
fi
chmod +x config/hooks/live/*.hook.chroot
mkdir -p config/includes.chroot/opt/privux-build/src/privux
rsync -a --exclude='vpn_*.py' "$ROOT/src/privux/" config/includes.chroot/opt/privux-build/src/privux/
python3 "$ROOT/scripts/prepare-branding.py"
chmod +x config/hooks/normal/*.hook.binary
bash auto/config
lb build
echo "ISO build finished. Check $PWD for *.iso"
