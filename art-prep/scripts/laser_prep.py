#!/usr/bin/env python3
"""Laser cut / engrave files (SVG, millimetres) traced from the art's own pixels.

Usage:
  laser_prep.py ART.png OUTDIR --width-mm 100 --mode stencil [options]
  laser_prep.py - OUTDIR --mode kerf-test [--kerf 0.15]

Modes
  stencil   Blank (disc by default) with the art cut OUT of it, so the art pops out.
            Parts of the blank trapped inside letters (the hole of A, R, O...) become loose
            "islands": listed, numbered and previewed. --counters piece (default) leaves them
            loose so they can be glued back onto a backer; --counters bridge leaves a small
            bridge of material so each stays attached (stencil style).
            Also writes backer.svg (plain blank outline) for a layered sign.
  positive  The art as pieces (letters/logo cut out of the sheet) + the backer outline.
  inlay     stencil front with fit offsets + positive pieces + backer, for a second colour
            pressed into the first. --kerf and --fit give a true press fit.
  stack     backer + the art grown outward by each --grow mm (outline layers) + the art
            itself, for a glued-up multi-layer sign.
  engrave   the art as a filled engrave layer plus the blank outline as a cut path.
  kerf-test a coupon to measure your kerf and find your fit on your own material.

Layer colours in the SVGs: cut = red hairline, engrave = blue fill, so a colour = a
laser operation when imported (check how your software maps colours to layers).

Kerf: the laser removes a strip of material (kerf) centred on the path, so a cut-out
HOLE comes out larger than its path and a cut-out PIECE smaller. --kerf K corrects
for it (hole paths shrink by K/2, piece paths grow by K/2). --fit C is the wanted gap
per side between a piece and its hole (negative = press fit; acrylic cracks if too tight).
Measure K and find C with the kerf-test coupon on the same material and settings.
"""
import argparse, json, math, os, sys
import numpy as np

try:
    import cv2
    from PIL import Image
    from shapely.geometry import Polygon, MultiPolygon, Point, box, LineString, LinearRing
    from shapely.ops import unary_union, nearest_points
    from shapely import affinity
except ImportError as e:
    raise SystemExit("needs numpy, Pillow, opencv-python-headless and shapely: "
                     "pip install --break-system-packages opencv-python-headless shapely") from e

CUT = "#FF0000"
ENGRAVE = "#0000FF"
Q = 24  # arc segments per quarter circle for offsets


# ---------------------------------------------------------------- tracing
def ink_field(path, ink, tol):
    """Soft ink field in [0,1] from the image: alpha, dark pixels, or a chosen colour."""
    im = Image.open(path)
    im.load()
    rgba = np.array(im.convert("RGBA")).astype(np.float32)
    a = rgba[..., 3] / 255.0
    rgb = rgba[..., :3]
    mode = ink
    if mode == "auto":
        mode = "alpha" if (a < 0.98).mean() > 0.01 else "dark"
    if mode == "alpha":
        return a, "alpha"
    if mode == "dark":
        luma = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255.0
        return (1.0 - luma) * a + 0 * a, "dark pixels"
    if mode == "light":
        luma = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255.0
        return luma * a, "light pixels"
    hx = mode.lstrip("#")
    target = np.array([int(hx[i:i + 2], 16) for i in (0, 2, 4)], np.float32)
    d = np.sqrt(((rgb - target) ** 2).sum(axis=2))
    return np.clip(1.0 - d / float(tol), 0, 1) * a, f"colour #{hx.upper()} (tolerance {tol})"


