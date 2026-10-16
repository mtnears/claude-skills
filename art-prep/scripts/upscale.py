#!/usr/bin/env python3
"""Upscale 4x without redrawing the art.

Usage:
  upscale.py IN.png OUT.png [--method ai|lanczos] [--weights PATH] [--tile 192]

ai:      Real-ESRGAN x4plus (needs torch + spandrel and the weights file).
         Colour is upscaled by the model; transparency by Lanczos, then the
         edge is re-snapped so the AI pass can't create new ghost pixels.
lanczos: plain resampling; always available; no new detail.

Setup for ai (one time per workspace, ~2-3 GB, several minutes):
  pip install --break-system-packages torch spandrel
  curl -sSL -o RealESRGAN_x4plus.pth \
    https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth
CPU speed: roughly 10-15 s per 192 px tile (a 1536x1024 image is ~48 tiles).
Run it in the background and poll; print lines show progress.
"""
import argparse, os, sys, time
import numpy as np
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--method", choices=["ai", "lanczos"], default="ai")
    ap.add_argument("--weights", default="RealESRGAN_x4plus.pth")
    ap.add_argument("--tile", type=int, default=192)
    ap.add_argument("--lo", type=int, default=16)
    ap.add_argument("--hi", type=int, default=240)
    a_ = ap.parse_args()
    im = Image.open(a_.inp).convert("RGBA")
    W, H = im.size
    S = 4
    a4 = im.getchannel("A").resize((W * S, H * S), Image.LANCZOS)
    if a_.method == "lanczos":
        out = im.resize((W * S, H * S), Image.LANCZOS)
    else:
        import torch
        from spandrel import ModelLoader
        torch.set_num_threads(max(1, os.cpu_count() or 1))
        model = ModelLoader().load_from_file(a_.weights).eval()
        rgb = np.asarray(im.convert("RGB")).astype(np.float32) / 255.0
        x = torch.from_numpy(rgb).permute(2, 0, 1)[None]
        T, P = a_.tile, 16
        res = np.zeros((H * S, W * S, 3), np.float32)
        tiles = [(y, xx) for y in range(0, H, T) for xx in range(0, W, T)]
        t0 = time.time()
        with torch.inference_mode():
            for i, (y, xx) in enumerate(tiles):
                y0, x0 = max(y - P, 0), max(xx - P, 0)
                y1, x1 = min(y + T + P, H), min(xx + T + P, W)
                o = model(x[:, :, y0:y1, x0:x1])[0].permute(1, 2, 0).numpy()
                oy, ox = (y - y0) * S, (xx - x0) * S
                th, tw = min(T, H - y) * S, min(T, W - xx) * S
                res[y * S:y * S + th, xx * S:xx * S + tw] = o[oy:oy + th, ox:ox + tw]
                print(f"tile {i + 1}/{len(tiles)} {time.time() - t0:.0f}s", flush=True)
        out = Image.fromarray((np.clip(res, 0, 1) * 255).round().astype(np.uint8))
        out.putalpha(a4)
    # re-snap alpha so resampling ripples don't add ghost pixels
    a = np.array(out.getchannel("A"))
    a[a < a_.lo] = 0
    a[a >= a_.hi] = 255
    out.putalpha(Image.fromarray(a))
    out.save(a_.out, optimize=True)
    print("done", out.size)


if __name__ == "__main__":
    main()
