#!/usr/bin/env python3
"""Illustrative baseball-tee mockups of a screen-print separation (plates -> ink layer -> shirt).
Usage: shirt_mockup.py SEPDIR OUTDIR --width-in 11 [--sleeve HEX|same] [--bodies FFFFFF:white,C9CBCD:heather]
Body/sleeve colours come from the person (ask for the shirt colour; hex if they have it, otherwise propose one and show it for approval).
Reads plate_*_<hex>.tif (black = ink) from SEPDIR; builds an RGBA ink layer from the plates (so the
shirt colour shows where there is no ink), then draws simple flat raglan tees. Mockup is illustrative
(not to scale beyond the print width), not a colour proof."""
import argparse, glob, os, re
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ap = argparse.ArgumentParser()
ap.add_argument("sepdir"); ap.add_argument("out")
ap.add_argument("--width-in", type=float, default=11)
ap.add_argument("--sleeve", default="same", help="sleeve colour hex, or 'same' for a plain tee (sleeves = body colour)")
ap.add_argument("--bodies", default="FFFFFF:white,C9CBCD:heather gray")
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
hx = lambda h: tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

plates = sorted(glob.glob(os.path.join(a.sepdir, "plate_*_*.tif")))
plates = [p for p in plates if "underbase" not in p]
first = Image.open(plates[0]); W, H = first.size
ink = np.zeros((H, W, 4), np.uint8)
for p in plates:                                   # print order: later plates on top
    col = hx(re.search(r"_([0-9A-Fa-f]{6})\.tif$", p).group(1))
    m = np.array(Image.open(p).convert("L")) < 128
    ink[m] = (*col, 255)
art = Image.fromarray(ink, "RGBA")

S = 2000
PX_IN = 45.0                                       # px per inch in the mockup (body ~20 in wide)
def tee(body_hex, sleeve_hex, label):
    im = Image.new("RGBA", (S, S), (236, 238, 240, 255))
    d = ImageDraw.Draw(im)
    sleeve_hex = body_hex if a.sleeve.lower() == "same" else a.sleeve
    body, sleeve = hx(body_hex), hx(sleeve_hex)
    cx = S // 2
    L = lambda pts: [(cx + x, y) for x, y in pts]
    R = lambda pts: [(cx - x, y) for x, y in pts]
    sl = [(-120, 250), (-400, 330), (-860, 850), (-720, 1010), (-450, 720)]     # left sleeve piece (raglan)
    bd = [(-120, 250), (120, 250), (450, 720), (470, 1640), (-470, 1640), (-450, 720)]
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0)); sd = ImageDraw.Draw(shadow)
    for pts in (bd, sl, [(-x, y) for x, y in sl]):
        sd.polygon([(cx + x + 14, y + 22) for x, y in pts], fill=(0, 0, 0, 70))
    im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(im)
    d.polygon(L(bd), fill=body)
    d.polygon(L(sl), fill=sleeve); d.polygon(R(sl), fill=sleeve)
    # raglan seams + hem + cuff stitching
    seam = tuple(max(0, c - 40) for c in body)
    d.line(L([(-120, 250), (-450, 720)]), fill=seam, width=3)
    d.line(L([(120, 250), (450, 720)]), fill=seam, width=3)
    d.line(L([(-470, 1612), (470, 1612)]), fill=seam, width=3)
    # neck: dark inside back + rib collar in sleeve colour
    d.ellipse([cx - 135, 190, cx + 135, 330], fill=tuple(int(c * 0.78) for c in body))
    d.arc([cx - 135, 190, cx + 135, 330], 0, 180, fill=sleeve, width=22)
    d.arc([cx - 135, 190, cx + 135, 330], 180, 360, fill=sleeve, width=12)
    # fabric: faint noise (stronger for heather), slight vertical light falloff
    rng = np.random.default_rng(3); arr = np.array(im).astype(np.int16)
    mask = (np.abs(arr[..., :3] - np.array(body)).sum(2) < 3) | (np.abs(arr[..., :3] - np.array(sleeve)).sum(2) < 3)
    heather = body_hex.upper() != "FFFFFF" and "heather" in label.lower()
    n = rng.normal(0, 7 if heather else 2.2, (S, S, 1))
    arr[..., :3] = np.where(mask[..., None], np.clip(arr[..., :3] + n, 0, 255), arr[..., :3])
    im = Image.fromarray(arr.astype(np.uint8), "RGBA")
    # place the print
    pw = int(a.width_in * PX_IN); ph = int(pw * H / W)
    pr = art.resize((pw, ph), Image.LANCZOS)
    im.alpha_composite(pr, (cx - pw // 2, 520))
    d = ImageDraw.Draw(im)
    from PIL import ImageFont
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
    fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    d.text((60, 50), f"{label} body" + ("" if sleeve_hex == body_hex else f", sleeves #{sleeve_hex.upper()}"), fill=(40, 40, 40), font=f)
    d.text((60, 100), f"Print {a.width_in:g} in wide x {a.width_in * H / W:.1f} in tall. Illustrative mockup, not a colour proof.", fill=(90, 90, 90), font=fs)
    return im.convert("RGB")

outs = []
for item in a.bodies.split(","):
    hexv, label = item.split(":")
    im = tee(hexv, a.sleeve, label)
    fn = os.path.join(a.out, f"mockup_{label.replace(' ', '_')}.png"); im.save(fn); outs.append(im)
both = Image.new("RGB", (S * len(outs) // 2, S // 2), (236, 238, 240))
for i, im in enumerate(outs):
    both.paste(im.resize((S // 2, S // 2), Image.LANCZOS), (i * S // 2, 0))
both.save(os.path.join(a.out, "mockups_side_by_side.png"))
print("wrote", len(outs), "mockups; art", W, "x", H)
