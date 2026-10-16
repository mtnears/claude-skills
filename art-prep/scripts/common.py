"""Shared helpers for art-prep scripts. Pure numpy/Pillow/OpenCV, no network."""
import json
import numpy as np
from PIL import Image

try:
    import cv2  # opencv-python-headless
except ImportError as e:  # pragma: no cover
    raise SystemExit("OpenCV missing: pip install --break-system-packages opencv-python-headless") from e


def load_rgba(path):
    """Load any image as RGBA uint8 numpy array (H, W, 4)."""
    im = Image.open(path)
    im.load()
    return np.array(im.convert("RGBA"))


def save_png(arr, path, dpi=None):
    im = Image.fromarray(arr.astype(np.uint8))
    kw = {"optimize": True}
    if dpi:
        kw["dpi"] = (dpi, dpi)
    im.save(path, **kw)


def estimate_bg(rgba):
    """Colour of the background the art was cut from.

    Fully transparent pixels usually still carry the old background RGB
    (ChatGPT exports keep ~white there). Falls back to corner pixels.
    """
    a = rgba[..., 3]
    clear = a == 0
    if clear.sum() > 100:
        c = rgba[clear][:, :3]
        if (c.max(axis=1) == 0).mean() > 0.98:
            return None  # transparent pixels were zeroed on export: old background unknown
        return np.median(c, axis=0)
    h, w = a.shape
    k = max(4, min(h, w) // 50)
    corners = np.concatenate([rgba[:k, :k], rgba[:k, -k:], rgba[-k:, :k], rgba[-k:, -k:]]).reshape(-1, 4)
    return np.median(corners[:, :3], axis=0)


def solid_background(rgba, tol=12):
    """If an image has no real transparency, detect a solid border colour.
    Returns the colour or None."""
    a = rgba[..., 3]
    if (a < 250).mean() > 0.01:
        return None
    border = np.concatenate([rgba[0], rgba[-1], rgba[:, 0], rgba[:, -1]])[:, :3].astype(int)
    med = np.median(border, axis=0)
    if (np.abs(border - med).max(axis=1) <= tol).mean() > 0.9:
        return med
    return None


def islands_of(mask):
    """Connected components of a boolean mask that do not touch the image border.
    Returns (labels, list of (id, area, bbox))."""
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    h, w = mask.shape
    out = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if x == 0 or y == 0 or x + bw >= w or y + bh >= h:
            continue
        out.append((i, int(area), (int(x), int(y), int(bw), int(bh))))
    return lab, out


def write_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))


def mm_to_px(mm, dpi):
    return mm * dpi / 25.4


def find_bg_islands(rgba, bg, hi=240, tol=28, near_px=0, min_area=12):
    """Islands of old-background colour left inside the art by background removal.

    Two tests separate them from real white/light parts of the design:
      - flat: the island is uniformly the background colour (removal leftovers are a
        solid fill; highlights, clouds and chrome have texture);
      - near real transparency: leftovers sit inside thin strokes (letter holes), so
        transparent pixels are within a stroke width. Light areas deep inside the
        artwork fail this.
    Returns (labels, [(label_id, area, bbox)]) sorted by area, ids stable for a given input.
    """
    a = rgba[..., 3]
    if bg is None:
        return np.zeros(a.shape, np.int32), []
    d = np.abs(rgba[..., :3].astype(int) - bg.astype(int)).max(axis=2)
    bglike = (a >= hi) & (d <= tol)
    max_area = a.size * 0.01  # leftovers are small; big areas of that colour are design
    lab, isl = islands_of(bglike)
    if near_px <= 0:
        near_px = max(8, int(min(a.shape) * 0.012))
    clear = (a == 0).astype(np.uint8)
    dt = cv2.distanceTransform(1 - clear, cv2.DIST_L2, 3) if clear.any() else np.full(a.shape, 1e9, np.float32)
    keep = []
    for i, area, bbox in isl:
        if area < min_area or area > max_area:
            continue
        m = lab == i
        if dt[m].min() > near_px:
            continue
        if d[m].mean() > tol * 0.6 or rgba[..., :3][m].std(axis=0).max() > 10:
            continue
        keep.append((i, area, bbox))
    keep.sort(key=lambda t: (t[2][1] // 20, t[2][0]))  # reading order: top to bottom, left to right
    return lab, keep
