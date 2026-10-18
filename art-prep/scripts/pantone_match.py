#!/usr/bin/env python3
"""Nearest Pantone / Cotton TCX codes for a list of ink colours -> the "inks" block spec_sheet.py reads.

Usage:
  pantone_match.py HEX[,HEX...] [--out inks.json] [--names "AE6232=Burnt orange,616A3E=Olive green"]

Needs node/npm and the offline index (one-time, a few seconds):
  npm install pantone-cli            (in a scratch folder; or use npx)
  npx pantone-cli fetch-index
Matches are CIEDE2000 on the colours measured in the artwork: dE00 under ~3 is very close.
They are STARTING POINTS for the printer, not ink formulas; a physical swatch book decides.
If the person gave Pantone/hex codes, pass those instead of measured colours and say so.
Missing node or index: the script says so and writes the hex-only skeleton so the spec sheet still builds.
"""
import argparse, json, shutil, subprocess, sys

NAMES = {"white": (255, 255, 255), "cream": (250, 247, 238), "light gray": (200, 200, 200), "gray": (128, 128, 128), "charcoal": (46, 50, 51),
         "black": (20, 20, 20), "red": (200, 30, 40), "burnt orange": (174, 98, 50), "orange": (240, 130, 30), "gold": (212, 160, 40),
         "yellow": (245, 215, 40), "olive green": (97, 106, 62), "forest green": (40, 90, 50), "pine green": (49, 62, 52),
         "kelly green": (40, 150, 70), "teal": (30, 130, 130), "sky blue": (110, 170, 220), "royal blue": (40, 70, 170),
         "navy": (25, 40, 90), "slate blue": (53, 93, 113), "purple": (110, 60, 150), "pink": (235, 130, 170),
         "maroon": (110, 25, 40), "brown": (110, 70, 45), "tan": (200, 170, 125)}


def lab(rgb):
    def f(c):
        c /= 255; c = ((c + .055) / 1.055) ** 2.4 if c > .04045 else c / 12.92; return c
    r, g, b = (f(c) for c in rgb)
    x, y, z = (r * .4124 + g * .3576 + b * .1805) / .95047, r * .2126 + g * .7152 + b * .0722, (r * .0193 + g * .1192 + b * .9505) / 1.08883
    t = lambda v: v ** (1 / 3) if v > .008856 else 7.787 * v + 16 / 116
    return 116 * t(y) - 16, 500 * (t(x) - t(y)), 200 * (t(y) - t(z))


def guess_name(rgb):
    l = lab(rgb); return min(NAMES, key=lambda n: sum((a - b) ** 2 for a, b in zip(l, lab(NAMES[n])))).capitalize()


def match(hexv):
    cmd = (["pantone-cli"] if shutil.which("pantone-cli") else ["npx", "--yes", "pantone-cli"]) + [
        "match", "#" + hexv, "--json", "--books", "pantoneSolidCoated,pantoneFhCottonTcx", "--no-relationships"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode: raise RuntimeError(r.stderr.strip()[:300])
    res = {x["book"]["id"]: x for x in json.loads(r.stdout)["results"]}
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("hexes"); ap.add_argument("--out"); ap.add_argument("--names", default="")
    a = ap.parse_args()
    given = dict(p.split("=", 1) for p in a.names.split(",") if "=" in p)
    inks = {}; ok = True
    for h in [x.strip().lstrip("#").upper() for x in a.hexes.split(",") if x.strip()]:
        rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)); e = {"name": given.get(h) or guess_name(rgb), "use": ""}
        try:
            r = match(h); s, t = r["pantoneSolidCoated"], r["pantoneFhCottonTcx"]
            e.update(pms=s["color"]["code"], pms_hex=s["color"]["hex"], de=round(s["deltaE"], 1),
                     tcx=(t["color"]["code"] + " " + (t["color"]["name"] or "")).strip(), tcx_de=round(t["deltaE"], 1))
        except Exception as ex:
            ok = False; e.update(pms="(lookup unavailable)", pms_hex=h, de=0, tcx="", tcx_de=0); print("pantone lookup failed:", ex, file=sys.stderr)
        inks[h] = e; print(h, e["name"], "->", e["pms"], f"dE00 {e['de']}")
    if a.out: json.dump({"inks": inks}, open(a.out, "w"), indent=1)
    if not ok: print("Install: npm install pantone-cli && npx pantone-cli fetch-index", file=sys.stderr)


if __name__ == "__main__":
    main()
