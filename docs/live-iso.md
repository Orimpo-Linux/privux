# Privux development live ISO

This is an **experimental live image**, not a production installer.
It uses Debian 13 (Trixie), KDE Plasma and the Privux Python CLI source.
No VPN service or graphical Privux Shield is included.

## Build on Debian 13 amd64

Install dependencies:

```sh
sudo apt update
sudo apt install live-build debootstrap squashfs-tools xorriso \
  grub-pc-bin grub-efi-amd64-bin mtools dosfstools rsync
```

From the repository root:

```sh
sudo bash scripts/build-live-iso.sh
```

The output should be in `build/live/`. Build needs substantial disk space,
internet access and time. Use tmux for remote SSH builds.

## Safety and limitations

* The image is a **live session only**: it does not provide a supported graphical installer.
* The Privux CLI is included from repository source; the `.deb` package build
  remains a separate CI task.
* Firewall rules are **not automatically applied** at boot, to avoid disrupting
  SSH and networking. Test `privux status` and `privux apply --dry-run`
  before making changes.
* WireGuard and OpenVPN tools do not include VPN accounts or servers.
* This configuration has not yet passed an end-to-end ISO build or boot test.
* Test in VirtualBox before installing on real hardware.