def trace(field, up=8, speck_mm2=0.2, width_mm=100.0):
    """Threshold an upsampled field and return shapely geometry in mm, y down, centred on 0,0."""
    f = cv2.resize(field.astype(np.float32), None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
    f = cv2.GaussianBlur(f, (0, 0), up * 0.7)
    f = np.pad(f, 4, constant_values=0)
    m = (f >= 0.5).astype(np.uint8)
    cs, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None or not len(cs):
        raise SystemExit("no ink found: check --ink (dark / light / alpha / a hex colour)")
    hier = hier[0]
    pts_all = np.concatenate([c.reshape(-1, 2) for c in cs])
    w_px = pts_all[:, 0].max() - pts_all[:, 0].min()
    s = width_mm / float(w_px)
    polys = []
    for i, c in enumerate(cs):
        if hier[i][3] != -1 or len(c) < 4:
            continue
        holes = []
        j = hier[i][2]
        while j != -1:
            if len(cs[j]) >= 4:
                holes.append(cs[j].reshape(-1, 2) * s)
            j = hier[j][0]
        p = Polygon(c.reshape(-1, 2) * s, holes)
        if not p.is_valid:
            p = p.buffer(0)
        if p.area >= speck_mm2:
            polys.append(p)
    g = unary_union(polys)
    minx, miny, maxx, maxy = g.bounds
    g = affinity.translate(g, -(minx + maxx) / 2, -(miny + maxy) / 2)
    return g


def clean(g, simplify_mm=0.015, speck_mm2=0.2, hole_mm2=0.2):
    out = []
    for p in polys_of(g):
        holes = [h for h in p.interiors if Polygon(h).area >= hole_mm2]
        q = Polygon(p.exterior, holes).simplify(simplify_mm, preserve_topology=True)
        if q.area >= speck_mm2:
            out.append(q)
    return unary_union(out)


def polys_of(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    return [p for p in getattr(g, "geoms", []) for p in polys_of(p)]


def offset(g, d):
    if g.is_empty or abs(d) < 1e-9:
        return g
    return g.buffer(d, quad_segs=Q, join_style=1)


# ---------------------------------------------------------------- blank
def make_blank(kind, ink, diam, size, margin):
    minx, miny, maxx, maxy = ink.bounds
    if kind == "none":
        return None
    if kind == "circle":
        r = (diam / 2.0) if diam else math.hypot(maxx - minx, maxy - miny) / 2.0 + margin
        return Point(0, 0).buffer(r, quad_segs=Q * 4)
    if kind == "rect":
        if size:
            w, h = size
        else:
            w, h = (maxx - minx) + 2 * margin, (maxy - miny) + 2 * margin
        return box(-w / 2, -h / 2, w / 2, h / 2)
    raise SystemExit("--blank must be circle, rect or none")


# ---------------------------------------------------------------- bridges / islands
def add_bridges(ink_nominal, ink_off, width_mm):
    """Cut a bridge through the stroke next to every hole so the island stays attached.
    The bridge runs along the shortest line from the hole to the outside of the shape."""
    out = []
    bridges = []
    off_polys = polys_of(ink_off)
    for p in off_polys:
        q = p
        for hole in p.interiors:
            ring = LinearRing(hole)
            a, b = nearest_points(ring, p.exterior)
            v = np.array([b.x - a.x, b.y - a.y])
            L = np.hypot(*v)
            if L < 1e-6:
                continue
            u = v / L
            ln = LineString([(a.x - u[0] * 0.4, a.y - u[1] * 0.4), (b.x + u[0] * 0.4, b.y + u[1] * 0.4)])
            br = ln.buffer(width_mm / 2.0, cap_style=2)
            bridges.append(br)
            q = q.difference(br)
        out.append(q)
    return unary_union(out), bridges


def split_front(front):
    """Main body (largest piece) and loose islands, numbered in reading order."""
    ps = sorted(polys_of(front), key=lambda p: -p.area)
    if not ps:
        return None, []
    main, isl = ps[0], ps[1:]
    isl.sort(key=lambda p: (round(p.centroid.y / 8.0), p.centroid.x))
    return main, isl


# ---------------------------------------------------------------- warnings
def thin_report(ink, min_mm):
    r = min_mm / 2.0
    opened = offset(offset(ink, -r), r)
    thin = ink.difference(opened.buffer(0.01))
    parts = [p for p in polys_of(thin) if p.area > 0.15 * min_mm]
    parts.sort(key=lambda p: -p.area)
    share = thin.area / ink.area if ink.area else 0
    return thin, parts, share


# ---------------------------------------------------------------- SVG
def path_d(g, ox, oy):
    d = []
    for p in polys_of(g):
        for ring in [p.exterior] + list(p.interiors):
            c = list(ring.coords)[:-1]
            d.append("M" + " L".join(f"{x + ox:.3f},{y + oy:.3f}" for x, y in c) + " Z")
    return " ".join(d)


def write_svg(path, layers, note=""):
    """layers: list of (name, geometry, kind) with kind 'cut' or 'engrave'."""
    geoms = [g for _, g, _ in layers if g is not None and not g.is_empty]
    minx = min(g.bounds[0] for g in geoms); miny = min(g.bounds[1] for g in geoms)
    maxx = max(g.bounds[2] for g in geoms); maxy = max(g.bounds[3] for g in geoms)
    m = 0.0  # canvas = exact bounds, so an imported file reads its real size
    ox, oy = -minx + m, -miny + m
    W, H = maxx - minx + 2 * m, maxy - miny + 2 * m
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.3f}mm" height="{H:.3f}mm" viewBox="0 0 {W:.3f} {H:.3f}">']
    if note:
        s.append(f"<desc>{note}</desc>")
    for name, g, kind in layers:
        if g is None or g.is_empty:
            continue
        d = path_d(g, ox, oy)
        if kind == "cut":
            s.append(f'<g id="{name}"><path d="{d}" fill="none" stroke="{CUT}" stroke-width="0.1"/></g>')
        else:
            s.append(f'<g id="{name}"><path d="{d}" fill="{ENGRAVE}" fill-rule="evenodd" stroke="none"/></g>')
    s.append("</svg>")
    open(path, "w").write("\n".join(s))
    return W, H


# ---------------------------------------------------------------- preview
def hex2bgr(h):
    h = h.lstrip("#")
    return (int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16))


def gmask(g, shape, ppm, org):
    m = np.zeros(shape, np.uint8)
    for p in polys_of(g):
        ext = np.round((np.array(p.exterior.coords) * ppm + org)).astype(np.int32)
        cv2.fillPoly(m, [ext], 255, lineType=cv2.LINE_AA)
        for h in p.interiors:
            hh = np.round((np.array(h.coords) * ppm + org)).astype(np.int32)
            cv2.fillPoly(m, [hh], 0, lineType=cv2.LINE_AA)
    return m


