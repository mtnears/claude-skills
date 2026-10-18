---
name: "art-prep"
description: Prepare artwork for production without redrawing it - AI-generated images, logos, and art other people send in. Inspects for print/cut problems, cleans transparency, upscales faithfully, and builds outputs for UV printing (flat, or raised with a custom depth map), print-and-cut and die-cut stickers, screen-print colour separations with Pantone codes and a printer spec sheet, shirts/DTF, decals and web. Asks for the output type, size, colours and (for relief) the look and texture when not given; always shows a draft for approval before building the package, then offers to archive it. Also answers "what can you do?". Use whenever someone wants to clean up, upscale, get "high-res" or print-ready files from an image, make a sticker/decal/cut file, a raised UV depth map or relief, prep art for a UV printer or shirt, separate colours for screen printing, fix transparency or white edges, or file finished art - even if they don't say "art prep".
---

# Art prep

Turn a piece of art into production files **from its own pixels**. Nothing is redrawn or
regenerated: every output is computed from the source, so lettering, logos and details
can't drift. An image model asked to "make it high-res" draws a new picture; this doesn't.

## Setup
- **Scripts** are in `scripts/` next to this file. Run with `python3 -I`. They need numpy,
  Pillow and OpenCV (`pip install --break-system-packages opencv-python-headless` if
  `import cv2` fails); `spec_sheet.py` also needs reportlab. If `scripts/` is missing
  (skill installed without it), look for the person's shared scripts folder (`scripts_home`
  in `config.json`), have them connect it, and copy it into the workspace.
- **Settings** live in `config.json` beside this file (template: `config.example.json`):
  `archive_root` (where finished packages are filed), `scripts_home`, `owner`, `clients`.
  If it's missing, ask once for the archive root and scripts folder, and offer to write it.
  **Never assume someone else's paths.**
- Details per device and per use: `references/devices.md`. Output menu and feasibility:
  `references/outputs.md`. Relief / depth maps: `references/relief.md`. Colours, Pantone,
  garments: `references/colour.md`. Filing: `references/archive.md`.

## "What can you do?" (help)
If asked what this can do, what outputs exist, or how it works: answer from
`references/outputs.md` in a short menu (output types, what each needs from them, what's
not supported and what happens then), then ask what they're making. Offer examples of
finished packages if the archive has any.

## Workflow

### 1. Intake: ask only what changes the outputs
Get the file into the working directory. Then settle, **asking for whatever wasn't said**
(one short message; offer choices and always allow a write-in):
1. **Output type** (if not stated): UV print flat / UV raised with depth map / print-and-cut
   sticker / die-cut / screen print (garment colour, ink count) / DTF-DTG shirt / web /
   "other: tell me". Several are fine.
2. **Physical size** (width in inches) for each use.
3. **Colours** where the output needs them: shirt or background colour (mockups and the
   garment-matching ink), ink colours (screen print). If they give hex, Pantone or other
   codes, use exactly those. If not, **approximate from the art, show the picks as
   swatches, and ask for approval** (see `references/colour.md`). Never block on this.
4. **For relief work** (raised UV, embossing, patch): the **look and feel**: coin, embossed
   patch, faux leather, embroidery, carved wood, paper-cut layers... plus any texture
   (leather grain, wood grain, weave), or "I'll give you my own tier list". Menu in
   `references/relief.md`.
5. **Where it came from** (AI prompt, their own, someone else's) for the README. Keep other
   people's personal details out of it.

If they just say "clean it up", inspect first and propose uses from what you find.

**Output not in the menu?** Don't refuse. Judge feasibility in plain words (what the device
or process needs, whether it can be computed from the art's pixels, what can't be promised),
build it as a one-off if it can be done, and **then ask whether to add it to the skill**
(a short note for `references/outputs.md`; the person decides, you propose the text).

### 2. Inspect (read-only)
```
inspect_art.py ART.png OUT/inspect --target-in 4
```
Read `report.md`, then look at `overlay.png` and `islands.png` yourself. Report in plain
words what matters for their use: art type (flat colour vs photographic, which decides
what screen print and vector cutting can do), ghost pixels and specks (UV printers lay
white ink under them; cutters trace them), halo (soft edges tinted with the old
background: `--defringe`), leftover-background islands (white trapped in letters; **the
person picks the numbers**, ids only hold for the exact file inspected), print size at
150/300 dpi and the dpi at their target width (under ~200 dpi → offer the upscale). If the
old background colour is unknown, ask or skip island/halo fixes.

### 3. Propose
A short list: which fixes, which outputs per use, sizes, colours/look chosen, and anything
the art can't do well (Limits). Wait for a yes.

### 4. Draft for approval
Build only what's needed to judge the look, at native size, and **look at every image
yourself before showing it**:
```
clean_alpha.py ART.png OUT/draft/clean.png --speck-px 25 --clear-islands 54,55 --defringe
preview_sheet.py ART.png OUT/draft/clean.png OUT/draft/preview.png
```
plus the use-specific drafts:
- **Relief:** the region overlay (`make_masks.py`) *then* the height-map draft (`depthmap.py`),
  as two approval steps. See `references/relief.md`.
