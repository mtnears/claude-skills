#!/usr/bin/env python3
"""Zoomed crop with a labelled coordinate grid, for reading polygon points off the art.

Usage:
  grid_zoom.py ART.png OUT.png [--box X Y W H] [--zoom 2.4] [--step 50]

The grid labels are the art's own pixel coordinates (not the zoomed ones), so numbers you
read off the picture go straight into make_masks.py regions. Without --box the whole
image is shown. Look at the result with the image viewer, pick points, then check the
outline with make_masks.py's overlay.
"""
import argparse
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("art"); ap.add_argument("out")
ap.add_argument("--box", nargs=4, type=int, metavar=("X", "Y", "W", "H"))
ap.add_argument("--zoom", type=float, default=2.4); ap.add_argument("--step", type=int, default=50)
a = ap.parse_args()
im = Image.open(a.art).convert("RGBA")
bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im); im = bg.convert("RGB")
x0, y0, w, h = a.box if a.box else (0, 0, im.width, im.height)
crop = im.crop((x0, y0, x0 + w, y0 + h)).resize((int(w * a.zoom), int(h * a.zoom)), Image.LANCZOS)
d = ImageDraw.Draw(crop)
gx = (x0 // a.step + 1) * a.step
while gx < x0 + w:
    X = (gx - x0) * a.zoom; d.line([(X, 0), (X, crop.height)], fill=(255, 0, 255), width=1); d.text((X + 2, 2), str(gx), fill=(255, 0, 255)); gx += a.step
gy = (y0 // a.step + 1) * a.step
while gy < y0 + h:
    Y = (gy - y0) * a.zoom; d.line([(0, Y), (crop.width, Y)], fill=(0, 160, 255), width=1); d.text((2, Y + 2), str(gy), fill=(0, 160, 255)); gy += a.step
crop.save(a.out); print("wrote", a.out, crop.size)
