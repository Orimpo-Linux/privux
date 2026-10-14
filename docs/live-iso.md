# Privux development live ISO

This is an **experimental live image**, not a production installer.
It uses Debian 13 (Trixie), KDE Plasma and the Privux Python CLI source.
The Privux VPN client (`privux-vpn`, WireGuard) is included, but no VPN
service (servers or accounts) and no graphical panel for the `privux`
hardening options.

## Getting the image

The ISO is not committed to the repository and is not published as a
release. Two ways to get it:

* **GitHub Actions:** the workflow `live-iso.yml` ("Build Privux Cyber
  Desktop Beta") runs manually (**Run workflow**) or on pushes to
  `feature/live-iso-builder` and `feature/privux-desktop-cyber-beta`, not on
  `main`. Open a successful run and download the artifact
  `privux-cyber-desktop-beta-amd64` (a `.zip` containing the `.iso`).
  Artifacts are kept for **7 days**; downloading requires being signed in to
  GitHub.
* **Local build:** see below.

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
* None of the `privux` options (firewall, DNS over TLS, MAC randomization,
  kernel sysctl, Firefox policy, automatic updates) are **automatically
  applied** at boot, to avoid disrupting SSH and networking. Test
  `privux status` and `privux apply --dry-run` before making changes.
* The `privux-vpn-guard` service runs at boot before networking, but only
  restores a kill switch the user had enabled; it never connects a VPN.
* WireGuard and OpenVPN tools do not include VPN accounts or servers; import
  your own WireGuard `.conf` (full tunnel, numeric endpoint IP).
* The CI build of this configuration completes successfully, but no
  end-to-end boot test is documented here yet.
* Test in VirtualBox before installing on real hardware.