- **Screen print:** `separations.py` preview, ink swatches with their codes, and a garment
  mockup (`shirt_mockup.py`) on the shirt colour(s) they gave.
- **Sticker / cut:** `*_cut_preview.png`. **UV:** `*_white_check.png`.
Ask for approval or changes. **Don't build the package until they approve**; iterate one
preview at a time.

### 5. Build the package
Run the heavy steps (AI upscale) now and re-apply the same approved edits to the upscaled
file (scale coordinates by 4; masks and depth configs scale automatically). Layout:
```
<Title YYYY-MM>/
  00-source/     original exactly as received, file name ending _ORIGINAL
  01-master/     cleaned master at native size; 4x master if upscaled
  02-outputs/    one folder per use: uv/ (uv/depth/), sticker/, screen/, shirt-dtf/, web/
  03-previews/   approval sheets, mockups
  README.txt
```
- Screen print adds `printer_spec_sheet.pdf` (ink table with Pantone codes, notes, questions
  for the printer, mockups), `films/` named `NN_<ink>_<HEX>.tif` in print order, `films.json`.
- Relief adds `depth/` with the depth map(s) at each print size, and `depth-build/`
  (masks, the tier config and the commands used) so it can be changed and rebuilt later.
- Write `manifest.json` (fields in `scripts/package.py`) and run
  `package.py PKGDIR manifest.json --zip <Title>.zip`. Open the README and a couple of
  outputs. Check every film shares one canvas size.
- Send the ZIP. Over ~20 MB and headed for email: share by link, attach only the native master.

### 6. Archive prompt
Offer to file it at the configured archive root (`references/archive.md`). Ask once;
copy only after a yes. File sizes: the folder tools often cap a file near 30 MB; send the
larger files through the chat file-send first and commit from there.

## Per-use recipes
| Use | Clean | Output |
|---|---|---|
| UV flat (eufyMake) | `--speck-px 25 --hard 128 --dpi <px ÷ inches>` | cleaned PNG at 4x; `white_layer.py --choke-mm 0` check file |
| UV raised + depth map | `--speck-px 50 --hard 128` | colour PNG as above + `depthmap.py` map (black low, white tall) |
| Print-and-cut sticker | `--speck-px 25 --hard 128` | `cutline.py --offset-mm 1.5 --border white`: `_print.png` + `_cut.svg` |
| Die-cut on art edge | same | `cutline.py --offset-mm 0 --bleed-mm 1` (solid outline only) |
| Screen print | `--hard 128` | `separations.py --colors N --garment HEX` (flat art), or `--palette` for chosen inks |
| DTF/DTG shirt, web | `--speck-px 25 --defringe` | cleaned PNG / 4x master; previews on light and dark |

`upscale.py IN OUT --method ai|lanczos`. AI (Real-ESRGAN) needs a one-time install each new
workspace (header of the script), takes ~10-15 s per 192 px tile, so run it in the
background and poll. **The PNG appears before it is fully written; confirm it opens
completely before using it.** Keep the lanczos version for a side-by-side check on new kinds
of art. A container restart kills a running upscale: restart it.

## Gotchas learned on real jobs
- `separations.py --palette`: the garment-matching colour **must be in the palette** (add the
  shirt colour as a no-ink entry) or those pixels get assigned to the nearest ink (a fit
  error near 28 and a huge wrong plate).
- Near-identical darks (charcoal vs deep green) flip pixels between plates. Split them **by
  location** (a region box) rather than by colour, then sweep hairline slivers
  (components under ~150 px at 4x) off the small plates.
- Films must all share one canvas and dpi; print order is light to dark; no trapping,
  halftones or registration marks are added: say so and let the printer ask.
- Pantone matches are approximate (CIEDE2000 on measured colours). The printer confirms
  against a swatch book. Use the person's codes when they have them.
- Depth maps: heights come from what things **are**, never from colour; build masks first and
  approve the overlay; avoid flat white tops (cap ~245) and keep the area outside the art
  pure black; keep bevels and the rim taper so edges aren't cliffs.
- `pkill -f "<pattern>"` inside a command kills its own shell when the command text contains
  the pattern; use PIDs.
- Never write another person's paths or details into their package; use `config.json`.

## Limits (say plainly when they apply)
- **Photographic art and spot colours:** separations posterize gradients into hard bands;
  `separations.py` reports the fit error. Recommend DTF/DTG, or separation software with
  halftones, for photo art.
- **Soft shadows in flat art** become thin hard slivers on a film; halftones fix that.
- **Vector cut on ragged art** (brush strokes, spatter, loose letters): use a border offset.
- **Vector/SVG of the artwork itself** isn't offered for photographic art (tracing posterizes it).
- **Upscaling** sharpens edges; it cannot invent detail the source never had.
- **Depth maps are an interpretation**: the draft/approve loop exists because what should be
  taller is a design decision, and the person makes it.

## Teaching notes
People using this are learning the tooling. When something is found or fixed, say what it is
and why it matters for their device in a sentence ("these 7,800 nearly clear pixels would
each get a dot of white ink"). Keep it short.
