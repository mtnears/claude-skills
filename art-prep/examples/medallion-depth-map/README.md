Worked example: a "challenge coin" style depth map for a 1254 px medallion (printed Oct 2026, 2.5 mm).
- `make_masks.py` / `depthmap3.py`: the original art-specific scripts used on the job
  (hand-placed polygons, GrabCut, per-digit hulls for the numerals).
- `config.json`: the same tier design expressed for the general `scripts/depthmap.py`
  (needs masks named scene, jeep, flag, num from the job's `depth-build/masks.npz`).
Use them as a pattern for new artwork; do not reuse the coordinates.
