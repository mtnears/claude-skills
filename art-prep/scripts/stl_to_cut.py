#!/usr/bin/env python3
"""Flat 3D model (STL) -> laser cut SVG in mm, from the model's own triangles.

For a thin slab (a relief or a plain extrusion). Finds the slab's plane (PCA), projects every
triangle onto it, unions them into one outline, keeps holes (slits) and drops specks.
Usage:  stl_to_cut.py MODEL.stl OUT_PREFIX --height-mm 120 [--rotate 0|90|180|270] [--mirror]
Writes OUT_PREFIX.svg (red hairline = cut, real mm) and OUT_PREFIX_preview.png, and prints the
parts, holes and slit widths. The STL's units are unreliable: always set --height-mm.
A flat cut-out has no front, so which way it faces is the person's call: check the preview,
then use --rotate / --mirror. Store the file in its correct orientation (flip in the laser
software only if needed). No kerf is applied.
"""
import argparse, struct
import numpy as np, cv2
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity

ap = argparse.ArgumentParser()
ap.add_argument("stl"); ap.add_argument("out")
ap.add_argument("--height-mm", type=float, required=True)
ap.add_argument("--rotate", type=float, default=0.0)
ap.add_argument("--mirror", action="store_true")
ap.add_argument("--min-hole-mm2", type=float, default=0.05)
ap.add_argument("--simplify-mm", type=float, default=0.02)
a = ap.parse_args()

b = open(a.stl, "rb").read()
n = struct.unpack("<I", b[80:84])[0]
dt = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
if len(b) != 84 + 50 * n:
    raise SystemExit("ASCII or damaged STL: re-export as binary STL")
v = np.frombuffer(b, dt, count=n, offset=84)["v"].astype(float)
P = v.reshape(-1, 3); c = P.mean(0)
w, U = np.linalg.eigh(np.cov((P - c).T))
R = (v - c) @ U[:, ::-1]                       # x = longest, z = thickness
ext = np.ptp(R.reshape(-1, 3), 0)
print("slab extent (model units): %.3f x %.3f x %.3f" % tuple(ext))
if ext[2] > 0.5 * ext[1]:
    print("WARNING: not a thin slab; the outline is only the silhouette")
tris = [Polygon(t[:, :2]) for t in R]
g = unary_union([t.buffer(1e-4 * ext[0], join_style=2) for t in tris if t.area > 0]).buffer(-1e-4 * ext[0], join_style=2)
if a.rotate: g = affinity.rotate(g, a.rotate, origin=(0, 0))
if a.mirror: g = affinity.scale(g, -1, 1, origin=(0, 0))
parts = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
body = max(parts, key=lambda p: p.area)
print("parts found %d (kept the largest; %d specks dropped)" % (len(parts), len(parts) - 1))
bx = body.bounds; s = a.height_mm / (bx[3] - bx[1])
body = affinity.scale(body, s, s, origin=(0, 0))
holes = [Polygon(i) for i in body.interiors if Polygon(i).area > a.min_hole_mm2]
body = Polygon(body.exterior, [h.exterior for h in holes]).simplify(a.simplify_mm)
bx = body.bounds; W = bx[2] - bx[0]; H = bx[3] - bx[1]
print("size %.1f x %.1f mm, %d holes" % (W, H, len(body.interiors)))
for i in body.interiors:
    h = Polygon(i); print("  slit/hole ~%.2f mm wide, ~%.1f mm long" % (2 * h.area / (h.length / 2), h.length / 2))
d = " ".join("M" + " L".join("%.3f,%.3f" % (x - bx[0], bx[3] - y) for x, y in r.coords) + " Z"
             for r in [body.exterior] + list(body.interiors))
open(a.out + ".svg", "w").write(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.3f}mm" height="{H:.3f}mm" viewBox="0 0 {W:.3f} {H:.3f}">'
    f'<path d="{d}" fill="none" stroke="#ff0000" stroke-width="0.1"/></svg>')
sc = 6; im = np.full((int(H * sc) + 20, int(W * sc) + 20), 255, np.uint8)
for r in [body.exterior] + list(body.interiors):
    cv2.polylines(im, [np.array([((x - bx[0]) * sc + 10, (bx[3] - y) * sc + 10) for x, y in r.coords], np.int32)], True, 0, 1)
cv2.imwrite(a.out + "_preview.png", im)
