#!/usr/bin/env python3
"""Spot-colour separations for screen printing (one film per ink).

Usage:
  separations.py CLEAN.png OUTDIR --width-in 12 [--colors 4 | --palette FF0000,1A3FA0,FFFFFF]
                 [--garment 000000] [--underbase] [--choke-mm 0.3] [--speck-px 20]

How it works: every visible pixel is assigned to its nearest ink (k-means in L*a*b*,
or the inks you list). Each ink becomes a black-on-white film plate. Pixels matching the
garment colour get no ink (the shirt shows through). --underbase adds a white plate
under all inks for dark garments, choked so it never peeks out.

Honest limits: this is right for flat-colour art (logos, text, few solid colours).
Photographic art (gradients, chrome, photos) posterizes into hard bands; it needs
simulated-process separation with halftones, which dedicated software does far better.
The script reports the colour-fit error so you can see which case you're in.

Writes: plate_NN_<hex>.tif (black = ink), plate_00_underbase.tif, seps_preview.png
(simulated print on the garment colour), seps_sheet.png (all plates side by side),
separations.json (inks, coverage %, print order, fit error).
"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from common import load_rgba, write_json, mm_to_px, cv2


def to_lab(rgb):
    return cv2.cvtColor((rgb.astype(np.float32) / 255.0).reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3)


def nearest(lab, ilab, chunk=1_000_000):
    """Index of the nearest ink for each pixel, in chunks so 4x images fit in memory."""
    out = np.empty(len(lab), np.int32)
    for i in range(0, len(lab), chunk):
        out[i:i + chunk] = np.argmin(((lab[i:i + chunk, None, :] - ilab[None]) ** 2).sum(-1), axis=1)
    return out


def hexrgb(h):
    h = h.strip().lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("outdir")
    ap.add_argument("--width-in", type=float, required=True)
    ap.add_argument("--colors", type=int, default=4)
    ap.add_argument("--palette", default="")
    ap.add_argument("--garment", default="")
    ap.add_argument("--garment-tol", type=float, default=12.0, help="L*a*b* distance treated as shirt colour")
    ap.add_argument("--underbase", action="store_true")
    ap.add_argument("--choke-mm", type=float, default=0.3)
    ap.add_argument("--speck-px", type=int, default=20)
    a_ = ap.parse_args()
    os.makedirs(a_.outdir, exist_ok=True)
    rgba = load_rgba(a_.inp)
    H, W = rgba.shape[:2]
    dpi = W / a_.width_in
    vis = rgba[..., 3] >= 128
    px = rgba[vis][:, :3]
    lab = to_lab(px)

    if a_.palette:
        inks = np.array([hexrgb(h) for h in a_.palette.split(",")])
        ilab = to_lab(inks)
        lbl = nearest(lab, ilab)
    else:
        rng = np.random.default_rng(0)
        s = lab[rng.choice(len(lab), min(len(lab), 80000), replace=False)]
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.2)
        _, _, cen = cv2.kmeans(s, a_.colors, None, crit, 3, cv2.KMEANS_PP_CENTERS)
        lbl = nearest(lab, cen)
        inks = np.array([np.median(px[lbl == k], axis=0) if (lbl == k).any() else [0, 0, 0]
                         for k in range(len(cen))]).astype(np.uint8)
        ilab = to_lab(inks)
    err = float(np.linalg.norm(lab - ilab[lbl], axis=1).mean())

    labmap = np.full((H, W), -1, np.int32)
    labmap[vis] = lbl
    garment = hexrgb(a_.garment) if a_.garment else None
    if garment is not None:
        glab = to_lab(garment[None])[0]
        for k in range(len(inks)):
            if np.linalg.norm(ilab[k] - glab) <= a_.garment_tol:
                labmap[labmap == k] = -2  # shirt shows through, no ink

    order = sorted(range(len(inks)), key=lambda k: -ilab[k][0])  # light to dark
    plates, info = [], []
    for n, k in enumerate(order, start=1):
        m = (labmap == k).astype(np.uint8)
        if not m.any():
            continue
        cnt, cl, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        for i in range(1, cnt):
            if st[i][4] < a_.speck_px:
                m[cl == i] = 0
        hexs = "%02X%02X%02X" % tuple(inks[k])
        fn = f"plate_{n:02d}_{hexs}.tif"
        Image.fromarray(np.where(m > 0, 0, 255).astype(np.uint8)).save(
            os.path.join(a_.outdir, fn), dpi=(round(dpi),) * 2, compression="tiff_lzw")
        plates.append((fn, m, inks[k]))
        info.append({"plate": fn, "ink_hex": hexs, "coverage_pct": round(float(m.mean() * 100), 2)})

    ub = None
    if a_.underbase:
        ub = np.isin(labmap, [k for k in range(len(inks))]).astype(np.uint8)
        r = int(round(mm_to_px(a_.choke_mm, dpi)))
        if r > 0:
            ub = cv2.erode(ub, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
        Image.fromarray(np.where(ub > 0, 0, 255).astype(np.uint8)).save(
            os.path.join(a_.outdir, "plate_00_underbase.tif"), dpi=(round(dpi),) * 2, compression="tiff_lzw")
        info.insert(0, {"plate": "plate_00_underbase.tif", "ink_hex": "FFFFFF (underbase)",
                        "coverage_pct": round(float(ub.mean() * 100), 2), "choke_mm": a_.choke_mm})

    shirt = tuple(int(v) for v in (garment if garment is not None else (255, 255, 255)))
    prev = np.zeros((H, W, 3), np.uint8); prev[:] = shirt
    for fn, m, ink in plates:
        prev[m > 0] = ink
    Image.fromarray(prev).save(os.path.join(a_.outdir, "seps_preview.png"))

    thumbs = [Image.fromarray(np.where(m > 0, 0, 255).astype(np.uint8)).convert("RGB") for _, m, _ in plates]
    names = [fn for fn, _, _ in plates]
    if ub is not None:
        thumbs.insert(0, Image.fromarray(np.where(ub > 0, 0, 255).astype(np.uint8)).convert("RGB"))
        names.insert(0, "underbase")
    tw = 420; th = int(H * tw / W)
    sheet = Image.new("RGB", (tw * len(thumbs), th + 24), "white")
    d = ImageDraw.Draw(sheet)
    for i, (t, nme) in enumerate(zip(thumbs, names)):
        sheet.paste(t.resize((tw, th)), (i * tw, 24)); d.text((i * tw + 6, 6), nme, fill=(0, 0, 0))
        d.rectangle([i * tw, 24, i * tw + tw - 1, 24 + th - 1], outline=(180, 180, 180))
    sheet.save(os.path.join(a_.outdir, "seps_sheet.png"))

    kind = "flat - separations should be clean" if err < 6 else (
        "mixed - check edges and gradients" if err < 12 else
        "photographic - spot plates will posterize; use simulated process or DTF/DTG")
    out = {"dpi": round(dpi), "fit_error_deltaE": round(err, 2), "verdict": kind,
           "garment": a_.garment or "white", "print_order": [p["plate"] for p in info], "plates": info}
    write_json(out, os.path.join(a_.outdir, "separations.json"))
    print(f"{len(plates)} ink plates{' + underbase' if ub is not None else ''}; fit error {err:.1f} -> {kind}")
    for p in info:
        print(" ", p["plate"], p["ink_hex"], f'{p["coverage_pct"]}%')


if __name__ == "__main__":
    main()