def render(layers, path, bounds, ppm=None, bg=(255, 255, 255), labels=None):
    """layers: list of (geometry, bgr colour, alpha 0-1). Painter's order."""
    minx, miny, maxx, maxy = bounds
    pad = 4
    w, h = maxx - minx + 2 * pad, maxy - miny + 2 * pad
    ppm = ppm or min(1500 / w, 1500 / h)
    shape = (int(h * ppm) + 1, int(w * ppm) + 1)
    org = np.array([(-minx + pad) * ppm, (-miny + pad) * ppm])
    img = np.zeros(shape + (3,), np.float32)
    img[:] = bg
    for g, col, al in layers:
        if g is None or g.is_empty:
            continue
        m = (gmask(g, shape, ppm, org).astype(np.float32) / 255.0 * al)[..., None]
        img = img * (1 - m) + np.array(col, np.float32) * m
    img = img.astype(np.uint8)
    for text, (x, y) in (labels or []):
        px = (int(x * ppm + org[0]), int(y * ppm + org[1]))
        cv2.putText(img, text, px, cv2.FONT_HERSHEY_SIMPLEX, max(0.5, ppm / 14.0), (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, text, px, cv2.FONT_HERSHEY_SIMPLEX, max(0.5, ppm / 14.0), (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(path, img)


def bounds_of(*gs):
    gs = [g for g in gs if g is not None and not g.is_empty]
    return (min(g.bounds[0] for g in gs), min(g.bounds[1] for g in gs),
            max(g.bounds[2] for g in gs), max(g.bounds[3] for g in gs))


# ---------------------------------------------------------------- 7-segment labels for the coupon
SEG = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
       "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", "+": "gh"}


def seg_text(txt, h=3.0, t=0.5, gap=0.8):
    w = h * 0.55
    parts, x = [], 0.0
    for ch in txt:
        segs = SEG.get(ch, "")
        for sname in segs:
            if sname == "a": r = box(x, 0, x + w, t)
            elif sname == "b": r = box(x + w - t, 0, x + w, h / 2 + t / 2)
            elif sname == "c": r = box(x + w - t, h / 2 - t / 2, x + w, h)
            elif sname == "d": r = box(x, h - t, x + w, h)
            elif sname == "e": r = box(x, h / 2 - t / 2, x + t, h)
            elif sname == "f": r = box(x, 0, x + t, h / 2 + t / 2)
            elif sname == "g": r = box(x, h / 2 - t / 2, x + w, h / 2 + t / 2)
            elif sname == "h": r = box(x + w / 2 - t / 2, h / 4, x + w / 2 + t / 2, 3 * h / 4)
            parts.append(r)
        x += w + gap
    return unary_union(parts)


# ---------------------------------------------------------------- modes
def kerf_test(out, kerf, args):
    """Compact coupon, exact size, no margin.
    A: a 20 mm square piece and a 20 mm square hole in a plate -> measure the kerf.
    B: eight 10 mm plug/hole pairs, hole offset c from -0.10 to +0.25 mm per side."""
    k = kerf
    cs = [-0.10, -0.05, 0.0, 0.05, 0.10, 0.15, 0.20, 0.25]
    pieceA = offset(box(0, 0, 20, 20), k / 2.0)
    holeA = offset(box(34, 0, 54, 20), -k / 2.0)
    plateA = offset(box(30, -4, 58, 24), k / 2.0).difference(holeA)
    pitch = 15.0
    plateB_nom = box(0, 32, 4 + 8 * pitch, 58)
    holes, plugs, eng = [], [], []
    for i, c in enumerate(cs):
        x0 = 4 + i * pitch
        holes.append(offset(box(x0, 36, x0 + 10, 46), c - k / 2.0))
        plugs.append(offset(box(x0, 64, x0 + 10, 74), k / 2.0))
        lab = ("+" if c > 0 else "-" if c < 0 else "") + f"{int(round(abs(c) * 100)):02d}"
        eng.append(affinity.translate(seg_text(lab, h=3.0), x0 + 0.3, 50.0))
    plateB = offset(plateB_nom, k / 2.0).difference(unary_union(holes))
    cutg = unary_union([pieceA, plateA, plateB] + plugs)
    labels = unary_union(eng)
    W, H = write_svg(os.path.join(out, "kerf_test_coupon.svg"),
                     [("cut", cutg, "cut"), ("labels", labels, "engrave")], note="kerf/fit coupon, see README")
    b = bounds_of(cutg)
    render([(plateA, (200, 200, 255), 1), (plateB, (200, 200, 255), 1), (pieceA, (180, 220, 180), 1),
            (unary_union(plugs), (180, 220, 180), 1), (labels, (255, 0, 0), 1)],
           os.path.join(out, "kerf_test_preview.png"), b)
    txt = f"""KERF / FIT COUPON   size {W:.1f} x {H:.1f} mm.  Do NOT scale it.
Kerf used for compensation in this file: {k} mm (0 = raw paths, measure it).

Cut it in the SAME material, thickness and settings as the real job (power, speed,
passes, focus). Red lines cut; blue number labels engrave (light), not cut.

STEP A, kerf (top): a 20 mm square piece, and a plate with a 20 mm square hole.
  With kerf 0 the paths are exactly 20.00 mm, so the cut piece is a little smaller and the
  hole a little bigger. Measure each at 3 places, average:
      kerf = 20 - W_piece        (and kerf = W_hole - 20; the two should agree)
  Re-run: laser_prep.py - OUT --mode kerf-test --kerf <your number>
  A second coupon with the correction applied should now measure 20.00 / 20.00.

STEP B, fit (middle and bottom): eight 10 mm plugs and eight holes. Numbers are the hole
  path offset in hundredths of a mm per side, in addition to the kerf correction. With the
  correction applied (--kerf set) the number IS the clearance per side: -10 tight, +25 loose.
  With kerf 0 the true clearance is the number + your kerf.
  Push each plug into its own hole: pick the one that is snug and needs a light push.
  That clearance is your --fit value. Do not force them: acrylic cracks.
  (Glued inlay: about +0.05 is a good start; a dry press fit is around -0.05 to 0.)
Record kerf, fit, material, thickness and settings in config.json (laser section).
"""
    open(os.path.join(out, "kerf_test_README.txt"), "w").write(txt)
    print(txt)


# ---------------------------------------------------------------- reference plate
FONT = {
    "0": [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]], "1": [[(.25, .2), (.6, 0), (.6, 1)]],
    "2": [[(0, 0), (1, 0), (1, .5), (0, .5), (0, 1), (1, 1)]],
    "3": [[(0, 0), (1, 0), (1, 1), (0, 1)], [(0, .5), (1, .5)]],
    "4": [[(0, 0), (0, .5), (1, .5)], [(1, 0), (1, 1)]],
    "5": [[(1, 0), (0, 0), (0, .5), (1, .5), (1, 1), (0, 1)]],
    "6": [[(1, 0), (0, 0), (0, 1), (1, 1), (1, .5), (0, .5)]],
    "7": [[(0, 0), (1, 0), (.4, 1)]],
    "8": [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)], [(0, .5), (1, .5)]],
    "9": [[(1, .5), (0, .5), (0, 0), (1, 0), (1, 1), (0, 1)]],
    "+": [[(.1, .5), (.9, .5)], [(.5, .2), (.5, .8)]], "-": [[(.1, .5), (.9, .5)]],
    "X": [[(0, 0), (1, 1)], [(0, 1), (1, 0)]], "Y": [[(0, 0), (.5, .5)], [(1, 0), (.5, .5)], [(.5, .5), (.5, 1)]],
    "S": [[(1, 0), (0, 0), (0, .5), (1, .5), (1, 1), (0, 1)]], "H": [[(0, 0), (0, 1)], [(1, 0), (1, 1)], [(0, .5), (1, .5)]],
    "D": [[(0, 0), (0, 1), (.6, 1), (1, .7), (1, .3), (.6, 0), (0, 0)]],
    "F": [[(0, 1), (0, 0), (1, 0)], [(0, .5), (.8, .5)]], "R": [[(0, 1), (0, 0), (1, 0), (1, .5), (0, .5)], [(.4, .5), (1, 1)]],
    "P": [[(0, 1), (0, 0), (1, 0), (1, .5), (0, .5)]], "T": [[(0, 0), (1, 0)], [(.5, 0), (.5, 1)]],
    "O": [[(.2, 0), (.8, 0), (1, .2), (1, .8), (.8, 1), (.2, 1), (0, .8), (0, .2), (.2, 0)]],
    "L": [[(0, 0), (0, 1), (1, 1)]], "M": [[(0, 1), (0, 0), (.5, .6), (1, 0), (1, 1)]],
    "W": [[(0, 0), (.25, 1), (.5, .4), (.75, 1), (1, 0)]],
    "I": [[(.2, 0), (.8, 0)], [(.5, 0), (.5, 1)], [(.2, 1), (.8, 1)]],
    "E": [[(1, 0), (0, 0), (0, 1), (1, 1)], [(0, .5), (.7, .5)]],
}


