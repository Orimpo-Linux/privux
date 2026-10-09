# Privux desktop + cybersecurity beta

This branch extends the tested Debian 13 KDE live ISO. It is **not a
production-ready or fully installed operating system**.

## Scope

* Daily-use KDE Plasma desktop, Firefox ESR, LibreOffice, Thunderbird.
* Privacy CLI `privux` and AppArmor packages.
* Defensive tools: Nmap, Wireshark, tshark, tcpdump, DNS utilities,
  ClamAV, YARA, ExifTool, MAT2.
* **No VPN packages or server configuration in this build.**
* Do not enable firewall or hardening settings automatically until their
  networking impact is tested.

Use network scanning and packet capture only on systems you own or have
explicit authorization to assess.

## Branding asset

The approved Privux blue wallpaper must be committed as a JPEG at:

`iso/config/includes.chroot/usr/share/wallpapers/Privux/contents/images/1920x1080.jpg`

The build includes that image automatically and the desktop hook attempts
to set it on first Plasma login. Without this file the ISO still builds,
but KDE keeps its stock wallpaper. This behavior is intentional so that
CI does not silently substitute another brand.

## Still required for release

* Upload the approved wallpaper JPEG to the path above.
* Verify build artifact and KDE first-login wallpaper.
* Verify tools start and networking works in VirtualBox.
* Test AppArmor profiles, DNS and firewall separately.
* Implement and test Calamares, LUKS2 and Btrfs/Snapper before claiming
  installable, encrypted release status.
* Review ISO size and artifact retention before distribution.
