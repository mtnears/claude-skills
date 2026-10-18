#!/usr/bin/env python3
"""Printer spec sheet (PDF) + renamed films for a screen-print separation.
Usage: spec_sheet.py SEPDIR OUTDIR --title T --width-in 11 --garment "..." --job-json job.json
job.json: {"inks": {"AE6232": {"name": "Burnt orange", "pms": "7566 C", "pms_hex": "AD6433", "de": 1.0,
                               "tcx": "17-1340 TCX Adobe", "tcx_de": 2.6, "use": "U and N"}, ...},
           "notes": [...], "questions": [...], "mock": "path/to/mockups_side_by_side.png"}
Films are copied to OUTDIR/films/NN_<name>_<HEX>.tif in print order (light to dark, as the separation script orders them)."""
import argparse, json, os, re, shutil
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black, white, Color
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("sepdir"); ap.add_argument("out")
ap.add_argument("--title", required=True); ap.add_argument("--width-in", type=float, required=True)
ap.add_argument("--garment", default=""); ap.add_argument("--job-json", required=True)
ap.add_argument("--date", default="")
a = ap.parse_args()
job = json.load(open(a.job_json)); sep = json.load(open(os.path.join(a.sepdir, "separations.json")))
os.makedirs(os.path.join(a.out, "films"), exist_ok=True)
pdfmetrics.registerFont(TTFont("DV", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))

DEFAULT_Q = ["Mesh count and ink type you would use for these colours, and any change to the films you want.",
             "Do you want trapping, halftones or registration marks added? None are included.",
             "Is the artwork size and film resolution what you need, and is the print order right?",
             "Do any colours need merging, splitting or re-matching to your inks?"]
rows = []
for n, p in enumerate([p for p in sep["plates"] if "underbase" not in p["plate"]], start=1):
    hx = re.search(r"_([0-9A-Fa-f]{6})\.tif$", p["plate"]).group(1).upper()
    meta = job["inks"][hx]
    safe = re.sub(r"[^A-Za-z0-9]+", "-", meta["name"]).strip("-")
    fn = f"{n:02d}_{safe}_{hx}.tif"
    shutil.copy(os.path.join(a.sepdir, p["plate"]), os.path.join(a.out, "films", fn))
    with Image.open(os.path.join(a.out, "films", fn)) as im:
        W, H = im.size
    rows.append(dict(n=n, hex=hx, rgb=tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4)), cov=p["coverage_pct"], film=fn, **meta))
json.dump({"title": a.title, "width_in": a.width_in, "canvas_px": [W, H], "dpi": sep["dpi"],
           "print_order": [r["film"] for r in rows], "inks": rows}, open(os.path.join(a.out, "films", "films.json"), "w"), indent=2)

PW, PH = letter; M = 40
c = canvas.Canvas(os.path.join(a.out, "printer_spec_sheet.pdf"), pagesize=letter)
c.setTitle(a.title + " - printer spec sheet")
y = PH - M
c.setFont("DVB", 16); c.drawString(M, y - 10, a.title); y -= 26
c.setFont("DV", 9); c.setFillColor(Color(.3, .3, .3))
c.drawString(M, y - 4, f"Screen-print separation, spot colour. Draft for printer review. {a.date}"); y -= 24
c.setFillColor(black)
hh = W / sep["dpi"] if False else None
info = [("Print size", f'{a.width_in:g} in wide x {a.width_in * H / W:.2f} in tall'),
        ("Garment", a.garment),
        ("Inks", f"{len(rows)} spot colours, no halftones, no underbase (light garment)"),
        ("Films", f"{len(rows)} films, all {W} x {H} px at {sep['dpi']} dpi ({W / sep['dpi']:.2f} x {H / sep['dpi']:.2f} in), same canvas so they register by overlay"),
        ("Film polarity", "Black = ink, white = no ink. Hard-edged (no grey). LZW TIFF, 8-bit grey.")]
for k, v in info:
    c.setFont("DVB", 9); c.drawString(M, y, k + ":"); c.setFont("DV", 9)
    # wrap value
    words, line, x0 = v.split(), "", M + 78
    for w_ in words:
        if c.stringWidth(line + " " + w_, "DV", 9) > PW - M - x0: c.drawString(x0, y, line.strip()); y -= 12; line = ""
        line += " " + w_
    c.drawString(x0, y, line.strip()); y -= 14