def stext(txt, h, x, y, t=0.3):
    """Stroke-font text as engrave geometry. x,y = top-left, h = cap height (mm)."""
    w = 0.6 * h
    parts, cx = [], x
    for ch in txt:
        for pl in FONT.get(ch, []):
            pts = [(cx + u * w, y + v * h) for u, v in pl]
            parts.append(LineString(pts).buffer(t / 2.0, cap_style=1))
        cx += w + 0.45 * h
    if parts and set(txt) & set("69MW"):
        # underline anything that reads the same upside down (6/9, M/W) so "up" is unambiguous
        parts.append(LineString([(x, y + h + 0.28 * h), (cx - 0.45 * h, y + h + 0.28 * h)]).buffer(t / 2.0, cap_style=1))
    return unary_union(parts) if parts else Polygon()


def stext_w(txt, h):
    return len(txt) * (0.6 * h + 0.45 * h) - 0.45 * h


def stext_c(txt, h, cx, cy, t=0.3):
    return stext(txt, h, cx - stext_w(txt, h) / 2.0, cy - h / 2.0, t)


def hl(x0, x1, y, t=0.2):
    return LineString([(x0, y), (x1, y)]).buffer(t / 2.0, cap_style=2)


def vl(x, y0, y1, t=0.2):
    return LineString([(x, y0), (x, y1)]).buffer(t / 2.0, cap_style=2)


def chamf_box(x0, y0, x1, y1, c):
    return Polygon([(x0 + c, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0 + c)])


def moff(g, d):
    return g if abs(d) < 1e-9 else g.buffer(d, join_style=2, mitre_limit=4)


def aoff(g, dx, dy):
    """Offset by dx in X and dy in Y (an elliptical beam spot): scale Y, buffer, scale back."""
    if g is None or g.is_empty:
        return g
    if abs(dx - dy) < 1e-9:
        return moff(g, dx)
    if dx * dy <= 0:  # mixed sign: fall back to the mean
        return moff(g, (dx + dy) / 2.0)
    sy = dx / dy
    t = affinity.scale(g, 1.0, sy, origin=(0, 0))
    t = t.buffer(dx, join_style=2, mitre_limit=4)
    return affinity.scale(t, 1.0, 1.0 / sy, origin=(0, 0))


def axis_kerfs(a):
    """Piece kerf (outside size shrink) and hole kerf (hole growth), each per axis, in mm (total across).
    --kerf sets all four; --kerf-piece X,Y and --kerf-hole X,Y override."""
    def two(v, d):
        if not v:
            return d, d
        p = [float(t) for t in str(v).split(",")]
        return (p[0], p[0]) if len(p) == 1 else (p[0], p[1])
    kpx, kpy = two(a.kerf_piece, a.kerf)
    khx, khy = two(a.kerf_hole, a.kerf)
    return kpx, kpy, khx, khy


