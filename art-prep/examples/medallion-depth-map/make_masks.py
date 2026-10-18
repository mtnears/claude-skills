#!/usr/bin/env python3
"""Region masks for a semantic depth map of a medallion illustration (native 1254 px).
Hand-placed outlines (coordinates read off the art) refined with GrabCut on the art's own colours.
Writes masks.npz and masks_overlay.png (each region tinted) for review."""
import sys, numpy as np, cv2
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
im = np.array(Image.open(src).convert("RGBA"))
rgb, al = im[..., :3], im[..., 3] > 0
bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
Hh, Ww = al.shape

def poly(pts):
    m = np.zeros((Hh, Ww), np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1)
    return m

scene = poly([(627,218),(800,228),(950,285),(1060,370),(1115,470),(1135,580),(1128,700),(1110,790),(1085,850),
              (1000,860),(800,845),(627,838),(450,845),(300,870),(190,880),(150,850),(125,780),(115,680),
              (118,570),(140,470),(200,380),(300,300),(450,240)]) & al.astype(np.uint8)

def grab(prior_poly, grow=18, shrink=14, iters=5):
    """GrabCut seeded by a rough polygon: inside-shrunk = sure fg, outside-grown = sure bg."""
    k = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*r+1, 2*r+1))
    sure_fg = cv2.erode(prior_poly, k(shrink)); outer = cv2.dilate(prior_poly, k(grow))
    mask = np.full((Hh, Ww), cv2.GC_BGD, np.uint8)
    mask[outer > 0] = cv2.GC_PR_BGD; mask[prior_poly > 0] = cv2.GC_PR_FGD; mask[sure_fg > 0] = cv2.GC_FGD
    bg, fg = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(bgr, mask, None, bg, fg, iters, cv2.GC_INIT_WITH_MASK)
    r = ((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)).astype(np.uint8)
    r = cv2.morphologyEx(r, cv2.MORPH_CLOSE, k(3)); r = cv2.morphologyEx(r, cv2.MORPH_OPEN, k(2))
    return r

jeep_p = poly([(470,540),(520,500),(700,478),(752,495),(765,545),(790,600),(835,660),(850,720),(848,790),(800,812),
               (740,795),(700,830),(640,840),(560,830),(480,820),(420,830),(330,830),(285,825),(280,780),(300,720),
               (335,660),(380,625),(430,590)])
flag_p = poly([(345,322),(430,288),(485,272),(488,520),(470,530),(380,555),(300,590),(210,620),(135,640),(150,590),
               (185,500),(260,400)])
jeep = grab(jeep_p, grow=22, shrink=22) & scene
flag = grab(flag_p, grow=16, shrink=10) & scene
pole = np.zeros((Hh, Ww), np.uint8); cv2.line(pole, (487, 243), (479, 535), 1, 7)

# 250: cream front faces inside its bounding box, filled and cleaned
lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
L = lab[..., 0] / 255 * 100; ch = np.hypot(lab[..., 1] - 128, lab[..., 2] - 128)
def zpoly(pts, z=2.4, x0=480, y0=255):   # points read off a 2.4x zoom of the 250 -> native coords
    return poly([(x0 + X / z, y0 + Y / z) for X, Y in pts])
hull2 = zpoly([(140,55),(240,20),(350,20),(440,50),(495,110),(500,190),(485,270),(430,340),(350,410),(480,480),(485,570),(420,610),(250,612),(125,600),(125,480),(190,400),(240,330),(200,250),(140,200)])
hull5 = zpoly([(540,45),(795,80),(795,185),(735,215),(800,300),(810,420),(790,540),(740,600),(640,625),(510,590),(500,430),(545,365),(535,200)])
hull0 = zpoly([(835,190),(890,150),(990,145),(1070,185),(1112,280),(1118,400),(1110,520),(1075,620),(1010,665),(920,660),(860,610),(830,480),(828,300)])
box = hull2 | hull5 | hull0
num = ((L > 58) & (ch < 32)).astype(np.uint8) & box & (1 - jeep) & (1 - flag)
num = cv2.morphologyEx(num, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
num = cv2.morphologyEx(num, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
n, lbl, st, _ = cv2.connectedComponentsWithStats(num)
for i in range(1, n):
    if st[i, cv2.CC_STAT_AREA] < 2500: num[lbl == i] = 0
block = poly([(500,300),(560,275),(760,270),(940,330),(955,480),(930,540),(780,540),(600,520),(500,500)]) & scene & (1 - jeep) & (1 - flag)

np.savez_compressed(out + "/masks.npz", scene=scene, jeep=jeep, flag=flag, pole=pole, num=num, block=block)
ov = rgb.copy().astype(np.float32)
for m, c in [(scene, (0, 90, 255)), (block, (255, 160, 0)), (jeep, (0, 255, 0)), (flag, (255, 0, 255)), (num, (255, 255, 0)), (pole, (255, 0, 0))]:
    ov[m > 0] = ov[m > 0] * 0.55 + np.array(c) * 0.45
Image.fromarray(np.where(al[..., None], ov, 0).astype(np.uint8)).save(out + "/masks_overlay.png")
print({k: int(v.sum()) for k, v in dict(scene=scene, jeep=jeep, flag=flag, num=num, block=block).items()})
