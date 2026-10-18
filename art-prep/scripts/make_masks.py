#!/usr/bin/env python3
"""Region masks for a semantic depth map (or any "which part is which" job).

Usage:
  make_masks.py ART.png REGIONS.json OUTDIR

Regions are named areas of the art (e.g. "scene", "jeep", "flag", "numerals"). You place
rough outlines in the art's own pixel coordinates (read them off `grid_zoom.py` crops),
and the script tightens them against the art's real colours. Nothing is drawn freehand
into the result: every mask edge comes from the pixels.

REGIONS.json:
{
  "regions": {                       # processed in order; later ones may reference earlier ones
    "scene":  {"poly": [[x,y], ...]},                        # polygon only, clipped to the art's alpha
    "jeep":   {"poly": [[x,y], ...], "grabcut": true,        # polygon refined by GrabCut
               "grow": 22, "shrink": 22, "within": "scene"},
    "digits": {"poly": [[x,y], ...],                         # colour rule inside a polygon
               "colour": {"L_min": 58, "chroma_max": 32},
               "minus": ["jeep", "flag"], "close": 11, "open": 5, "min_area": 2500},
    "pole":   {"line": [[487,243],[479,535]], "width": 7}    # a stroke
  }
}
Region keys (all optional except one of poly/line/colour-only):
  poly, line+width      shape the region starts from
  grabcut, grow, shrink GrabCut refinement seeded by the polygon (shrink = sure inside, grow = sure outside)
  colour                {"L_min","L_max","chroma_max","chroma_min","hue":[lo,hi],"s_min","v_min","v_max"}
                        keep only pixels that satisfy the rule (L is 0-100, hue 0-360, s/v 0-1)
  within                name of an earlier region to intersect with
  minus                 list of earlier regions to subtract
  close, open, min_area morphology (px, art scale) and drop-small-blobs cleanup

Writes OUTDIR/masks.npz (one uint8 mask per region) and OUTDIR/masks_overlay.png
(each region tinted + a legend) so the person can approve or correct before heights are built.
Coordinates are in the pixels of the file you pass in; use the native-size clean file and
let depthmap.py resize the masks for any larger master.
"""
import argparse, json, os
import numpy as np, cv2
from PIL import Image, ImageDraw

PALETTE = [(0, 90, 255), (255, 160, 0), (0, 255, 0), (255, 0, 255), (255, 255, 0), (255, 0, 0),
           (0, 220, 220), (160, 80, 255), (255, 120, 120), (120, 255, 120)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("art"); ap.add_argument("regions"); ap.add_argument("out")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    spec = json.load(open(a.regions))["regions"]
    im = np.array(Image.open(a.art).convert("RGBA")); rgb, al = im[..., :3], im[..., 3] > 0
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR); H, W = al.shape
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    L = lab[..., 0] / 255 * 100; ch = np.hypot(lab[..., 1] - 128, lab[..., 2] - 128)
    Hue, S, V = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
    ell = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))

    def poly(pts):
        m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [np.array(pts, np.int32)], 1); return m

    def grab(prior, grow, shrink, iters=5):
        sure_fg = cv2.erode(prior, ell(shrink)); outer = cv2.dilate(prior, ell(grow))
        m = np.full((H, W), cv2.GC_BGD, np.uint8)
        m[outer > 0] = cv2.GC_PR_BGD; m[prior > 0] = cv2.GC_PR_FGD; m[sure_fg > 0] = cv2.GC_FGD
        bg, fg = np.zeros((1, 65)), np.zeros((1, 65))
        cv2.grabCut(bgr, m, None, bg, fg, iters, cv2.GC_INIT_WITH_MASK)
        r = ((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)).astype(np.uint8)
        r = cv2.morphologyEx(r, cv2.MORPH_CLOSE, ell(3)); return cv2.morphologyEx(r, cv2.MORPH_OPEN, ell(2))

    def colour_rule(c):
        m = np.ones((H, W), bool)
        if "L_min" in c: m &= L > c["L_min"]
        if "L_max" in c: m &= L < c["L_max"]
        if "chroma_max" in c: m &= ch < c["chroma_max"]
        if "chroma_min" in c: m &= ch > c["chroma_min"]
        if "hue" in c:
            lo, hi = c["hue"]; m &= ((Hue >= lo) & (Hue <= hi)) if lo <= hi else ((Hue >= lo) | (Hue <= hi))
        if "s_min" in c: m &= S > c["s_min"]
        if "v_min" in c: m &= V > c["v_min"]
        if "v_max" in c: m &= V < c["v_max"]
        return m.astype(np.uint8)

    out = {}
    for name, r in spec.items():
        if "poly" in r: m = poly(r["poly"])
        elif "line" in r:
            m = np.zeros((H, W), np.uint8); cv2.line(m, tuple(map(int, r["line"][0])), tuple(map(int, r["line"][1])), 1, int(r.get("width", 5)))
        else: m = al.astype(np.uint8)
        if r.get("grabcut"): m = grab(m, int(r.get("grow", 18)), int(r.get("shrink", 14)))
        if "colour" in r: m = m & colour_rule(r["colour"])
        if "within" in r: m = m & out[r["within"]]
        for other in r.get("minus", []): m = m & (1 - out[other])
        if r.get("close"): m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, ell(int(r["close"]) // 2))
        if r.get("open"): m = cv2.morphologyEx(m, cv2.MORPH_OPEN, ell(int(r["open"]) // 2))
        if r.get("min_area"):
            n, lbl, st, _ = cv2.connectedComponentsWithStats(m)
            for i in range(1, n):
                if st[i, cv2.CC_STAT_AREA] < r["min_area"]: m[lbl == i] = 0
        out[name] = (m & al.astype(np.uint8)).astype(np.uint8)

    np.savez_compressed(os.path.join(a.out, "masks.npz"), **out)
    ov = rgb.astype(np.float32).copy()
    for i, (name, m) in enumerate(out.items()):
        c = np.array(PALETTE[i % len(PALETTE)]); ov[m > 0] = ov[m > 0] * 0.55 + c * 0.45
    img = Image.fromarray(np.where(al[..., None], ov, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    for i, name in enumerate(out):
        c = PALETTE[i % len(PALETTE)]; y = 8 + i * 22
        d.rectangle([8, y, 24, y + 14], fill=c, outline=(0, 0, 0)); d.text((30, y), f"{name} ({int(out[name].sum())} px)", fill=(0, 0, 0))
    img.save(os.path.join(a.out, "masks_overlay.png"))
    print({k: int(v.sum()) for k, v in out.items()})


if __name__ == "__main__":
    main()
