#!/usr/bin/env python3
"""Prepare Privux images during ISO build, without altering the original ZIP."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "privux-branding-assets.zip"
DEST = ROOT / "build/live/config/includes.chroot/usr/share/privux/branding"
GRUB = ROOT / "build/live/config/includes.binary/boot/grub"
assert ARCHIVE.is_file(), "Missing approved Privux artwork archive"
DEST.mkdir(parents=True, exist_ok=True)
GRUB.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(ARCHIVE) as z:
    for name in ("boot.png", "splash.png", "login.png"):
        members = [m for m in z.namelist() if m.endswith("/" + name)]
        if len(members) != 1:
            raise RuntimeError(f"Expected exactly one {name} in archive")
        (DEST / name).write_bytes(z.read(members[0]))

# GRUB image: retain the approved wave design.
Image.open(DEST / "boot.png").convert("RGB").save(GRUB / "privux-boot.png")

# Remove the baked-in username, password, clock and buttons from the
# reference screenshot. Preserve its colors and vortex aesthetic by
# using a strongly blurred original as an SDDM background.
login = Image.open(DEST / "login.png").convert("RGB")
login = login.filter(ImageFilter.GaussianBlur(radius=46))
login.save(DEST / "login-clean.png", optimize=True)

# Plymouth animation: darken only the P emblem (not the waves/shield),
# then progressively reveal its original blue from bottom to top.
source = Image.open(DEST / "splash.png").convert("RGB")
w, h = source.size
# Relative coordinates account for the approved 630x310 artwork.
left, top, right, bottom = (int(w*.405), int(h*.15), int(w*.65), int(h*.64))
for i in range(16):
    frame = source.copy()
    pixels = frame.load()
    reveal = bottom - int((bottom-top)*i/15)
    for y in range(top, bottom):
        if y < reveal:
            for x in range(left, right):
                r,g,b = pixels[x,y]
                # Keep the bright shield centered in the P.
                if int(w*.53) <= x <= int(w*.595) and int(h*.25) <= y <= int(h*.44):
                    continue
                pixels[x,y] = (int(r*.20),int(g*.22),int(b*.28))
    frame.save(DEST / f"frame{i:02d}.png", optimize=True)
print("Privux GRUB, clean login and 16 Plymouth animation frames prepared")
