#!/usr/bin/env python3
"""Tiered ('challenge coin') depth map for raised UV printing, computed from the art's own pixels.
Usage: depthmap3.py ART.png MASKS.npz OUTDIR [--border 150 --obj-mid 196 --obj-top 234 --field 10 --texture 0]
Black = flat/lowest, white = tallest, transparent = pure black.
Tiers (0-255):  FIELD (ring/banner background, sky)  <  SCENE (rocks/trees, always below the border)
                <  BORDER (ring lines, ring + banner lettering, stars: ALL the same level)
                <  OBJ_MID (flag, carved 250: same level)  <  OBJ_TOP (the Jeep).
Tops are rounded (bevel) and the outer rim tapers off, per eufyMake's depth-map guide (no flat pure-white tops)."""
import argparse, os, numpy as np, cv2
from PIL import Image
ap = argparse.ArgumentParser()
ap.add_argument("art"); ap.add_argument("masks"); ap.add_argument("out")
ap.add_argument("--field", type=float, default=10); ap.add_argument("--border", type=float, default=150)
ap.add_argument("--obj-mid", type=float, default=196); ap.add_argument("--obj-top", type=float, default=234)
ap.add_argument("--scene-max", type=float, default=100, help="tallest background rock, kept under the border")
ap.add_argument("--texture", type=float, default=0.0, help="extra grain depth (0 = none)")
ap.add_argument("--bevel", type=float, default=3.5, help="rounded-edge width in base px")
A = ap.parse_args(); os.makedirs(A.out, exist_ok=True)

pil = Image.open(A.art).convert("RGBA"); dpi = Image.open(A.art).info.get("dpi")
im = np.array(pil); Hh, Ww = im.shape[:2]; s = Ww / 1254.0
rgb, al = im[..., :3], im[..., 3] > 0
bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
L = lab[..., 0] / 255 * 100; ch = np.hypot(lab[..., 1] - 128, lab[..., 2] - 128)
Hue, S, V = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
M = np.load(A.masks)
def mk(name, soft=1.2):
    m = cv2.resize(M[name].astype(np.float32), (Ww, Hh), interpolation=cv2.INTER_LINEAR)
    return np.clip((cv2.GaussianBlur(m, (0, 0), soft * s) - 0.5) * 3 + 0.5, 0, 1)
scene, jeep, flag, pole, num, block = (mk(n) for n in ("scene", "jeep", "flag", "pole", "num", "block"))
jeepb, flagb, numb = (m > 0.5 for m in (jeep, flag, num))
smooth = lambda x: (lambda c: c * c * (3 - 2 * c))(np.clip(x, 0, 1))
dist_in = lambda m: cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5) / s
T = np.clip((L - cv2.GaussianBlur(L, (0, 0), 2.5 * s)) / 30, -1, 1)       # rock grain / folds, around 0
tx = A.texture

def clean_cls(m, close=2, minpx=40):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * max(1, int(close * s)) + 1,) * 2)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, k)
    n, lbl, st, _ = cv2.connectedComponentsWithStats(m)
    keep = np.zeros(n, bool); keep[1:] = st[1:, cv2.CC_STAT_AREA] >= minpx * s * s
    return keep[lbl]
cream = (L > 62) & (ch < 28); gold = (Hue > 28) & (Hue < 55) & (S > 0.40) & (V > 0.55)
red = ((Hue < 14) | (Hue > 340)) & (S > 0.55) & (V > 0.25)
cream, gold, red = (clean_cls(c) & al for c in (cream, gold, red))
graphic = cream | gold | red                                     # borders, lettering, stars, bunting
xx = (np.arange(Ww)[None, :] / s) * np.ones((Hh, 1)); yy = (np.arange(Hh)[:, None] / s) * np.ones((1, Ww))
side_tree = ((xx < 150) | (xx > 1104)) & (yy > 590) & (yy < 860)