y -= 6
# table
cols = [("Order", 32), ("Swatch", 36), ("Ink", 126), ("Hex / RGB", 84), ("Pantone Solid Coated", 112), ("Cotton TCX (alt)", 108), ("Cover", 34)]
x = M; c.setFillColor(Color(.92, .92, .92)); c.rect(M, y - 4, sum(w_ for _, w_ in cols), 16, fill=1, stroke=0); c.setFillColor(black)
c.setFont("DVB", 7.5)
for name, w_ in cols: c.drawString(x + 3, y, name); x += w_
y -= 8
for r in rows:
    y -= 30; x = M
    c.setStrokeColor(Color(.8, .8, .8)); c.line(M, y - 6, M + sum(w_ for _, w_ in cols), y - 6)
    c.setFont("DVB", 10); c.drawString(x + 12, y + 8, str(r["n"])); x += cols[0][1]
    c.setFillColor(HexColor("#" + r["hex"])); c.setStrokeColor(black); c.rect(x + 4, y - 2, 28, 22, fill=1, stroke=1); c.setFillColor(black); x += cols[1][1]
    c.setFont("DVB", 8); c.drawString(x + 3, y + 12, r["name"]); c.setFont("DV", 7); c.drawString(x + 3, y + 2, r.get("use", "")); x += cols[2][1]
    c.setFont("DV", 8); c.drawString(x + 3, y + 12, "#" + r["hex"]); c.drawString(x + 3, y + 2, "RGB %d, %d, %d" % r["rgb"]); x += cols[3][1]
    c.setFont("DVB", 8); c.drawString(x + 3, y + 12, "PMS " + r["pms"]); c.setFont("DV", 7); c.drawString(x + 3, y + 2, f"screen #{r['pms_hex']}, dE00 {r['de']:.1f}"); x += cols[4][1]
    c.setFont("DV", 7); c.drawString(x + 3, y + 12, r["tcx"][:26]); c.drawString(x + 3, y + 2, f"dE00 {r['tcx_de']:.1f}"); x += cols[5][1]
    c.setFont("DV", 8); c.drawString(x + 3, y + 8, f"{r['cov']:.1f}%")
y -= 14
c.setFont("DV", 7); c.setFillColor(Color(.3, .3, .3))
foot = ("Print order is light to dark (order 1 first). Hex values are the colours measured in the artwork. Pantone numbers are the nearest match from an offline Pantone "
        "index (CIEDE2000; dE00 under 3 is very close). They are starting points, not ink formulas: please match against a physical swatch book and mix to your own formulas.")
words, line = foot.split(), ""
for w_ in words:
    if c.stringWidth(line + " " + w_, "DV", 7) > PW - 2 * M: c.drawString(M, y, line.strip()); y -= 9; line = ""
    line += " " + w_
c.drawString(M, y, line.strip()); y -= 9
c.setFillColor(black); y -= 8
for head, items in (("Notes", job.get("notes", [])), ("What we would like your feedback on", job.get("questions", DEFAULT_Q))):
    c.setFont("DVB", 10); c.drawString(M, y, head); y -= 13; c.setFont("DV", 8)
    for it in items:
        words, line, first = it.split(), "", True
        for w_ in words:
            if c.stringWidth(line + " " + w_, "DV", 8) > PW - 2 * M - 12: c.drawString(M + (0 if first else 10), y, ("- " if first else "") + line.strip()); y -= 10.5; line = ""; first = False
            line += " " + w_
        c.drawString(M + (0 if first else 10), y, ("- " if first else "") + line.strip()); y -= 12
    y -= 4
if job.get("mock") and os.path.exists(job["mock"]):
    im = Image.open(job["mock"]); iw = PW - 2 * M; ih = iw * im.size[1] / im.size[0]
    if y - ih < M + 10:
        c.showPage(); y = PH - M
    c.setFont("DVB", 10); c.drawString(M, y, "Illustrative mockups (not a colour proof)"); y -= 6
    c.drawImage(ImageReader(im), M, y - ih, width=iw, height=ih)
c.showPage(); c.save()
print("films:", [r["film"] for r in rows]); print("spec sheet written")
