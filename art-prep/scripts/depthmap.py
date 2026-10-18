#!/usr/bin/env python3
"""Tiered height ("depth") map for raised UV printing, embossing, relief and patches.

Usage:
  depthmap.py ART.png MASKS.npz CONFIG.json OUTDIR

Black = lowest, white = tallest, transparent = pure black. Heights are DECIDED from what
each part of the art is (see references/relief.md), not from its colours: you list tiers
from lowest to highest, say which region or colour rule belongs to each, and give a level
0-255. Later tiers paint over earlier ones. Everything is computed from the art's own
pixels and the approved masks; masks made at the native size are resized, so the same
config builds the native-size and the 4x master maps.

CONFIG.json
{
  "field": 10,                 # level of everything not in a tier (the flat background)
  "bevel": 3.5,                # rounded-edge width in native px (0 = hard edges)
  "rim_px": 9,                 # outer edge tapers off over this many px (0 = off)
  "max": 245,                  # never go whiter than this (flat white tops print badly)
  "smooth": 0.9,               # final blur, native px
  "texture": {"style": "leather", "amp": 6, "scale": 3},   # optional; styles: leather wood weave stipple brushed grain
  "tiers": [                   # LOWEST FIRST
    {"name": "scenery", "mask": "scene", "level": 70,
     "gradient_y": [300, 820, 0.35, 1.0],     # optional: multiplier from y0 to y1 (native px), e.g. far = lower
     "luma": 0.14, "detail": 0.12,            # optional: brighter/rock-grain areas a bit taller (fractions of level)
     "texture": true},                        # apply the texture style to this tier
    {"name": "borders", "colour": {"L_min": 62, "chroma_max": 28}, "minus": ["jeep"], "level": 150},
    {"name": "flag",    "mask": "flag", "level": 196},
    {"name": "jeep",    "mask": "jeep", "level": 234}
  ]
}
Tier region = "mask" (a region from make_masks.py) and/or "colour" (rule keys as in
make_masks.py: L_min L_max chroma_max chroma_min hue s_min v_min v_max), optionally
"within": name, "minus": [names] (mask names or earlier tier names).
Other tier keys: "bevel" (override), "edge" (profile at the very edge, 0-1, default 0.6),
"max" (cap), "soft" (mask feather in px).

Writes OUTDIR/depth.png (8-bit L, DPI tag copied from the art), OUTDIR/depth_preview.png
(art | depth | shaded relief) and prints each tier's measured median level.
"""
import argparse, json, os
import numpy as np, cv2
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("art"); ap.add_argument("masks"); ap.add_argument("config"); ap.add_argument("out")
A = ap.parse_args(); os.makedirs(A.out, exist_ok=True)
cfg = json.load(open(A.config)); M = np.load(A.masks)

pil = Image.open(A.art).convert("RGBA"); dpi = Image.open(A.art).info.get("dpi")
im = np.array(pil); Hh, Ww = im.shape[:2]
ref_w = next(iter(M.values())).shape[1]; s = Ww / ref_w          # art px per native px
rgb, al = im[..., :3], im[..., 3] > 0
bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32); hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
L = lab[..., 0] / 255 * 100; ch = np.hypot(lab[..., 1] - 128, lab[..., 2] - 128)
Hue, S, V = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
smooth = lambda x: (lambda c: c * c * (3 - 2 * c))(np.clip(x, 0, 1))
dist_in = lambda m: cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5) / s
T = np.clip((L - cv2.GaussianBlur(L, (0, 0), 2.5 * s)) / 30, -1, 1)      # local light/dark detail, about 0
yy = (np.arange(Hh)[:, None] / s) * np.ones((1, Ww))


def resized(name, soft=1.2):
    m = cv2.resize(M[name].astype(np.float32), (Ww, Hh), interpolation=cv2.INTER_LINEAR)
    return np.clip((cv2.GaussianBlur(m, (0, 0), soft * s) - 0.5) * 3 + 0.5, 0, 1) > 0.5


def clean(m, close=2, minpx=40):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * max(1, int(close * s)) + 1,) * 2)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, k)
    n, lbl, st, _ = cv2.connectedComponentsWithStats(m)
    keep = np.zeros(n, bool); keep[1:] = st[1:, cv2.CC_STAT_AREA] >= minpx * s * s
    return keep[lbl]


def rule(c):
    m = np.ones((Hh, Ww), bool)
    if "L_min" in c: m &= L > c["L_min"]
    if "L_max" in c: m &= L < c["L_max"]
    if "chroma_max" in c: m &= ch < c["chroma_max"]
    if "chroma_min" in c: m &= ch > c["chroma_min"]
    if "hue" in c:
        lo, hi = c["hue"]; m &= ((Hue >= lo) & (Hue <= hi)) if lo <= hi else ((Hue >= lo) | (Hue <= hi))
    if "s_min" in c: m &= S > c["s_min"]
    if "v_min" in c: m &= V > c["v_min"]
    if "v_max" in c: m &= V < c["v_max"]
    return clean(m) & al


