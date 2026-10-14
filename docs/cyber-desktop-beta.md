# Privux desktop + cybersecurity beta

This branch extends the tested Debian 13 KDE live ISO. It is **not a
production-ready or fully installed operating system**.

## Scope

* Daily-use KDE Plasma desktop, Firefox ESR, LibreOffice, Thunderbird.
* Privacy CLI `privux` and AppArmor packages.
* Defensive tools: Nmap, Wireshark, tshark, tcpdump, DNS utilities,
  ClamAV, YARA, ExifTool, MAT2.
* Privux VPN client (`privux-vpn`, WireGuard, in KDE System Settings under
  Network) with an optional kill switch, plus OpenVPN tools and the
  NetworkManager OpenVPN plugin. **No VPN servers or accounts are included**:
  you must import your own WireGuard `.conf`. The VPN never connects by itself.
* The live image does **not** apply the `privux` hardening options at boot
  (firewall, DNS over TLS, MAC randomization, kernel sysctl, Firefox policy,
  automatic updates). Do not enable them automatically until their networking
  impact is tested; run `sudo privux apply --dry-run` first, then
  `sudo privux apply`. The only service that runs at boot is
  `privux-vpn-guard`, which restores a kill switch the user had enabled
  before; it never connects a VPN.

Use network scanning and packet capture only on systems you own or have
explicit authorization to assess.

## Branding asset

The approved Privux blue wallpaper is committed as a JPEG at:

`iso/config/includes.chroot/usr/share/wallpapers/Privux/contents/images/privux-wallpaper.jpg`

The build includes that image automatically. The branding hook
(`020-privux-branding.hook.chroot`) uses it for the SDDM login screen and
the Plasma lock screen, and an autostart script applies it as the desktop
wallpaper once, on first Plasma login. Without this file the ISO still
builds and the OS identity (`/etc/os-release`, `/etc/issue`, hostname) is
still set, but the wallpaper, lock screen and login screen configuration is
skipped and KDE keeps its stock look. This behavior is intentional so that
CI does not silently substitute another brand.

## Still required for release

* Verify build artifact and KDE first-login wallpaper.
* Verify tools start and networking works in VirtualBox.
* Test AppArmor profiles, DNS and firewall separately.
* Implement and test Calamares, LUKS2 and Btrfs/Snapper before claiming
  installable, encrypted release status.
* Review ISO size and artifact retention before distribution.
