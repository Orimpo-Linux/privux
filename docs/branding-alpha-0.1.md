# Privux Alpha 0.1 visual identity

The existing tested ISO is preserved on branch
`feature/privux-cyber-complete-alpha-0.1` (successful build #14).
This experimental branding work lives separately on
`feature/privux-alpha-0.1-branding`.

Approved user-provided images:
- `boot.png`: blue waves for the boot menu (GRUB customization pending).
- `splash.png`: blue P/shield for Plymouth startup.
- `login.png`: vortex login reference (contains *baked-in* login form and
  must be cleaned before using it as an SDDM background).

These files are **not yet committed**. Copy the approved PNGs into
`iso/config/includes.chroot/usr/share/privux/branding/` before building.
The startup hook uses the splash only when the asset exists. The original
wallpaper and SDDM Breeze configuration remain in place.

The current Plymouth hook displays the approved splash as a still image;
the progressive P fill requires separate transparent layers/frames and
validation in a virtual machine. Do not claim the animation is working yet.

Before release, integrate GRUB background for BIOS and UEFI boot, use a
clean login background with SDDM controls rendered only once, verify the
Plymouth theme on a real boot, and update version labels consistently.
