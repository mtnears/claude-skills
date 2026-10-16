#!/usr/bin/env python3
"""Inspect a piece of art for print/cut problems. Read-only: changes nothing.

Usage:
  inspect_art.py ART.png OUTDIR [--lo 16] [--hi 240] [--speck-px 25] [--target-in 10]

Writes OUTDIR/report.json, OUTDIR/report.md and OUTDIR/overlay.png.
Overlay colours: magenta = ghost pixels (nearly clear, still non-zero),
cyan = soft edge (semi-transparent), red boxes = specks (tiny islands of art),
yellow numbered boxes = background-coloured islands inside the art (often
leftover from background removal, e.g. the holes in A/P/R/0; sometimes real
white parts of the design, so a human picks which ones to clear).
"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from common import load_rgba, estimate_bg, solid_background, find_bg_islands, write_json, cv2


def classify(rgba):
    """Flat-colour vs photographic: how well 8 colours describe the art."""
    a = rgba[..., 3]
    px = rgba[a >= 250][:, :3]
    if len(px) < 50:
        return "empty", 0.0, 0
    rng = np.random.default_rng(0)
    s = px[rng.choice(len(px), min(len(px), 60000), replace=False)].astype(np.float32)
    lab = cv2.cvtColor((s / 255.0).reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3)  # true L*a*b*
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    _, labels, centers = cv2.kmeans(lab, 8, None, crit, 2, cv2.KMEANS_PP_CENTERS)
    err = float(np.linalg.norm(lab - centers[labels.ravel()], axis=1).mean())
    q = (s // 16).astype(int)
    uniq = len(np.unique(q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]))
    kind = "flat" if err < 6 else ("mixed" if err < 12 else "photographic")
    return kind, err, uniq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("art"); ap.add_argument("outdir")
    ap.add_argument("--lo", type=int, default=16, help="alpha below this counts as ghost")
    ap.add_argument("--hi", type=int, default=240, help="alpha at/above this counts as solid")
    ap.add_argument("--speck-px", type=int, default=25, help="art islands smaller than this are specks")
    ap.add_argument("--bg", default="", help="old background colour as hex, when it can't be detected")
    ap.add_argument("--bg-tol", type=int, default=28, help="colour distance to call a pixel background-like")
    ap.add_argument("--near-px", type=int, default=0, help="max distance from real transparency (0 = auto)")
    ap.add_argument("--target-in", type=float, default=None, help="intended print width in inches")
    a_ = ap.parse_args()
    os.makedirs(a_.outdir, exist_ok=True)

    rgba = load_rgba(a_.art)
    H, W = rgba.shape[:2]
    alpha = rgba[..., 3]
    info = Image.open(a_.art).info
    rep = {"file": os.path.basename(a_.art), "width_px": W, "height_px": H,
           "embedded_dpi": info.get("dpi"), "mode": Image.open(a_.art).mode}

    solid = solid_background(rgba)
    rep["has_transparency"] = bool((alpha < 255).any())
    rep["solid_background_rgb"] = None if solid is None else [int(v) for v in solid]

    total = alpha.size
    ghost = (alpha > 0) & (alpha < a_.lo)
    semi = (alpha >= a_.lo) & (alpha < a_.hi)
    rep["alpha"] = {"clear_pct": round(float((alpha == 0).mean() * 100), 2),
                    "ghost_px": int(ghost.sum()), "soft_edge_px": int(semi.sum()),
                    "solid_pct": round(float((alpha >= a_.hi).mean() * 100), 2),
                    "distinct_alpha_levels": int(len(np.unique(alpha)))}

    # specks: tiny islands of visible art
    vis = (alpha >= a_.lo).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(vis, connectivity=8)
    specks = [(int(stats[i][0]), int(stats[i][1]), int(stats[i][2]), int(stats[i][3]), int(stats[i][4]))
              for i in range(1, n) if stats[i][4] < a_.speck_px]
    rep["specks"] = {"count": len(specks), "max_px": a_.speck_px}

    # background-coloured islands inside the art
    if a_.bg:
        bg = np.array([int(a_.bg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)])
    else:
        bg = estimate_bg(rgba) if solid is None else solid
    rep["background_estimate_rgb"] = None if bg is None else [int(v) for v in bg]
    lab_isl, isl = find_bg_islands(rgba, bg, a_.hi, a_.bg_tol, a_.near_px)
    rep["bg_islands"] = [{"id": k + 1, "area_px": i[1], "bbox_xywh": list(i[2])} for k, i in enumerate(isl)]

    # halo: a soft-edge pixel is "halo" when it is pulled toward the old background,
    # away from the solid art next to it (compare with the local solid-art colour).
    if semi.sum() and bg is not None:
        solid = (alpha >= a_.hi).astype(np.float32)
        k = (7, 7)
        num = cv2.blur(rgba[..., :3].astype(np.float32) * solid[..., None], k)
        den = cv2.blur(solid, k)[..., None]
        inner = num / np.maximum(den, 1e-3)
        has = (den[..., 0] > 0.05) & semi
        e = rgba[..., :3].astype(np.float32)
        d_in = np.abs(e - inner).max(axis=2)
        d_bg = np.abs(e - bg.astype(np.float32)).max(axis=2)
        contrast = np.abs(inner - bg.astype(np.float32)).max(axis=2) > 60
        halo = has & contrast & (d_bg < d_in)
        rep["halo_pct_of_edge"] = round(float(halo.sum() / max(1, (has & contrast).sum()) * 100), 1)
    else:
        rep["halo_pct_of_edge"] = 0.0

    kind, err, uniq = classify(rgba)
    rep["art_type"] = kind
    rep["eight_colour_error"] = round(err, 2)
    rep["colour_bins_used"] = uniq

    bb = Image.fromarray(rgba).getbbox() or (0, 0, W, H)
    rep["art_bbox_xywh"] = [bb[0], bb[1], bb[2] - bb[0], bb[3] - bb[1]]
    sizes = {}
    for dpi in (150, 300):
        sizes[f"{dpi}dpi"] = f'{W / dpi:.1f} x {H / dpi:.1f} in'
    rep["max_print_size"] = sizes
    if a_.target_in:
        rep["dpi_at_target"] = round(W / a_.target_in)

    # overlay
    ov = Image.new("RGBA", (W, H), (235, 235, 235, 255))
    checker = ((np.indices((H, W)).sum(axis=0) // 16) % 2).astype(np.uint8) * 25 + 205
    ov = Image.fromarray(np.dstack([checker] * 3 + [np.full((H, W), 255, np.uint8)]))
    ov.alpha_composite(Image.fromarray(rgba))
    o = np.array(ov)
    o[ghost] = (255, 0, 255, 255)
    o[semi & (alpha < 128)] = (0, 200, 255, 255)
    ov = Image.fromarray(o)
    d = ImageDraw.Draw(ov)
    for x, y, w, h, _ in specks:
        d.rectangle([x - 3, y - 3, x + w + 3, y + h + 3], outline=(255, 0, 0, 255), width=2)
    for k, i in enumerate(isl):
        x, y, w, h = i[2]
        d.rectangle([x - 2, y - 2, x + w + 2, y + h + 2], outline=(255, 200, 0, 255), width=2)
        d.text((x, max(0, y - 12)), str(k + 1), fill=(255, 120, 0, 255))
    ov.convert("RGB").save(os.path.join(a_.outdir, "overlay.png"))

    # numbered close-ups of each background-coloured island, for the human to pick from
    if isl:
        cell, cols = 150, 8
        rows = (len(isl) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * (cell + 16)), (255, 255, 255))
        sd = ImageDraw.Draw(sheet)
        mag = np.array(Image.fromarray(rgba).convert("RGBA"))
        bgc = Image.new("RGBA", (W, H), (255, 0, 255, 255)); bgc.alpha_composite(Image.fromarray(rgba))
        base = np.array(bgc.convert("RGB"))
        for k, i in enumerate(isl):
            x, y, w, h = i[2]
            r = max(w, h) * 2 + 10
            cx, cy = x + w // 2, y + h // 2
            x0, y0 = max(0, cx - r), max(0, cy - r)
            crop = Image.fromarray(base[y0:cy + r, x0:cx + r]).copy()
            cd = ImageDraw.Draw(crop)
            cd.rectangle([x - x0 - 2, y - y0 - 2, x - x0 + w + 2, y - y0 + h + 2], outline=(255, 160, 0), width=1)
            crop = crop.resize((cell, cell), Image.NEAREST)
            gx, gy = (k % cols) * cell, (k // cols) * (cell + 16)
            sheet.paste(crop, (gx, gy + 16))
            sd.text((gx + 4, gy + 2), f"#{k + 1}  {i[1]}px  @{x},{y}", fill=(0, 0, 0))
        sheet.save(os.path.join(a_.outdir, "islands.png"))

    write_json(rep, os.path.join(a_.outdir, "report.json"))
    lines = [f"# Inspection: {rep['file']}", "",
             f"- Size: {W} x {H} px; embedded DPI: {rep['embedded_dpi']}",
             f"- Art type: **{kind}** (8-colour fit error {rep['eight_colour_error']}; flat < 6, photographic > 12)",
             f"- Transparency: {'yes' if rep['has_transparency'] else 'no'}"
             + (f"; solid background {rep['solid_background_rgb']}" if solid is not None else ""),
             f"- Ghost pixels (alpha 1-{a_.lo - 1}): {rep['alpha']['ghost_px']}",
             f"- Soft edge pixels (alpha {a_.lo}-{a_.hi - 1}): {rep['alpha']['soft_edge_px']}"
             f" ({rep['halo_pct_of_edge']}% look like the old background = halo)",
             f"- Specks (< {a_.speck_px} px): {len(specks)}",
             (f"- Background-coloured islands inside the art: {len(isl)} (numbered close-ups in islands.png; magenta = transparent)"
              if bg is not None else "- Leftover-background check skipped: the old background colour is unknown "
              "(transparent pixels were zeroed). Pass --bg RRGGBB if you know it."),
             f"- Max print size: {sizes['150dpi']} at 150 dpi, {sizes['300dpi']} at 300 dpi"]
    if a_.target_in:
        lines.append(f"- At {a_.target_in} in wide: {rep['dpi_at_target']} dpi")
    open(os.path.join(a_.outdir, "report.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
