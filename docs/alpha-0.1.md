# Privux Cyber Complete Alpha 0.1

Experimental Debian 13 KDE Plasma amd64 live ISO, without VPN.

Includes Privux privacy CLI, Firefox ESR, LibreOffice, Thunderbird, Nmap,
Wireshark, tshark, tcpdump, Nikto, sqlmap, dirb, Aircrack-ng, Sleuth Kit,
TestDisk, Foremost, ExifTool, MAT2, binwalk, ClamAV, YARA, radare2 and John.

No VPN packages, GUI, privileged helper or guard service are installed by
the Alpha 0.1 ISO. The VPN code remains in the repository for future versions.

No graphical installer, disk encryption or Btrfs snapshot integration yet.
Privacy hardening is opt-in, not applied automatically at boot.

## Build

On Debian 13 amd64 install live-build, debootstrap, squashfs-tools, xorriso,
grub-pc-bin, grub-efi-amd64-bin, mtools, dosfstools and rsync, then run:

```sh
sudo bash scripts/build-live-iso.sh
```

Or use the GitHub Actions ISO workflow. Verify first boot, desktop, networking,
tool availability and VPN absence in a disposable VM before distributing.
Use security tools only on authorized targets.
