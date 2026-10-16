---
name: art-prep
description: Prepare artwork for production without redrawing it - AI-generated images (ChatGPT etc.), logos, and art other people send in. Inspects for print/cut problems (ghost pixels, soft halo edges, specks, white left inside letters by background removal), cleans transparency, upscales faithfully, and builds outputs for UV printing (eufyMake white underbase), print-and-cut and die-cut stickers (Siser Leonardo SVG cut lines with bleed), screen-printing spot-colour separations with underbase, shirts/DTF, decals and web. Always shows a draft for approval before building the package, then offers to archive it. Use whenever someone wants to clean up, upscale, get "high-res" or print-ready files from an image, make a sticker/decal/cut file, prep art for a UV printer or shirt, separate colours for screen printing, fix transparency or white edges, or file finished art - even if they don't say "art prep".
---

# Art prep

Turn a piece of art into production files **from its own pixels**. Nothing is redrawn or
regenerated: every output is computed from the source, so lettering, logos and details
can't drift. That is the point of this skill; an image model asked to "make it high-res"
draws a new picture.

The scripts live in `scripts/` next to this file. Run them with `python3 -I`. They need
numpy, Pillow and OpenCV (`pip install --break-system-packages opencv-python-headless`
if `import cv2` fails). Each script's header documents every option.

## Workflow

### 1. Intake
Get the file into the working directory (attachment, connected folder, or a file the
person names). Ask only what changes the outputs:
- **What it's for:** UV print (eufyMake), print-and-cut sticker (Leonardo), die-cut on
  the art edge, screen print (garment colour, max colours), DTF/DTG shirt, web/social,
  or "send to someone".
- **Physical size** (width in inches) for each use. DPI, cut offsets and chokes depend on it.
- **Where it came from:** AI prompt, the person's own design, or someone else's art
  (for the README; never publish or archive other people's personal details with it).

If they just say "clean it up", inspect first and propose uses from what you find.

### 2. Inspect (read-only)
```
inspect_art.py ART.png OUT/inspect --target-in 4
```
Read `report.md`, then look at `overlay.png` and `islands.png` yourself. Report in plain
words what matters for their use:
- **Art type.** Flat colour (logos, text) vs photographic (gradients, chrome, photos).
  This decides what screen printing and vector cutting can do.
- **Ghost pixels and specks:** nearly invisible pixels that UV printers lay white ink
  under and cutters trace as stray paths. Almost always remove.
- **Halo:** soft edges still tinted with the old background (white fringe on dark art).
  Fix with `--defringe`.
- **Leftover-background islands:** background removal only clears background connected
  to the outside, so white trapped inside letters (A, P, R, 0, 4…) stays opaque.
  `islands.png` shows each candidate as a numbered close-up. Some are leftovers, some
  are real white parts of the design (stripes, highlights, flag squares). **The person
  picks the numbers**; don't guess. The ids only hold for the exact file inspected.
- **Size:** max print size at 150/300 dpi and the DPI at their target width. Under
  ~200 dpi at the target size → offer the upscale.
- If the report says the old background is unknown, ask what colour it was (or skip
  island/halo fixes).

### 3. Propose
State the plan as a short list: which fixes (with the island numbers), which outputs per
use, sizes. Flag anything the art can't do well (see Limits). Wait for a yes.

### 4. Draft for approval
Build only what's needed to judge the look, at native size:
```
clean_alpha.py ART.png OUT/draft/clean.png --speck-px 25 --clear-islands 54,55 --defringe
preview_sheet.py ART.png OUT/draft/clean.png OUT/draft/preview.png
```
plus the use-specific previews (`*_cut_preview.png`, `*_white_check.png`,
`seps_preview.png`). Look at every image yourself before showing it: the zoomed crops
on the preview sheet are where problems show. Send the preview images and ask for
approval or changes. **Don't build the package until the person approves**; design
edits (e.g. a backing bar behind text that vanishes on dark shirts) are iterated here,
one preview at a time.

### 5. Build the package
Only after approval. Run the heavy steps (AI upscale) now, re-apply the same approved
edits to the upscaled file (scale any pixel coordinates by 4), and lay the files out:
```
<Title>/
  00-source/     original exactly as received
  01-master/     cleaned master at native size; 4x master if upscaled
  02-outputs/    one folder per use: uv/, sticker/, screen/, shirt-dtf/, web/
  03-previews/   approval sheet(s)
  README.txt
```
Write a `manifest.json` (fields in `scripts/package.py`) and run
`package.py PKGDIR manifest.json --zip <Title>.zip`. Open the README and a couple of
outputs to check them. Send the ZIP; if it's over ~20 MB and headed for email, say to
share it by link and attach only the native master.

### 6. Archive prompt
Offer to file it in the user's asset folder (`<root>\<client or project>\Artwork\`):
see `references/archive.md` for the layout and rules. Ask once; don't copy anything without a yes.

## Per-use recipes
Read `references/devices.md` for device settings and why. Short version:

| Use | Clean | Output |
|---|---|---|
| UV print (eufyMake) | `--speck-px 25 --hard 128 --dpi <px ÷ inches>` (hard edge: no semi-transparent pixels to put white under; DPI tag = imports at size) | cleaned PNG; `white_layer.py` check file (choke 0 here, software chokes) |
| Print-and-cut sticker (Leonardo) | `--speck-px 25 --hard 128` | `cutline.py --offset-mm 1.5 --border white`: `_print.png` + `_cut.svg` |
| Die-cut on art edge | same | `cutline.py --offset-mm 0 --bleed-mm 1` (only for a solid outline; see Limits) |
| Screen print | `--hard 128` | `separations.py --colors N --garment HEX --underbase` (flat art) |
| DTF/DTG shirt, web | soft edges fine: `--speck-px 25 --defringe` | cleaned PNG / 4x master; previews on light and dark |

`upscale.py IN OUT --method ai` (Real-ESRGAN; setup in its header, ~10-15 s per tile on
CPU, run in background and poll) or `--method lanczos` (always available). Always keep
the lanczos version for a side-by-side check the first time on a new kind of art.

## Limits (say these plainly when they apply)
- **Photographic art and spot colours:** separations posterize gradients into hard
  bands; `separations.py` reports the fit error. Recommend DTF/DTG, or a separation
  program with halftones (simulated process), for photo art.
- **Soft shadows in flat art** become thin hard slivers on a film plate; halftones fix that.
- **Vector cut on ragged art** (brush strokes, spatter, free-floating letters): an
  on-edge cut is messy. Use a border offset (the cut follows a smooth outline).
- **Vector/SVG of the artwork itself** (not the cut line) is not offered for photographic
  art: tracing posterizes it.
- **Upscaling** sharpens edges; it cannot invent detail the source never had.

## Teaching notes
People using this are learning the tooling. When something is found or fixed, say what
it is and why it matters for their device in a sentence ("these 7,800 nearly clear
pixels would each get a dot of white ink"). Keep it short.
