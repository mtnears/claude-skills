#!/usr/bin/env python3
"""Draft-approval sheet: before vs after on light, dark and checker backgrounds,
plus zoomed crops of where the pixels changed most.

Usage:
  preview_sheet.py BEFORE.png AFTER.png OUT.png [--bgs FFFFFF,000000,808080] [--zooms 3]

Use it every time before building a package: the user approves the look on this
sheet, not on a description. AFTER may be a different size (e.g. a 4x upscale);
it is compared at BEFORE's size.
"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from common import load_rgba, cv2


def on(bg, im):
    if bg == "checker":
        h, w = im.shape[:2]
        c = (((np.indices((h, w)).sum(axis=0) // 12) % 2) * 40 + 190).astype(np.uint8)
        base = Image.fromarray(np.dstack([c, c, c, np.full((h, w), 255, np.uint8)]))
    else:
        rgb = tuple(int(bg[i:i + 2], 16) for i in (0, 2, 4))
        base = Image.new("RGBA", (im.shape[1], im.shape[0]), rgb + (255,))
    base.alpha_composite(Image.fromarray(im))
    return base.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before"); ap.add_argument("after"); ap.add_argument("out")
    ap.add_argument("--bgs", default="FFFFFF,000000,checker")
    ap.add_argument("--zooms", type=int, default=3)
    ap.add_argument("--col-w", type=int, default=520)
    a_ = ap.parse_args()
    b = load_rgba(a_.before)
    af = load_rgba(a_.after)
    if af.shape[:2] != b.shape[:2]:
        af = np.array(Image.fromarray(af).resize((b.shape[1], b.shape[0]), Image.LANCZOS))
    H, W = b.shape[:2]
    cw = a_.col_w; ch = int(H * cw / W)
    bgs = a_.bgs.split(",")
    rows = []
    for bg in bgs:
        rows.append([on(bg, b).resize((cw, ch), Image.LANCZOS), on(bg, af).resize((cw, ch), Image.LANCZOS)])

    # zooms where the composite on the first two backgrounds changed most
    diff = np.zeros((H, W), np.float32)
    for bg in bgs[:2]:
        diff += np.abs(np.asarray(on(bg, b), np.float32) - np.asarray(on(bg, af), np.float32)).sum(-1)
    zs = max(48, min(H, W) // 6)
    blur = cv2.boxFilter(diff, -1, (zs, zs))
    crops = []
    for _ in range(a_.zooms):
        y, x = np.unravel_index(np.argmax(blur), blur.shape)
        if blur[y, x] <= 0:
            break
        x0 = int(np.clip(x - zs, 0, W - 2 * zs)); y0 = int(np.clip(y - zs // 2, 0, H - zs))
        crops.append((x0, y0, x0 + 2 * zs, y0 + zs))
        blur[max(0, y - zs):y + zs, max(0, x - 2 * zs):x + 2 * zs] = 0
    zrows = []
    for c in crops:
        zb, za = on(bgs[0], b).crop(c), on(bgs[0], af).crop(c)
        zb2, za2 = on(bgs[1], b).crop(c), on(bgs[1], af).crop(c)
        zh = int(cw / 2)
        zrows.append([zb.resize((cw, zh), Image.NEAREST), za.resize((cw, zh), Image.NEAREST)])
        zrows.append([zb2.resize((cw, zh), Image.NEAREST), za2.resize((cw, zh), Image.NEAREST)])

    pad, head = 10, 26
    allrows = rows + zrows
    tot_h = head + sum(r[0].height + pad for r in allrows)
    sheet = Image.new("RGB", (2 * cw + 3 * pad, tot_h), (225, 225, 225))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 6), "BEFORE", fill=(0, 0, 0)); d.text((2 * pad + cw, 6), "AFTER", fill=(0, 0, 0))
    y = head
    for i, r in enumerate(allrows):
        sheet.paste(r[0], (pad, y)); sheet.paste(r[1], (2 * pad + cw, y))
        if i == len(rows):
            d.line([(0, y - pad // 2), (sheet.width, y - pad // 2)], fill=(200, 0, 200), width=2)
        y += r[0].height + pad
    sheet.save(a_.out)
    print(f"sheet {sheet.size}; backgrounds {bgs}; zoom crops {len(crops)}")


if __name__ == "__main__":
    main()
