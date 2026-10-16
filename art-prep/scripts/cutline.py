#!/usr/bin/env python3
"""Cut line, cut mask and bleed image for print-and-cut (Siser Leonardo, sticker cutters).

Usage:
  cutline.py CLEAN.png OUTDIR --width-in 4 [--offset-mm 1.5] [--bleed-mm 1.0]
             [--holes] [--min-area-mm2 2] [--smooth-mm 0.3] [--name NAME]

Input should already be cleaned (clean_alpha.py --hard or at least --lo/--speck-px),
otherwise ghost pixels and specks become stray cut paths.

Writes (NAME defaults to the input file name):
  NAME_cut.svg       cut path only, true size in mm (Leonardo imports SVG). Red hairline.
  NAME_print.png     art with a bleed band (edge colours pushed outward) and DPI set,
                     so a slightly off cut never shows a white edge.
  NAME_cutmask.png   solid black shape of the cut area on white (for software that traces).
  NAME_cut_preview.png  art with the cut line drawn on it, for approval.

offset-mm: how far outside the art the cut runs (sticker border). 0 = on the edge.
border:    what fills that border: white (default), clear (clear vinyl), or a hex colour.
bleed-mm:  how far colour extends past the cut line: the border colour when offset > 0,
           the art's own edge colours when offset is 0 (die cut on the art edge).
--holes:   also cut interior holes (letter counters etc). Default: outer outline only.
"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from common import load_rgba, save_png, mm_to_px, cv2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("outdir")
    ap.add_argument("--width-in", type=float, required=True, help="printed width of the whole image, inches")
    ap.add_argument("--offset-mm", type=float, default=1.5)
    ap.add_argument("--bleed-mm", type=float, default=1.0)
    ap.add_argument("--holes", action="store_true")
    ap.add_argument("--border", default="white", help="sticker border fill: white, clear, or hex like 000000")
    ap.add_argument("--min-area-mm2", type=float, default=2.0)
    ap.add_argument("--smooth-mm", type=float, default=0.3)
    ap.add_argument("--name", default=None)
    a_ = ap.parse_args()
    os.makedirs(a_.outdir, exist_ok=True)
    name = a_.name or os.path.splitext(os.path.basename(a_.inp))[0]

    rgba = load_rgba(a_.inp)
    H, W = rgba.shape[:2]
    dpi = W / a_.width_in
    pxmm = dpi / 25.4
    art = (rgba[..., 3] >= 128).astype(np.uint8)

    # pad so offsets/bleed past the canvas edge aren't clipped
    pad = int(np.ceil(mm_to_px(a_.offset_mm + a_.bleed_mm + 2, dpi)))
    art_p = np.pad(art, pad)
    rgba_p = np.pad(rgba, ((pad, pad), (pad, pad), (0, 0)))
    Hp, Wp = art_p.shape

    def grow(m, mm):
        r = int(round(mm * pxmm))
        if r <= 0:
            return m.copy()
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        return cv2.dilate(m, k)

    cut = grow(art_p, a_.offset_mm)
    if not a_.holes:  # fill interior holes: outer outline only
        ff = cut.copy() * 255
        h = np.zeros((Hp + 2, Wp + 2), np.uint8)
        cv2.floodFill(ff, h, (0, 0), 128)
        cut = (ff != 128).astype(np.uint8)
    sm = max(1, int(round(a_.smooth_mm * pxmm)))
    cut = (cv2.GaussianBlur(cut.astype(np.float32), (0, 0), sm) >= 0.5).astype(np.uint8)

    mode = cv2.RETR_CCOMP if a_.holes else cv2.RETR_EXTERNAL
    cnts, _ = cv2.findContours(cut, mode, cv2.CHAIN_APPROX_NONE)
    min_area = a_.min_area_mm2 * pxmm * pxmm
    cnts = [cv2.approxPolyDP(c, 0.25 * pxmm / 4, True) for c in cnts if cv2.contourArea(c) >= min_area]

    # SVG in mm, origin = padded canvas top-left
    wmm, hmm = Wp / pxmm, Hp / pxmm
    paths = []
    for c in cnts:
        pts = c.reshape(-1, 2) / pxmm
        d = "M " + " L ".join(f"{x:.3f},{y:.3f}" for x, y in pts) + " Z"
        paths.append(f'<path d="{d}" fill="none" stroke="#FF0000" stroke-width="0.1"/>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{wmm:.3f}mm" height="{hmm:.3f}mm" '
           f'viewBox="0 0 {wmm:.3f} {hmm:.3f}">\n<g id="cut">\n' + "\n".join(paths) + "\n</g>\n</svg>\n")
    open(os.path.join(a_.outdir, f"{name}_cut.svg"), "w").write(svg)

    # Fill between the art and the cut, plus bleed past the cut.
    #  offset > 0 (sticker with a border): the gap is border colour (white by default,
    #    or left clear for clear vinyl); the border colour runs bleed-mm past the cut.
    #  offset == 0 (cut on the art edge): edge colours of the art are pushed outward
    #    bleed-mm, so a slightly off cut never shows the backing.
    reach = grow(cut, a_.bleed_mm) if a_.bleed_mm > 0 else cut.copy()
    band = (reach > 0) & (art_p == 0)
    out = rgba_p.copy()
    if band.any():
        if a_.offset_mm > 0:
            if a_.border != "clear":
                col = (255, 255, 255) if a_.border == "white" else tuple(int(a_.border[i:i + 2], 16) for i in (0, 2, 4))
                under = np.zeros_like(out); under[..., :3] = col; under[..., 3] = (reach > 0) * 255
                u = Image.fromarray(under); u.alpha_composite(Image.fromarray(out)); out = np.array(u)
        else:
            rgb = cv2.cvtColor(np.ascontiguousarray(out[..., :3]), cv2.COLOR_RGB2BGR)
            filled = cv2.inpaint(rgb, band.astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
            out[..., :3][band] = cv2.cvtColor(filled, cv2.COLOR_BGR2RGB)[band]
            out[..., 3][band] = 255
    save_png(out, os.path.join(a_.outdir, f"{name}_print.png"), dpi=round(dpi))

    mask = np.where(cut > 0, 0, 255).astype(np.uint8)
    Image.fromarray(mask).save(os.path.join(a_.outdir, f"{name}_cutmask.png"), dpi=(round(dpi), round(dpi)))

    prev = Image.new("RGBA", (Wp, Hp), (255, 255, 255, 255))
    prev.alpha_composite(Image.fromarray(out))
    d = ImageDraw.Draw(prev)
    lw = max(1, int(round(0.3 * pxmm)))
    for c in cnts:
        pts = [tuple(p) for p in c.reshape(-1, 2).tolist()]
        d.line(pts + [pts[0]], fill=(255, 0, 0, 255), width=lw)
    prev.convert("RGB").save(os.path.join(a_.outdir, f"{name}_cut_preview.png"))

    print(f"dpi {dpi:.0f}; canvas {wmm:.1f} x {hmm:.1f} mm (incl. {pad}px pad); "
          f"cut paths {len(cnts)}; offset {a_.offset_mm} mm; bleed {a_.bleed_mm} mm")


if __name__ == "__main__":
    main()
