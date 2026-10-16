#!/usr/bin/env python3
"""White underbase mask for UV printing (eufyMake) or garment underbase.

Usage:
  white_layer.py CLEAN.png OUTDIR --width-in 4 [--choke-mm 0] [--threshold 128]
                 [--exclude-black] [--name NAME]

Writes:
  NAME_white.png        white where white ink goes, transparent elsewhere (layer file)
  NAME_white_mask.png   black = white ink, on white (for software that wants a mask)
  NAME_white_check.png  art on a dark background with the white area outlined, for approval

choke-mm: pull the white in from the colour edge so it never peeks out.
  eufyMake Studio has its own "White Underbase Choke" (default 0.2 mm) and builds white
  from the image's transparency, so for eufyMake keep --choke-mm 0 here and let the
  software choke; this file is mainly a check of what white WILL print. Use a choke
  here only when the software takes a separate white layer.
--exclude-black: no white ink under near-black art (black on a dark substrate needs none).
The run also counts isolated white dots: any above zero usually means the art wasn't
cleaned first (ghost pixels and specks are exactly what prints as stray white).
"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from common import load_rgba, mm_to_px, cv2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("outdir")
    ap.add_argument("--width-in", type=float, required=True)
    ap.add_argument("--choke-mm", type=float, default=0.0)
    ap.add_argument("--threshold", type=int, default=128)
    ap.add_argument("--exclude-black", action="store_true", help="no white under near-black art")
    ap.add_argument("--name", default=None)
    a_ = ap.parse_args()
    os.makedirs(a_.outdir, exist_ok=True)
    name = a_.name or os.path.splitext(os.path.basename(a_.inp))[0]
    rgba = load_rgba(a_.inp)
    H, W = rgba.shape[:2]
    dpi = W / a_.width_in
    m = (rgba[..., 3] >= a_.threshold).astype(np.uint8)
    if a_.exclude_black:
        m[rgba[..., :3].max(axis=2) < 40] = 0
    r = int(round(mm_to_px(a_.choke_mm, dpi)))
    if r > 0:
        m = cv2.erode(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    stray = 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    tiny = [i for i in range(1, n) if st[i][4] < 9]
    stray = len(tiny)

    layer = np.zeros((H, W, 4), np.uint8)
    layer[m > 0] = (255, 255, 255, 255)
    Image.fromarray(layer).save(os.path.join(a_.outdir, f"{name}_white.png"), dpi=(round(dpi),) * 2)
    Image.fromarray(np.where(m > 0, 0, 255).astype(np.uint8)).save(
        os.path.join(a_.outdir, f"{name}_white_mask.png"), dpi=(round(dpi),) * 2)

    chk = Image.new("RGBA", (W, H), (40, 40, 48, 255))
    chk.alpha_composite(Image.fromarray(rgba))
    edge = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    c = np.array(chk)
    c[edge] = (0, 255, 120, 255)
    Image.fromarray(c).convert("RGB").save(os.path.join(a_.outdir, f"{name}_white_check.png"))
    print(f"white area {m.mean() * 100:.1f}% of canvas; choke {a_.choke_mm} mm ({r}px at {dpi:.0f} dpi); "
          f"isolated white dots < 9px: {stray}")


if __name__ == "__main__":
    main()
