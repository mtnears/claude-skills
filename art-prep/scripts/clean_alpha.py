#!/usr/bin/env python3
"""Clean an image's transparency for printing and cutting.

Usage:
  clean_alpha.py IN.png OUT.png [options]

Steps (each optional, in this order):
  --remove-bg            make a solid background colour transparent (flood from the edges only)
  --lo N / --hi N        alpha < lo -> 0 (kills ghost pixels); alpha >= hi -> 255
  --speck-px N           delete islands of art smaller than N px
  --clear-islands IDS    make background-coloured islands transparent: "all" or "1,4,7"
                         (ids from inspect_art.py run on THIS input file with the same
                         --hi/--bg-tol/--near-px; they are matched before any other step.
                         If you need --remove-bg, run it as its own pass and inspect that output.)
  --fill-islands IDS     instead fill them with --fill-rgb (default black)
  --defringe             remove the old background colour bleeding into soft edges
  --hard [T]             binary alpha at threshold T (default 128): crisp edge for
                         UV white ink and contour detection. Keeps nothing semi-transparent.

Everything is computed from the input pixels; nothing is redrawn.
"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from common import load_rgba, save_png, estimate_bg, solid_background, find_bg_islands, cv2


def parse_ids(s, n):
    if not s:
        return set()
    if s == "all":
        return set(range(1, n + 1))
    return {int(x) for x in s.split(",") if x.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--remove-bg", action="store_true")
    ap.add_argument("--bg", default="", help="old background colour as hex, when it can't be detected")
    ap.add_argument("--bg-tol", type=int, default=28)
    ap.add_argument("--lo", type=int, default=16)
    ap.add_argument("--hi", type=int, default=240)
    ap.add_argument("--speck-px", type=int, default=0)
    ap.add_argument("--clear-islands", default="")
    ap.add_argument("--fill-islands", default="")
    ap.add_argument("--near-px", type=int, default=0)
    ap.add_argument("--fill-rgb", default="0,0,0")
    ap.add_argument("--defringe", action="store_true")
    ap.add_argument("--hard", nargs="?", const=128, type=int, default=None)
    ap.add_argument("--dpi", type=int, default=None, help="DPI tag to write (default: keep the input's). "
                    "Set width_px / print_width_in so device software imports at the right size")
    a_ = ap.parse_args()

    rgba = load_rgba(a_.inp).astype(np.int32)
    log = []

    if a_.remove_bg:
        bg = solid_background(rgba.astype(np.uint8))
        if bg is None:
            bg = estimate_bg(rgba.astype(np.uint8))
        if bg is None:
            raise SystemExit("no background colour found to remove: pass --bg RRGGBB")
        near = (np.abs(rgba[..., :3] - bg.astype(int)).max(axis=2) <= a_.bg_tol).astype(np.uint8)
        # flood only background connected to the border, so enclosed areas are left for review
        n, lab = cv2.connectedComponents(near, connectivity=4)
        edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
        m = np.isin(lab, list(edge))
        rgba[..., 3][m] = 0
        log.append(f"removed background {bg.astype(int).tolist()} connected to the edge: {int(m.sum())} px")

    if a_.clear_islands or a_.fill_islands:
        # numbered on the input as given, exactly as inspect_art.py numbered them
        bg = (np.array([int(a_.bg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]) if a_.bg
              else estimate_bg(rgba.astype(np.uint8)))
        if bg is None:
            raise SystemExit("old background colour unknown: pass --bg RRGGBB")
        dist = np.abs(rgba[..., :3] - bg.astype(int)).max(axis=2)
        lab, isl = find_bg_islands(rgba.astype(np.uint8), bg, a_.hi, a_.bg_tol, a_.near_px)
        clr = parse_ids(a_.clear_islands, len(isl))
        fil = parse_ids(a_.fill_islands, len(isl))
        fill = np.array([int(v) for v in a_.fill_rgb.split(",")])
        for k, i in enumerate(isl):
            m = lab == i[0]
            # include the soft ring around the island so no light outline is left behind
            ring = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~m
            ringlike = ring & (dist <= a_.bg_tol + 40)
            if (k + 1) in clr:
                rgba[..., 3][m | ringlike] = 0
            elif (k + 1) in fil:
                rgba[..., :3][m | ringlike] = fill
        log.append(f"islands: {len(isl)} found; cleared {sorted(clr)}; filled {sorted(fil)}")

    al = rgba[..., 3]
    g = (al > 0) & (al < a_.lo)
    al[g] = 0
    s = (al >= a_.hi) & (al < 255)
    al[s] = 255
    log.append(f"ghost pixels cleared: {int(g.sum())}; near-solid snapped: {int(s.sum())}")

    if a_.speck_px:
        n, lab, st, _ = cv2.connectedComponentsWithStats((al >= a_.lo).astype(np.uint8), connectivity=8)
        small = [i for i in range(1, n) if st[i][4] < a_.speck_px]
        m = np.isin(lab, small)
        al[m] = 0
        log.append(f"specks removed: {len(small)} ({int(m.sum())} px)")

    if a_.defringe:
        bg = (np.array([int(a_.bg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]) if a_.bg
              else estimate_bg(rgba.astype(np.uint8)))
        if bg is None:
            raise SystemExit("defringe needs the old background colour: pass --bg RRGGBB")
        bg = np.asarray(bg, np.float32)
        a = al.astype(np.float32) / 255.0
        e = (al > 0) & (al < 255)
        c = rgba[..., :3].astype(np.float32)
        ae = a[e][:, None]
        c[e] = np.clip((c[e] - (1 - ae) * bg) / np.maximum(ae, 0.05), 0, 255)
        rgba[..., :3] = c.astype(np.int32)
        log.append(f"defringed {int(e.sum())} edge px against background {bg.astype(int).tolist()}")

    if a_.hard is not None:
        al[:] = np.where(al >= a_.hard, 255, 0)
        log.append(f"hard edge at alpha {a_.hard}")
        if a_.speck_px:  # thresholding can split spatter into new tiny pieces: sweep again
            n, lab, st, _ = cv2.connectedComponentsWithStats((al > 0).astype(np.uint8), connectivity=8)
            small = [i for i in range(1, n) if st[i][4] < a_.speck_px]
            al[np.isin(lab, small)] = 0
            log.append(f"specks after hard edge removed: {len(small)}")

    rgba[..., 3] = al
    rgba[..., :3][al == 0] = 0  # transparent pixels carry no colour that software could pick up
    dpi = a_.dpi
    if dpi is None:  # keep the source's DPI tag so the file still imports at its intended size
        from PIL import Image as _I
        d = _I.open(a_.inp).info.get("dpi")
        dpi = round(d[0]) if d else None
    save_png(rgba.clip(0, 255), a_.out, dpi=dpi)
    print("\n".join(log))


if __name__ == "__main__":
    main()