def reference_plate(a, out):
    """One-shot kerf / fit / scale / engrave reference. Parts are separate, labelled, orientable."""
    kpx, kpy, khx, khy = axis_kerfs(a)
    offs = [float(v) for v in a.fit_offsets.split(",")]
    P = lambda g: aoff(g, kpx / 2, kpy / 2)            # piece / outer outline path: grow
    Hh = lambda g, c=0.0: aoff(g, c - khx / 2, c - khy / 2)  # hole path: shrink (c = wanted clearance per side)
    k = (kpx + kpy) / 2
    cut, eng, parts = [], [], {}
    # S1: 20 mm square piece, chamfered top-left, with measuring lines 1-3 (left-right) and 4-6 (top-bottom)
    s1 = chamf_box(0, 0, 20, 20, 2)
    cut.append(P(s1))
    for i, p in enumerate((4, 10, 16)):
        eng += [hl(3.5, 16.5, p), stext(str(i + 1), 2.0, 1.2, p - 1.0), stext(str(i + 1), 2.0, 17.4, p - 1.0),
                vl(p, 3.5, 16.5), stext(str(i + 4), 2.0, p - 0.6, 1.0), stext(str(i + 4), 2.0, p - 0.6, 17.7)]
    eng.append(stext("S1", 2.0, 5.4, 12.0))
    # H1: plate with the matching 20 mm hole (same chamfer), ticks on the plate edges
    h1_hole = chamf_box(36, 6, 56, 26, 2)
    cut.append(P(box(30, 0, 62, 32)).difference(Hh(h1_hole)))
    for i, p in enumerate((4, 10, 16)):
        y, x = 6 + p, 36 + p
        eng += [hl(32.6, 35.4, y), hl(56.6, 59.4, y), stext(str(i + 1), 2.0, 30.6, y - 1.0), stext(str(i + 1), 2.0, 60.2, y - 1.0),
                vl(x, 2.6, 5.4), vl(x, 26.6, 29.4), stext(str(i + 4), 2.0, x - 0.6, 0.2), stext(str(i + 4), 2.0, x - 0.6, 29.8)]
    eng.append(stext("H1", 2.2, 30.6, 29.0))
    # the pieces that DROP OUT of H1 and H2 are real samples too (cut on the hole path): mark them
    for i, p_ in enumerate((4, 10, 16)):
        eng += [hl(36 + 3.5, 36 + 16.5, 6 + p_), stext(str(i + 1), 2.0, 36 + 1.2, 6 + p_ - 1.0), stext(str(i + 1), 2.0, 36 + 17.4, 6 + p_ - 1.0),
                vl(36 + p_, 6 + 3.5, 6 + 16.5), stext(str(i + 4), 2.0, 36 + p_ - 0.6, 6 + 1.0), stext(str(i + 4), 2.0, 36 + p_ - 0.6, 6 + 17.7)]
    eng.append(stext("H1", 2.0, 36 + 5.4, 6 + 12.0))
    # D1: 40 mm disc with the logo engraved, orientation triangle at top; H2: plate with matching hole
    dc, dr, c_d = (92, 22), 20.0, a.disc_offset
    cut.append(P(Point(*dc).buffer(dr, quad_segs=Q * 4)))
    if a.art != "-":
        field, _ = ink_field(a.art, a.ink, a.tol)
        logo = clean(trace(field, width_mm=a.ref_logo_width), a.simplify_mm, a.speck_mm2)
        eng.append(affinity.translate(logo, dc[0], dc[1] - 1.5))
    eng += [Polygon([(92, 2.8), (90.4, 5.8), (93.6, 5.8)]), Point(92, 39.8).buffer(0.9), stext_c("D1", 2.6, 92, 35.6)]
    hc = (150, 26)
    cut.append(P(box(124, 0, 176, 52)).difference(Hh(Point(*hc).buffer(dr, quad_segs=Q * 4), c_d)))
    eng += [hl(126, 129, 26), hl(171, 173.6, 26), stext("1", 2.0, 124.6, 25.0), stext("1", 2.0, 174.2, 25.0), vl(150, 2.6, 5.4), vl(150, 46.6, 49.4),
            stext("2", 2.0, 149.4, 0.2), stext("2", 2.0, 149.4, 49.8), stext("H2", 2.4, 125.5, 46.5), stext(f"{int(round(c_d * 100)):+03d}".replace("+0", "0") if c_d else "00", 2.2, 160, 46.8)]
    eng += [Polygon([(150, 7.2), (148.4, 10.2), (151.6, 10.2)]), hl(131.5, 168.5, 26), vl(150, 11.5, 40.5),
            stext("1", 2.0, 132.2, 23.0), stext("1", 2.0, 165.8, 23.0), stext("2", 2.0, 151.0, 11.8), stext("2", 2.0, 151.0, 37.0),
            Point(150, 42.6).buffer(0.9), stext("H2", 2.0, 154, 28.5)]
    # F1: eight fit holes (offset per side, hundredths of a mm) + eight numbered plugs
    holes, plugs = [], []
    for i, c in enumerate(offs):
        x0 = 4 + i * 15.0
        holes.append(Hh(chamf_box(x0, 66, x0 + 10, 76, 1), c))
        plugs.append(P(chamf_box(x0, 104, x0 + 10, 114, 1)))
        lab = ("-" if c < 0 else "+" if c > 0 else "") + f"{int(round(abs(c) * 100)):02d}"
        eng += [vl(x0 + 5, 62.4, 64.8), vl(x0 + 5, 77.2, 79.6), hl(x0 - 2.0, x0 - 0.6, 71), hl(x0 + 10.6, x0 + 12.0, 71),
                stext(str(i + 1), 2.2, x0, 81.0), stext(lab, 2.2, x0 + 3.0, 81.0),
                stext_c(str(i + 1), 4.0, x0 + 5, 109)]
    cut.append(P(box(0, 60, 124, 98)).difference(unary_union(holes)))
    cut += plugs
    eng.append(stext("F1", 3.0, 4, 89))
    tag = "".join(ch for ch in (a.machine or "").upper() if ch in FONT or ch == " ").strip()
    if tag:
        eng.append(stext(tag, 2.6, 17, 89.2))
    # R1 / R2: rulers cut as plates, ticks engraved: check scale in X and Y
    cut.append(P(box(0, 120, 108, 134)))
    for mm in range(0, 101):
        x = 2 + mm
        ln = 5.0 if mm % 10 == 0 else 3.2 if mm % 5 == 0 else 1.6
        eng.append(vl(x, 120.8, 120.8 + ln, 0.15))
        if mm % 10 == 0:
            eng.append(stext_c(str(mm), 2.4, x, 127.8))
    eng.append(stext("R1", 2.2, 2, 130.6))
    cut.append(P(box(134, 60, 148, 130)))
    for mm in range(0, 61):
        y = 62 + mm
        ln = 5.0 if mm % 10 == 0 else 3.2 if mm % 5 == 0 else 1.6
        eng.append(hl(135.0, 135.0 + ln, y, 0.15))
        if mm % 10 == 0:
            eng.append(stext_c(str(mm), 2.4, 143.2, y))
    eng.append(stext("R2", 2.2, 135.5, 126.4))
    cutg, engg = unary_union(cut), unary_union(eng)
    W, H = write_svg(os.path.join(out, "reference_plate.svg"), [("engrave", engg, "engrave"), ("cut", cutg, "cut")],
                     note="reference plate: engrave first, then cut")
    b = bounds_of(cutg, engg)
    render([(cutg, (225, 225, 225), 1), (engg, (200, 60, 0), 1)], os.path.join(out, "reference_plate_preview.png"), b, ppm=14)
    # measurement guide image with big callouts
    img = cv2.imread(os.path.join(out, "reference_plate_preview.png"))
    ppm, pad = 14, 4
    def at(x, y): return (int((x - b[0] + pad) * ppm), int((y - b[1] + pad) * ppm))
    notes = [((0, -2.5), "S1: 20 mm piece"), ((30, -2.5), "H1: its 20 mm hole"), ((72, -2.5), "D1: disc + engraved logo"),
             ((124, -2.5), "H2: its disc hole"), ((0, 58), "F1: 8 fit holes (offset in 1/100 mm, per side)"),
             ((0, 102), "plugs 1-8 (match hole numbers)"), ((0, 118), "R1: ruler 0-100 mm (X)"), ((134, 58), "R2: ruler 0-60 mm (Y)")]
    for (x, y), t in notes:
        cv2.putText(img, t, at(x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(out, "reference_plate_guide.png"), img)
    guide = f"""REFERENCE PLATE   {W:.1f} x {H:.1f} mm   (kerf in this file: piece x/y {kpx}/{kpy}, hole x/y {khx}/{khy} mm, fit offsets {offs}, disc offset {c_d})
ORIENTATION: every loose piece has its TOP-LEFT corner cut off (chamfered); the discs have a triangle at the top. The pieces that drop out of the H1 and H2 holes are marked too and are extra samples. Hold it with the chamfer
top-left and the engraving readable. All "left-right" = X, "top-bottom" = Y, as the part sat in the file.
RUN: engrave first, then cut (or engraving on the loose pieces will be lost). Same settings as the real job.
Record: laser/module, material + thickness, cut and engrave settings (power, speed, passes, line
interval), date. Let everything cool overnight before measuring.

MEASURE (calipers closed gently; write numbers as read):
 S1 piece, along lines 1,2,3 (left-right) and lines 4,5,6 (top-bottom): 6 readings.  Nominal 20.00
 H1 hole,  at the tick marks 1,2,3 (left-right) and 4,5,6 (top-bottom): 6 readings.   Nominal 20.00
    -> kerf X = 20 - mean(S1 lines 1-3) = mean(H1 lines 1-3) - 20 ;  kerf Y the same with lines 4-6.
 D1 disc: diameter at 3 angles (note them).  H2 hole: diameter at tick 1 (left-right) and tick 2 (top-bottom).  Nominal 40.00 / hole path 40 + 2*offset.
 Plugs 1-8: left-right and top-bottom each, nominal 10.00. Holes 1-8: same, nominal 10 + 2 * offset (see label), before kerf.
 FIT: take plug 1 and try it in each hole, then plug 8: note snug / loose / won't enter / needs force. Do not force.
 R1: distance between engraved tick 0 and tick 100 (nominal 100.00); R2: tick 0 to 60 (nominal 60.00). Also overall plate lengths.
 Thickness of the sheet at 3 places. Edges: clean / dark film / melted lip / slanted wall (top vs bottom width).
"""
    open(os.path.join(out, "reference_plate_MEASURE.txt"), "w").write(guide)
    prof = {"profile_id": a.profile_id, "date": "", "laser": a.machine, "module": "", "material": a.material,
            "thickness_mm": None, "cut_settings": {"power": "", "speed": "", "passes": "", "focus": ""},
            "engrave_settings": {"power": "", "speed": "", "line_interval": ""},
            "kerf_x_mm": None, "kerf_y_mm": None, "fit_clearance_mm": None, "notes": "",
            "plate_kerf_in_file_mm": {"piece_x": kpx, "piece_y": kpy, "hole_x": khx, "hole_y": khy}, "fit_offsets_mm": offs, "disc_offset_mm": c_d}
    json.dump(prof, open(os.path.join(out, "reference_profile_TEMPLATE.json"), "w"), indent=2)
    print(guide)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("art")
    ap.add_argument("out")
    ap.add_argument("--mode", default="stencil", choices=["stencil", "positive", "inlay", "stack", "engrave", "kerf-test", "reference"])
    ap.add_argument("--width-mm", type=float, default=100.0, help="overall width of the traced art")
    ap.add_argument("--ink", default="auto", help="auto | dark | light | alpha | HEX (which pixels are the shape)")
    ap.add_argument("--tol", type=float, default=90.0, help="colour distance for --ink HEX")
    ap.add_argument("--blank", default="circle", help="circle | rect | none (the sheet the art is cut from/in)")
    ap.add_argument("--blank-diam", type=float, default=0.0, help="circle diameter, mm (default: fits the art + margin)")
    ap.add_argument("--blank-size", default="", help="rect WxH mm")
    ap.add_argument("--margin-mm", type=float, default=6.0)
    ap.add_argument("--kerf", type=float, default=0.0, help="measured kerf in mm")
    ap.add_argument("--kerf-piece", default="", help="X,Y total shrink of cut-out PIECES (outside jaws), mm")
    ap.add_argument("--kerf-hole", default="", help="X,Y total growth of HOLES, mm")
    ap.add_argument("--fit", type=float, default=0.0, help="clearance per side in inlay mode (negative = press fit)")
    ap.add_argument("--counters", default="piece", choices=["piece", "bridge"])
    ap.add_argument("--bridge-mm", type=float, default=1.2)
    ap.add_argument("--grow", default="2.0", help="stack mode: outline layers, mm each, comma separated")
    ap.add_argument("--min-feature-mm", type=float, default=1.0)
    ap.add_argument("--simplify-mm", type=float, default=0.015)
    ap.add_argument("--speck-mm2", type=float, default=0.25)
    ap.add_argument("--colours", default="", help="preview colours: backer=HEX,front=HEX,pieces=HEX")
    ap.add_argument("--fit-offsets", default="-0.40,-0.35,-0.30,-0.25,-0.20,-0.15,-0.10,-0.05", help="reference mode: hole path offsets per side, mm")
    ap.add_argument("--disc-offset", type=float, default=-0.20, help="reference mode: disc-hole path offset per side, mm")
    ap.add_argument("--ref-logo-width", type=float, default=30.0)
    ap.add_argument("--profile-id", default="01")
    ap.add_argument("--name", default="logo")
    ap.add_argument("--material", default="")
    ap.add_argument("--machine", default="")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    if a.mode == "kerf-test":
        return kerf_test(a.out, a.kerf, a)
    if a.mode == "reference":
        return reference_plate(a, a.out)

    cols = {"backer": "#2B3A67", "front": "#E8DCC0", "pieces": "#C0392B"}
    for kv in filter(None, a.colours.split(",")):
        k, v = kv.split("=")
        cols[k.strip()] = v.strip()

    field, how = ink_field(a.art, a.ink, a.tol)
    ink = clean(trace(field, width_mm=a.width_mm, speck_mm2=a.speck_mm2),
                a.simplify_mm, a.speck_mm2)
    size = tuple(float(x) for x in a.blank_size.lower().split("x")) if a.blank_size else None
    blank = make_blank(a.blank, ink, a.blank_diam, size, a.margin_mm)
    kpx, kpy, khx, khy = axis_kerfs(a)
    k = (kpx + kpy) / 2
    report = {"traced": how, "width_mm": a.width_mm, "ink_area_mm2": round(ink.area, 1),
              "shapes": len(polys_of(ink)), "holes_in_shapes": sum(len(p.interiors) for p in polys_of(ink)),
              "kerf_mm": k, "fit_mm": a.fit, "mode": a.mode, "blank": a.blank}
    if blank is not None:
        report["blank_bounds_mm"] = [round(v, 1) for v in blank.bounds]
        report["blank_size_mm"] = [round(blank.bounds[2] - blank.bounds[0], 1), round(blank.bounds[3] - blank.bounds[1], 1)]
        if not blank.contains(ink):
            print("WARNING: the art does not fit inside the blank; raise --blank-diam / --margin-mm")

    thin, thin_parts, share = thin_report(ink, a.min_feature_mm)
    report["thin_share_pct"] = round(100 * share, 1)
    report["thin_spots"] = [[round(p.centroid.x, 1), round(p.centroid.y, 1), round(p.area, 2)] for p in thin_parts[:6]]

    files = {}
    layers_prev = []
    labels = []
    fitc = a.fit if a.mode == "inlay" else 0.0
    piece_d = k / 2.0
    ink_hole = aoff(ink, fitc - khx / 2.0, fitc - khy / 2.0)
    ink_piece = aoff(ink, kpx / 2.0, kpy / 2.0)
    blank_cut = aoff(blank, kpx / 2.0, kpy / 2.0) if blank is not None else None
    name = a.name
    islands = []
    bridges = []
    front = None

    def save(fname, layers, what, note=""):
        write_svg(os.path.join(a.out, fname), layers, note)
        files[fname] = what

    if a.mode in ("stencil", "inlay"):
        if blank is None:
            raise SystemExit("stencil/inlay need a blank (--blank circle|rect)")
        ink_for_front = ink_hole
        if a.counters == "bridge":
            ink_for_front, bridges = add_bridges(ink, ink_hole, a.bridge_mm)
        front_geom = blank_cut.difference(ink_for_front)
        main, islands = split_front(front_geom)
        front = main
        layers = [("front_cut", unary_union([main] + islands), "cut")]
        save(f"{name}_front_stencil_cut.svg", layers,
             "the blank with the art cut out (pop-out letters). Islands (numbered in the preview) fall out loose "
             "unless --counters bridge was used.")
        report["islands"] = [{"n": i + 1, "area_mm2": round(p.area, 1),
                              "bbox_mm": [round(p.bounds[2] - p.bounds[0], 1), round(p.bounds[3] - p.bounds[1], 1)],
                              "centre_mm": [round(p.centroid.x, 1), round(p.centroid.y, 1)]} for i, p in enumerate(islands)]
        report["bridges"] = len(bridges) if a.counters == "bridge" else 0
        for i, p in enumerate(islands):
            labels.append((str(i + 1), (p.centroid.x - 0.8, p.centroid.y + 1.0)))
        if any(min(p.bounds[2] - p.bounds[0], p.bounds[3] - p.bounds[1]) < 2.5 for p in islands):
            print("NOTE: some islands are under 2.5 mm across: fiddly to glue; consider --counters bridge")
    if a.mode in ("positive", "inlay", "stack"):
        pcs = ink_piece
        save(f"{name}_pieces_cut.svg", [("pieces_cut", pcs, "cut")],
             "the art as cut-out pieces (letters/logo). Holes inside pieces are waste.")
    if a.mode in ("stencil", "inlay", "positive", "stack") and blank is not None:
        save(f"{name}_backer_cut.svg", [("backer_cut", blank_cut, "cut")], "plain blank outline: the backer layer")
    if a.mode == "stack":
        grows = [float(x) for x in a.grow.split(",") if x.strip()]
        outer = None
        for i, gmm in enumerate(grows):
            lay = clean(aoff(ink, gmm + kpx / 2.0, gmm + kpy / 2.0), a.simplify_mm, a.speck_mm2)
            outer = lay
            save(f"{name}_layer{i + 2}_grow{gmm:g}mm_cut.svg", [(f"layer{i + 2}_cut", lay, "cut")],
                 f"outline layer grown {gmm:g} mm beyond the art (glue between backer and art; counters shrink)")
        report["layers"] = ["backer", *[f"grow {g:g} mm" for g in grows], "art"]
    if a.mode == "engrave":
        layers = [("engrave", ink, "engrave")]
        if blank is not None:
            layers.append(("blank_cut", blank_cut, "cut"))
        save(f"{name}_engrave.svg", layers, "art as a filled engrave layer (blue) + blank outline (red cut)")

    # ---- previews
    allg = [g for g in [blank_cut, ink] if g is not None]
    b = bounds_of(*allg)
    cB, cF, cP = hex2bgr(cols["backer"]), hex2bgr(cols["front"]), hex2bgr(cols["pieces"])
    if a.mode in ("stencil", "inlay"):
        prev = [(blank_cut, cB, 1)]
        prev.append((front, cF, 1)); prev += [(p, (60, 60, 230), 1) for p in islands]
        if bridges:
            prev.append((unary_union(bridges), (0, 140, 255), 0.8))
        prev.append((thin, (0, 165, 255), 0.55))
        render(prev, os.path.join(a.out, f"{name}_preview_stencil.png"), b, labels=labels)
        render([(blank_cut, (230, 230, 230), 1), (front, (255, 255, 255), 1)] +
               [(p, (60, 60, 230), 1) for p in islands] + [(thin, (0, 165, 255), 0.55)],
               os.path.join(a.out, f"{name}_preview_cutfile.png"), b, labels=labels)
        render([(blank_cut, cB, 1)] + ([(front, cF, 1)] if front else []) + [(p, cF, 1) for p in islands] +
               ([(ink_hole, cB, 1)] if False else []), os.path.join(a.out, f"{name}_preview_assembled.png"), b)
    if a.mode in ("positive", "inlay", "stack"):
        prev = [(blank_cut, cB, 1)] if blank_cut is not None else []
        if a.mode == "stack":
            for gmm in sorted(grows, reverse=True):
                prev.append((clean(aoff(ink, gmm + kpx / 2.0, gmm + kpy / 2.0)), cF, 1))
        prev.append((ink_piece, cP, 1))
        prev.append((thin, (0, 165, 255), 0.55))
        render(prev, os.path.join(a.out, f"{name}_preview_{a.mode}.png"), b)
    if a.mode == "engrave":
        render([(blank_cut, (230, 230, 230), 1) if blank_cut is not None else (ink, (230, 230, 230), 0),
                (ink, (255, 0, 0), 1), (thin, (0, 165, 255), 0.55)],
               os.path.join(a.out, f"{name}_preview_engrave.png"), b)

    report["files"] = files
    report["settings_to_record"] = {"machine": a.machine, "material": a.material,
                                    "note": "power, speed, passes and focus are yours: record them from your test cut"}
    json.dump(report, open(os.path.join(a.out, f"{name}_laser_report.json"), "w"), indent=2)
    print(json.dumps({k_: v for k_, v in report.items() if k_ not in ("files", "settings_to_record")}, indent=1))


if __name__ == "__main__":
    main()
