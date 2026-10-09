#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ${EUID} -ne 0 ]]; then
  echo "Run with sudo: sudo bash scripts/build-live-iso.sh" >&2
  exit 1
fi
for cmd in lb rsync; do
  command -v "$cmd" >/dev/null || { echo "Missing dependency: $cmd" >&2; exit 1; }
done
mkdir -p "$ROOT/build/live"
cd "$ROOT/build/live"
rsync -a --delete "$ROOT/iso/" ./
mkdir -p config/includes.chroot/opt/privux-build/src
rsync -a "$ROOT/src/privux/" config/includes.chroot/opt/privux-build/src/privux/
# Explicitly invoke config because the auto/config file is kept for local use.
bash auto/config
lb build
echo "ISO build finished. Check $PWD for *.iso"