# ---- ring / banner: field low; every border + letter + star at ONE level ----
ring = np.full((Hh, Ww), A.field, np.float32)
ring = np.where(side_tree & ~graphic, 0.62 * A.border + 6 * T * (tx > 0) * tx, ring)
d = dist_in(graphic)
prof = 0.6 + 0.4 * smooth(d / A.bevel)
ring = np.where(graphic, A.field + (A.border - A.field) * prof + 3 * T + 8 * tx * T, ring)

# ---- scene: background stays below the border; objects pop above it ----
sky = (Hue > 185) & (Hue < 250) & (S > 0.22) & (V > 0.50)
green = (Hue > 55) & (Hue < 170) & (V < 0.55)
sm = A.scene_max
terrain = 0.28 * sm + 0.55 * sm * smooth((yy - 300) / 520.0) + 0.16 * sm * T + 0.14 * sm * (L / 100 - 0.5)
terrain = np.where(green, 0.48 * sm + 0.17 * sm * smooth((yy - 300) / 520.0) + 0.12 * sm * T, terrain)
wfar = 1 - smooth((yy - 500) / 150.0)
terrain = np.where(green, terrain, terrain * (1 - wfar) + (0.25 * sm + 0.08 * sm * T) * wfar)
terrain = np.where(sky, 0.05 * sm, terrain)
wb = cv2.GaussianBlur(block.astype(np.float32), (0, 0), 14 * s) * (1 - sky.astype(np.float32))
terrain = terrain * (1 - wb) + (0.62 * sm + 0.18 * sm * T) * wb          # rock mass behind the 250: soft hill
terrain = np.clip(terrain + 10 * tx * T, 0, A.border - 12)
dn = dist_in(numb); df = dist_in(flagb); dj = dist_in(jeepb)
mid_prof = lambda dd: 0.82 + 0.18 * smooth(dd / 5)
terrain = np.where(numb, (A.obj_mid + 6 * T + 8 * tx * T) * mid_prof(dn), terrain)
terrain = np.where(flagb, (A.obj_mid - 4 + 8 * (L / 100 - 0.5) + 6 * T + 8 * tx * T) * mid_prof(df), terrain)
terrain = np.where(pole > 0.5, A.obj_mid, terrain)
terrain = np.where(jeepb, (A.obj_top - 14 + 14 * np.clip(L / 100, 0, 1) + 5 * T + 8 * tx * T) * (0.82 + 0.18 * smooth(dj / 5)), terrain)

h = ring * (1 - scene) + terrain * scene
h = np.where(al, h, 0).astype(np.float32)
h = cv2.GaussianBlur(h, (0, 0), 0.9 * s)
de = dist_in(al); h *= 0.30 + 0.70 * smooth(de / 9.0)               # tapered outer rim
depth = np.where(al, np.clip(h, 0, 245), 0).astype(np.uint8)
Image.fromarray(depth, "L").save(os.path.join(A.out, "depth.png"), dpi=dpi if dpi else (72, 72))

rs = lambda a: cv2.resize(a, (1254, 1254), interpolation=cv2.INTER_AREA)
g = rs(depth).astype(np.float32)                                     # shade the preview at 1254 px so it looks the same at any scale
gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
al_s = rs(al.astype(np.uint8) * 255) > 127
relief = np.where(al_s, np.clip(0.55 + (-gx - gy) / (255 * 2.2), 0, 1) * 225, 235).astype(np.uint8)
art_bg = rs(np.where(al[..., None], rgb, 255).astype(np.uint8))
Image.fromarray(np.hstack([art_bg, np.dstack([rs(depth)] * 3), np.dstack([relief] * 3)])).save(os.path.join(A.out, "depth_preview.png"))
vals = lambda m: int(np.median(depth[m & al])) if (m & al).any() else -1
print("levels (median): field/ring-bg", vals(~graphic & (scene < .5) & ~side_tree), "| border+lettering", vals(graphic & (scene < .5)),
      "| flag", vals(flagb), "| 250", vals(numb), "| jeep", vals(jeepb), "| max", int(depth.max()),
      "| pure-black outside:", int((depth[~al] == 0).all()))