# ---- optional surface texture (small height ripples, in level units) ----
def texture_field(style, scale):
    rng = np.random.default_rng(7); k = max(0.6, scale) * s
    n = lambda sig: cv2.GaussianBlur(rng.normal(0, 1, (Hh, Ww)).astype(np.float32), (0, 0), sig * k)
    z = lambda f: f / (f.std() + 1e-6)
    if style == "stipple": return np.clip(z(n(0.5)), -2.5, 2.5) / 2.5
    if style == "leather":                                   # pebbled cells: ridges between blobs
        f = z(n(1.6)); return np.clip(1 - np.abs(f) * 1.6, -1, 1)
    if style == "brushed":                                   # horizontal streaks
        f = cv2.GaussianBlur(rng.normal(0, 1, (Hh, Ww)).astype(np.float32), (int(40 * k) | 1, 1), 0); return np.clip(z(f), -2.5, 2.5) / 2.5
    if style == "weave":
        xs = np.arange(Ww)[None, :] / (3.0 * k); ys = np.arange(Hh)[:, None] / (3.0 * k)
        return (np.sin(xs * np.pi) * np.sin(ys * np.pi)).astype(np.float32)
    if style in ("wood", "grain"):                           # long wavy grain along x
        warp = z(n(6)) * 2.0; ys = np.arange(Hh)[:, None] / (2.2 * k) + warp
        return (np.sin(ys * np.pi) * 0.6 + z(n(1.0)) * 0.25).astype(np.float32)
    return np.zeros((Hh, Ww), np.float32)


tx = cfg.get("texture") or {}
TEX = texture_field(tx["style"], tx.get("scale", 3)) * tx.get("amp", 6) if tx.get("style") else None

bevel_default = cfg.get("bevel", 3.5)
h = np.where(al, float(cfg.get("field", 10)), 0).astype(np.float32)
region = {}                                                   # name -> bool mask, so later tiers can reference earlier ones
for t in cfg["tiers"]:
    m = np.ones((Hh, Ww), bool)
    if "mask" in t: m &= resized(t["mask"], t.get("soft", 1.2))
    if "colour" in t: m &= rule(t["colour"])
    if "within" in t: m &= region[t["within"]] if t["within"] in region else resized(t["within"])
    for o in t.get("minus", []): m &= ~(region[o] if o in region else resized(o))
    m &= al; region[t["name"]] = m
    if not m.any(): print("WARNING: tier", t["name"], "is empty"); continue
    lvl = float(t["level"]); val = np.full((Hh, Ww), lvl, np.float32)
    if "gradient_y" in t:
        y0, y1, f0, f1 = t["gradient_y"]; val *= f0 + (f1 - f0) * smooth((yy - y0) / max(1, y1 - y0))
    if t.get("luma"): val += lvl * t["luma"] * (L / 100 - 0.5)
    if t.get("detail"): val += lvl * t["detail"] * T
    if t.get("texture") and TEX is not None: val += TEX
    bev = float(t.get("bevel", bevel_default))
    if bev > 0:
        edge = float(t.get("edge", 0.6)); val *= edge + (1 - edge) * smooth(dist_in(m) / bev)
    if "max" in t: val = np.minimum(val, float(t["max"]))
    h = np.where(m, val, h)

h = np.where(al, h, 0).astype(np.float32)
if cfg.get("smooth", 0.9) > 0: h = cv2.GaussianBlur(h, (0, 0), cfg.get("smooth", 0.9) * s)
rim = float(cfg.get("rim_px", 9))
if rim > 0: h *= 0.30 + 0.70 * smooth(dist_in(al) / rim)                     # tapered outer edge
depth = np.where(al, np.clip(h, 0, cfg.get("max", 245)), 0).astype(np.uint8)
Image.fromarray(depth, "L").save(os.path.join(A.out, "depth.png"), dpi=dpi if dpi else (72, 72))

rs = lambda a: cv2.resize(a, (1254, int(1254 * Hh / Ww)), interpolation=cv2.INTER_AREA)   # shade at one size so it looks the same at any scale
g = rs(depth).astype(np.float32)
gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
al_s = rs(al.astype(np.uint8) * 255) > 127
relief = np.where(al_s, np.clip(0.55 + (-gx - gy) / (255 * 2.2), 0, 1) * 225, 235).astype(np.uint8)
art_bg = rs(np.where(al[..., None], rgb, 255).astype(np.uint8))
Image.fromarray(np.hstack([art_bg, np.dstack([rs(depth)] * 3), np.dstack([relief] * 3)])).save(os.path.join(A.out, "depth_preview.png"))
print("tier medians:", {t["name"]: int(np.median(depth[region[t["name"]]])) for t in cfg["tiers"] if t["name"] in region and region[t["name"]].any()},
      "| field", cfg.get("field", 10), "| max", int(depth.max()), "| pure-black outside art:", int((depth[~al] == 0).all()))
